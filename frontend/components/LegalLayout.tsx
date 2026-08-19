import type { ReactNode } from "react";

import Container from "./Container";
import PageHeader from "./PageHeader";

interface LegalLayoutProps {
  title: string;
  description?: string;
  children: ReactNode;
}

export default function LegalLayout({
  title,
  description,
  children,
}: LegalLayoutProps) {
  return (
    <Container>
      <PageHeader title={title} description={description} />
      {children}
    </Container>
  );
}