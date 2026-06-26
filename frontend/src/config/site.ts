export const siteConfig = {
  name: "ContestForge",
  tagline: "Live Contest Platform",
  description:
    "Run timed competitive quizzes at scale. Multi-tenant live contest engine for 10,000+ concurrent participants.",
  url: process.env.NEXT_PUBLIC_APP_URL ?? "https://contestforge.example",
} as const;

export type SiteConfig = typeof siteConfig;
