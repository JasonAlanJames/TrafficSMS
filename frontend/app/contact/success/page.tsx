import Link from "next/link";

import Card from "../../../components/Card";
import Section from "../../../components/Section";
import { siteConfig } from "../../../lib/site";

export default function ContactSuccessPage() {
  return (
    <>
      <Section id="contact-success">
        <Card title="Message Sent Successfully">
          <div
            style={{
              display: "grid",
              gap: "1.5rem",
            }}
          >
            <p>
              Thank you for contacting{" "}
              <strong>{siteConfig.organization.product}</strong>.
            </p>

            <p>
              Your message has been received successfully. A member of{" "}
              <strong>{siteConfig.organization.legalName}</strong> will review
              your inquiry and respond as soon as possible.
            </p>

            <p>
              If your request is urgent, you may also contact our support team
              by phone.
            </p>

            <div>
              <strong>Support Phone</strong>
              <br />
              {siteConfig.contact.phone}
            </div>

            <div
              style={{
                display: "flex",
                gap: "1rem",
                flexWrap: "wrap",
                marginTop: "0.5rem",
              }}
            >
              <Link
                href="/"
                className="cta"
              >
                Return Home
              </Link>

              <Link
                href="/support"
                className="ghostButton"
              >
                Visit Support Center
              </Link>
            </div>
          </div>
        </Card>
      </Section>
    </>
  );
}