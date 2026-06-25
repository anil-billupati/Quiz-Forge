import type { MetadataRoute } from "next";
import { siteConfig } from "@/config/site";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: ["/", "/login", "/terms", "/privacy"],
      disallow: [
        "/super-admin",
        "/org-admin",
        "/participant",
        "/moderator",
        "/api",
        "/_next",
      ],
    },
    sitemap: `${siteConfig.url}/sitemap.xml`,
  };
}
