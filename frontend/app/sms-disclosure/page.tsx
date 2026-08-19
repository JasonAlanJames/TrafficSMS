import SMSDisclosure from "../../components/SMSDisclosure";
import LegalLayout from "../../components/LegalLayout";

export default function SMSDisclosurePage() {
  return (
    <LegalLayout
      title="SMS Disclosure"
      description="SMS terms and messaging disclosures."
    >
      <SMSDisclosure />
    </LegalLayout>
  );
}