# Hosting GPT Usage

GPT Usage supports a maintainer-operated default service and self-hosted deployments. Both use the same plugin and MCP implementation.

## Default hosting

Default hosting is intended for people who want to install the plugin and connect from ChatGPT without operating infrastructure.

1. Install the published GPT Usage plugin.
2. Authorize the plugin through its OAuth connection flow.
3. Ask GPT Usage to connect Codex.
4. Open the returned OpenAI device URL and enter the one-time code.
5. Ask GPT Usage to check the connection, then call `get_usage`.

The OAuth token identifies the user to GPT Usage. A hash of its stable `sub` claim selects a dedicated persistent Vercel Sandbox. Codex login state is stored in that sandbox, not in the ChatGPT Work execution container.

Default hosting properties:

- no computer needs to remain online
- mobile Work container IP and filesystem changes do not matter
- one isolated persistent Sandbox per OAuth subject
- 90-day inactive snapshot retention in the current configuration
- the maintainer controls the Vercel project and Sandbox infrastructure

Users should call `disconnect_codex` before abandoning the service. The operator must also provide account deletion, sandbox deletion, incident response, privacy policy, and credential-rotation procedures before public launch.

## Self-hosting on Vercel

Self-hosting keeps the MCP service and persistent Codex sandbox under the user's own Vercel account.

### 1. Configure an OAuth authorization server

The production MCP endpoint requires OAuth. Auth0 is the current reference configuration.

Create an Auth0 API with an audience equal to your public deployment URL, then configure an Auth0 application for the ChatGPT connector. The authorization server must expose standard OIDC/OAuth metadata and JWKS endpoints. Register the redirect URL shown by the ChatGPT plugin builder.

### 2. Configure Vercel

Set these environment variables in Preview and Production:

```text
PEAK_AUTH_MODE=auth0
PEAK_PUBLIC_URL=https://your-project.vercel.app
AUTH0_ISSUER=https://your-tenant.auth0.com/
AUTH0_AUDIENCE=https://your-project.vercel.app
```

Vercel Sandbox authentication uses project OIDC automatically in production. Local Sandbox testing additionally requires Vercel project linkage and pulled development credentials.

### 3. Deploy

```text
npm install
npm run typecheck
npm run build
vercel deploy --prod
```

### 4. Point the plugin at the deployment

Change `plugin/gpt-usage/.mcp.json`:

```json
{
  "mcpServers": {
    "gpt-usage": {
      "url": "https://your-project.vercel.app/api/mcp",
      "auth": "oauth"
    }
  }
}
```

Package or install that plugin build, connect OAuth, and call `connect_codex` once.

## Local development

For a single trusted local client, OAuth verification can be replaced temporarily with a shared bearer secret:

```text
PEAK_AUTH_MODE=shared-secret
PEAK_SHARED_SECRET=use-a-long-random-value
```

Shared-secret mode is not suitable for a public ChatGPT plugin and must not be used for multi-user hosting.

## Data and trust boundaries

The MCP server stores no copied `auth.json` in its own Function filesystem or database. Codex writes and refreshes its own credentials inside the persistent Sandbox selected for that user. The Sandbox filesystem is infrastructure controlled by the Vercel project owner.

Self-hosting reduces trust in the GPT Usage maintainer but does not remove trust in Vercel and OpenAI. Default hosting additionally requires trusting the GPT Usage operator to secure project access, logs, deployment credentials, OAuth configuration, and sandbox lifecycle operations.

## Known constraints

- Device login relies on the official Codex CLI and Codex App Server account surface.
- A sandbox whose persistent state expires or is deleted requires device authorization again.
- Vercel Sandbox usage has compute and snapshot-storage costs.
- Public plugin submission requires working OAuth, domain verification, privacy and terms URLs, support contact details, and review credentials where applicable.
- Standard Chat message limits are separate from Work/Codex agent usage and are not returned.

