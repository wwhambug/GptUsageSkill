# GptUsageSkill

GptUsageSkill is an Agent Skill that lets Codex report the current ChatGPT agent usage limits it can see for the signed-in account.

The first version targets the supported Codex App Server account surface:

- `account/read` for the active auth mode and plan
- `account/rateLimits/read` for ChatGPT/Codex rate-limit buckets
- `account/usage/read` for token-activity summaries when requested

It avoids reading `~/.codex/auth.json` directly. Codex owns login, token storage, and refresh.

## Install

Copy or install the `gpt-usage/` folder as a Codex skill.

For local testing, place it in one of Codex's skill locations, for example:

```text
~/.agents/skills/gpt-usage
```

Then ask Codex:

```text
$gpt-usage how much agent usage do I have left?
```

## Requirements

- Codex CLI available on `PATH`
- Signed in with ChatGPT through Codex (`codex login`)
- A Codex version with `codex app-server` and `account/rateLimits/read`

On Windows, the script first looks for the Codex desktop app's bundled CLI. This lets it reuse the desktop app's ChatGPT login even when a separately installed npm CLI is logged out. Set `CODEX_BIN` to override automatic discovery.

API-key-only and Bedrock auth do not provide ChatGPT account rate limits through this path.

## Current Scope

This v0.0.1 reports agent/Codex rate limits from the local Codex account surface. It does not yet provide a hosted ChatGPT Work plugin/MCP server, and it does not scrape private browser sessions.

ChatGPT Work and Codex share agentic usage limits, so this is the right first data source for the shared agent budget. Standard Chat message limits are a separate product surface and are not normalized in this version.

