import path from "node:path";
import type { NextConfig } from "next";

// The pnpm workspace root (prototype/), where the lockfile and the real
// node_modules live; mock-lender/node_modules only holds symlinks into it.
const workspaceRoot = path.join(__dirname, "..");

const nextConfig: NextConfig = {
  // A self-contained server.js plus only the files it needs, for the Docker
  // image (mock-lender/Dockerfile).
  output: "standalone",
  outputFileTracingRoot: workspaceRoot,
  // cacheComponents: true,
  // partialPrefetching: true,
  turbopack: {
    root: workspaceRoot,
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
