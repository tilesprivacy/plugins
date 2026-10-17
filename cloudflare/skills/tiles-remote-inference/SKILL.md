---
name: tiles-remote-inference
description: Share a local Tiles inference server with another device through a named Cloudflare Tunnel and authenticated Access policy. Use when the user wants a protected HTTPS endpoint for Tiles model inference, remote client setup, or tunnel troubleshooting and teardown.
---

# Share Tiles inference through Cloudflare

Provide a protected HTTPS endpoint to the user's local Tiles model. The host
runs Tiles and `cloudflared`; the receiving device uses a Responses API client
that can send Cloudflare Access headers. The plugin supplies instructions, not
a connector binary, proxy, or running tunnel.

## Choose the client and transport

Establish the host, receiving client, Cloudflare account, unused hostname on a
Cloudflare-managed domain, intended access, and sharing duration. Check current
installed help and official docs before changing resources. Preparing this
workflow or installing the plugin does not itself authorize publishing a server.

- Use a **named tunnel** for this workflow. Quick Tunnels do not support Server
  Sent Events (SSE), which Tiles uses for streaming inference.
- A Cloudflare hostname is an HTTPS API endpoint, not a Tiles remote ticket.
  Current Tiles CLI/UI does not accept an arbitrary HTTPS model endpoint. For
  native Tiles-to-Tiles use, explain the supported host commands
  `tiles server start` and `tiles remote share`, then run `tiles --remote <ticket>`
  on the receiving device. `tiles remote status` and `tiles remote unshare`
  inspect and stop that Iroh share. Do not pass a tunnel URL as the ticket or
  silently replace the user's requested Cloudflare workflow.
- An API client must support the **Responses API**, streaming, a manually
  specified model ID, and custom headers. A Chat Completions-only client or a
  client with only a Bearer API-key field is insufficient. Do not claim support
  for those clients without a separately requested, tested adapter.

Cloudflare terminates HTTPS and forwards requests through its network; this
flow is not end-to-end encryption that excludes Cloudflare. Keep prompts and
credentials out of shared diagnostics.

## Verify the local origin

Check `tiles --version`, `tiles server --help`, `cloudflared version`, and
`cloudflared tunnel --help`. Install missing tools from their official sources
only within the requested setup scope. `cloudflared` and `cf` are separate tools
with separate authentication; `cf auth login` does not provision tunnel credentials.

Current Tiles server source uses `http://127.0.0.1:6969` with `GET /ping` and
`POST /v1/responses`. Confirm the installed version and listener first. Port
`1729` is the management daemon, `5173` is the development WebUI, and `18080`
is an internal model backend. Do not forward those services or all of `/v1`.

Start inference with `tiles server start` when requested and needed. Run
`curl --fail-with-body --max-time 5 http://127.0.0.1:6969/ping`, then inspect the local
`/openapi.json` if endpoint/schema discovery is needed. Use an already downloaded
model's exact Tiles model ID from local model selection/configuration. Do not
dump the entire config or assume that a model is available because `/ping` works.
There is no supported `/v1/models` discovery endpoint in this version. On the
host, `curl -fsS --max-time 5 http://127.0.0.1:1729/config | jq -er '.model.current // empty'`
reads only the selected model. Keep this request local; never tunnel `/config`.
Avoid `/v1/tilekit/model/status` as a passive probe because it may start inference.

Create a private `request.json`, substituting that verified model ID:

```json
{
  "model": "MODEL_ID_FROM_HOST",
  "input": "Reply with a short greeting.",
  "stream": true,
  "max_output_tokens": 128
}
```

```sh
curl --fail-with-body --no-buffer --max-time 120 \
  -H 'Content-Type: application/json' \
  --data-binary @request.json http://127.0.0.1:6969/v1/responses
```

Require actual output and a successful `response.completed` event; HTTP 200
alone is insufficient because model failures can arrive as `response.failed`
inside the stream. Keep `stream: true`; do not assume this version's non-stream
response is a normal Responses JSON object. Resolve local errors before tunneling.
The management daemon must remain running locally for model-cache resolution.
The local server has no built-in API-key enforcement; the client value `tiles`
is a placeholder, not a secret that protects the server.

## Protect the hostname before publishing it

Use the user's selected account and zone. Reuse existing resources only after
checking their purpose and scope; do not overwrite unrelated routes or policies.
For API-driven setup, use `cf cli search`, then the selected command's `--help`
and `cf schema` to discover current Access/application/token operations. The
Cloudflare dashboard is also suitable. Do not guess generated CLI flags.

1. Create a self-hosted Cloudflare Access application covering the **entire**
   intended hostname, before adding DNS/routing. Create a dedicated service
   token with an expiry appropriate to the sharing duration. Add a **Service
   Auth** policy whose Include selector is that specific Service Token. Do not
   add Bypass or Everyone rules. Record the application's AUD and team slug.
2. Save the token ID/secret privately on the receiving device, not in the
   plugin, repository, URL, shell history, or output. An interactive email login
   policy alone does not authenticate an API client. Send service-token headers
   on every request.
3. Authenticate the connector with `cloudflared tunnel login` if needed, allowing
   the user to finish sign-in. Verify that an existing connector certificate
   belongs to the selected Cloudflare account before reusing it; `cf` profiles
   do not select `cloudflared` credentials. Use an explicit `--origincert` path
   when needed for multiple accounts. Then create a dedicated tunnel with
   `cloudflared tunnel create tiles-inference`. Record the returned UUID and
   credentials path. Do not overwrite an existing tunnel of that name.

Create a separate private config file. Replace every placeholder with verified
values, retaining the loopback origin, exact path allowlist, JWT check, and 404
fallback. This does not expose `/start`, `/v1/warmup`, `/openapi.json`, or daemon APIs.

```yaml
tunnel: TUNNEL_UUID
credentials-file: /absolute/private/path/TUNNEL_UUID.json
ingress:
  - hostname: inference.example.com
    path: ^/v1/responses$
    service: http://127.0.0.1:6969
    originRequest:
      access:
        required: true
        teamName: ZERO_TRUST_TEAM_SLUG
        audTag:
          - ACCESS_APPLICATION_AUD
  - service: http_status:404
```

Set `TILES_TUNNEL_CONFIG` to that file's absolute path, and replace the example
hostname and UUID below. Validate before publishing DNS or starting the connector:

```sh
cloudflared tunnel --config "$TILES_TUNNEL_CONFIG" ingress validate
cloudflared tunnel --config "$TILES_TUNNEL_CONFIG" ingress rule https://inference.example.com/v1/responses
cloudflared tunnel --config "$TILES_TUNNEL_CONFIG" ingress rule https://inference.example.com/v1/tilekit/session/list
cloudflared tunnel route dns TUNNEL_UUID inference.example.com
cloudflared tunnel --config "$TILES_TUNNEL_CONFIG" run TUNNEL_UUID
```

The first test must match the inference rule; the second must match the final
404. Keep the process foreground or record its specific PID for the requested
session. Do not install an automatic system service unless persistent hosting
was requested. Never disable origin TLS verification or JWT checks to fix an error.

## Connect from the other device

Store these headers in a private file with owner-only permissions (`0600`),
using the actual service-token credentials, and set `TILES_ACCESS_HEADERS_FILE`
to its path. Do not display the populated file:

```text
CF-Access-Client-Id: SERVICE_TOKEN_CLIENT_ID
CF-Access-Client-Secret: SERVICE_TOKEN_CLIENT_SECRET
```

With the same safe `request.json`, test from the receiving device:

```sh
curl --fail-with-body --no-buffer --max-time 120 \
  --header @"$TILES_ACCESS_HEADERS_FILE" \
  -H 'Content-Type: application/json' \
  --data-binary @request.json https://inference.example.com/v1/responses
```

Configure a compatible client with base URL `https://inference.example.com/v1`,
the host's model ID, Responses API, streaming, and both Access headers. The
full HTTP endpoint is `/v1/responses`; avoid adding `/v1` twice. A dummy API key
does not replace Access headers. Do not put service-token secrets in a public
web frontend; use a private native/server client. Direct browser clients may
also need explicitly configured CORS and are not covered by this basic setup.

Verify all three outcomes before calling the share ready:

- Without credentials, the inference request is denied by Access, not forwarded
  to Tiles. A login HTML redirect is not an inference response; do not follow it
  as though it were API authentication.
- With credentials, `/start`, `/openapi.json`, and `/v1/tilekit/session/list`
  return 404, while the allowed response request emits `text/event-stream`,
  useful output, and `response.completed`. Report `response.failed` as failure.
- The same inference request succeeds from the actual receiving device. A test
  run only on the host verifies the public route, not the other device's setup.

If an unauthenticated request reaches inference or an excluded route reaches
the origin, stop this connector immediately and fix the policy or ingress before
restarting. Do not leave a failed protection test running as a usable share.

For 403/login HTML inspect the Access policy, token expiry, and headers; for
502 inspect the local origin and connector; for SSE failures compare local and
remote events and content type. Resolve the cause instead of disabling Access.
Keep the host awake and Tiles inference running for the requested session.

## Stop sharing

Stop only this connector process and revoke/delete its dedicated service token.
For a permanent teardown, remove the dedicated DNS route, then delete the named
tunnel with `cloudflared tunnel delete TUNNEL_UUID`. Remove the Access application
only after routing is gone. Preserve shared resources. Stop Tiles with
`tiles server stop` only if this workflow started it and nothing else needs it.
Report what was removed and whether any intentional persistent resources remain.

## References

- Tiles server commands and Iroh sharing: https://www.tiles.run/book/manual
- Named tunnel setup: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/local-management/create-local-tunnel/
- Access before publishing: https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/
- Service tokens: https://developers.cloudflare.com/cloudflare-one/access-controls/service-credentials/service-tokens/
- Origin Access validation: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/origin-parameters/#access
- Quick Tunnel limitations: https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/#limitations
