# GptUsageSkill

Check the shared ChatGPT Work and Codex agent usage limit from the account already signed in to Codex.

## Install and use

Install the `gpt-usage/` folder as a Codex skill, for example at:

```text
~/.agents/skills/gpt-usage
```

In ChatGPT Work, ask it to install the skill from `wwhambug/GptUsageSkill`. Then run:

```text
$gpt-usage how much Work/Codex agent usage do I have left?
```

Example:

```text
Account: chatgpt, plan=plus
codex:
  primary: 96% remaining (4% used), 10080 min window
  secondary: not returned
  credits: balance 0
```

## How it works

The single `gpt_usage.py` script discovers an authenticated Codex installation and calls the local Codex App Server account API:

- `account/read` for the active account and plan
- `account/rateLimits/read` for usage windows, reset times, and credits

It searches Windows, macOS, and Linux across running desktop apps, `PATH`, and common desktop, npm, pnpm, bun, Cargo, Homebrew, NVM, Volta, AppImage, Snap, and system install locations. It tries every discovered binary until one returns authenticated account limits.

If a mobile or headless Work container has no Codex installation, the same file can bootstrap the official CLI and start device-code login:

```text
python gpt_usage.py --device-login
```

The temporary CLI and Codex-managed login state are stored under the OS temporary directory, not in the repository. This fallback requires npm, outbound package access, and completion of the displayed ChatGPT device login.

**Security:** The skill never opens the token file or asks for OAuth credentials. Authentication and token refresh remain owned by Codex.

## Verified surfaces

- Codex desktop on Windows
- ChatGPT Work hosted container with the current user's OAuth identity preserved
- Mobile/headless Work containers after temporary CLI bootstrap and device-code login, when the runtime permits npm and outbound access

ChatGPT Work and Codex use the same agent usage budget, so the returned `codex` bucket represents the shared Work/Codex allowance.

## Limitations

- Some accounts return only one rate-limit bucket; a secondary bucket may be absent.
- API-key-only and Bedrock authentication do not expose ChatGPT account rate limits through this API.
- Standard Chat message limits are separate from agent usage and are not reported.
- The skill depends on Codex App Server account methods and may require updates if that interface changes.
- Mobile fallback cannot run in containers that block npm, outbound network access, or device authentication.

