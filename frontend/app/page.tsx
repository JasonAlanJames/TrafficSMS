import Link from "next/link";
import { getPricing } from "../lib/api";

export default async function Home() {
  let startingPrice = "$5.99";

  try {
    const pricing = await getPricing();

    const standardPlan =
      pricing.find(
        (plan) => plan.plan.toLowerCase() === "standard"
      ) ??
      pricing.find(
        (plan) => plan.name.toLowerCase() === "standard"
      ) ??
      pricing[0];

    if (standardPlan) {
      startingPrice = new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: standardPlan.currency.toUpperCase(),
        minimumFractionDigits: 2,
      }).format(standardPlan.price);
    }
  } catch (error) {
    console.error("Unable to load Stripe pricing:", error);
    // Keep default fallback price so the homepage still renders.
  }

  return (
    <>
      <section className="hero">
        <span className="pill">
          Text TRAFFIC. Know what is ahead.
        </span>

        <h1 style={{ fontSize: 58, maxWidth: 800 }}>
          Local traffic incidents and community road reports by SMS.
        </h1>

        <p
          className="muted"
          style={{ fontSize: 20, maxWidth: 720 }}
        >
          Traffic conditions, collisions, closures, travel delays,
          peer-reported police presence, enforcement-camera notices,
          and official DUI enforcement announcements.
        </p>

        <Link className="cta" href="/pricing">
          Start for {startingPrice}/month
        </Link>
      </section>

      <section className="grid">
        <div className="card">
          <h2>SMS first</h2>

          <p className="muted">
            Text TRAFFIC plus a ZIP, city, road, or saved route.
          </p>
        </div>

        <div className="card">
          <h2>Community confidence</h2>

          <p className="muted">
            Police reports can be marked Still There, Cleared, or
            Unsure and expire automatically.
          </p>
        </div>

        <div className="card">
          <h2>Source transparency</h2>

          <p className="muted">
            Camera and DUI notices identify whether data is official,
            verified, or peer reported.
          </p>
        </div>
      </section>
    </>
  );
}