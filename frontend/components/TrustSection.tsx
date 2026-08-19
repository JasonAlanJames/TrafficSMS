import Card from "./Card";

export default function TrustSection() {
  return (
    <section className="grid gap-8 lg:grid-cols-3">

      <Card>
        <h3 className="mb-4 text-2xl font-bold">
          Secure Infrastructure
        </h3>

        <p className="leading-8 text-slate-300">
          SSL encrypted communications, secure authentication,
          protected APIs, and industry-standard security practices.
        </p>
      </Card>

      <Card>
        <h3 className="mb-4 text-2xl font-bold">
          Trusted Partners
        </h3>

        <p className="leading-8 text-slate-300">
          Payments processed securely by Stripe.
          <br />
          Messaging delivered through Twilio.
          <br />
          Mapping powered by Google Maps Platform.
        </p>
      </Card>

      <Card>
        <h3 className="mb-4 text-2xl font-bold">
          Reliable Information
        </h3>

        <p className="leading-8 text-slate-300">
          Traffic reports combine official agency notifications with
          community-submitted reports while identifying the source of
          each report whenever possible.
        </p>
      </Card>

    </section>
  );
}