import type { Metadata } from "next";

import AccessibilityStatement from "../../components/AccessibilityStatement";
import { createPageMetadata } from "../../lib/metadata";

export const metadata: Metadata = createPageMetadata(
  "Accessibility Statement",
  "Read the TrafficSMS Accessibility Statement and learn about our commitment to providing an accessible experience for all users.",
  "/accessibility"
);

export default function AccessibilityPage() {
  return <AccessibilityStatement />;
}