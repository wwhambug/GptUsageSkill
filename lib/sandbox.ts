import { createHash } from "node:crypto";
import { Sandbox } from "@vercel/sandbox";
import { USAGE_SCRIPT } from "./usage-script";

const DEVICE_LOG = "/vercel/sandbox/.peak-device-login.log";
const CODEX_HOME = "/vercel/sandbox/.codex";

function sandboxName(subject: string): string {
  const digest = createHash("sha256").update(subject).digest("hex").slice(0, 32);
  return `gpt-usage-${digest}`;
}

async function userSandbox(subject: string) {
  return Sandbox.getOrCreate({
    name: sandboxName(subject),
    runtime: "node24",
    timeout: 5 * 60 * 1000,
    snapshotExpiration: 90 * 24 * 60 * 60 * 1000,
    env: { CODEX_HOME },
    onCreate: async (sandbox) => {
      const install = await sandbox.runCommand("npm", ["install", "-g", "@openai/codex@latest"]);
      if (install.exitCode !== 0) throw new Error(`Codex install failed: ${await install.stderr()}`);
      await sandbox.writeFiles([
        { path: "/vercel/sandbox/read_usage.py", content: Buffer.from(USAGE_SCRIPT) },
      ]);
    },
  });
}

export async function connectionStatus(subject: string) {
  const sandbox = await userSandbox(subject);
  const result = await sandbox.runCommand("codex", ["login", "status"]);
  const output = `${await result.stdout()}\n${await result.stderr()}`.trim();
  return { connected: result.exitCode === 0, status: output };
}

export async function startDeviceLogin(subject: string) {
  const current = await connectionStatus(subject);
  if (current.connected) return { status: "connected" as const };

  const sandbox = await userSandbox(subject);
  await sandbox.runCommand({
    cmd: "sh",
    args: ["-lc", `: > ${DEVICE_LOG}; codex login --device-auth > ${DEVICE_LOG} 2>&1`],
    detached: true,
  });

  const deadline = Date.now() + 20_000;
  while (Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, 500));
    try {
      const buffer = await sandbox.readFileToBuffer({ path: DEVICE_LOG });
      if (!buffer) continue;
      const log = buffer.toString("utf8");
      const verificationUrl = log.match(/https:\/\/auth\.openai\.com\/codex\/device\S*/)?.[0];
      const userCode = log.match(/\b[A-Z0-9]{4}-[A-Z0-9]{4}\b/)?.[0];
      if (verificationUrl && userCode) {
        return { status: "authorization_required" as const, verificationUrl, userCode };
      }
    } catch {
      // The detached command may not have created the log yet.
    }
  }
  throw new Error("Device login started but no verification code was produced");
}

export async function readUsage(subject: string) {
  const status = await connectionStatus(subject);
  if (!status.connected) return { connected: false, action: "Call connect_codex first" };

  const sandbox = await userSandbox(subject);
  const result = await sandbox.runCommand("python3", ["/vercel/sandbox/read_usage.py"]);
  if (result.exitCode !== 0) throw new Error((await result.stderr()).trim() || "Usage read failed");
  return { connected: true, ...(JSON.parse(await result.stdout()) as object) };
}

export async function disconnect(subject: string) {
  const sandbox = await userSandbox(subject);
  const result = await sandbox.runCommand("codex", ["logout"]);
  await sandbox.stop();
  return { disconnected: result.exitCode === 0 };
}

