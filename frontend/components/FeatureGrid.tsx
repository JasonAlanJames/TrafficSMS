import type { ReactNode } from "react";

interface FeatureGridProps {
  children: ReactNode;
}

export default function FeatureGrid({
  children,
}: FeatureGridProps) {
  return (
    <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
      {children}
    </div>
  );
}