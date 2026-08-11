export function publicUrl(): string {
  if (process.env.PEAK_PUBLIC_URL) return process.env.PEAK_PUBLIC_URL.replace(/\/$/, "");

  const vercelUrl = process.env.VERCEL_PROJECT_PRODUCTION_URL ?? process.env.VERCEL_URL;
  return vercelUrl ? `https://${vercelUrl}` : "http://localhost:3000";
}

