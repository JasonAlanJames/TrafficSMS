import type { ReactNode } from "react";

interface CardProps {
  title?: string;
  children: ReactNode;
  className?: string;
}

export default function Card({
  title,
  children,
  className = "",
}: CardProps) {
  return (
    <div
      className={`rounded-3xl border border-slate-800 bg-slate-900 p-8 shadow-lg ${className}`}
    >
      {title && (
        <h3 className="mb-4 text-2xl font-bold text-white">
          {title}
        </h3>
      )}

      <div className="leading-8 text-slate-300">
        {children}
      </div>
    </div>
  );
}