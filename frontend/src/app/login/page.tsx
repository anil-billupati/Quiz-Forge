import type { Metadata } from "next";
import LoginForm from "./LoginForm";
import { siteConfig } from "@/config/site";
import {
  OrganizationJsonLd,
  WebSiteJsonLd,
  serializeJsonLd,
} from "@/lib/jsonld";

export const metadata: Metadata = {
  title: "Sign in",
  description: "Sign in to ContestForge to manage or join live contests.",
  alternates: { canonical: "/login" },
  robots: { index: true, follow: true },
  openGraph: {
    url: "/login",
    title: "Sign in | ContestForge",
    description: "Sign in to ContestForge to manage or join live contests.",
    images: ["/opengraph-image.png"],
  },
  twitter: {
    card: "summary_large_image",
    title: "Sign in | ContestForge",
    description: "Sign in to ContestForge to manage or join live contests.",
    images: ["/opengraph-image.png"],
  },
};

export default function LoginPage() {
  const organization: OrganizationJsonLd = {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: siteConfig.name,
    url: siteConfig.url,
    logo: `${siteConfig.url}/logo.png`,
    description: siteConfig.description,
  };

  const website: WebSiteJsonLd = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: siteConfig.name,
    url: siteConfig.url,
    potentialAction: {
      "@type": "SearchAction",
      target: `${siteConfig.url}/?q={search_term_string}`,
      "query-input": "required name=search_term_string",
    },
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: serializeJsonLd(organization) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: serializeJsonLd(website) }}
      />
      <LoginForm />
    </>
  );
}
