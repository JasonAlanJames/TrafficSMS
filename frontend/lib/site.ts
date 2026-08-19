export const siteConfig = {
  // Branding
  organization: {
    legalName: "JPPM Solutions",
    product: "TrafficSMS",
    foundingDate: "2026",
  },

  // appStore and playStore links
  appStore: "",
  playStore: "",

  url: "https://trafficsms.com",

  siteName: "TrafficSMS",

  locale: "en-US",

  themeColor: "#07111f",

  // Copyright
  copyrightYear: new Date().getFullYear(),

  // Social
  social: {
    twitter: "",
    facebook: "",
    linkedin: "",
    youtube: "",
  },

  // SMS
  smsHelp: "Reply HELP for help.",
  smsStop: "Reply STOP to cancel.",
  smsRates: "Message and data rates may apply.",

  // Contact
  contact: {
    phone: "(844) 793-2020",
    address: "",
    page: "/contact",
  },

  // Forms
  forms: {
    contact: {
      action: "https://formspree.io/f/xoeayloo",
      method: "POST",
      successPage: "/contact/success",
    },
  },

  // Business
  state: "California",
  country: "United States",

  copyrightText: "All Rights Reserved.",

  providers: {
    billing: "Stripe",
    sms: "Twilio",
    maps: "Google Maps Platform",
  },

  registration: {
    supportedCountries: "United States",
  },

  support: {
    areaServed: "US",
    language: "English",
  },

  logo: "/android-chrome-512x512.png",

  version: process.env.NEXT_PUBLIC_APP_VERSION,

  build: process.env.NEXT_PUBLIC_BUILD,

  productName: "TrafficSMS",

  defaultOgImage: "/images/og-image.jpg",

  favicon: "/favicon.ico",

  tagline:
    "Real-time traffic alerts delivered by SMS.",

  description:
    "TrafficSMS delivers real-time traffic alerts, incidents, police activity, and roadway intelligence directly to your phone via SMS.",

};

export const mainNavigation = [
  { label: "Pricing", href: "/pricing" },
  { label: "Contact", href: "/contact" },
  { label: "Compliance & Trust", href: "/compliance" },
];

export const footerSections = [
  {
    title: "Product",
    links: [
      { label: "Home", href: "/" },
      { label: "Pricing", href: "/pricing" },
      { label: "Dashboard", href: "/dashboard" },
      { label: "SMS Opt-In", href: "/sms-opt-in" },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Privacy Policy", href: "/privacy-policy" },
      { label: "Terms of Service", href: "/terms" },
      { label: "SMS Disclosure", href: "/sms-disclosure" },
      { label: "Cookie Policy", href: "/cookie-policy" },
      { label: "Accessibility", href: "/accessibility" },
    ],
  },
  {
    title: "Support",
    supportInfo: [
      {
        label: "Support Hours",
        supportHours: "24/7",
      },
    ],
    links: [
      { label: "Support Center", href: "/support" },
    ],
    contactInfo: [
      {
        phone: siteConfig.contact.phone,
        address: siteConfig.contact.address,
      },
    ],
  },
];