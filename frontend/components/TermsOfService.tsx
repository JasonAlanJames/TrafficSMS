import Section from "../components/Section";
import Card from "../components/Card";
import { siteConfig } from "../lib/site";

export default function TermsOfService() {
  return (
    <>
      <Section id="acceptance">
        <p className="max-w-3xl text-lg text-slate-300">
          Welcome to <strong>{siteConfig.organization.product}</strong>. By
          accessing or using this service, you agree to be bound by these Terms
          of Service. If you do not agree with these terms, please discontinue
          use of the service.
        </p>
      </Section>

      <Section id="eligibility">
        <Card title="Eligibility">
          <p>
            You must be legally capable of entering into a binding agreement in{" "}
            {siteConfig.country}. By registering an account, you represent that
            you meet all applicable legal requirements.
          </p>
        </Card>
      </Section>

      <Section id="service-description">
        <Card title="Service Description">
          <p>
            {siteConfig.organization.product} provides real-time traffic alerts,
            roadway intelligence, community traffic reports, police activity,
            traffic incidents, and related SMS-based transportation information.
            Service availability may vary by location and network conditions.
          </p>
        </Card>
      </Section>

      <Section id="accounts">
        <Card title="Accounts">
          <ul className="list-disc space-y-2 pl-5">
            <li>You are responsible for maintaining your account credentials.</li>
            <li>Provide accurate and current registration information.</li>
            <li>You are responsible for all activity under your account.</li>
            <li>
              Notify us immediately of any unauthorized access to your account.
            </li>
          </ul>
        </Card>
      </Section>

      <Section id="sms">
        <Card title="SMS Messaging">
          <ul className="list-disc space-y-2 pl-5">
            <li>{siteConfig.smsHelp}</li>
            <li>{siteConfig.smsStop}</li>
            <li>{siteConfig.smsRates}</li>
            <li>
              SMS delivery depends upon wireless carrier availability and cannot
              be guaranteed.
            </li>
          </ul>
        </Card>
      </Section>

      <Section id="subscriptions">
        <Card title="Subscriptions & Billing">
          <p>
            Paid subscriptions are securely processed through{" "}
            <strong>{siteConfig.providers.billing}</strong>. Subscription fees,
            billing cycles, renewals, cancellations, and refunds are governed
            by your selected subscription plan and applicable law.
          </p>
        </Card>
      </Section>

      <Section id="acceptable-use">
        <Card title="Acceptable Use">
          <ul className="list-disc space-y-2 pl-5">
            <li>Do not misuse or interfere with the service.</li>
            <li>Do not attempt unauthorized access to our systems.</li>
            <li>Do not submit fraudulent or misleading traffic reports.</li>
            <li>
              Use the service only in compliance with applicable laws and
              regulations.
            </li>
          </ul>
        </Card>
      </Section>

      <Section id="availability">
        <Card title="Service Availability">
          <p>
            We strive to provide reliable service; however, uptime,
            notifications, traffic information, and delivery times cannot be
            guaranteed. Features may be modified, suspended, or discontinued at
            any time without prior notice.
          </p>
        </Card>
      </Section>

      <Section id="intellectual-property">
        <Card title="Intellectual Property">
          <p>
            All software, branding, content, logos, graphics, and related
            materials associated with{" "}
            <strong>{siteConfig.organization.product}</strong> remain the
            property of{" "}
            <strong>{siteConfig.organization.legalName}</strong> unless
            otherwise stated.
          </p>
        </Card>
      </Section>

      <Section id="disclaimer">
        <Card title="Disclaimer">
          <p>
            Traffic information is provided for informational purposes only.
            While we strive for accuracy, we do not guarantee that reported
            traffic incidents, police activity, road closures, travel times, or
            community reports are complete, current, or error-free.
          </p>
        </Card>
      </Section>

      <Section id="limitation-liability">
        <Card title="Limitation of Liability">
          <p>
            To the maximum extent permitted by applicable law,{" "}
            {siteConfig.organization.legalName} shall not be liable for any
            indirect, incidental, consequential, special, or punitive damages
            arising from the use or inability to use{" "}
            {siteConfig.organization.product}.
          </p>
        </Card>
      </Section>

      <Section id="termination">
        <Card title="Termination">
          <p>
            We reserve the right to suspend or terminate accounts that violate
            these Terms of Service or engage in fraudulent, abusive, or unlawful
            conduct.
          </p>
        </Card>
      </Section>

      <Section id="changes">
        <Card title="Changes to These Terms">
          <p>
            We may update these Terms of Service periodically. Continued use of{" "}
            {siteConfig.organization.product} following publication of updated
            terms constitutes acceptance of the revised Terms.
          </p>
        </Card>
      </Section>

      <Section id="governing-law">
        <Card title="Governing Law">
          <p>
            These Terms shall be governed by the laws of{" "}
            {siteConfig.state}, {siteConfig.country}, without regard to conflict
            of law principles.
          </p>
        </Card>
      </Section>

      <Section id="contact">
        <Card title="Contact Information">
            <p>
            If you have questions regarding these Terms of Service, please contact us
            through our{" "}
            <a href={siteConfig.contact.page}>Contact Page</a>.
            </p>

            <p>Phone: {siteConfig.contact.phone}</p>

            {siteConfig.contact.address && (
            <p>Address: {siteConfig.contact.address}</p>
            )}

            <p>Company: {siteConfig.organization.legalName}</p>
        </Card>
        </Section>
    </>
  );
}