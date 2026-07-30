'use client';

import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

type PlanPricing = {
    id: string;
    name: string;
    description: string;
    price: number;
    currency: string;
    interval: string;
    price_id: string;
};

export default function Pricing() {
    const [email, setEmail] = useState('');
    const [busy, setBusy] = useState(false);

    const [pricing, setPricing] = useState<PlanPricing[]>([]);

    useEffect(() => {
    async function loadPricing() {
        try {
            const response = await fetch(`${API}/billing/pricing`);

            if (!response.ok) {
                throw new Error("Unable to load pricing.");
            }

            const data: PlanPricing[] = await response.json();
            setPricing(data);
        } catch (err) {
            console.error("Failed to load pricing:", err);
        }
    }

    loadPricing();
}, []);

const standard =
    pricing.find((p) => p.name.includes("Standard"));

const unlimited =
    pricing.find((p) => p.name.includes("Unlimited"));

    async function buy(plan: 'standard' | 'unlimited') {
        setBusy(true);	

        try {
            const response = await fetch(`${API}/billing/checkout`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email,
                    plan,
                }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Checkout failed.');
            }

            window.location.href = data.url;
        } catch (error) {
            alert(error instanceof Error ? error.message : 'Checkout failed.');
            setBusy(false);
        }
    }

    return (
        <section className="hero">
            <h1>Choose Your TrafficSMS Plan</h1>

            <div className="grid">

                <div className="card">
                    <h2>Standard</h2>

                    <div className="price">
                        {standard ? `$${standard.price.toFixed(2)}` : "..."}
                    </div>

                    <p className="muted">
                        {standard ? `per ${standard.interval}` : "Loading..."}
                    </p>

                    <ul className="muted">
                        <li>60 SMS traffic requests/month</li>
                        <li>5 saved routes</li>
                        <li>Commute alerts</li>
                        <li>Traffic incidents</li>
                        <li>Road closures</li>
                        <li>Travel delays</li>
                    </ul>

                    <input
                        className="input"
                        type="email"
                        placeholder="you@example.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                    />

                    <button
                        className="cta"
                        disabled={busy || !email}
                        onClick={() => buy('standard')}
                    >
                        Subscribe to Standard
                    </button>
                </div>

                <div className="card">
                    <h2>Unlimited</h2>

                    <div className="price">
                         {unlimited ? `$${unlimited.price.toFixed(2)}` : "..."}
                    </div>

                    <p className="muted">
                         {unlimited ? `per ${unlimited.interval}` : "Loading..."}
                    </p>

                    <ul className="muted">
                        <li>Unlimited SMS requests</li>
                        <li>Unlimited saved routes</li>
                        <li>Priority notifications</li>
                        <li>Community traffic reports</li>
                        <li>Enforcement camera notices</li>
                        <li>DUI checkpoint alerts</li>
                    </ul>

                    <input
                        className="input"
                        type="email"
                        placeholder="you@example.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                    />

                    <button
                        className="cta"
                        disabled={busy || !email}
                        onClick={() => buy('unlimited')}
                    >
                        Subscribe to Unlimited
                    </button>
                </div>

            </div>

            <p className="muted">
                TrafficSMS subscriptions renew monthly until canceled. Message and
                data rates may apply depending on your wireless carrier.
            </p>
        </section>
    );
}
