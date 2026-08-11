import { publicUrl } from "../../../lib/public-url";

export function GET() {
  const issuer = process.env.AUTH0_ISSUER;
  return Response.json({
    resource: publicUrl(),
    authorization_servers: issuer ? [issuer] : [],
    scopes_supported: ["usage:read", "codex:connect"],
    resource_documentation: "https://github.com/wwhambug/GptUsageSkill",
  });
}

