import type { MetadataRoute } from "next";
import { siteConfig } from "../lib/site";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: siteConfig.productName,
    short_name: siteConfig.productName,

    description: siteConfig.description,

    start_url: "/",

    scope: "/",

    display: "standalone",

    orientation: "portrait",

    background_color: "#07111f",

    theme_color: siteConfig.themeColor,

    categories: [
      "navigation",
      "travel",
      "utilities",
    ],

    lang: siteConfig.locale,

    icons: [
      {
        src: "/favicon.ico",
        sizes: "any",
        type: "image/x-icon",
      },
      {
        src: "/android-chrome-192x192.png",
        sizes: "192x192",
        type: "image/png",
      },
      {
        src: "/android-chrome-512x512.png",
        sizes: "512x512",
        type: "image/png",
      },
      {
        src: "/apple-touch-icon.png",
        sizes: "180x180",
        type: "image/png",
      },
    ],
  };
}