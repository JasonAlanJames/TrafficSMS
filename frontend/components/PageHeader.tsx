import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  subtitle?: ReactNode;
  description?: string;
}

export default function PageHeader({
  title,
  subtitle,
  description,
}: PageHeaderProps) {
  return (
    <header className="mb-16">
      <h1 className="mb-6 text-5xl font-bold">
        {title}
      </h1>

      {description && (
        <p className="mb-6 max-w-3xl text-lg text-slate-300">
          {description}
        </p>
      )}

      {subtitle && (
        <div className="max-w-3xl text-lg text-slate-300">
          {subtitle}
        </div>
      )}
    </header>
  );
}