import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Produces a pruned, self-contained server bundle (.next/standalone) -
  // the Docker image copies just that plus public/ and .next/static,
  // instead of shipping the full node_modules.
  output: "standalone",
};

export default nextConfig;
