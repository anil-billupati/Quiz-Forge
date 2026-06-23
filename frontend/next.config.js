/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    // API base URL is supplied per environment (ADR-003, deployment-agnostic).
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/v1",
  },
};

module.exports = nextConfig;
