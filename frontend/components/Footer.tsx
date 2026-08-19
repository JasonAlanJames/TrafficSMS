import Link from "next/link";

import { footerSections, siteConfig } from "../lib/site";

export default function Footer() {
  return (
    <footer
      style={{
        marginTop: 60,
        padding: "40px 20px",
        borderTop: "1px solid #24435f",
      }}
    >
      <div
        style={{
          maxWidth: "1200px",
          margin: "0 auto",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "32px",
          marginBottom: "32px",
        }}
      >
        {footerSections.map((section) => (
          <div key={section.title}>
            <h3
              style={{
                marginBottom: "14px",
                fontSize: "1rem",
                fontWeight: 600,
              }}
            >
              {section.title}
            </h3>

            <nav
              aria-label={section.title}
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "10px",
              }}
            >
              {section.links.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  style={{
                    textDecoration: "none",
                  }}
                >
                  {link.label}
                </Link>
              ))}
            </nav>

            {section.supportInfo?.map((support) => (
              <div
                key={support.label}
                style={{
                  marginTop: "16px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "6px",
                  fontSize: "0.9rem",
                }}
              >
                <div>
                  <strong>{support.label}:</strong> {support.supportHours}
                </div>
              </div>
            ))}

            {section.contactInfo?.map((contact) => (
              <div
                key={contact.phone}
                style={{
                  marginTop: "16px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "6px",
                  fontSize: "0.9rem",
                }}
              >
                <div>{contact.phone}</div>

                {contact.address && (
                  <div>{contact.address}</div>
                )}
              </div>
            ))}
          </div>
        ))}
      </div>

      <div
        className="muted"
        style={{
          textAlign: "center",
          borderTop: "1px solid #24435f",
          paddingTop: "20px",
          fontSize: "0.9rem",
        }}
      >
        {"\u00A9"} {siteConfig.copyrightYear}{" "}
        {siteConfig.organization.product} |{" "}
        {siteConfig.organization.legalName}.{" "}
        {siteConfig.copyrightText}
      </div>
    </footer>
  );
}