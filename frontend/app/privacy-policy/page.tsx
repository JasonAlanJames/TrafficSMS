import PrivacyPolicy from "../../components/PrivacyPolicy";
import LegalLayout from "../../components/LegalLayout";

export default function PrivacyPolicyPage() {
  return (
    <LegalLayout
      title="Privacy Policy"
      description="How TrafficSMS collects, uses, and protects your information."
    >
      <PrivacyPolicy />
    </LegalLayout>
  );
}