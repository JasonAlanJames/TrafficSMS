import type { Metadata } from "next";

import CookiePolicy from "../../components/CookiePolicy";
import { createPageMetadata } from "../../lib/metadata";

export const metadata: Metadata = createPageMetadata(
  "Cookie Policy",
  "Learn how TrafficSMS uses cookies and similar technologies to improve security, performance, and your browsing experience.",
  "/cookie-policy"
);

export default function CookiePolicyPage() {
  return <CookiePolicy />;
}