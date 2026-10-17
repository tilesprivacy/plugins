# plugins
Plugins for Tiles.

## Cloudflare

Manage Cloudflare resources and Workers projects, and share Tiles inference through account-free Cloudflare Quick Tunnels.

- [Plugin source](./cloudflare/)
- [Agent skill](./cloudflare/skills/cloudflare-cli/SKILL.md)
- [Tiles remote inference skill](./cloudflare/skills/tiles-remote-inference/SKILL.md)
- [Download ZIP](https://download.tiles.run/plugins/cloudflare.zip)
- [Cloudflare CLI setup](https://developers.cloudflare.com/cf/)

Install the plugin:

```sh
tiles plugin install https://download.tiles.run/plugins/cloudflare.zip
```

Restart Tiles after installation, then ask, for example:

```text
@cloudflare List the DNS records for my domain and explain what each record does.
```

The Cloudflare CLI is currently in beta. It requires Node.js 22.18 or newer. Install the official CLI with `npm install --global cf`, then run `cf auth login` and authenticate with access to the account you want to manage. Existing Wrangler authentication is separate. This package supplies agent instructions and a Python inference bridge, not the Cloudflare CLI or an MCP server.

For remote inference, ask:

```text
@tiles-remote-inference Share my Tiles inference server through an unauthenticated Quick Tunnel so I can use it from another device.
```

This workflow requires `cloudflared` and Python 3, with no Cloudflare account, login, domain, or API token. The connector uses Cloudflare's unauthenticated Quick Tunnel API. A bundled loopback bridge exposes only the Responses API and buffers Tiles' SSE into a completed JSON response, because Quick Tunnels do not support live SSE. Use a non-streaming Responses API client; anyone with the temporary URL can call that endpoint. Native Tiles-to-Tiles sharing still uses `tiles remote share` and an Iroh ticket. Named tunnels with Access remain available for streaming or persistent hosting. Installing this plugin does not start a tunnel.

Use `@tiles-remote-inference` to open the sharing skill directly. `@cloudflare` also covers general Cloudflare work. The sharing skill locates its bundled helper through Tiles' agent directory and checks it before setup; no separate script download is needed. After updating the plugin, start a fresh chat to load the revised instructions.

The ZIP follows [Agent Plugins 1.0.0](https://agent-plugins.org/): `plugin.json`, `LICENSE`, and both skill folders under `skills/` are at the archive root. To rebuild it from this repository:

```sh
cd cloudflare
zip -r ../cloudflare.zip plugin.json LICENSE skills
```

Maintained by Tiles Privacy. Cloudflare is a trademark of its respective owner; this is an independent integration.

## Obsidian

Search, read, and organize an Obsidian vault from Tiles using the official Obsidian CLI.

- [Plugin source](./obsidian/)
- [Agent skill](./obsidian/skills/obsidian/SKILL.md)
- [Download ZIP](https://github.com/tilesprivacy/plugins/raw/refs/heads/main/obsidian.zip)
- [Obsidian CLI setup](https://obsidian.md/cli)

Install the plugin:

```sh
tiles plugin install https://github.com/tilesprivacy/plugins/raw/refs/heads/main/obsidian.zip
```

Restart Tiles after installation, then ask, for example:

```text
@obsidian Find my notes about Project Atlas and summarize the open questions.
```

Install a current Obsidian desktop installer, enable **Settings → General → Command line interface**, and register `obsidian` on your PATH. The CLI connects to the desktop app, which must be running. This package supplies agent instructions, not Obsidian or an MCP server.

The ZIP follows [Agent Plugins 1.0.0](https://agent-plugins.org/): `plugin.json`, `LICENSE`, and `skills/obsidian/SKILL.md` are at the archive root. To rebuild it from this repository:

```sh
cd obsidian
zip -r ../obsidian.zip plugin.json LICENSE skills
```

Maintained by Tiles Privacy. Obsidian is a trademark of its respective owner; this is an independent integration.
