# plugins
Plugins for Tiles.

## Solstone

Search and read your Solstone journal from Tiles, on the computer where your journal lives.

- [Plugin source](./solstone/)
- [Agent skill](./solstone/skills/solstone-memory/SKILL.md)
- [Download ZIP](https://download.tiles.run/plugins/solstone.zip)
- [Upstream project and setup guide](https://github.com/solpbc/solstone-tiles)

Install version 0.1.1:

```sh
tiles plugin install https://download.tiles.run/plugins/solstone.zip
```

Requires Solstone journal 2.0.24 or later and a Tiles build with plugin support, such as the canary channel, running on the same computer. The plugin connects to the local journal at `http://127.0.0.1:7659/mcp`.

To connect:

1. In your journal, open **agents > connect an agent** and create a pairing code. Choose **on this computer** if asked. If this option is missing, enable agents on this computer first. The code is single-use and expires after 10 minutes.
2. In Tiles chat, enter `/mcp-auth solstone__journal`.
3. On the journal page that opens, choose the journal or facets and at least one kind of material to share, then enter the code and connect. You can change access or disconnect Tiles in the journal's agents app.

If Tiles stays on "Processing..." after connecting, quit and reopen it. The connection is kept.

The `solstone.zip` archive is an unchanged copy of the upstream `solstone-tiles-0.1.1.zip` package, renamed for the catalog. Its SHA-256 is `d82e91e52d332187aeb005ca8b4006a225e6cc3c367f6eb3b2a9b55cb6e48ac1`. It contains `plugin.json`, `mcp.json`, `LICENSE`, and `skills/solstone-memory/SKILL.md` at the archive root.

Maintained by [sol pbc](https://solpbc.org). Licensed under [AGPL-3.0-only](./solstone/LICENSE).

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
