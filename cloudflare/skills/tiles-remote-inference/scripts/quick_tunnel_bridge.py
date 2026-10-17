#!/usr/bin/env python3
"""Buffer Tiles Responses SSE for an unauthenticated, temporary Quick Tunnel.

Only inference is exposed. Anyone with the tunnel URL can submit prompts; keep
the session temporary and stop this process when finished. The bridge does not
log request bodies; upstream services may have their own logging.
"""

import argparse
import http.client
import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM_PORT = 6969
MAX_REQUEST = 1024 * 1024
MAX_RESPONSE = 8 * 1024 * 1024


class BridgeError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def parse_json(data):
    def invalid_constant(value):
        raise ValueError("Non-finite JSON number")
    return json.loads(data, parse_constant=invalid_constant)


def buffered_response(payload, timeout):
    """Read bounded SSE until a successfully completed response is received."""
    connection = http.client.HTTPConnection("127.0.0.1", UPSTREAM_PORT, timeout=timeout)
    expired = threading.Event()
    deadline = time.monotonic() + timeout
    upstream_socket = None
    response = None

    def abort():
        expired.set()
        if upstream_socket is not None:
            try:
                upstream_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    timer = threading.Timer(timeout, abort)
    timer.daemon = True
    timer.start()
    try:
        connection.connect()
        upstream_socket = connection.sock
        if expired.is_set():
            raise BridgeError(504, "Tiles inference timed out")
        payload["stream"] = True
        connection.request("POST", "/v1/responses", json.dumps(payload, allow_nan=False),
                           {"Content-Type": "application/json", "Accept": "text/event-stream"})
        response = connection.getresponse()
        if response.status != 200:
            raise BridgeError(502, "Tiles upstream returned an unsuccessful HTTP status")
        if response.headers.get_content_type() != "text/event-stream":
            raise BridgeError(502, "Tiles upstream did not return an SSE response")
        used, event, data = 0, "", []
        while True:
            if expired.is_set() or time.monotonic() >= deadline:
                raise BridgeError(504, "Tiles inference timed out")
            line = response.readline(MAX_RESPONSE - used + 1)
            used += len(line)
            if used > MAX_RESPONSE:
                raise BridgeError(502, "Tiles response exceeded the buffer limit")
            if not line:
                raise BridgeError(502, "Tiles stream ended without a completed response")
            line = line.decode("utf-8").rstrip("\r\n")
            if line == "":
                if data:
                    message = parse_json("\n".join(data))
                    if not isinstance(message, dict):
                        raise BridgeError(502, "Tiles returned an invalid response event")
                    kind = message.get("type", event)
                    if kind in ("response.failed", "response.incomplete", "error") or event in (
                            "response.failed", "response.incomplete", "error"):
                        raise BridgeError(502, "Tiles inference did not complete successfully")
                    if kind == "response.completed" or event == "response.completed":
                        result = message.get("response")
                        if not isinstance(result, dict) or result.get("status") != "completed":
                            raise BridgeError(502, "Tiles completion did not have a successful status")
                        if expired.is_set() or time.monotonic() >= deadline:
                            raise BridgeError(504, "Tiles inference timed out")
                        return result
                event, data = "", []
            elif not line.startswith(":"):
                field, _, value = line.partition(":")
                value = value[1:] if value.startswith(" ") else value
                if field == "event":
                    event = value
                elif field == "data":
                    data.append(value)
    except BridgeError:
        if expired.is_set():
            raise BridgeError(504, "Tiles inference timed out") from None
        raise
    except (OSError, ValueError, RecursionError, http.client.HTTPException):
        if expired.is_set() or time.monotonic() >= deadline:
            raise BridgeError(504, "Tiles inference timed out") from None
        raise BridgeError(502, "Could not read a valid response from Tiles") from None
    finally:
        timer.cancel()
        if response is not None:
            response.close()
        connection.close()


class BridgeServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port, timeout):
        self.inference_lock = threading.Lock()
        self.inference_timeout = timeout
        super().__init__(("127.0.0.1", port), BridgeHandler)

    def handle_error(self, request, client_address):
        pass  # Never expose request contents or tracebacks in logs.


class BridgeHandler(BaseHTTPRequestHandler):
    def setup(self):
        self.request.settimeout(10)
        super().setup()

    def log_message(self, format, *args):
        pass

    def reply(self, status, body):
        encoded = json.dumps(body, allow_nan=False, ensure_ascii=False).encode("utf-8")
        if status == 200 and len(encoded) > MAX_RESPONSE:
            raise BridgeError(502, "Tiles response exceeded the buffer limit")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(encoded)
        self.close_connection = True

    def do_POST(self):
        locked = False
        try:
            if self.path != "/v1/responses":
                raise BridgeError(404, "Only POST /v1/responses is available")
            if not self.server.inference_lock.acquire(blocking=False):
                raise BridgeError(429, "One inference request is already running; retry later")
            locked = True
            lengths = self.headers.get_all("Content-Length", [])
            if self.headers.get("Transfer-Encoding") or len(lengths) > 1:
                raise BridgeError(400, "Use a single Content-Length; chunked requests are unsupported")
            if not lengths:
                raise BridgeError(411, "Content-Length is required")
            if not lengths[0].isascii() or not lengths[0].isdecimal():
                raise BridgeError(400, "Invalid Content-Length")
            length = int(lengths[0])
            if length > MAX_REQUEST:
                raise BridgeError(413, "Request body exceeds the 1 MiB limit")
            if self.headers.get_content_type() != "application/json":
                raise BridgeError(415, "Content-Type must be application/json")
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise BridgeError(400, "Incomplete request body")
            payload = parse_json(raw)
            if not isinstance(payload, dict):
                raise BridgeError(400, "Request body must be a JSON object")
            if payload.get("stream", False) is not False:
                raise BridgeError(400, "Quick Tunnels require stream:false; this bridge buffers SSE")
            if not isinstance(payload.get("model"), str) or not payload["model"].strip():
                raise BridgeError(400, "A nonempty model name is required")
            if not isinstance(payload.get("input"), (str, list)):
                raise BridgeError(400, "input must be a string or an array")
            self.reply(200, buffered_response(payload, self.server.inference_timeout))
        except (ValueError, RecursionError):
            self.reply(400, {"error": {"message": "Invalid JSON request"}})
        except (TimeoutError, socket.timeout):
            self.reply(408, {"error": {"message": "Request body timed out"}})
        except BridgeError as error:
            self.reply(error.status, {"error": {"message": error.message}})
        finally:
            if locked:
                self.server.inference_lock.release()

    def do_GET(self):
        self.reply(405, {"error": {"message": "Only POST /v1/responses is available"}})

    do_HEAD = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_GET


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=6970, help="Loopback listen port (default: 6970)")
    parser.add_argument("--timeout", type=float, default=90, help="Inference timeout, 1–90 seconds")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535 or not 1 <= args.timeout <= 90:
        parser.error("--port must be 1–65535 and --timeout must be 1–90")
    with BridgeServer(args.port, args.timeout) as server:
        print(f"Inference bridge listening on http://127.0.0.1:{args.port}/v1/responses", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
