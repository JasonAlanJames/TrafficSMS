import type { Metadata } from 'next';
import Link from 'next/link';

import styles from '../../../components/sms-opt-in/smsOptIn.module.css';

export const metadata: Metadata = {
  title: 'TrafficSMS Registration Complete',
  description: 'Your TrafficSMS account was created successfully. Verify your email address to continue.',
};

export default function SmsOptInSuccessPage() {
  return (
    <section className={styles.page}>
      <div className={styles.heroGrid}>
        <div className={styles.heroPanel}>
          <span className={styles.eyebrow}>Success Page</span>
          <h1 className={styles.heroTitle}>Account Created!</h1>
          <p className={styles.heroBody}>We&apos;ve sent a verification email.</p>
          <p className={styles.heroBody}>
            Please verify your email address before signing in.
          </p>
          <p className={styles.heroBody}>
            After verification you&apos;ll be able to choose your TrafficSMS subscription.
          </p>
          <div className={styles.stack}>
            <Link className={styles.button} href="/">
              Return to Home
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
