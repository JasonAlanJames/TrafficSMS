import Section from "./Section";
import Card from "./Card";
import { siteConfig } from "../lib/site";

export default function Support() {
  return (
    <>
      <Section id="support-introduction">
        <p className="max-w-3xl text-lg text-slate-300">
          {siteConfig.organization.product} is committed to providing reliable
          customer support. If you need assistance with your account,
          subscriptions, SMS alerts, billing, or technical issues, our support
          team is here to help.
        </p>
      </Section>

      <Section id="support-services">
        <div className="grid gap-6 lg:grid-cols-2">
          <Card title="How We Can Help">
            <ul className="list-disc space-y-2 pl-5">
              <li>Account registration assistance</li>
              <li>Password reset assistance</li>
              <li>Subscription and billing questions</li>
              <li>SMS delivery troubleshooting</li>
              <li>Traffic alert questions</li>
              <li>Technical support</li>
              <li>Privacy and account requests</li>
            </ul>
          </Card>

          <Card title="Support Availability">
            <ul className="list-disc space-y-2 pl-5">
              <li>Customer Support: 24 Hours / 7 Days</li>
              <li>Email responses typically within one business day</li>
              <li>Urgent issues receive priority handling</li>
            </ul>
          </Card>
        </div>
      </Section>

      <Section id="billing-support">
        <Card title="Billing Support">
          <p className="text-slate-300">
            Questions regarding subscriptions, invoices, payment methods, or
            recurring billing are securely processed through{" "}
            <strong>{siteConfig.providers.billing}</strong>. If you experience a
            billing issue, please contact our support team using the information
            below.
          </p>
        </Card>
      </Section>

      <Section id="sms-support">
        <Card title="SMS Support">
          <p className="text-slate-300">
            If you experience issues receiving SMS traffic alerts, verify that
            your mobile number is registered correctly and that your wireless
            carrier supports SMS messaging.
          </p>

          <div className="mt-4 space-y-2">
            <p>
              <strong>HELP:</strong> {siteConfig.smsHelp}
            </p>

            <p>
              <strong>STOP:</strong> {siteConfig.smsStop}
            </p>

            <p>{siteConfig.smsRates}</p>
          </div>
        </Card>
      </Section>

      <Section id="technical-support">
        <Card title="Technical Support">
          <p className="text-slate-300">
            If you encounter technical issues while using{" "}
            {siteConfig.organization.product}, please include as much detail as
            possible when contacting us, including:
          </p>

          <ul className="list-disc space-y-2 pl-5 mt-4">
            <li>Description of the issue</li>
            <li>Device type</li>
            <li>Operating system</li>
            <li>Browser (if applicable)</li>
            <li>Approximate time the issue occurred</li>
            <li>Screenshots when available</li>
          </ul>
        </Card>
      </Section>

      <Section id="contact-support">
        <Card title="Contact Support">
          <div className="space-y-3">
            <p>
                <strong>Contact Form:</strong>{" "}
                <a
                    href={siteConfig.contact.page}
                    className="text-cyan-400 hover:underline"
                >
                    Contact Us
                </a>
                </p>

            <p>
                <strong>Phone:</strong>{" "}
                <a
                    href={`tel:${siteConfig.contact.phone.replace(/[^\d]/g, "")}`}
                    className="text-cyan-400 hover:underline"
                >
                    {siteConfig.contact.phone}
                </a>
                </p>

            {siteConfig.contact.address && (
              <p>
                <strong>Address:</strong> {siteConfig.contact.address}
              </p>
            )}

            <p>
              <strong>Company:</strong>{" "}
              {siteConfig.organization.legalName}
            </p>

            <p>
              <strong>Website:</strong>{" "}
              <a
                href={siteConfig.url}
                className="text-cyan-400 hover:underline"
              >
                {siteConfig.url}
              </a>
            </p>
          </div>
        </Card>
      </Section>
    </>
  );
}