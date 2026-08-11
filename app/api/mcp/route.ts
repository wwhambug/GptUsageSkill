import { authenticate, authChallenge, UnauthorizedError } from "@/lib/auth";
import { handleMcp } from "@/lib/mcp";

export const runtime = "nodejs";
export const maxDuration = 300;

export async function POST(request: Request) {
  let subject: string;
  try {
    subject = await authenticate(request);
  } catch (error) {
    if (error instanceof UnauthorizedError) {
      return Response.json({ error: "unauthorized" }, { status: 401, headers: { "WWW-Authenticate": authChallenge() } });
    }
    throw error;
  }

  const rpc = await request.json();
  if (rpc.method === "notifications/initialized") return new Response(null, { status: 202 });
  try {
    const result = await handleMcp(subject, rpc);
    return Response.json({ jsonrpc: "2.0", id: rpc.id ?? null, result });
  } catch (error) {
    return Response.json({
      jsonrpc: "2.0",
      id: rpc.id ?? null,
      error: { code: -32601, message: error instanceof Error ? error.message : "Request failed" },
    });
  }
}

export function OPTIONS() {
  return new Response(null, { status: 204, headers: { Allow: "POST, OPTIONS" } });
}

