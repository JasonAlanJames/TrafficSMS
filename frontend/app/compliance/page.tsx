import ComplianceTrust from "../../components/ComplianceTrust";
import LegalLayout from "../../components/LegalLayout";

export default function CompliancePage() {
  return (
    <LegalLayout
      title="Compliance & Trust Center"
      description="Learn how TrafficSMS protects your privacy, secures your data, complies with SMS regulations, and delivers trustworthy roadway intelligence."
    >
      <ComplianceTrust />
    </LegalLayout>
  );
}