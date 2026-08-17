import type { Metadata } from 'next';
import Link from 'next/link';

import RegistrationForm from '../../components/sms-opt-in/RegistrationForm';
import styles from '../../components/sms-opt-in/smsOptIn.module.css';

const benefitCards = [
  {
    title: 'Live roadway intelligence',
    description: 'Get fast updates on collisions, congestion, closures, travel times, and activity that can change your route in minutes.',
  },
  {
    title: 'Saved routes that work for you',
    description: 'Registration unlocks the account foundation for home, work, school, gym, and other personalized route tools later in the dashboard.',
  },
  {
    title: 'SMS access from anywhere',
    description: 'TrafficSMS is designed for quick access when you are away from your desk and need signal-level updates delivered to your phone.',
  },
  {
    title: 'Secure account management',
    description: 'Start with the essentials now, verify your email, and continue into subscription setup with a clean authentication flow later.',
  },
];

export const metadata: Metadata = {
  title: 'TrafficSMS SMS Opt-In',
  description: 'Create your TrafficSMS account and consent to receive traffic alerts, service notifications, and account-related SMS messages.',
};

function CheckIcon() {
  return (
    <svg viewBox="0 0 16 16" width="12" height="12" fill="none" aria-hidden="true">
      <path d="M3 8.2 6.1 11 13 4.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function SmsOptInPage() {
  return (
    <section className={styles.page}>
      <div className={styles.heroGrid}>
        <div>
          <div className={styles.heroPanel}>
            <span className={styles.eyebrow}>TrafficSMS Registration</span>
            <h1 className={styles.heroTitle}>Real-Time Traffic Alerts by SMS</h1>
            <p className={styles.heroBody}>
              Receive live traffic updates, accidents, congestion, road closures, travel times, police activity, and important account notifications directly to your phone.
            </p>

            <ul className={styles.heroList} aria-label="TrafficSMS benefits">
              {[
                'Live traffic updates',
                'Personalized saved routes',
                'SMS access from anywhere',
                'Secure account management',
              ].map((item) => (
                <li className={styles.heroListItem} key={item}>
                  <span className={styles.iconBadge}>
                    <CheckIcon />
                  </span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>

            <div className={styles.heroMeta}>
              <div className={styles.metaCard}>
                <p className={styles.metaTitle}>Public opt-in workflow</p>
                <p className={styles.metaText}>
                  This page is built to serve as TrafficSMS&apos;s permanent account registration flow and visible proof-of-consent entry point.
                </p>
              </div>
              <div className={styles.metaCard}>
                <p className={styles.metaTitle}>Twilio-ready disclosures</p>
                <p className={styles.metaText}>
                  STOP, HELP, frequency, rates, privacy, terms, and purchase-independence language are all surfaced clearly before signup.
                </p>
              </div>
            </div>
          </div>

          <div className={styles.stack}>
            <section className={styles.surfaceCard} aria-labelledby="benefits-title">
              <h2 className={styles.sectionTitle} id="benefits-title">
                Benefits Section
              </h2>
              <p className={styles.sectionText}>
                The signup flow stays lean now so users can create an account quickly, then finish profile setup and subscription choices after verification.
              </p>
              <div className={styles.benefitGrid}>
                {benefitCards.map((benefit) => (
                  <article className={styles.benefitCard} key={benefit.title}>
                    <h3>{benefit.title}</h3>
                    <p>{benefit.description}</p>
                  </article>
                ))}
              </div>
            </section>

            <section className={styles.surfaceCard} aria-labelledby="privacy-title">
              <h2 className={styles.sectionTitle} id="privacy-title">
                Privacy / Terms Section
              </h2>
              <p className={styles.sectionText}>
                TrafficSMS links directly to its existing public legal pages so users can review data handling and service terms before completing SMS opt-in.
              </p>
              <div className={styles.legalLinks}>
                <a className={styles.legalLink} href="https://trafficsms.com/privacy">
                  Privacy Policy
                </a>
                <a className={styles.legalLink} href="https://trafficsms.com/terms">
                  Terms of Service
                </a>
              </div>
            </section>

            <section className={styles.surfaceCard} aria-labelledby="existing-account-title">
              <h2 className={styles.sectionTitle} id="existing-account-title">
                Existing Account Section
              </h2>
              <p className={styles.sectionText}>
                Already registered? Sign back in to manage saved routes, review account settings, and continue with your subscription.
              </p>
              <Link className={styles.secondaryButton} href="/login">
                Already have an account? Sign In
              </Link>
            </section>
          </div>
        </div>

        <RegistrationForm />
      </div>
    </section>
  );
}
