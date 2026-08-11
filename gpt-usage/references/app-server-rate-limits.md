# App Server Rate Limits

Use Codex App Server account APIs as the primary data source.

Relevant JSON-RPC methods:

- `account/read`
- `account/rateLimits/read`
- `account/rateLimits/updated`
- `account/usage/read`
- `account/rateLimitResetCredit/consume`

Important fields:

- `rateLimitsByLimitId.codex` is the preferred Codex/agent bucket when returned.
- `rateLimits` is the backward-compatible single-bucket fallback.
- `primary` and `secondary` may represent different quota windows.
- `usedPercent` is current usage within the quota window.
- `windowDurationMins` is the window length.
- `resetsAt` is a Unix timestamp in seconds.
- Some account types may return only one bucket or omit fields.

Do not read or expose `auth.json`. Let Codex manage ChatGPT login, refresh, and account scoping.
