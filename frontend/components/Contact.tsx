import Card from "./Card";
import Section from "./Section";
import { siteConfig } from "../lib/site";

export default function Contact() {
  return (
    <>
      <Section id="contact-introduction">
        <p className="max-w-3xl text-lg text-slate-300">
          Have a question about{" "}
          <strong>{siteConfig.organization.product}</strong>?
          Whether you need technical support, have billing questions, want to
          report an issue, or simply need assistance, we're here to help.
          Complete the form below and a member of{" "}
          <strong>{siteConfig.organization.legalName}</strong> will respond as
          soon as possible.
        </p>
      </Section>

      <Section id="contact-form">
        <Card title="Send Us a Message">
          <form
            action={siteConfig.forms.contact.action}
            method={siteConfig.forms.contact.method}
            style={{
              display: "grid",
              gap: "1rem",
            }}
          >
            <input
              type="hidden"
              name="_subject"
              value={`${siteConfig.organization.product} Contact Form Submission`}
            />

            <input
              type="hidden"
              name="_next"
              value={`${siteConfig.url}${siteConfig.forms.contact.successPage}`}
            />

            <div>
              <label htmlFor="name">
                <strong>Name</strong>
              </label>

              <input
                id="name"
                name="name"
                type="text"
                required
                className="input"
                placeholder="Your Name"
              />
            </div>

            <div>
              <label htmlFor="email">
                <strong>Email Address</strong>
              </label>

              <input
                id="email"
                name="email"
                type="email"
                required
                className="input"
                placeholder="your@email.com"
              />
            </div>

            <div>
              <label htmlFor="subject">
                <strong>Subject</strong>
              </label>

              <input
                id="subject"
                name="subject"
                type="text"
                required
                className="input"
                placeholder="How can we help?"
              />
            </div>

            <div>
              <label htmlFor="message">
                <strong>Message</strong>
              </label>

              <textarea
                id="message"
                name="message"
                required
                rows={8}
                className="input"
                placeholder="Please describe your question or issue..."
                style={{
                  resize: "vertical",
                  minHeight: "180px",
                }}
              />
            </div>

            <button
              type="submit"
              className="cta"
            >
              Send Message
            </button>
          </form>
        </Card>
      </Section>

      <Section id="support-information">
        <div className="grid gap-6 lg:grid-cols-2">
          <Card title="Customer Support">
            <ul className="list-disc space-y-2 pl-5">
              <li>Technical Support</li>
              <li>Subscription Assistance</li>
              <li>Billing Questions</li>
              <li>Account Assistance</li>
              <li>Traffic Alert Questions</li>
              <li>General Inquiries</li>
            </ul>
          </Card>

          <Card title="Contact Information">
            <div
              style={{
                display: "grid",
                gap: ".75rem",
              }}
            >
              <div>
                <strong>Company</strong>
                <br />
                {siteConfig.organization.legalName}
              </div>

              <div>
                <strong>Product</strong>
                <br />
                {siteConfig.organization.product}
              </div>

              <div>
                <strong>Phone</strong>
                <br />
                <a
                  href={`tel:${siteConfig.contact.phone.replace(/[^\d]/g, "")}`}
                >
                  {siteConfig.contact.phone}
                </a>
              </div>

              {siteConfig.contact.address && (
                <div>
                  <strong>Address</strong>
                  <br />
                  {siteConfig.contact.address}
                </div>
              )}

              <div>
                <strong>Website</strong>
                <br />
                <a
                  href={siteConfig.url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {siteConfig.url}
                </a>
              </div>
            </div>
          </Card>
        </div>
      </Section>

      <Section id="response-time">
        <Card title="Response Time">
          <p>
            We strive to respond to all inquiries as quickly as possible.
            Most messages receive a response within one business day.
            Complex technical or billing inquiries may require additional
            investigation before a response can be provided.
          </p>
        </Card>
      </Section>
    </>
  );
}