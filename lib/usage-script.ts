export const USAGE_SCRIPT = String.raw`#!/usr/bin/env python3
import json, shutil, subprocess

def send(p, message):
    p.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
    p.stdin.flush()

def receive(p, request_id):
    while True:
        line = p.stdout.readline()
        if not line:
            raise RuntimeError("app-server exited")
        message = json.loads(line)
        if message.get("id") == request_id:
            if "error" in message:
                raise RuntimeError(json.dumps(message["error"]))
            return message.get("result", {})

codex = shutil.which("codex")
if not codex:
    raise RuntimeError("codex binary missing")
p = subprocess.Popen([codex, "app-server", "--stdio"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
try:
    send(p, {"id":1,"method":"initialize","params":{"clientInfo":{"name":"gpt_usage_plugin","version":"0.2.0"}}})
    receive(p, 1)
    send(p, {"method":"initialized"})
    send(p, {"id":2,"method":"account/read","params":{"refreshToken":True}})
    account = receive(p, 2)
    send(p, {"id":3,"method":"account/rateLimits/read"})
    limits = receive(p, 3)
    info = account.get("account") or {}
    print(json.dumps({"account":{"type":info.get("type"),"planType":info.get("planType")},"rateLimits":limits}, separators=(",", ":")))
finally:
    p.terminate()
`;

