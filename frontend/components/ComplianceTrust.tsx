import Card from "./Card";
import Section from "./Section";
import Buttons from "./Buttons";
import { siteConfig } from "../lib/site";

export default function ComplianceTrust() {
  return (
    <>
      <Section>
        <p className="pill">Compliance • Security • Privacy</p>

        <h2>
          Compliance & Trust Center
        </h2>

        <p className="muted">
          {siteConfig.productName} is committed to protecting your privacy,
          securing your information, and providing reliable roadway
          intelligence while complying with applicable SMS messaging
          regulations.
        </p>
      </Section>

      {/* Privacy */}

      <Section title="Privacy">
        <div className="grid">

          <Card title="Your Privacy">
            <p>
              {siteConfig.productName} does not sell your personal
              information.
            </p>

            <ul className="features">
              <li>Minimal personal information collected</li>
              <li>Encrypted communications</li>
              <li>Secure account authentication</li>
              <li>User-controlled account deletion</li>
              <li>Privacy-first design</li>
            </ul>
          </Card>

          <Card title="Payment Security">
            <p>
              Subscription billing is securely processed using{" "}
              <strong>{siteConfig.providers.billing}</strong>.
            </p>

            <ul className="features">
              <li>PCI-compliant payment processing</li>
              <li>No payment cards stored by TrafficSMS</li>
              <li>Encrypted checkout sessions</li>
            </ul>
          </Card>

        </div>
      </Section>

      {/* Security */}

      <Section title="Platform Security">

        <div className="grid">

          <Card title="Infrastructure">

            <ul className="features">
              <li>HTTPS / TLS encryption</li>
              <li>Secure authentication</li>
              <li>Password hashing</li>
              <li>Rate limiting</li>
              <li>Cloud-hosted infrastructure</li>
              <li>Continuous monitoring</li>
            </ul>

          </Card>

          <Card title="Messaging">

            <p>
              SMS messaging is delivered through{" "}
              <strong>{siteConfig.providers.sms}</strong>.
            </p>

            <ul className="features">
              <li>Reliable nationwide delivery</li>
              <li>Carrier-compliant messaging</li>
              <li>Opt-in required</li>
              <li>STOP and HELP support</li>
            </ul>

          </Card>

        </div>

      </Section>

      {/* Data Sources */}

      <Section title="Roadway Intelligence">

        <div className="grid">

          <Card title="Official Sources">

            <ul className="features">
              <li>Department of Transportation information</li>
              <li>Road closure notices</li>
              <li>Construction updates</li>
              <li>Official public roadway data</li>
            </ul>

          </Card>

          <Card title="Community Reports">

            <ul className="features">
              <li>Traffic incidents</li>
              <li>Police presence</li>
              <li>Hazards</li>
              <li>Congestion</li>
              <li>Road closures</li>
            </ul>

            <p className="muted">
              Community reports automatically expire to improve reliability.
            </p>

          </Card>

          <Card title="AI Assistance">

            <p>
              Artificial intelligence assists with organizing roadway
              information, summarizing reports, and reducing duplicate
              incidents. AI assists drivers but does not replace safe driving
              decisions.
            </p>

          </Card>

        </div>

      </Section>

      {/* Confidence */}

      <Section title="Report Confidence">

        <Card title="How Confidence Is Determined">

          <p>
            Report confidence may consider factors such as:
          </p>

          <ul className="features">
            <li>Official confirmation</li>
            <li>Multiple independent reports</li>
            <li>Community verification</li>
            <li>Geographic consistency</li>
            <li>Age of report</li>
          </ul>

        </Card>

      </Section>

      {/* SMS Compliance */}

      <Section title="SMS Compliance">

        <div className="grid">

          <Card title="Messaging Compliance">

            <ul className="features">
              <li>{siteConfig.smsHelp}</li>
              <li>{siteConfig.smsStop}</li>
              <li>{siteConfig.smsRates}</li>
              <li>Express consent required before messaging</li>
              <li>TrafficSMS follows applicable TCPA requirements</li>
              <li>TrafficSMS follows CTIA messaging best practices</li>
            </ul>

          </Card>

          <Card title="Supported Region">

            <p>

              Current service availability:

            </p>

            <strong>
              {siteConfig.registration.supportedCountries}
            </strong>

          </Card>

        </div>

      </Section>

      {/* Availability */}

      <Section title="Platform Availability">

        <div className="grid">

          <Card title="24/7 Service">
            <p>
              Core services are designed for continuous availability.
            </p>
          </Card>

          <Card title="Cloud Infrastructure">
            <p>
              Hosted using redundant cloud infrastructure for high reliability.
            </p>
          </Card>

          <Card title="Secure Payments">
            <p>
              Powered by {siteConfig.providers.billing}.
            </p>
          </Card>

        </div>

      </Section>

      {/* User Rights */}

      <Section title="Your Rights">

        <Card title="Account Management">

          <ul className="features">
            <li>Manage your account</li>
            <li>Update your information</li>
            <li>Cancel your subscription</li>
            <li>Opt out of SMS messaging</li>
            <li>Request account deletion</li>
          </ul>

        </Card>

      </Section>

      {/* Contact */}

      <Section title="Need Assistance?">

        <Card title="Support">

          <p>
            Our support team is available to assist with account,
            billing, accessibility, and messaging questions.
          </p>

          <p>
            <strong>Phone:</strong>{" "}
            {siteConfig.contact.phone}
          </p>

          <div className="actionRow">

            <Buttons
              href={siteConfig.contact.page}
            >
              Contact Us
            </Buttons>

            <Buttons
              href="/support"
              variant="secondary"
            >
              Support Center
            </Buttons>

          </div>

        </Card>

      </Section>
    </>
  );
}