# Named tunnel with Cloudflare Access

Use this alternative when the user requests a stable hostname, authenticated
access, or live SSE streaming. It requires a Cloudflare account and managed
domain. Complete the local server and model checks in [SKILL.md](../SKILL.md)
first. Forward the original inference server on loopback port 6969, not the
Quick Tunnel bridge. Create a private `streaming-request.json` with the verified
model ID, a short `input`, `"stream": true`, and `"max_output_tokens": 128`.
The receiving client must support Responses SSE and custom Access headers.

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
```

The first test must match the inference rule; the second must match the final
404. After those checks and the local model test succeed, launch the connector
separately from Pi's one-shot `bash` call. Set and export `TILES_TUNNEL_CONFIG`
and `TILES_TUNNEL_UUID` to the verified private config path and returned tunnel
UUID in this same invocation; shell variables do not persist across tool calls.
Do not use example values or guess a credentials file:

```sh
python3 - <<'PY'
import json, os, pathlib, shutil, subprocess, tempfile, time, uuid
os.umask(0o077)
config_value = os.environ.get("TILES_TUNNEL_CONFIG")
tunnel_value = os.environ.get("TILES_TUNNEL_UUID")
if not config_value or not tunnel_value:
    raise SystemExit("Set TILES_TUNNEL_CONFIG and TILES_TUNNEL_UUID to the verified values")
config = pathlib.Path(config_value).expanduser()
tunnel_id = str(uuid.UUID(tunnel_value))
if not config.is_absolute() or not config.is_file() or not os.access(config, os.R_OK):
    raise SystemExit("The selected tunnel config must be an absolute readable file")
if config.stat().st_mode & 0o077:
    raise SystemExit("Make the selected private config owner-only before starting")
connector = shutil.which("cloudflared")
if not connector:
    raise SystemExit("cloudflared is not installed or is not on PATH")
run_dir = pathlib.Path(tempfile.mkdtemp(prefix="tiles-named-tunnel-"))
log_path, pid_file = run_dir / "cloudflared.log", run_dir / "pid"
command = [connector, "tunnel", "--config", str(config), "run", tunnel_id]
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

Keep the returned run directory for its PID and private log. A surviving process
is not proof of a ready connector or working inference; inspect the log and run
the Access and inference tests below. Do not wait for the connector to finish in
the tool call. Do not install an automatic system service unless persistent
hosting was requested. Never disable origin TLS verification or JWT checks to
fix an error.

## Connect from the other device

Store these headers in a private file with owner-only permissions (`0600`),
using the actual service-token credentials, and set `TILES_ACCESS_HEADERS_FILE`
to its path. Do not display the populated file:

```text
CF-Access-Client-Id: SERVICE_TOKEN_CLIENT_ID
CF-Access-Client-Secret: SERVICE_TOKEN_CLIENT_SECRET
```

With the same safe `streaming-request.json`, test from the receiving device:

```sh
curl --fail-with-body --no-buffer --max-time 120 \
  --header @"$TILES_ACCESS_HEADERS_FILE" \
  -H 'Content-Type: application/json' \
  --data-binary @streaming-request.json https://inference.example.com/v1/responses
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

Read `pid` from this connector's recorded run directory, and compare
`ps -p PID -o pid=,lstart=,args=` with its saved `process.txt`. Only send `SIGTERM`
when the PID, start time, and command match; if it is gone or the record differs,
do not signal another process. Verify exit, then revoke/delete its dedicated
service token. Do not use broad `pkill` or `killall` commands.
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
