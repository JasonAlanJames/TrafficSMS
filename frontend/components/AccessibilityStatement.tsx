import Section from "./Section";
import Card from "./Card";
import { siteConfig } from "../lib/site";

export default function AccessibilityStatement() {
  return (
    <>
      <Section id="accessibility-introduction">
        <p className="max-w-3xl text-lg text-slate-300">
          {siteConfig.productName} is committed to providing a website and
          services that are accessible to all users, including individuals with
          disabilities. We continually strive to improve the accessibility,
          usability, and inclusiveness of our platform by following recognized
          accessibility standards and best practices.
        </p>
      </Section>

      <Section id="commitment">
        <Card title="Commitment to Accessibility">
          <p>
            {siteConfig.organization.legalName} believes that everyone should
            have equal access to information and digital services. We are
            committed to designing and maintaining {siteConfig.productName} so
            that it can be used by the widest possible audience regardless of
            technology, ability, or circumstance.
          </p>
        </Card>
      </Section>

      <Section id="wcag">
        <Card title="WCAG Compliance">
          <p>
            We strive to design and maintain our website in accordance with the
            Web Content Accessibility Guidelines (WCAG) 2.1 Level AA whenever
            reasonably practical. These internationally recognized guidelines
            help ensure that digital content is perceivable, operable,
            understandable, and robust for all users.
          </p>
        </Card>
      </Section>

      <Section id="keyboard-navigation">
        <Card title="Keyboard Navigation">
          <p>
            Our goal is to ensure that all primary navigation, forms, buttons,
            and interactive elements can be accessed using only a keyboard. We
            regularly review keyboard accessibility as new features are added to
            the platform.
          </p>
        </Card>
      </Section>

      <Section id="screen-reader-support">
        <Card title="Screen Reader Support">
          <p>
            We aim to use semantic HTML, meaningful headings, descriptive link
            text, appropriate labels, and ARIA attributes where appropriate to
            improve compatibility with modern screen readers and assistive
            technologies.
          </p>
        </Card>
      </Section>

      <Section id="color-contrast">
        <Card title="Color Contrast">
          <p>
            We work to provide sufficient color contrast between text,
            backgrounds, and interface elements to improve readability for users
            with visual impairments or color vision deficiencies. Information is
            not conveyed solely through color whenever practical.
          </p>
        </Card>
      </Section>

      <Section id="responsive-design">
        <Card title="Responsive Design">
          <p>
            {siteConfig.productName} is designed to function across a variety of
            devices and screen sizes, including desktop computers, tablets, and
            mobile devices. Responsive layouts help improve accessibility by
            allowing users to interact with the platform using their preferred
            device.
          </p>
        </Card>
      </Section>

      <Section id="feedback">
        <Card title="Accessibility Feedback">
          <p>
            Accessibility is an ongoing effort. If you encounter an
            accessibility barrier or have suggestions that could improve your
            experience, we encourage you to contact us. Your feedback helps us
            continue improving the accessibility of our services.
          </p>
        </Card>
      </Section>

      <Section id="contact">
        <Card title="Contact Information">
          <p>
            If you have questions, accessibility concerns, or need assistance accessing any portion of {siteConfig.organization.product}, please contact us through our Contact page or by phone:
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