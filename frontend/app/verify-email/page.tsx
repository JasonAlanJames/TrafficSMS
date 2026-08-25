'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

import { ApiError, verifyEmail } from '../../lib/api';
import styles from '../account-email.module.css';

function verificationFailureMessage(error: unknown): string {
  if (error instanceof ApiError && error.status < 500) {
    return error.message;
  }

  return 'This verification link is invalid or expired. Request a new verification email and try again.';
}

export default function VerifyEmailPage() {
  const [state, setState] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('Verifying your TrafficSMS email address...');

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get('token');

    if (!token) {
      setState('error');
      setMessage('This verification link is incomplete. Request a new verification email and try again.');
      return;
    }

    void verifyEmail(token)
      .then((result) => {
        setState('success');
        setMessage(result.message || 'Your email address has been verified.');
      })
      .catch((error: unknown) => {
        setState('error');
        setMessage(verificationFailureMessage(error));
      });
  }, []);

  const title = state === 'success'
    ? 'Email verified'
    : state === 'error'
      ? 'Verification link unavailable'
      : 'Verifying your email';

  return (
    <section className={styles.page}>
      <div className={styles.card}>
        <span className={styles.eyebrow}>TrafficSMS account</span>
        <h1 className={styles.title}>{title}</h1>
        <p className={styles.copy}>{message}</p>
        {state === 'loading' ? <div className={styles.loader} aria-label="Verification in progress" /> : null}
        {state !== 'loading' ? (
          <Link className={styles.button} href="/login">
            Continue to sign in
          </Link>
        ) : null}
      </div>
    </section>
  );
}
