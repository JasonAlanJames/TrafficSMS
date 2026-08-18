'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { startTransition, useEffect, useState, type FormEvent } from 'react';

import { ApiError, forgotPassword, resendVerification } from '../../lib/api';
import { useAuth } from '../../components/auth/AuthProvider';
import styles from './login.module.css';

function mapLoginError(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof TypeError) {
    return 'We could not reach TrafficSMS. Check your connection and try again.';
  }

  return 'Something unexpected happened. Please try again.';
}

export default function LoginPage() {
  const router = useRouter();
  const { initialized, isAuthenticated, login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  const [forgotEmail, setForgotEmail] = useState('');
  const [verificationEmail, setVerificationEmail] = useState('');
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [showVerificationHelp, setShowVerificationHelp] = useState(false);
  const [generalError, setGeneralError] = useState('');
  const [forgotMessage, setForgotMessage] = useState('');
  const [sessionNotice, setSessionNotice] = useState('');
  const [verificationMessage, setVerificationMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSendingReset, setIsSendingReset] = useState(false);
  const [isSendingVerification, setIsSendingVerification] = useState(false);

  useEffect(() => {
    if (initialized && isAuthenticated) {
      router.replace('/dashboard');
    }
  }, [initialized, isAuthenticated, router]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const reason = new URLSearchParams(window.location.search).get('reason');

    if (reason === 'password-updated') {
      setSessionNotice('Your password was updated on August 17, 2026. Sign in again with the new password.');
      return;
    }

    if (reason === 'logout-all') {
      setSessionNotice('All active devices were signed out on August 17, 2026.');
      return;
    }

    if (reason === 'session-revoked') {
      setSessionNotice('This session was revoked on August 17, 2026. Sign in again to continue.');
      return;
    }

    if (reason === 'session-expired') {
      setSessionNotice('Your session expired on August 17, 2026. Sign in again to continue.');
      return;
    }

    setSessionNotice('');
  }, []);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setGeneralError('');
    setForgotMessage('');
    setVerificationMessage('');
    setIsSubmitting(true);

    try {
      await login({
        email: email.trim(),
        password,
        rememberMe,
      });

      startTransition(() => {
        router.push('/dashboard');
      });
    } catch (error) {
      setGeneralError(mapLoginError(error));
      if (error instanceof ApiError && error.status === 403 && email.trim()) {
        setShowVerificationHelp(true);
        setVerificationEmail(email.trim());
      } else {
        setShowVerificationHelp(false);
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleForgotPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setGeneralError('');
    setForgotMessage('');
    setVerificationMessage('');
    setIsSendingReset(true);

    try {
      const response = await forgotPassword(forgotEmail.trim());
      setForgotMessage(response.message);
    } catch (error) {
      setGeneralError(mapLoginError(error));
    } finally {
      setIsSendingReset(false);
    }
  }

  async function handleResendVerification() {
    setGeneralError('');
    setVerificationMessage('');
    setIsSendingVerification(true);

    try {
      const response = await resendVerification(verificationEmail.trim());
      setVerificationMessage(response.message);
    } catch (error) {
      setGeneralError(mapLoginError(error));
    } finally {
      setIsSendingVerification(false);
    }
  }

  return (
    <section className={styles.page}>
      <div className={styles.shell}>
        <div className={styles.heroCard}>
          <span className={styles.eyebrow}>TrafficSMS Authentication</span>
          <h1 className={styles.title}>Sign in and keep your session alive across devices.</h1>
          <p className={styles.body}>
            TrafficSMS uses short-lived access tokens, rotating refresh tokens, and account-level session revocation so your saved routes and future billing state stay protected.
          </p>
          <ul className={styles.benefits}>
            <li>JWT access tokens with automatic refresh</li>
            <li>Secure logout and logout-all-devices support</li>
            <li>Password reset flow ready for SMTP delivery wiring</li>
          </ul>
          <div className={styles.actionRow}>
            <Link className={styles.secondaryLink} href="/sms-opt-in">
              Need an account? Register here
            </Link>
          </div>
        </div>

        <div className={styles.formCard}>
          <div className={styles.tabs}>
            <button
              className={!showForgotPassword ? styles.tabActive : styles.tab}
              type="button"
              onClick={() => {
                setShowForgotPassword(false);
                setGeneralError('');
                setForgotMessage('');
                setVerificationMessage('');
              }}
            >
              Sign in
            </button>
            <button
              className={showForgotPassword ? styles.tabActive : styles.tab}
              type="button"
              onClick={() => {
                setShowForgotPassword(true);
                setGeneralError('');
                setForgotMessage('');
                setVerificationMessage('');
              }}
            >
              Forgot password
            </button>
          </div>

          {sessionNotice ? (
            <div className={styles.success} role="status">
              {sessionNotice}
            </div>
          ) : null}

          {!showForgotPassword ? (
            <form className={styles.form} onSubmit={handleLogin}>
              <label className={styles.label} htmlFor="email">
                Email address
              </label>
              <input
                id="email"
                className={styles.input}
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
                required
              />

              <label className={styles.label} htmlFor="password">
                Password
              </label>
              <input
                id="password"
                className={styles.input}
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter your password"
                required
              />

              <label className={styles.checkboxRow}>
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(event) => setRememberMe(event.target.checked)}
                />
                <span>Remember me on this device</span>
              </label>

              {generalError ? (
                <div className={styles.alert} role="alert">
                  {generalError}
                </div>
              ) : null}

              {showVerificationHelp ? (
                <div className={styles.success} role="status">
                  <p style={{ margin: 0 }}>
                    If this account is still awaiting email verification, you can resend the verification message now.
                  </p>
                  <div className={styles.actionRow}>
                    <button
                      className={styles.submitButton}
                      type="button"
                      onClick={() => void handleResendVerification()}
                      disabled={isSendingVerification}
                    >
                      {isSendingVerification ? 'Sending verification...' : 'Resend verification email'}
                    </button>
                  </div>
                </div>
              ) : null}

              {verificationMessage ? (
                <div className={styles.success} role="status">
                  {verificationMessage}
                </div>
              ) : null}

              <button className={styles.submitButton} type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Signing in...' : 'Sign in'}
              </button>
            </form>
          ) : (
            <form className={styles.form} onSubmit={handleForgotPassword}>
              <label className={styles.label} htmlFor="forgot-email">
                Account email
              </label>
              <input
                id="forgot-email"
                className={styles.input}
                type="email"
                autoComplete="email"
                value={forgotEmail}
                onChange={(event) => setForgotEmail(event.target.value)}
                placeholder="you@example.com"
                required
              />

              <p className={styles.helperText}>
                TrafficSMS will issue a reset token and hand it to the configured email delivery service when SMTP is connected.
              </p>

              {generalError ? (
                <div className={styles.alert} role="alert">
                  {generalError}
                </div>
              ) : null}

              {forgotMessage ? (
                <div className={styles.success} role="status">
                  {forgotMessage}
                </div>
              ) : null}

              <button className={styles.submitButton} type="submit" disabled={isSendingReset}>
                {isSendingReset ? 'Sending reset...' : 'Send reset link'}
              </button>
            </form>
          )}
        </div>
      </div>
    </section>
  );
}
