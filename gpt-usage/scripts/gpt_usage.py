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
import time
from datetime import datetime, timezone
from typing import Any


class RpcError(RuntimeError):
    pass


def find_codex() -> str:
    override = os.environ.get("CODEX_BIN")
    if override:
        return override

    desktop_codex = find_running_desktop_codex()
    if desktop_codex:
        return desktop_codex

    names = ["codex"]
    if platform.system().lower().startswith("win"):
        names = ["codex.cmd", "codex.exe", "codex"]

    for name in names:
        resolved = shutil.which(name)
        if resolved:
            return resolved

    raise RpcError("Codex CLI was not found on PATH. Install Codex or set CODEX_BIN.")


def find_running_desktop_codex() -> str | None:
    """Prefer the signed-in Codex desktop binary over a separate npm CLI."""
    if not platform.system().lower().startswith("win"):
        return None

    command = (
        "Get-Process -Name codex -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Path -like '*\\WindowsApps\\OpenAI.Codex_*\\app\\resources\\codex.exe' } | "
        "Select-Object -First 1 -ExpandProperty Path"
    )
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    candidate = result.stdout.strip()
    return candidate if result.returncode == 0 and candidate else None


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


def start_app_server() -> subprocess.Popen[str]:
    codex = find_codex()
    return subprocess.Popen(
        [codex, "app-server", "--stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def read_codex_account() -> dict[str, Any]:
    proc = start_app_server()
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
        }
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


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
    args = parser.parse_args()

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

