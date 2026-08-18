import Link from 'next/link';

import type { SubscriptionSummary } from '../../lib/api';
import styles from './SubscriptionStatusCard.module.css';

type Props = {
  subscription: SubscriptionSummary | null;
  loading?: boolean;
  showActions?: boolean;
};

function formatDate(value: string | null): string {
  if (!value) {
    return 'Not available';
  }

  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
  }).format(new Date(value));
}

export function SubscriptionStatusCard({ subscription, loading = false, showActions = false }: Props) {
  if (loading) {
    return (
      <article className={`card ${styles.panel}`}>
        <div className={styles.header}>
          <div>
            <h2>Subscription status</h2>
            <p className="muted">Loading your billing status, usage, and verification details.</p>
          </div>
        </div>
      </article>
    );
  }

  if (!subscription || subscription.plan === 'free' || !subscription.has_active_subscription) {
    return (
      <article className={`card ${styles.panel}`}>
        <div className={styles.header}>
          <div>
            <h2>Subscription status</h2>
            <p className="muted">Your verified account is ready for activation.</p>
          </div>
          <span className={`${styles.statusBadge} ${styles.statusBadgeRestricted}`}>Subscription required</span>
        </div>

        <div className={styles.onboarding}>
          <strong>No Active Subscription</strong>
          <p className="muted">
            Your account has been successfully verified. Choose a TrafficSMS plan to begin receiving live traffic alerts.
          </p>
          {showActions ? (
            <div className="actionRow">
              <Link className="cta" href="/pricing">
                View plans
              </Link>
            </div>
          ) : null}
        </div>
      </article>
    );
  }

  return (
    <article className={`card ${styles.panel}`}>
      <div className={styles.header}>
        <div>
          <h2>Subscription status</h2>
          <p className="muted">Live billing, quota, verification, and renewal details from the backend.</p>
        </div>
        <span className={styles.statusBadge}>{subscription.status_label}</span>
      </div>

      <div className={styles.grid}>
        <div className={styles.gridItem}>
          <span className={styles.label}>Current plan</span>
          <strong className={styles.value}>{subscription.plan_label}</strong>
          <span className="muted">Unlimited web access: {subscription.has_unlimited_web_access ? 'Yes' : 'No'}</span>
        </div>
        <div className={styles.gridItem}>
          <span className={styles.label}>Billing cycle</span>
          <strong className={styles.value}>{subscription.billing_cycle}</strong>
          <span className="muted">Renewal: {formatDate(subscription.renewal_date)}</span>
        </div>
        <div className={styles.gridItem}>
          <span className={styles.label}>Included SMS</span>
          <strong className={styles.value}>{subscription.usage.sms_allowance}</strong>
          <span className="muted">Remaining: {subscription.usage.remaining_sms}</span>
        </div>
        <div className={styles.gridItem}>
          <span className={styles.label}>Payment method</span>
          <strong className={styles.value}>{subscription.payment_method ?? 'Not available yet'}</strong>
          <span className="muted">Auto renewal: {subscription.auto_renew_enabled ? 'Enabled' : 'Off'}</span>
        </div>
        <div className={styles.gridItem}>
          <span className={styles.label}>Email verification</span>
          <strong className={styles.value}>{subscription.email_verified ? 'Verified' : 'Pending'}</strong>
          <span className="muted">Phone verification: {subscription.phone_verified ? 'Verified' : 'Pending'}</span>
        </div>
        <div className={styles.gridItem}>
          <span className={styles.label}>Stripe customer</span>
          <strong className={styles.value}>{subscription.stripe_customer_id_masked ?? 'Pending assignment'}</strong>
          <span className="muted">Auto renewal status reflects Stripe subscription settings.</span>
        </div>
      </div>
    </article>
  );
}
