import Contact from "../../components/Contact";
import LegalLayout from "../../components/LegalLayout";

export default function ContactPage() {
  return (
    <LegalLayout
      title="Contact Us"
      description="Contact the TrafficSMS team for support, billing questions, technical assistance, or general inquiries."
    >
      <Contact />
    </LegalLayout>
  );
}