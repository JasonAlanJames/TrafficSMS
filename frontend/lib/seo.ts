import type { Metadata } from "next";

import { defaultMetadata } from "../lib/metadata";

interface SEOOptions {
  title: string;

  description: string;

  path?: string;
}

export function buildMetadata({
  title,
  description,
  path = "",
}: SEOOptions): Metadata {
  return {
    ...defaultMetadata,

    title,

    description,

    alternates: {
      canonical: `${defaultMetadata.metadataBase}${path}`,
    },

    openGraph: {
      ...defaultMetadata.openGraph,

      title,

      description,

      url: `${defaultMetadata.metadataBase}${path}`,
    },

    twitter: {
      ...defaultMetadata.twitter,

      title,

      description,
    },
  };
}