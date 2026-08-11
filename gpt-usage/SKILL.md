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

If the script reports that Codex is not signed in, ask the user to run `codex login`. If it reports that `account/rateLimits/read` is unavailable, explain that their local Codex version or auth mode does not expose ChatGPT account rate limits.

Allow the script to search running desktop apps, `PATH`, and common installation locations on Windows, macOS, and Linux. It tries every discovered Codex binary until authenticated account limits are returned. Use `CODEX_BIN` only when an explicit binary should be tried first.

Never ask the user for tokens. Never open or print `auth.json`.

