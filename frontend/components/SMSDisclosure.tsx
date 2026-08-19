import Link from "next/link";

export default function SMSDisclosure() {
  return (
    <div className="rounded-2xl border border-emerald-500 bg-slate-900 p-6 text-sm leading-7">

      <p className="font-semibold text-white">
        SMS Program Disclosure
      </p>

      <p className="mt-3 text-slate-300">
        By subscribing to TrafficSMS alerts, you consent to receive SMS
        messages containing traffic incidents, road closures, enforcement
        notices, and other transportation updates based on your selected
        locations or routes.
      </p>

      <p className="mt-4 text-slate-400">
        Message frequency varies. Reply STOP to cancel.
        Reply HELP for assistance.
        Message and data rates may apply.
      </p>

      <p className="mt-4">

        <Link
          href="/privacy"
          className="text-emerald-400"
        >
          Privacy Policy
        </Link>

        {" • "}

        <Link
          href="/terms"
          className="text-emerald-400"
        >
          Terms of Service
        </Link>

      </p>

    </div>
  );
}