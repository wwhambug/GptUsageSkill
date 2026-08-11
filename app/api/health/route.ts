export function GET() {
  return Response.json({ ok: true, service: "gpt-usage-mcp", version: "0.2.0" });
}

