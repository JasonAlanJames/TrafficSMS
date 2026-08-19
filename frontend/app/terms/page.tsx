import TermsOfService from "../../components/TermsOfService";
import LegalLayout from "../../components/LegalLayout";

export default function TermsPage() {
  return (
    <LegalLayout
      title="Terms of Service"
      description="Terms governing use of TrafficSMS."
    >
      <TermsOfService />
    </LegalLayout>
  );
}