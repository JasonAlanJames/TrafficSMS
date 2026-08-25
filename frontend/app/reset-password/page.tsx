'use client';

import Link from 'next/link';
import { type FormEvent, useState } from 'react';

import { ApiError, resetPassword } from '../../lib/api';
import styles from '../account-email.module.css';

function validatePassword(password: string): string | null {
  if (password.length < 8) return 'Password must be at least 8 characters long.';
  if (!/[A-Z]/.test(password)) return 'Password must contain an uppercase letter.';
  if (!/[a-z]/.test(password)) return 'Password must contain a lowercase letter.';
  if (!/\d/.test(password)) return 'Password must contain a number.';
  if (!/[^A-Za-z0-9]/.test(password)) return 'Password must contain a special character.';
  return null;
}

function resetFailureMessage(error: unknown): string {
  if (error instanceof ApiError && error.status < 500) {
    return error.message;
  }

  return 'This password reset link is invalid or expired. Request a new password reset email and try again.';
}

export default function ResetPasswordPage() {
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [message, setMessage] = useState('');
  const [complete, setComplete] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = new URLSearchParams(window.location.search).get('token');
    const passwordError = validatePassword(password);

    if (!token) {
      setMessage('This password reset link is incomplete. Request a new password reset email and try again.');
      return;
    }

    if (passwordError) {
      setMessage(passwordError);
      return;
    }

    if (password !== confirmation) {
      setMessage('Passwords do not match.');
      return;
    }

    setMessage('');
    setIsSubmitting(true);
    try {
      const result = await resetPassword(token, password);
      setComplete(true);
      setMessage(result.message || 'Your password has been updated.');
    } catch (error) {
      setMessage(resetFailureMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className={styles.page}>
      <div className={styles.card}>
        <span className={styles.eyebrow}>TrafficSMS account</span>
        <h1 className={styles.title}>{complete ? 'Password updated' : 'Reset your password'}</h1>
        <p className={styles.copy}>
          {message || 'Choose a strong new password to keep your account protected.'}
        </p>
        {complete ? (
          <Link className={styles.button} href="/login">
            Continue to sign in
          </Link>
        ) : (
          <form className={styles.form} onSubmit={submit}>
            <label className={styles.label} htmlFor="new-password">New password</label>
            <input
              id="new-password"
              className={styles.input}
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
            <label className={styles.label} htmlFor="confirm-password">Confirm new password</label>
            <input
              id="confirm-password"
              className={styles.input}
              type="password"
              autoComplete="new-password"
              value={confirmation}
              onChange={(event) => setConfirmation(event.target.value)}
              required
            />
            <button className={styles.button} type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Updating password...' : 'Reset password'}
            </button>
          </form>
        )}
      </div>
    </section>
  );
}
