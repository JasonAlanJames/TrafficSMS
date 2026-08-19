import type { Metadata } from "next";

import { siteConfig } from "./site";

const productName = siteConfig.organization.product;
const companyName = siteConfig.organization.legalName;

export const defaultMetadata: Metadata = {
  metadataBase: new URL(siteConfig.url),

  title: {
    default: `${productName} | Smarter Traffic Alerts by SMS`,
    template: `%s | ${productName}`,
  },

  description: siteConfig.description,

  applicationName: productName,

  keywords: [
    productName,
    "traffic alerts",
    "SMS traffic alerts",
    "road closures",
    "traffic notifications",
    "traffic reports",
    "commute alerts",
    "highway traffic",
    siteConfig.providers.maps,
    siteConfig.providers.sms,
    siteConfig.state,
    "live traffic",
    "traffic conditions",
    "text message alerts",
    "transportation",
  ],

  authors: [
    {
      name: companyName,
    },
  ],

  creator: companyName,

  publisher: companyName,

  robots: {
    index: true,
    follow: true,
  },

  openGraph: {
    type: "website",
    locale: "en_US",
    url: siteConfig.url,
    siteName: productName,
    title: `${productName} | Smarter Traffic Alerts by SMS`,
    description: siteConfig.description,
    images: [
      {
        url: siteConfig.defaultOgImage,
        width: 1200,
        height: 630,
        alt: productName,
      },
    ],
  },

  twitter: {
    card: "summary_large_image",
    title: `${productName} | Smarter Traffic Alerts by SMS`,
    description: siteConfig.description,
    images: [siteConfig.defaultOgImage],
  },

  alternates: {
    canonical: siteConfig.url,
  },
};

/**
 * Builds page-specific metadata while inheriting the
 * site's global SEO configuration.
 */
export function createPageMetadata(
  title: string,
  description: string,
  pathname: string
): Metadata {
  return {
    title,
    description,

    alternates: {
      canonical: `${siteConfig.url}${pathname}`,
    },

    openGraph: {
      type: "website",
      locale: "en_US",
      url: `${siteConfig.url}${pathname}`,
      siteName: productName,
      title: `${title} | ${productName}`,
      description,
      images: [
        {
          url: siteConfig.defaultOgImage,
          width: 1200,
          height: 630,
          alt: productName,
        },
      ],
    },

    twitter: {
      card: "summary_large_image",
      title: `${title} | ${productName}`,
      description,
      images: [siteConfig.defaultOgImage],
    },
  };
}