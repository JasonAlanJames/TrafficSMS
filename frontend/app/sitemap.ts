import type { MetadataRoute } from "next";
import { siteConfig } from "../lib/site";

export default function sitemap(): MetadataRoute.Sitemap {
  const pages = [
    "",
    "/pricing",
    "/contact",
    "/support",
    "/privacy-policy",
    "/terms",
    "/cookie-policy",
    "/sms-disclosure",
    "/accessibility",
    "/compliance",
    "/login",
    "/dashboard",
    "/sms-opt-in",
  ];

  return pages.map((page) => ({
    url: `${siteConfig.url}${page}`,
    lastModified: new Date(),
    changeFrequency: "weekly",
    priority: page === "" ? 1 : 0.8,
  }));
}