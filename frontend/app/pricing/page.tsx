'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

import { useAuth } from '../../components/auth/AuthProvider';
import { SubscriptionStatusCard } from '../../components/subscription/SubscriptionStatusCard';
import {
  ApiError,
  changePlan,
  createCheckoutSession,
  getBillingSubscription,
  getPricing,
  type BillingPlan,
  type PricingPlan,
  type SubscriptionSummary,
} from '../../lib/api';

function formatCurrency(amount: number, currency: string): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency || 'USD',
  }).format(amount);
}

function formatInterval(interval: string): string {
  if (interval === 'month') {
    return 'month';
  }

  return interval;
}

function planFeatures(plan: BillingPlan): string[] {
  if (plan === 'standard') {
    return ['60 SMS Requests', 'Nationwide Traffic', 'Saved Routes', 'Account Dashboard'];
  }

  return ['Unlimited Web Lookups', '200 SMS Included', 'Saved Routes', 'Future Premium Features'];
}

export default function PricingPage() {
  const router = useRouter();
  const { initialized, isAuthenticated, session } = useAuth();
  const [pricing, setPricing] = useState<PricingPlan[]>([]);
  const [subscription, setSubscription] = useState<SubscriptionSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [busyPlan, setBusyPlan] = useState<BillingPlan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadPage() {
      setIsLoading(true);
      setError(null);

      try {
        const nextPricing = await getPricing();

        if (!cancelled) {
          setPricing(nextPricing);
        }

        if (isAuthenticated && session?.accessToken) {
          const nextSubscription = await getBillingSubscription(session.accessToken);

          if (!cancelled) {
            setSubscription(nextSubscription);
          }
        } else if (!cancelled) {
          setSubscription(null);
        }
      } catch (loadError) {
        if (!cancelled) {
          const nextMessage =
            loadError instanceof Error
              ? loadError.message
              : 'Unable to load pricing right now.';
          setError(nextMessage);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadPage();

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, session?.accessToken]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('cancelled') === 'true' || params.get('checkout') === 'canceled') {
      setMessage('Checkout Cancelled. You may subscribe anytime.');
      return;
    }

    setMessage(null);
  }, []);

  const standard = useMemo(
    () => pricing.find((plan) => plan.plan === 'standard') ?? null,
    [pricing],
  );
  const unlimited = useMemo(
    () => pricing.find((plan) => plan.plan === 'unlimited') ?? null,
    [pricing],
  );

  const activePlan = subscription?.plan ?? 'free';
  const hasExistingSubscription = Boolean(subscription?.stripe_subscription_id);

  async function handlePlanAction(plan: BillingPlan) {
    if (!initialized) {
      return;
    }

    if (!isAuthenticated || !session?.accessToken) {
      router.push('/login');
      return;
    }

    setBusyPlan(plan);
    setError(null);
    setMessage(null);

    try {
      if (hasExistingSubscription && activePlan !== 'free') {
        const nextSubscription = await changePlan(session.accessToken, plan);
        setSubscription(nextSubscription);
        setMessage(`Your plan has been updated to ${plan}.`);
        return;
      }

      const checkout = await createCheckoutSession(session.accessToken, plan);
      window.location.assign(checkout.url);
    } catch (actionError) {
      const nextMessage =
        actionError instanceof ApiError || actionError instanceof Error
          ? actionError.message
          : 'Unable to start billing right now.';
      setError(nextMessage);
    } finally {
      setBusyPlan(null);
    }
  }

  function buttonLabel(plan: BillingPlan): string {
    if (!initialized || isLoading) {
      return 'Loading...';
    }

    if (!isAuthenticated) {
      return 'Sign in to subscribe';
    }

    if (activePlan === plan && subscription?.status === 'active') {
      return 'Current plan';
    }

    if (hasExistingSubscription && activePlan !== 'free') {
      return plan === 'unlimited' ? 'Upgrade to Unlimited' : 'Downgrade to Standard';
    }

    return plan === 'standard' ? 'Subscribe to Standard' : 'Subscribe to Unlimited';
  }

  function isButtonDisabled(plan: BillingPlan): boolean {
    return (
      busyPlan !== null ||
      isLoading ||
      !initialized ||
      (activePlan === plan && subscription?.status === 'active')
    );
  }

  return (
    <section className="hero">
      <div className="card" style={{ marginBottom: '1.25rem' }}>
        <span className="pill">Billing</span>
        <h1>Choose your TrafficSMS plan</h1>
        <p className="muted">
          Select a monthly subscription to activate your verified account through secure hosted Stripe Checkout.
        </p>
        {subscription ? (
          <p className="muted" style={{ marginTop: '0.75rem' }}>
            Current plan: <strong>{subscription.plan_label}</strong> with status <strong>{subscription.status_label}</strong>.
          </p>
        ) : null}
        {message ? <p className="statusMessage">{message}</p> : null}
        {error ? <p className="errorMessage">{error}</p> : null}
      </div>

      {isAuthenticated ? (
        <div style={{ marginBottom: '1.25rem' }}>
          <SubscriptionStatusCard subscription={subscription} loading={isLoading} />
        </div>
      ) : null}

      {!isAuthenticated ? (
        <div className="card" style={{ marginBottom: '1.25rem' }}>
          <strong>Sign in to activate your account</strong>
          <p className="muted">
            Register, verify your email, and sign in before starting subscription checkout.
          </p>
          <div className="actionRow">
            <Link className="cta" href="/login">
              Sign in
            </Link>
          </div>
        </div>
      ) : null}

      <div className="grid">
        {[standard, unlimited].map((plan) => {
          if (!plan) {
            return null;
          }

          const planKey = plan.plan as BillingPlan;

            return (
              <div className="card" key={plan.plan}>
                <h2>{plan.plan === 'standard' ? 'Standard' : 'Unlimited'}</h2>
                <div className="price">{formatCurrency(plan.price, plan.currency)}</div>
                <p className="muted">/ {formatInterval(plan.interval)}</p>

                <div className="features">
                  {planFeatures(planKey).map((feature) => (
                    <div key={feature}>✓ {feature}</div>
                  ))}
                </div>

              <button
                className="cta"
                type="button"
                disabled={isButtonDisabled(planKey)}
                onClick={() => void handlePlanAction(planKey)}
                style={{ marginTop: '1.25rem', width: '100%' }}
              >
                {busyPlan === planKey ? 'Working...' : buttonLabel(planKey)}
              </button>
            </div>
          );
        })}
      </div>

      <div className="card" style={{ marginTop: '1.25rem' }}>
        <h2>What happens next</h2>
        <ol className="features">
          <li>Choose your subscription plan.</li>
          <li>Complete your secure checkout.</li>
          <li>Your subscription is activated immediately after payment, so you can start requesting live traffic updates right away.</li>
        </ol>
        {!isAuthenticated ? (
          <p className="muted" style={{ marginTop: '1rem' }}>
            You'll need to <Link href="/login">sign in</Link> before checkout can begin.
          </p>
        ) : null}
      </div>
    </section>
  );
}
