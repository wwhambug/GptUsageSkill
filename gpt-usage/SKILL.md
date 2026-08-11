---
name: gpt-usage
description: Check the signed-in user's ChatGPT agent, Work, or Codex usage limits and reset times. Use when the user asks how much Codex, Work, agent, GPT usage, credits, rate limit, quota, or reset capacity remains.
---

# GPT Usage

Use this skill to report the current signed-in ChatGPT agent usage visible to Codex.

Run `scripts/gpt_usage.py` from this skill folder. Prefer the default summary output. Use `--json` only when the user asks for raw or machine-readable output.

Report:

- active account/auth mode when available
- each returned rate-limit bucket
- remaining percentage as `100 - usedPercent`
- reset time when available
- reset-credit count when available
- workspace credits or spend-control state when returned by Codex

If no Codex binary or authenticated App Server is available, run `scripts/gpt_usage.py --device-login`. This bootstraps the official `@openai/codex` package into an OS temporary cache, starts ChatGPT device-code login, and queries usage after login. Relay the verification URL and user code immediately while the command waits. Never run this setup path without the user's request because it downloads a package and starts authentication.

If device login cannot run because npm or outbound network access is unavailable, explain that the runtime blocks the mobile fallback. If `account/rateLimits/read` remains unavailable after login, report the installed Codex version and authentication error.

Allow the script to search running desktop apps, `PATH`, and common installation locations on Windows, macOS, and Linux. It tries every discovered Codex binary until authenticated account limits are returned. Use `CODEX_BIN` only when an explicit binary should be tried first.

Never ask the user for tokens. Never open or print `auth.json`.

