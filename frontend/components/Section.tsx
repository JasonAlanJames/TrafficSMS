import type { ReactNode } from "react";

interface SectionProps {
  id?: string;
  className?: string;
  title?: string;
  description?: string;
  children: ReactNode;
}

export default function Section({
  id,
  className = "",
  title,
  description,
  children,
}: SectionProps) {
  return (
    <section
      id={id}
      className={`mx-auto max-w-7xl px-6 py-20 lg:px-8 ${className}`}
    >
      {title && (
        <h2 className="mb-4 text-3xl font-bold tracking-tight text-white">
          {title}
        </h2>
      )}

      {description && (
        <p className="mb-10 max-w-3xl text-lg text-slate-300">
          {description}
        </p>
      )}

      {children}
    </section>
  );
}