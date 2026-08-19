import Link from "next/link";

export default function Navbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">

        <Link
          href="/"
          className="text-2xl font-bold text-white"
        >
          TrafficSMS
        </Link>

        <nav className="flex gap-8 text-sm">

          <Link href="/pricing">
            Pricing
          </Link>

          <Link href="/contact">
            Contact
          </Link>

          <Link href="/compliance">
            Trust
          </Link>

        </nav>

      </div>
    </header>
  );
}