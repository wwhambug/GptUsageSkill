import { connectionStatus, disconnect, readUsage, startDeviceLogin } from "./sandbox";

type RpcRequest = { jsonrpc?: string; id?: string | number | null; method?: string; params?: { name?: string; arguments?: unknown } };

const tools = [
  {
    name: "connect_codex",
    title: "Connect Codex account",
    description: "Start a one-time ChatGPT device authorization for GPT Usage. Use when get_usage says the account is not connected.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
  {
    name: "connection_status",
    title: "Check Codex connection",
    description: "Check whether the user's persistent GPT Usage sandbox is signed in to ChatGPT.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
    annotations: { readOnlyHint: true },
  },
  {
    name: "get_usage",
    title: "Get Work and Codex usage",
    description: "Return the signed-in user's shared ChatGPT Work and Codex agent usage windows, reset times, plan, and credits.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
    annotations: { readOnlyHint: true },
  },
  {
    name: "disconnect_codex",
    title: "Disconnect Codex account",
    description: "Remove the user's Codex login from the persistent GPT Usage sandbox.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
    annotations: { destructiveHint: true },
  },
];

function toolResult(value: unknown, isError = false) {
  return {
    content: [{ type: "text", text: JSON.stringify(value) }],
    structuredContent: value,
    ...(isError ? { isError: true } : {}),
  };
}

export async function handleMcp(subject: string, request: RpcRequest) {
  switch (request.method) {
    case "initialize":
      return { protocolVersion: "2025-11-25", capabilities: { tools: {} }, serverInfo: { name: "gpt-usage", version: "0.2.0" } };
    case "ping":
      return {};
    case "tools/list":
      return { tools };
    case "tools/call": {
      try {
        switch (request.params?.name) {
          case "connect_codex": return toolResult(await startDeviceLogin(subject));
          case "connection_status": return toolResult(await connectionStatus(subject));
          case "get_usage": return toolResult(await readUsage(subject));
          case "disconnect_codex": return toolResult(await disconnect(subject));
          default: return toolResult({ error: "Unknown tool" }, true);
        }
      } catch (error) {
        return toolResult({ error: error instanceof Error ? error.message : "Tool failed" }, true);
      }
    }
    default:
      throw new Error(`Method not found: ${request.method}`);
  }
}

