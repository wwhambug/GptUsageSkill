# GPT Usage

GPT Usage is an MCP-backed ChatGPT plugin that reports the agent usage budget shared by ChatGPT Work and Codex on web, desktop, and mobile.

The project is no longer distributed as a standalone skill. The plugin calls a remote MCP service, so mobile does not depend on a temporary Work container containing Codex or retaining its IP and filesystem.

## How it works

```text
ChatGPT plugin
  -> GPT Usage MCP on Vercel
  -> persistent Vercel Sandbox for the OAuth subject
  -> Codex App Server account/rateLimits/read
```

The plugin exposes four tools:

- `connect_codex`: starts one-time ChatGPT device authorization
- `connection_status`: checks whether authorization completed
- `get_usage`: returns Work/Codex usage windows, resets, plan, and credits
- `disconnect_codex`: removes the stored Codex login

Each OAuth user gets an isolated persistent Vercel Sandbox. The sandbox installs the official `@openai/codex` package once and keeps Codex-managed login state across sessions. IP addresses are never used as identity.

## Hosting

- **Default hosting:** use the maintainer-operated MCP URL from the plugin manifest.
- **Self-hosting:** deploy this repository to your own Vercel project and point `.mcp.json` at that deployment.

See [HOSTING.md](HOSTING.md) for setup, authentication, security, and operational differences.

## Development

```text
npm install
npm run typecheck
npm run build
```

Required production configuration is listed in [.env.example](.env.example).

## Security

- The MCP server identifies users from a verified OAuth JWT subject, never an IP address.
- Codex credentials remain inside the user's isolated persistent Sandbox filesystem.
- Tool responses omit email addresses and authentication material.
- Device authorization is completed directly on OpenAI's authorization page.
- The hosting operator still controls the Vercel project and must be treated as a credential custodian. Use self-hosting when that trust model is unacceptable.

## Status

The plugin package, OAuth resource metadata, MCP tools, persistent Sandbox orchestration, device-login flow, and usage reader are implemented. Production default hosting still requires the maintainer's Auth0 tenant and final Vercel deployment configuration.

