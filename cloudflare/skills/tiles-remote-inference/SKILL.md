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

Resolve the script relative to this skill's actual installed location:

```sh
python3 /absolute/path/to/skills/tiles-remote-inference/scripts/quick_tunnel_bridge.py --port 6970
```

Keep it running in a managed foreground session and record its PID. It listens
only on `127.0.0.1`, accepts only `POST /v1/responses`, forwards normal Responses
fields without executing tools, and buffers at most 8 MiB. Requests are limited
to 1 MiB, one active inference request, and a 90-second inference deadline.
If port `6970` is occupied, select an unused local port with `--port` and use
that same port throughout. Do not stop an unrelated process.

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

```sh
cloudflared tunnel --url http://127.0.0.1:6970
```

This uses the unauthenticated creation API described above and prints a random
`https://...trycloudflare.com` hostname. Capture the actual returned URL; never
invent one. Keep the connector running and record its PID. Do not install it
as a persistent system service unless requested. Do not add `--allowed-mail`:
that enables browser authentication and does not support this API client flow.

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

Stop the specific `cloudflared` process started for this share, then the bridge.
Confirm the old URL no longer serves inference. Quick Tunnels need no named
tunnel, DNS, or Access resource cleanup. Stop the Tiles inference server only
if this workflow started it and no other work needs it. Leave unrelated services
running. Keep the host awake for the intended session; closing the connector
or sleeping the host interrupts access.

## Official references

- [Quick Tunnels and their limitations](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)
- [Unauthenticated creation API implementation](https://github.com/cloudflare/cloudflared/blob/master/cmd/cloudflared/tunnel/quick_tunnel.go)
- [Cloudflare request timeout](https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/)
- [Tiles manual](https://www.tiles.run/book/manual)
