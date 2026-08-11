#!/usr/bin/env python3
"""Read ChatGPT/Codex account usage through the supported Codex app-server API."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RpcError(RuntimeError):
    pass


def bootstrap_root() -> Path:
    override = os.environ.get("GPT_USAGE_CACHE")
    return Path(override) if override else Path(tempfile.gettempdir()) / "gpt-usage-skill"


def bootstrap_binary() -> Path:
    name = "codex.cmd" if platform.system().lower().startswith("win") else "codex"
    return bootstrap_root() / "node_modules" / ".bin" / name


def codex_environment(codex: str) -> dict[str, str]:
    env = os.environ.copy()
    try:
        Path(codex).resolve().relative_to(bootstrap_root().resolve())
    except (OSError, ValueError):
        return env

    auth_dir = bootstrap_root() / "auth"
    auth_dir.mkdir(parents=True, exist_ok=True)
    env["CODEX_HOME"] = str(auth_dir)
    return env


def bootstrap_codex() -> str:
    npm_names = ["npm.cmd", "npm"] if platform.system().lower().startswith("win") else ["npm"]
    npm = next((resolved for name in npm_names if (resolved := shutil.which(name))), None)
    if not npm:
        raise RpcError(
            "Codex is absent and npm is unavailable. This runtime cannot bootstrap the official @openai/codex package."
        )

    root = bootstrap_root()
    root.mkdir(parents=True, exist_ok=True)
    print(f"Installing the official @openai/codex package in temporary cache: {root}", flush=True)
    result = subprocess.run(
        [
            npm,
            "install",
            "--prefix",
            str(root),
            "--no-save",
            "--no-audit",
            "--no-fund",
            "@openai/codex@latest",
        ],
        check=False,
    )
    binary = bootstrap_binary()
    if result.returncode != 0 or not binary.is_file():
        raise RpcError("The official @openai/codex package could not be installed in the temporary cache.")
    return str(binary)


def device_login(codex: str) -> None:
    print(
        "Starting ChatGPT device login. Open the displayed URL and enter the code; this command will continue automatically.",
        flush=True,
    )
    result = subprocess.run(
        [codex, "login", "--device-auth"],
        env=codex_environment(codex),
        check=False,
    )
    if result.returncode != 0:
        raise RpcError("ChatGPT device login did not complete.")


def _running_codex_paths() -> list[str]:
    system = platform.system().lower()
    if system.startswith("win"):
        command = (
            "Get-Process -Name codex -ErrorAction SilentlyContinue | "
            "Where-Object Path | Select-Object -ExpandProperty Path"
        )
        argv = ["powershell.exe", "-NoProfile", "-Command", command]
    else:
        argv = ["ps", "-axo", "comm="]

    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []

    paths = []
    for line in result.stdout.splitlines():
        candidate = line.strip()
        if candidate and "codex" in Path(candidate).name.lower():
            paths.append(candidate)
    return paths


def _known_codex_paths() -> list[str]:
    home = Path.home()
    system = platform.system().lower()
    paths: list[Path] = []

    if system.startswith("win"):
        local = Path(os.environ.get("LOCALAPPDATA", home / "AppData/Local"))
        roaming = Path(os.environ.get("APPDATA", home / "AppData/Roaming"))
        program_files = Path(os.environ.get("ProgramFiles", "C:/Program Files"))
        paths.extend(
            [
                local / "Microsoft/WindowsApps/codex.exe",
                local / "Programs/Codex/resources/codex.exe",
                local / "Codex/resources/codex.exe",
                roaming / "npm/codex.cmd",
                roaming / "npm/codex.exe",
                home / ".local/bin/codex.exe",
                home / ".cargo/bin/codex.exe",
                home / ".bun/bin/codex.exe",
                local / "pnpm/codex.cmd",
                program_files / "Codex/resources/codex.exe",
            ]
        )
        try:
            paths.extend(
                program_files.glob("WindowsApps/OpenAI.Codex_*/app/resources/codex.exe")
            )
        except OSError:
            pass
    elif system == "darwin":
        paths.extend(
            [
                Path("/Applications/Codex.app/Contents/Resources/codex"),
                home / "Applications/Codex.app/Contents/Resources/codex",
                home / "Library/Application Support/Codex/codex",
                Path("/opt/homebrew/bin/codex"),
                Path("/usr/local/bin/codex"),
                home / "Library/pnpm/codex",
            ]
        )
    else:
        paths.extend(
            [
                Path("/opt/Codex/resources/codex"),
                Path("/opt/Codex/codex"),
                Path("/opt/codex/resources/codex"),
                Path("/usr/lib/codex/resources/codex"),
                Path("/usr/lib/codex/codex"),
                Path("/usr/libexec/codex"),
                Path("/usr/local/bin/codex"),
                Path("/usr/bin/codex"),
                Path("/snap/bin/codex"),
                home / ".local/bin/codex",
                home / ".local/share/Codex/resources/codex",
            ]
        )
        uid = getattr(os, "getuid", lambda: 0)()
        for mount_root in (Path("/tmp"), Path("/run/user") / str(uid)):
            try:
                paths.extend(mount_root.glob(".mount_*odex*/resources/codex"))
            except OSError:
                pass

    paths.extend(
        [
            bootstrap_binary(),
            home / ".cargo/bin/codex",
            home / ".npm-global/bin/codex",
            home / ".local/share/pnpm/codex",
            home / ".bun/bin/codex",
            home / "node_modules/.bin/codex",
        ]
    )
    for root in (home / ".nvm/versions/node", home / ".volta/tools/image/node"):
        try:
            paths.extend(root.glob("*/bin/codex"))
        except OSError:
            pass
    return [str(path) for path in paths]


def discover_codex_candidates() -> list[str]:
    candidates: list[str] = []
    override = os.environ.get("CODEX_BIN")
    if override:
        candidates.append(override)

    candidates.extend(_running_codex_paths())

    names = ["codex"]
    if platform.system().lower().startswith("win"):
        names = ["codex.cmd", "codex.exe", "codex"]
    for name in names:
        resolved = shutil.which(name)
        if resolved:
            candidates.append(resolved)

    candidates.extend(_known_codex_paths())
    deduplicated: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        expanded = str(Path(candidate).expanduser())
        key = os.path.normcase(os.path.abspath(expanded))
        try:
            exists = Path(expanded).is_file()
        except OSError:
            exists = False
        if key not in seen and exists:
            seen.add(key)
            deduplicated.append(expanded)
    return deduplicated


def send(proc: subprocess.Popen[str], message: dict[str, Any]) -> None:
    if proc.stdin is None:
        raise RpcError("Codex app-server stdin is not available.")
    proc.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
    proc.stdin.flush()


def recv_until_id(
    proc: subprocess.Popen[str],
    request_id: int,
    timeout_seconds: float,
) -> dict[str, Any]:
    if proc.stdout is None:
        raise RpcError("Codex app-server stdout is not available.")

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                stderr = proc.stderr.read() if proc.stderr else ""
                raise RpcError(f"Codex app-server exited early. {stderr.strip()}")
            continue

        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue

        if message.get("id") == request_id:
            if "error" in message:
                raise RpcError(json.dumps(message["error"], ensure_ascii=False))
            return message.get("result", {})

    raise RpcError(f"Timed out waiting for JSON-RPC response id {request_id}.")


def rpc_call(
    proc: subprocess.Popen[str],
    request_id: int,
    method: str,
    params: dict[str, Any] | None = None,
    timeout_seconds: float = 12,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"id": request_id, "method": method}
    if params is not None:
        payload["params"] = params
    send(proc, payload)
    return recv_until_id(proc, request_id, timeout_seconds)


def start_app_server(codex: str) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [codex, "app-server", "--stdio"],
        env=codex_environment(codex),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def read_account_with(codex: str) -> dict[str, Any]:
    proc = start_app_server(codex)
    try:
        rpc_call(
            proc,
            1,
            "initialize",
            {
                "clientInfo": {
                    "name": "gpt_usage_skill",
                    "title": "GPT Usage Skill",
                    "version": "0.0.1",
                }
            },
        )
        send(proc, {"method": "initialized"})

        account = rpc_call(proc, 2, "account/read", {"refreshToken": False})
        rate_limits = rpc_call(proc, 3, "account/rateLimits/read")

        return {
            "account": account,
            "rate_limits": rate_limits,
            "source": "codex app-server account/rateLimits/read",
            "codex_binary": codex,
        }
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


def read_codex_account() -> dict[str, Any]:
    candidates = discover_codex_candidates()
    if not candidates:
        raise RpcError("Codex was not found in running apps, known install locations, or PATH.")

    failures: list[str] = []
    for candidate in candidates:
        try:
            return read_account_with(candidate)
        except (OSError, RpcError) as exc:
            failures.append(f"{candidate}: {exc}")

    details = " | ".join(failures)
    raise RpcError(f"No discovered Codex installation exposed account rate limits. {details}")


def iso_from_unix(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(float(value), timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def normalize_window(window: dict[str, Any] | None) -> dict[str, Any] | None:
    if not window:
        return None
    used = window.get("usedPercent")
    remaining = None
    if isinstance(used, (int, float)):
        remaining = max(0, min(100, 100 - used))
    return {
        "used_percent": used,
        "remaining_percent": remaining,
        "window_duration_mins": window.get("windowDurationMins"),
        "resets_at": window.get("resetsAt"),
        "resets_at_utc": iso_from_unix(window.get("resetsAt")),
    }


def normalize_bucket(bucket: dict[str, Any]) -> dict[str, Any]:
    return {
        "limit_id": bucket.get("limitId"),
        "limit_name": bucket.get("limitName"),
        "plan_type": bucket.get("planType"),
        "primary": normalize_window(bucket.get("primary")),
        "secondary": normalize_window(bucket.get("secondary")),
        "rate_limit_reached_type": bucket.get("rateLimitReachedType"),
        "credits": bucket.get("credits"),
    }


def normalize(data: dict[str, Any]) -> dict[str, Any]:
    result = data.get("rate_limits", {})
    buckets_by_id = result.get("rateLimitsByLimitId") or {}
    buckets: list[dict[str, Any]] = []

    if isinstance(buckets_by_id, dict) and buckets_by_id:
        for key in sorted(buckets_by_id):
            bucket = buckets_by_id[key]
            if isinstance(bucket, dict):
                buckets.append(normalize_bucket(bucket))
    elif isinstance(result.get("rateLimits"), dict):
        buckets.append(normalize_bucket(result["rateLimits"]))

    account = data.get("account", {})
    account_info = account.get("account") if isinstance(account, dict) else None

    return {
        "source": data.get("source"),
        "codex_binary": data.get("codex_binary"),
        "account": account_info,
        "requires_openai_auth": account.get("requiresOpenaiAuth") if isinstance(account, dict) else None,
        "buckets": buckets,
        "rate_limit_reset_credits": result.get("rateLimitResetCredits"),
        "individual_limit": result.get("individualLimit"),
        "spend_control_reached": result.get("spendControlReached"),
    }


def format_window(label: str, window: dict[str, Any] | None) -> list[str]:
    if not window:
        return [f"  {label}: not returned"]
    remaining = window.get("remaining_percent")
    used = window.get("used_percent")
    duration = window.get("window_duration_mins")
    reset = window.get("resets_at_utc") or window.get("resets_at")
    parts = [f"  {label}: {remaining}% remaining ({used}% used)"]
    if duration is not None:
        parts.append(f", {duration} min window")
    if reset:
        parts.append(f", resets {reset}")
    return ["".join(str(part) for part in parts)]


def format_summary(data: dict[str, Any]) -> str:
    lines: list[str] = []
    account = data.get("account") or {}
    if account:
        details = [str(account.get("type") or "unknown auth")]
        if account.get("email"):
            details.append(str(account["email"]))
        if account.get("planType"):
            details.append(f"plan={account['planType']}")
        lines.append("Account: " + ", ".join(details))

    buckets = data.get("buckets") or []
    if not buckets:
        lines.append("No ChatGPT rate-limit buckets were returned.")
    for bucket in buckets:
        label = bucket.get("limit_name") or bucket.get("limit_id") or "rate limit"
        lines.append(f"{label}:")
        lines.extend(format_window("primary", bucket.get("primary")))
        lines.extend(format_window("secondary", bucket.get("secondary")))
        if bucket.get("rate_limit_reached_type"):
            lines.append(f"  reached: {bucket['rate_limit_reached_type']}")
        if bucket.get("credits") is not None:
            lines.append(f"  credits: {bucket['credits']}")

    reset_credits = data.get("rate_limit_reset_credits")
    if isinstance(reset_credits, dict):
        lines.append(f"Reset credits: {reset_credits.get('availableCount')}")

    if data.get("individual_limit") is not None:
        lines.append(f"Individual limit: {data['individual_limit']}")
    if data.get("spend_control_reached") is not None:
        lines.append(f"Spend control reached: {data['spend_control_reached']}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read ChatGPT/Codex usage from Codex app-server.")
    parser.add_argument("--json", action="store_true", help="Print normalized JSON.")
    parser.add_argument(
        "--list-candidates",
        action="store_true",
        help="List discovered Codex binaries without starting them.",
    )
    parser.add_argument(
        "--device-login",
        action="store_true",
        help="Bootstrap Codex when needed, sign in with a device code, then read usage.",
    )
    parser.add_argument(
        "--bootstrap-only",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()

    if args.list_candidates:
        print("\n".join(discover_codex_candidates()))
        return 0


    if args.bootstrap_only:
        try:
            print(bootstrap_codex())
            return 0
        except RpcError as exc:
            print(f"GPT usage setup failed: {exc}", file=sys.stderr)
            return 2

    if args.device_login:
        try:
            codex = str(bootstrap_binary()) if bootstrap_binary().is_file() else bootstrap_codex()
            device_login(codex)
        except RpcError as exc:
            print(f"GPT usage setup failed: {exc}", file=sys.stderr)
            return 2

    try:
        normalized = normalize(read_codex_account())
    except RpcError as exc:
        print(f"GPT usage unavailable: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(normalized, indent=2, ensure_ascii=False))
    else:
        print(format_summary(normalized))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

