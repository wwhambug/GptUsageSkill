import { createRemoteJWKSet, jwtVerify } from "jose";

import { publicUrl } from "./public-url";

export class UnauthorizedError extends Error {}

function bearerToken(request: Request): string {
  const value = request.headers.get("authorization") ?? "";
  if (!value.startsWith("Bearer ")) throw new UnauthorizedError("Bearer token required");
  return value.slice(7);
}

export async function authenticate(request: Request): Promise<string> {
  const mode = process.env.PEAK_AUTH_MODE ?? "auth0";
  const token = bearerToken(request);

  if (mode === "shared-secret") {
    if (!process.env.PEAK_SHARED_SECRET || token !== process.env.PEAK_SHARED_SECRET) {
      throw new UnauthorizedError("Invalid shared secret");
    }
    return "self-hosted-user";
  }

  const issuer = process.env.AUTH0_ISSUER;
  const audience = process.env.AUTH0_AUDIENCE;
  if (!issuer || !audience) throw new Error("AUTH0_ISSUER and AUTH0_AUDIENCE are required");
  const normalizedIssuer = issuer.endsWith("/") ? issuer : `${issuer}/`;
  const jwks = createRemoteJWKSet(new URL(`${normalizedIssuer}.well-known/jwks.json`));
  const { payload } = await jwtVerify(token, jwks, { issuer: normalizedIssuer, audience });
  if (!payload.sub) throw new UnauthorizedError("OAuth token has no subject");
  return payload.sub;
}

export function authChallenge(): string {
  return `Bearer resource_metadata="${publicUrl()}/.well-known/oauth-protected-resource"`;
}

