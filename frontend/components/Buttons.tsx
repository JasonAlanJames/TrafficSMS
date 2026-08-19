import Link from "next/link";
import { ReactNode } from "react";

interface ButtonProps {
  href: string;
  children: ReactNode;
  variant?: "primary" | "secondary";
}

export default function Button({
  href,
  children,
  variant = "primary",
}: ButtonProps) {
  const classes =
    variant === "primary"
      ? "inline-flex items-center justify-center rounded-xl bg-emerald-500 px-6 py-3 font-semibold text-black transition hover:bg-emerald-400"
      : "inline-flex items-center justify-center rounded-xl border border-slate-600 px-6 py-3 font-semibold text-white transition hover:border-emerald-400 hover:text-emerald-400";

  return (
    <Link href={href} className={classes}>
      {children}
    </Link>
  );
}