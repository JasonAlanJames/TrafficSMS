import Section from "./Section";
import Card from "./Card";
import { siteConfig } from "../lib/site";

export default function CookiePolicy() {
  return (
    <>
      <Section id="cookie-introduction">
        <p className="max-w-3xl text-lg text-slate-300">
          {siteConfig.productName} uses cookies and similar technologies to
          improve your experience, enhance security, remember your preferences,
          and help us understand how our services are used. This Cookie Policy
          explains what cookies are, how we use them, and the choices available
          to you regarding their use.
        </p>
      </Section>

      <Section id="what-are-cookies">
        <Card title="What Are Cookies?">
          <p>
            Cookies are small text files that are stored on your device when you
            visit a website. They allow websites to remember information such as
            your preferences, authentication status, and browsing activity,
            making future visits faster and more personalized.
          </p>
        </Card>
      </Section>

      <Section id="cookies-we-use">
        <Card title="Cookies We Use">
          <p>
            {siteConfig.productName} uses cookies and similar technologies for
            several purposes, including maintaining secure user sessions,
            remembering preferences, improving website performance, and
            understanding how visitors interact with our platform.
          </p>
        </Card>
      </Section>

      <Section id="essential-cookies">
        <Card title="Essential Cookies">
          <p>
            Essential cookies are required for the website to function properly.
            These cookies enable core features such as account authentication,
            secure login sessions, fraud prevention, and application security.
            Disabling these cookies may prevent portions of the website from
            functioning correctly.
          </p>
        </Card>
      </Section>

      <Section id="analytics-cookies">
        <Card title="Analytics Cookies">
          <p>
            Analytics cookies help us understand how visitors use our website,
            identify popular features, measure application performance, and
            improve the overall user experience. These cookies do not identify
            individual users directly but provide aggregated usage information.
          </p>
        </Card>
      </Section>

      <Section id="performance-cookies">
        <Card title="Performance Cookies">
          <p>
            Performance cookies allow us to optimize page loading times,
            troubleshoot technical issues, improve reliability, and enhance the
            overall responsiveness of the {siteConfig.productName} platform.
          </p>
        </Card>
      </Section>

      <Section id="third-party-services">
        <Card title="Third-Party Services">
          <p>
            {siteConfig.productName} works with carefully selected third-party
            providers that may use cookies or similar technologies as part of
            delivering their services.
          </p>

          <ul className="list-disc space-y-3 pl-5 mt-4">
            <li>
              <strong>{siteConfig.providers.billing}</strong> processes secure
              subscription payments and may place cookies necessary to detect
              fraud, process transactions, and improve payment reliability.
            </li>

            <li>
              <strong>{siteConfig.providers.sms}</strong> helps deliver SMS
              communications and service notifications. Cookies may be used
              within administrative interfaces and customer management systems
              supporting message delivery.
            </li>

            <li>
              <strong>{siteConfig.providers.maps}</strong> may use cookies when
              displaying maps, geographic information, or traffic-related
              content to improve performance and user experience.
            </li>
          </ul>
        </Card>
      </Section>

      <Section id="managing-cookies">
        <Card title="Managing Cookies">
          <p>
            Most web browsers allow you to control or delete cookies through
            your browser settings. You may choose to block or remove cookies at
            any time. However, disabling certain cookies may affect the
            functionality, performance, or availability of portions of the{" "}
            {siteConfig.productName} platform.
          </p>

          <p className="mt-4">
            For more information about managing cookies, consult your browser's
            help documentation or visit your browser vendor's support website.
          </p>
        </Card>
      </Section>

      <Section id="changes">
        <Card title="Changes to This Cookie Policy">
          <p>
            We may update this Cookie Policy from time to time to reflect
            changes in technology, legal requirements, or our business
            practices. Updated versions will be posted on this page together
            with the revised effective date.
          </p>
        </Card>
      </Section>

      <Section id="contact">
        <Card title="Contact Information">
          <p>
            If you have questions regarding this Cookie Policy or our use of
            cookies, please contact us:
          </p>

          <div className="mt-4 space-y-2">
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
            </div>
        </Card>
      </Section>
    </>
  );
}