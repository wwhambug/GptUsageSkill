import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  serverExternalPackages: ["@vercel/sandbox"],
  turbopack: { root: process.cwd() },
};

export default nextConfig;

