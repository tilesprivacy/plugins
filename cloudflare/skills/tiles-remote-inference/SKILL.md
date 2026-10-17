---
name: tiles-remote-inference
description: Share a local Tiles inference server with another device using account-free Cloudflare Quick Tunnels and a bundled non-streaming Responses API bridge. Use for temporary remote inference, client setup, troubleshooting, and teardown; named tunnels remain an option for streaming or authenticated hosting.
---

# Share Tiles inference through Cloudflare

Use an **unauthenticated Quick Tunnel** by default. No Cloudflare account,
login, managed domain, or API token is required. The host runs Tiles, the
bundled Python bridge, and the official `cloudflared` connector. For a stable
hostname, authenticated access, or live streaming, use the optional
[named tunnel with Access](references/named-tunnel.md) workflow instead.

The connector creates the Quick Tunnel with an unauthenticated
`POST https://api.trycloudflare.com/tunnel`. Let `cloudflared` perform that
request and use the returned temporary connector credentials. Calling the API
alone does not establish a tunnel. Do not print or save those credentials in
the plugin. The raw endpoint is an implementation detail; the documented CLI
is the supported way to create and run the connector.

## Locate the installed helper first

This skill uses the host's available `read` and `bash` tools. It does not
register `cloudflare__` tools. Use the absolute `location` shown for this skill
in the available-skills list or expanded skill message. Its `scripts/` and
`references/` paths are relative to that SKILL.md, not the working directory.

Tiles loads plugin skills directly from the installed plugin directory. It
does not put this helper in a shared `pi/agent/skills` directory. Run this
preflight on the machine running Tiles; it prints the actual paths and checks
that Python can execute the helper without starting a server or tunnel:

```sh
TILES_TUNNEL_AGENT_DIR="${PI_CODING_AGENT_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/tiles/data/pi/agent}"
TILES_TUNNEL_SKILL_DIR="$TILES_TUNNEL_AGENT_DIR/plugins/cloudflare/skills/tiles-remote-inference"
TILES_TUNNEL_BRIDGE="$TILES_TUNNEL_SKILL_DIR/scripts/quick_tunnel_bridge.py"
printf 'Skill: %s\nBridge: %s\n' "$TILES_TUNNEL_SKILL_DIR/SKILL.md" "$TILES_TUNNEL_BRIDGE"
if [ ! -r "$TILES_TUNNEL_BRIDGE" ]; then
  printf 'Helper not readable at this path; check the registered skill location.\n' >&2
  exit 1
fi
python3 "$TILES_TUNNEL_BRIDGE" --help
```

`PI_CODING_AGENT_DIR` is set by Tiles for its agent and already accounts for
custom data locations. The fallback covers a default macOS/Linux installation,
including `XDG_DATA_HOME`. If the environment variable is unavailable and a
custom data location is configured, use the registered skill location instead
of guessing another folder. Outside Tiles, the local daemon can supply only
that data path without displaying the full configuration:

```sh
curl -fsS --max-time 5 http://127.0.0.1:1729/config | python3 -c 'import json,sys; print(json.load(sys.stdin).get("data", {}).get("path", ""))'
```

A nonempty data path contains `pi/agent/plugins/cloudflare/skills/` beneath it;
an empty path means the default above. Never tunnel this configuration endpoint.
If both the registered skill location and the actual installed plugin lack the
helper, check `tiles plugin list`, then repair this plugin with
`tiles plugin install https://download.tiles.run/plugins/cloudflare.zip` and
start a fresh chat so the updated skill is loaded. Do not reinstall repeatedly
or search the entire filesystem. Report an actual tool denial or missing host
access precisely; a wrong path is not evidence that execution is forbidden.

## Choose the receiving client

- Quick Tunnels **do not support Server Sent Events (SSE)**. Use the bundled
  [Python bridge](scripts/quick_tunnel_bridge.py) to consume Tiles' local SSE
  and return a completed JSON response. The receiving client must use the
  **Responses API with streaming disabled**, an explicit model ID, and a
  custom base URL. No Access headers or real API key are required.
- Current native Tiles CLI/UI cannot use an arbitrary HTTPS model endpoint.
  `tiles --remote` expects an **Iroh ticket**, not a tunnel URL. For native
  Tiles-to-Tiles sharing, the host uses `tiles server start` and
  `tiles remote share`; the other device uses `tiles --remote <ticket>`.
  `tiles remote status` and `tiles remote unshare` inspect and stop that share.
  Explain this limitation before setup and do not silently switch transports.
- Chat Completions-only clients are not supported by this bridge. Do not claim
  otherwise without a separately requested and tested adapter.

Establish the host, receiving client, and intended sharing duration. Anyone
with the temporary URL can submit inference requests. A request to share this
public temporary endpoint authorizes the corresponding setup; do not ask again
for that same scope. Editing or installing this skill does not start a tunnel.
Cloudflare terminates HTTPS, so this is not end-to-end encryption that excludes
Cloudflare. Keep prompts and credentials out of shared diagnostics.

## Verify the local origin

Check `tiles --version`, `tiles server --help`, `cloudflared version`,
`cloudflared tunnel --help`, and `python3 --version`. Install missing tools from
their official sources within the requested setup scope. The bridge uses only
Python's standard library. This workflow does not need `cf`, `cf auth login`,
`cloudflared tunnel login`, DNS setup, or an Access application.

Current Tiles inference runs at `http://127.0.0.1:6969`, with `GET /ping` and
`POST /v1/responses`. Confirm the installed version and listener. Port `1729`
is the management daemon, `5173` is the development WebUI, and `18080` is an
internal model backend. Never tunnel those services. Do not point a Quick
Tunnel directly at port `6969`: that would expose management routes and leave
the SSE incompatibility unresolved. Forward only the bridge below.

When requested and needed, start inference with `tiles server start`, then
verify it rather than relying on that command's exit status:

```sh
curl --fail-with-body --max-time 5 http://127.0.0.1:6969/ping
```

Use an already downloaded model's exact Tiles model ID from local selection or
configuration. On the host, this reads only the selected model:

```sh
curl -fsS --max-time 5 http://127.0.0.1:1729/config | jq -er '.model.current // empty'
```

Do not dump the full config, expose `/config`, or assume `/ping` proves the model
works. The daemon must remain running locally for model-cache resolution.
This version has no `/v1/models` or `/v1/chat/completions` on the inference
server. Avoid `/v1/tilekit/model/status` as a passive probe because it may start
inference. Inspect the local `/openapi.json` if the installed API differs.

Warm and verify the model locally with a short `POST /v1/responses` request
using the verified model ID, `"stream": true`, and `"max_output_tokens": 128`.
Require output and a successful `response.completed` event. HTTP 200 alone
is insufficient: failures can arrive as `response.failed` inside the stream.
Resolve local errors before sharing. The current raw `stream:false` handler
returns serialized SSE rather than a normal Responses object; the bridge
converts a completed stream into the expected JSON.

## Start the local bridge

After the preflight and local model checks succeed, launch the bridge with this
self-contained block. Pi's `bash` tool is a one-shot command runner, so start a
separate session with closed input and a private log instead of leaving a
foreground command waiting. Each tool call may start a fresh shell; this block
resolves the installed helper again:

```sh
python3 - <<'PY'
import json, os, pathlib, subprocess, sys, tempfile, time
os.umask(0o077)
agent_dir = pathlib.Path(os.environ.get("PI_CODING_AGENT_DIR") or
    pathlib.Path(os.environ.get("XDG_DATA_HOME", pathlib.Path.home() / ".local/share")) / "tiles/data/pi/agent")
helper = agent_dir / "plugins/cloudflare/skills/tiles-remote-inference/scripts/quick_tunnel_bridge.py"
if not helper.is_file() or not os.access(helper, os.R_OK):
    raise SystemExit(f"Helper is not readable: {helper}; resolve the registered skill location first")
run_dir = pathlib.Path(tempfile.mkdtemp(prefix="tiles-bridge-"))
log_path, pid_file = run_dir / "bridge.log", run_dir / "pid"
command = [sys.executable, str(helper), "--port", "6970"]
with log_path.open("xb") as log:
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
        stderr=subprocess.STDOUT, start_new_session=True)
pid_file.write_text(f"{process.pid}\n")
time.sleep(0.3)
if process.poll() is not None:
    raise SystemExit(f"Bridge PID {process.pid} exited with status {process.returncode}; inspect {log_path}")
(run_dir / "process.txt").write_text(subprocess.check_output(
    ["ps", "-p", str(process.pid), "-o", "pid=,lstart=,args="], text=True))
print(json.dumps({"pid": process.pid, "log": str(log_path), "pid_file": str(pid_file),
    "command": command, "run_dir": str(run_dir), "readiness_verified": False}))
PY
```

If preflight resolved a custom data location without `PI_CODING_AGENT_DIR`, set
that variable to the verified `pi/agent` directory in this same invocation.
Record the returned paths and PID. The short startup check only catches an
early exit; it does not establish listener or model readiness. Read the private
log on failure and correct the error before continuing.

The bridge listens only on `127.0.0.1`, accepts only `POST /v1/responses`, forwards
normal Responses fields without executing tools, and buffers at most 8 MiB.
Requests are limited to 1 MiB, one active inference request, and a 90-second
inference deadline. If port `6970` is occupied, choose an unused local port and
change it consistently in the launch block, local test, and connector URL.
Do not stop an unrelated process.

Create a private `request.json` with the verified model ID:

```json
{
  "model": "MODEL_ID_FROM_HOST",
  "input": "Reply with a short greeting.",
  "stream": false,
  "max_output_tokens": 128
}
```

Test the bridge before creating a public URL:

```sh
curl --fail-with-body --max-time 110 \
  -H 'Content-Type: application/json' \
  --data-binary @request.json http://127.0.0.1:6970/v1/responses
```

Require `application/json`, a response object with `status: "completed"`, and
actual output. The bridge rejects `stream:true`; it always enables streaming
only for its private request to Tiles.

## Create the unauthenticated Quick Tunnel

Only continue after the local bridge inference test above returned a completed
JSON response. This block also checks that its listener still exists, then
launches the connector independently of the one-shot shell:

```sh
python3 - <<'PY'
import json, os, pathlib, shutil, socket, subprocess, tempfile, time
os.umask(0o077)
connector = shutil.which("cloudflared")
if not connector:
    raise SystemExit("cloudflared is not installed or is not on PATH")
with socket.create_connection(("127.0.0.1", 6970), timeout=2):
    pass
run_dir = pathlib.Path(tempfile.mkdtemp(prefix="tiles-quick-tunnel-"))
log_path, pid_file = run_dir / "cloudflared.log", run_dir / "pid"
command = [connector, "tunnel", "--url", "http://127.0.0.1:6970"]
with log_path.open("xb") as log:
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
        stderr=subprocess.STDOUT, start_new_session=True)
pid_file.write_text(f"{process.pid}\n")
time.sleep(0.3)
if process.poll() is not None:
    raise SystemExit(f"Connector PID {process.pid} exited with status {process.returncode}; inspect {log_path}")
(run_dir / "process.txt").write_text(subprocess.check_output(
    ["ps", "-p", str(process.pid), "-o", "pid=,lstart=,args="], text=True))
print(json.dumps({"pid": process.pid, "log": str(log_path), "pid_file": str(pid_file),
    "command": command, "run_dir": str(run_dir), "readiness_verified": False}))
PY
```

This uses the unauthenticated creation API described above. Read the returned
private log path to capture the actual `https://...trycloudflare.com` hostname;
never invent one. The URL may take a few seconds to appear. Check the log again
after a short interval if needed, and report a connector error if it exits.
Do not wait for this long-running process to finish inside the tool call.
A live PID or a printed URL is not proof that public inference works.

Record the connector's run directory for cleanup. Do not install it as a
persistent system service unless requested. Do not add `--allowed-mail`: that
enables browser authentication and does not support this API client flow.

If an existing `cloudflared` configuration prevents Quick Tunnel mode, inspect
current installed help and use an isolated configuration approach that preserves
the user's existing config. Do not delete or overwrite other tunnel settings.

## Verify and use the other device

Replace the placeholder with the hostname actually printed by `cloudflared`:

```sh
curl --fail-with-body --max-time 110 \
  -H 'Content-Type: application/json' \
  --data-binary @request.json \
  https://GENERATED_HOST.trycloudflare.com/v1/responses
```

Configure the receiving client with:

- Base URL: `https://GENERATED_HOST.trycloudflare.com/v1`
- API: Responses, with **streaming disabled**
- Model: the exact verified host model ID
- API key: none; if the client insists on a value, `tiles` is a dummy value and
  provides no authentication or protection

Test the completed response through the public URL. Confirm that management
paths such as `/start`, `/openapi.json`, and `/v1/tilekit/session/list` are
rejected (404 for POST, 405 for GET), and that `stream:true` returns a clear
client error. Verify a request from the receiving device when accessible.
A test from the host alone is not a completed two-device end-to-end test.
The bridge does not enable cross-origin browser requests; do not claim a direct
browser client works without separately testing its CORS requirements.

Keep prompts and output limits small enough to complete within the bridge and
Cloudflare request deadlines. Increasing the client's timeout does not override
the Cloudflare edge timeout. Quick Tunnels have no uptime guarantee and the URL
changes between sessions. For repeated timeouts, required live streaming, or
persistent hosting, explain the [named tunnel option](references/named-tunnel.md)
before switching to its account-based setup. For 502 errors, check the bridge
and local Tiles model first; for 429, wait for the active request to finish.

## Stop sharing

Stop this connector first, then this bridge. For each recorded run directory,
read `pid` and compare `ps -p PID -o pid=,lstart=,args=` with its saved
`process.txt`. Confirm the PID, start time, and command all match before sending
`SIGTERM` to that PID. If the process is gone or the record does not match, do
not signal it. Never use broad `pkill` or `killall` commands that could stop
other shares. Verify each matching process exits, then confirm the old URL no
longer serves inference. Quick Tunnels need no named
tunnel, DNS, or Access resource cleanup. Stop the Tiles inference server only
if this workflow started it and no other work needs it. Leave unrelated services
running. Keep the host awake for the intended session; closing the connector
or sleeping the host interrupts access.

## Official references

- [Quick Tunnels and their limitations](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)
- [Unauthenticated creation API implementation](https://github.com/cloudflare/cloudflared/blob/master/cmd/cloudflared/tunnel/quick_tunnel.go)
- [Cloudflare request timeout](https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/)
- [Tiles manual](https://www.tiles.run/book/manual)
