# Workers projects and local resources

## Identify the project configuration

Inspect the project's package scripts, installed CLI version, and configuration before running project commands. `cf` projects use `cloudflare.config.ts`. Project commands do not read `wrangler.json`, `wrangler.jsonc`, or `wrangler.toml` and may autoconfigure a new project instead.

For a Wrangler project, retain its existing development and deployment workflow unless migration is part of the user's request. Generated `cf` resource commands can still manage its Cloudflare resources without migrating the project.

If migration is requested, inspect `cf migrate --help`, preview with `cf migrate --dry-run`, and review the proposed changes before applying them. Resolve generated `TODO(@cloudflare)` markers and validate the resulting configuration; do not treat conversion as proof of a working deployment.

## Build and deployment

Use `cf dev --help`, `cf build --help`, and `cf deploy --help` for the installed version. Inspect project scripts before executing them. `cf build` and `cf deploy` do not run `package.json` scripts; preserve required preparation such as type checking or code generation instead of assuming the CLI runs the project's build script. Keep the target account, environment/mode, Worker, bindings, routes, and secrets consistent with the requested deployment.

`cf deploy --dry-run` builds and validates without uploading or calling Cloudflare APIs, but it can execute build code and, for unconfigured projects, autoconfigure, install dependencies, or edit project files. It is not a read-only source inspection. Use it after understanding the project's setup and the authorized work.

For an existing cf project, a build followed by a preview of that exact output can look like:

```sh
cf build
cf deploy --prebuilt --mode production --dry-run
```

Use the mode actually used for the build; `production` is the usual default for Vite builds, not an instruction to choose production for every request. `--prebuilt` consumes `.cloudflare/output` without rebuilding. For output containing multiple Workers, select the intended `--worker NAME`; do not assume every Worker will deploy.

After an authorized preview succeeds, deploy the same reviewed build with matching options and without `--dry-run`. Verify the deployment and its intended endpoint before reporting it live. `cf previews deploy` publishes a preview and has **no dry-run option**; it is an external deployment, not a substitute for validation.

For CI, use a pinned project CLI and Node.js 22.18 or newer, a scoped `CLOUDFLARE_API_TOKEN`, and an explicit `CLOUDFLARE_ACCOUNT_ID`. Do not run interactive login or embed credentials in scripts, logs, or committed files. A cf login on a developer's machine does not configure CI authentication.

## Local resource data

Support for `--local` is command-specific. Inspect help and the official local-resource documentation. Supported families include KV key operations, D1 raw SQL and migrations, and R2 object operations. For local D1 SQL, use the discovered `cf d1 raw` command; `cf d1 query --local` is unsupported. Never drop `--local` to make a failed local operation succeed against production.

Keep any `--persist-to` directory consistent between local commands and the development environment. Local data and remote resources are separate; verify the one the user asked to change.

Official references:

- Projects: https://developers.cloudflare.com/cf/projects/
- Agents and local operation caveats: https://developers.cloudflare.com/cf/agents/
- CI and deployment previews: https://developers.cloudflare.com/cf/ci/
- Wrangler migration: https://developers.cloudflare.com/cf/wrangler/reference/
