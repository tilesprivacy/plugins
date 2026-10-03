# plugins
Plugins for Tiles.

## Cloudflare

Manage Cloudflare resources and Workers projects from Tiles using the official Cloudflare CLI.

- [Plugin source](./cloudflare/)
- [Agent skill](./cloudflare/skills/cloudflare/SKILL.md)
- [Download ZIP](https://github.com/tilesprivacy/plugins/raw/refs/heads/main/cloudflare.zip)
- [Cloudflare CLI setup](https://developers.cloudflare.com/cf/)

Install the plugin:

```sh
tiles plugin install https://github.com/tilesprivacy/plugins/raw/refs/heads/main/cloudflare.zip
```

Restart Tiles after installation, then ask, for example:

```text
@cloudflare List the DNS records for my domain and explain what each record does.
```

The Cloudflare CLI is currently in beta. It requires Node.js 22.18 or newer. Install the official CLI with `npm install --global cf`, then run `cf auth login` and authenticate with access to the account you want to manage. Existing Wrangler authentication is separate. This package supplies agent instructions, not the CLI or an MCP server.

The ZIP follows [Agent Plugins 1.0.0](https://agent-plugins.org/): `plugin.json`, `LICENSE`, and `skills/cloudflare/` are at the archive root. To rebuild it from this repository:

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
