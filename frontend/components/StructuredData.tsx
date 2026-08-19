import Script from "next/script";
import { siteConfig } from "../lib/site";

export default function StructuredData() {
  const organization = {
    "@context": "https://schema.org",
    "@type": "Organization",
    "@id": `${siteConfig.url}#organization`,
    name: siteConfig.organization.product,
    legalName: siteConfig.organization.legalName,
    url: siteConfig.url,
    logo: `${siteConfig.url}/android-chrome-512x512.png`,
    telephone: siteConfig.contact.phone,
    address: {
      "@type": "PostalAddress",
      addressRegion: siteConfig.state,
      addressCountry: siteConfig.country,
    },
    contactPoint: {
      "@type": "ContactPoint",
      telephone: siteConfig.contact.phone,
      contactType: "customer support",
      areaServed: "US",
      availableLanguage: "English",
      url: `${siteConfig.url}${siteConfig.contact.page}`,
    },
  };

  const website = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "@id": `${siteConfig.url}#website`,
    url: siteConfig.url,
    name: siteConfig.organization.product,
    description: siteConfig.description,
    publisher: {
      "@id": `${siteConfig.url}#organization`,
    },
  };

  const application = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    "@id": `${siteConfig.url}#software`,
    name: siteConfig.organization.product,
    applicationCategory: "UtilitiesApplication",
    operatingSystem: "Web",
    url: siteConfig.url,
    description: siteConfig.description,
    offers: [
      {
        "@type": "Offer",
        name: "Standard",
        price: "5.99",
        priceCurrency: "USD",
        availability: "https://schema.org/InStock",
      },
      {
        "@type": "Offer",
        name: "Unlimited",
        price: "9.99",
        priceCurrency: "USD",
        availability: "https://schema.org/InStock",
      },
    ],
    provider: {
      "@id": `${siteConfig.url}#organization`,
    },
  };

  const contactPoint = {
    "@context": "https://schema.org",
    "@type": "ContactPoint",
    telephone: siteConfig.contact.phone,
    contactType: "customer support",
    areaServed: "US",
    availableLanguage: "English",
    url: `${siteConfig.url}${siteConfig.contact.page}`,
  };

  return (
    <>
      <Script
        id="organization-schema"
        type="application/ld+json"
        strategy="afterInteractive"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(organization),
        }}
      />

      <Script
        id="website-schema"
        type="application/ld+json"
        strategy="afterInteractive"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(website),
        }}
      />

      <Script
        id="software-schema"
        type="application/ld+json"
        strategy="afterInteractive"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(application),
        }}
      />

      <Script
        id="contact-schema"
        type="application/ld+json"
        strategy="afterInteractive"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(contactPoint),
        }}
      />
    </>
  );
}