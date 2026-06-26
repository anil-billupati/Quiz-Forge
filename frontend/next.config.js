/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    // API/WS base URLs are supplied per environment (ADR-003, deployment-agnostic).
    // The current backend serves REST and WebSocket at the root path (no /v1 prefix).
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000",
    NEXT_PUBLIC_WS_BASE_URL: process.env.NEXT_PUBLIC_WS_BASE_URL ?? "ws://localhost:8000",
  },
};

module.exports = nextConfig;
