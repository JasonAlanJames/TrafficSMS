import Section from "./Section";
import Card from "./Card";
import { siteConfig } from "../lib/site";

export default function PrivacyPolicy() {
  return (
    <>
      <Section id="privacy-introduction">
        <p className="max-w-3xl text-lg text-slate-300">
          {siteConfig.productName} respects your privacy and is committed to
          protecting your personal information. This Privacy Policy explains
          what information we collect, how we use it, and the choices available
          to you regarding your information.
        </p>
      </Section>

      <Section id="information-collected">
        <div className="grid gap-6 lg:grid-cols-2">
          <Card title="Information We Collect">
            <ul className="list-disc space-y-2 pl-5">
              <li>Account registration information</li>
              <li>Email address</li>
              <li>Phone number</li>
              <li>Traffic alert preferences</li>
              <li>
                Billing information processed securely by{" "}
                {siteConfig.providers.billing}
              </li>
              <li>Usage analytics</li>
              <li>Device and browser information</li>
            </ul>
          </Card>

          <Card title="How We Use Your Information">
            <ul className="list-disc space-y-2 pl-5">
              <li>Deliver requested SMS alerts</li>
              <li>Provide customer support</li>
              <li>Improve platform reliability</li>
              <li>Maintain account security</li>
              <li>Process subscription payments</li>
              <li>Meet legal and regulatory requirements</li>
            </ul>
          </Card>
        </div>
      </Section>

      <Section id="sharing">
        <Card title="Information Sharing">
          <p>
            We do not sell your personal information. Information is shared only
            with trusted service providers necessary to operate the platform,
            including payment processing by {siteConfig.providers.billing}, SMS
            delivery by {siteConfig.providers.sms}, mapping services provided by{" "}
            {siteConfig.providers.maps}, and trusted cloud infrastructure
            providers.
          </p>
        </Card>
      </Section>

      <Section id="security">
        <Card title="Data Security">
          <p>
            We use industry-standard administrative, technical, and physical
            safeguards to protect your information. Communications are encrypted
            using HTTPS, and access to sensitive systems is restricted to
            authorized personnel.
          </p>
        </Card>
      </Section>

      <Section id="cookies">
        <Card title="Cookies &amp; Analytics">
          <p>
            Our website may use cookies and similar technologies to improve your
            browsing experience, remember preferences, and analyze platform
            performance.
          </p>
        </Card>
      </Section>

      <Section id="rights">
        <Card title="Your Privacy Rights">
          <p>
            Depending on your jurisdiction, you may have the right to access,
            correct, delete, or request a copy of your personal information.
            Contact us using the information below for assistance.
          </p>
        </Card>
      </Section>

      <Section id="contact">
        <Card title="Contact Us">
          <p>
            Contact Form:{" "}
            <a
              href={siteConfig.contact.page}
              className="text-cyan-400 hover:underline"
            >
              Contact Us
            </a>
          </p>

          <p>
            Phone:{" "}
            <a
              href={`tel:${siteConfig.contact.phone.replace(/[^\d]/g, "")}`}
              className="text-cyan-400 hover:underline"
            >
              {siteConfig.contact.phone}
            </a>
          </p>

          {siteConfig.contact.address && (
            <p>Address: {siteConfig.contact.address}</p>
          )}

          <p>Company: {siteConfig.organization.legalName}</p>
        </Card>
      </Section>
    </>
  );
}