'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { startTransition, useEffect, useMemo, useState, type FormEvent } from 'react';

import { useAuth } from '../../components/auth/AuthProvider';
import {
  ApiError,
  cancelSubscription,
  changeEmail,
  changePassword,
  changePhone,
  changePlan,
  createCustomerPortal,
  getBillingHistory,
  getBillingSubscription,
  getCurrentUser,
  listSessions,
  reconcileSubscription,
  resendVerification,
  revokeSession,
  updateCurrentUserProfile,
  type AuthenticatedUser,
  type BillingEvent,
  type BillingPlan,
  type SessionInfo,
  type SubscriptionSummary,
} from '../../lib/api';
import styles from './dashboard.module.css';

type ProfileFormState = {
  home_location: string;
  work_location: string;
  gym_location: string;
  school_location: string;
  default_state: string;
  default_country: string;
};

function formatDateTime(value: string | null): string {
  if (!value) {
    return 'Not available';
  }

  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function formatMoney(amountCents: number | null, currency: string | null): string {
  if (amountCents === null || !currency) {
    return 'N/A';
  }

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
  }).format(amountCents / 100);
}

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function labelForNextPlan(currentPlan: string): BillingPlan {
  return currentPlan === 'standard' ? 'unlimited' : 'standard';
}

function toNullable(value: string): string | null {
  const normalized = value.trim();
  return normalized ? normalized : null;
}

function buildDerivedRoutes(user: AuthenticatedUser | null): string[] {
  if (!user) {
    return [];
  }

  const routes: string[] = [];
  const home = user.home_location?.trim();
  const work = user.work_location?.trim();
  const gym = user.gym_location?.trim();
  const school = user.school_location?.trim();

  if (home && work) {
    routes.push(`Home to Work: ${home} -> ${work}`);
  }

  if (home && gym) {
    routes.push(`Home to Gym: ${home} -> ${gym}`);
  }

  if (home && school) {
    routes.push(`Home to School: ${home} -> ${school}`);
  }

  if (work && home) {
    routes.push(`Work to Home: ${work} -> ${home}`);
  }

  return routes;
}

function mapApiMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError || error instanceof Error) {
    return error.message;
  }

  return fallback;
}

export default function DashboardPage() {
  const router = useRouter();
  const {
    initialized,
    isAuthenticated,
    isRefreshing,
    logout,
    logoutAll,
    session,
    user,
  } = useAuth();

  const [accountUser, setAccountUser] = useState<AuthenticatedUser | null>(user);
  const [subscription, setSubscription] = useState<SubscriptionSummary | null>(null);
  const [history, setHistory] = useState<BillingEvent[]>([]);
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [pageMessage, setPageMessage] = useState<string | null>(null);
  const [billingError, setBillingError] = useState<string | null>(null);
  const [billingMessage, setBillingMessage] = useState<string | null>(null);
  const [profileMessage, setProfileMessage] = useState<string | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [securityMessage, setSecurityMessage] = useState<string | null>(null);
  const [securityError, setSecurityError] = useState<string | null>(null);
  const [verificationMessage, setVerificationMessage] = useState<string | null>(null);
  const [verificationError, setVerificationError] = useState<string | null>(null);
  const [profileBusy, setProfileBusy] = useState(false);
  const [verificationBusy, setVerificationBusy] = useState(false);
  const [billingAction, setBillingAction] = useState<'portal' | 'plan' | 'cancel' | 'reconcile' | null>(null);
  const [securityAction, setSecurityAction] = useState<'password' | 'email' | 'phone' | 'logout-all' | null>(null);
  const [revokingSessionId, setRevokingSessionId] = useState<string | null>(null);

  const [profileForm, setProfileForm] = useState<ProfileFormState>({
    home_location: '',
    work_location: '',
    gym_location: '',
    school_location: '',
    default_state: '',
    default_country: 'US',
  });
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
  });
  const [emailForm, setEmailForm] = useState({
    new_email: '',
    current_password: '',
  });
  const [phoneForm, setPhoneForm] = useState({
    phone_number: accountUser?.phone_e164 ?? '',
    current_password: '',
  });

  useEffect(() => {
    setAccountUser(user);
  }, [user]);

  useEffect(() => {
    if (!accountUser) {
      return;
    }

    setProfileForm({
      home_location: accountUser.home_location ?? '',
      work_location: accountUser.work_location ?? '',
      gym_location: accountUser.gym_location ?? '',
      school_location: accountUser.school_location ?? '',
      default_state: accountUser.default_state ?? '',
      default_country: accountUser.default_country ?? 'US',
    });
    setPhoneForm((current) => ({
      ...current,
      phone_number: accountUser.phone_e164 ?? '',
    }));
  }, [accountUser]);

  useEffect(() => {
    if (!initialized) {
      return;
    }

    if (!isAuthenticated) {
      router.replace('/login');
    }
  }, [initialized, isAuthenticated, router]);

  async function handleAuthFailure() {
    await logout();
    startTransition(() => {
      router.replace('/login?reason=session-expired');
    });
  }

  async function loadAccountData(options?: { reconcile?: boolean; checkoutState?: string | null }) {
    const accessToken = session?.accessToken;

    if (!accessToken) {
      return;
    }

    setIsLoading(true);
    setPageError(null);

    try {
      let nextSubscription: SubscriptionSummary | null = null;

      if (options?.reconcile) {
        const reconciliation = await reconcileSubscription(accessToken);
        nextSubscription = reconciliation.subscription;
        setBillingMessage(reconciliation.message);
      }

      const [nextUser, resolvedSubscription, nextHistory, nextSessions] = await Promise.all([
        getCurrentUser(accessToken),
        nextSubscription ? Promise.resolve(nextSubscription) : getBillingSubscription(accessToken),
        getBillingHistory(accessToken),
        listSessions(accessToken),
      ]);

      setAccountUser(nextUser);
      setSubscription(resolvedSubscription);
      setHistory(nextHistory);
      setSessions(nextSessions);

      if (options?.checkoutState === 'success') {
        setPageMessage('Stripe checkout completed on August 17, 2026. TrafficSMS refreshed your billing state from Stripe.');
      } else if (options?.checkoutState === 'canceled') {
        setPageMessage('Checkout was canceled on August 17, 2026. Your subscription did not change.');
      } else {
        setPageMessage(null);
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        await handleAuthFailure();
        return;
      }

      setPageError(mapApiMessage(error, 'Unable to load your account center right now.'));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    const accessToken = session?.accessToken;

    if (!initialized || !isAuthenticated || !accessToken) {
      return;
    }

    let cancelled = false;

    async function load() {
      const currentCheckoutState =
        typeof window === 'undefined'
          ? null
          : new URLSearchParams(window.location.search).get('checkout');

      await loadAccountData({
        reconcile: currentCheckoutState === 'success',
        checkoutState: currentCheckoutState,
      });

      if (!cancelled && currentCheckoutState) {
        startTransition(() => {
          router.replace('/dashboard');
        });
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [initialized, isAuthenticated, router, session?.accessToken]);

  const derivedRoutes = useMemo(() => buildDerivedRoutes(accountUser), [accountUser]);
  const nextPlan = useMemo(() => {
    if (!subscription || subscription.plan === 'free') {
      return 'standard';
    }

    return labelForNextPlan(subscription.plan);
  }, [subscription]);

  async function syncSessionUser() {
    if (!session?.accessToken) {
      return;
    }

    const nextUser = await getCurrentUser(session.accessToken);
    setAccountUser(nextUser);
  }

  async function handleProfileSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!session?.accessToken) {
      return;
    }

    setProfileBusy(true);
    setProfileMessage(null);
    setProfileError(null);

    try {
      const updated = await updateCurrentUserProfile(session.accessToken, {
        home_location: toNullable(profileForm.home_location),
        work_location: toNullable(profileForm.work_location),
        gym_location: toNullable(profileForm.gym_location),
        school_location: toNullable(profileForm.school_location),
        default_state: toNullable(profileForm.default_state)?.toUpperCase() ?? null,
        default_country: toNullable(profileForm.default_country)?.toUpperCase() ?? null,
      });
      setAccountUser(updated);
      setProfileMessage('Profile saved successfully.');
      await syncSessionUser();
    } catch (error) {
      setProfileError(mapApiMessage(error, 'Unable to save your profile right now.'));
    } finally {
      setProfileBusy(false);
    }
  }

  async function handleResendVerification() {
    const email = accountUser?.email;

    if (!email) {
      return;
    }

    setVerificationBusy(true);
    setVerificationMessage(null);
    setVerificationError(null);

    try {
      const response = await resendVerification(email);
      setVerificationMessage(response.message);
    } catch (error) {
      setVerificationError(mapApiMessage(error, 'Unable to resend verification right now.'));
    } finally {
      setVerificationBusy(false);
    }
  }

  async function handleChangePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!session?.accessToken) {
      return;
    }

    setSecurityAction('password');
    setSecurityMessage(null);
    setSecurityError(null);

    try {
      const response = await changePassword(session.accessToken, passwordForm);
      setSecurityMessage(response.message);
      setPasswordForm({
        current_password: '',
        new_password: '',
      });
      await logout();
      startTransition(() => {
        router.replace('/login?reason=password-updated');
      });
    } catch (error) {
      setSecurityError(mapApiMessage(error, 'Unable to update your password right now.'));
    } finally {
      setSecurityAction(null);
    }
  }

  async function handleChangeEmail(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!session?.accessToken) {
      return;
    }

    setSecurityAction('email');
    setSecurityMessage(null);
    setSecurityError(null);

    try {
      const response = await changeEmail(session.accessToken, {
        new_email: emailForm.new_email.trim(),
        current_password: emailForm.current_password,
      });
      setSecurityMessage(response.message);
      setEmailForm({
        new_email: '',
        current_password: '',
      });
      await syncSessionUser();
    } catch (error) {
      setSecurityError(mapApiMessage(error, 'Unable to request an email change right now.'));
    } finally {
      setSecurityAction(null);
    }
  }

  async function handleChangePhone(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!session?.accessToken) {
      return;
    }

    setSecurityAction('phone');
    setSecurityMessage(null);
    setSecurityError(null);

    try {
      const updated = await changePhone(session.accessToken, {
        phone_number: phoneForm.phone_number.trim(),
        current_password: phoneForm.current_password,
      });
      setAccountUser(updated);
      setPhoneForm((current) => ({
        ...current,
        current_password: '',
      }));
      setSecurityMessage('Phone number updated and marked unverified.');
      await syncSessionUser();
    } catch (error) {
      setSecurityError(mapApiMessage(error, 'Unable to update your phone number right now.'));
    } finally {
      setSecurityAction(null);
    }
  }

  async function handleLogoutAll() {
    setSecurityAction('logout-all');
    setSecurityMessage(null);
    setSecurityError(null);

    try {
      await logoutAll();
      startTransition(() => {
        router.replace('/login?reason=logout-all');
      });
    } catch (error) {
      setSecurityError(mapApiMessage(error, 'Unable to sign out all devices right now.'));
    } finally {
      setSecurityAction(null);
    }
  }

  async function handleManageSubscription() {
    if (!session?.accessToken) {
      return;
    }

    setBillingAction('portal');
    setBillingError(null);

    try {
      const portal = await createCustomerPortal(session.accessToken);
      window.location.assign(portal.url);
    } catch (error) {
      setBillingError(mapApiMessage(error, 'Unable to open the Stripe billing portal.'));
    } finally {
      setBillingAction(null);
    }
  }

  async function handlePlanChange() {
    if (!session?.accessToken) {
      return;
    }

    if (!subscription || subscription.plan === 'free' || !subscription.stripe_subscription_id) {
      router.push('/pricing');
      return;
    }

    setBillingAction('plan');
    setBillingError(null);
    setBillingMessage(null);

    try {
      const nextSubscription = await changePlan(session.accessToken, nextPlan);
      setSubscription(nextSubscription);
      setBillingMessage(`Plan updated to ${nextPlan}.`);
      await loadAccountData();
    } catch (error) {
      setBillingError(mapApiMessage(error, 'Unable to change your subscription plan.'));
    } finally {
      setBillingAction(null);
    }
  }

  async function handleCancelSubscription() {
    if (!session?.accessToken) {
      return;
    }

    if (!subscription?.stripe_subscription_id) {
      router.push('/pricing');
      return;
    }

    setBillingAction('cancel');
    setBillingError(null);
    setBillingMessage(null);

    try {
      const nextSubscription = await cancelSubscription(session.accessToken, true);
      setSubscription(nextSubscription);
      setBillingMessage('Subscription will cancel at the end of the current billing period.');
      await loadAccountData();
    } catch (error) {
      setBillingError(mapApiMessage(error, 'Unable to update cancellation settings.'));
    } finally {
      setBillingAction(null);
    }
  }

  async function handleReconcileBilling() {
    if (!session?.accessToken) {
      return;
    }

    setBillingAction('reconcile');
    setBillingError(null);
    setBillingMessage(null);

    try {
      const response = await reconcileSubscription(session.accessToken);
      setSubscription(response.subscription);
      setBillingMessage(response.message);
      await loadAccountData();
    } catch (error) {
      setBillingError(mapApiMessage(error, 'Unable to reconcile billing with Stripe right now.'));
    } finally {
      setBillingAction(null);
    }
  }

  async function handleRevokeSession(targetSession: SessionInfo) {
    if (!session?.accessToken) {
      return;
    }

    setRevokingSessionId(targetSession.id);
    setSecurityMessage(null);
    setSecurityError(null);

    try {
      await revokeSession(session.accessToken, targetSession.id);

      if (targetSession.is_current) {
        await logout();
        startTransition(() => {
          router.replace('/login?reason=session-revoked');
        });
        return;
      }

      setSessions((current) => current.filter((sessionItem) => sessionItem.id !== targetSession.id));
      setSecurityMessage('Session revoked successfully.');
    } catch (error) {
      setSecurityError(mapApiMessage(error, 'Unable to revoke that session right now.'));
    } finally {
      setRevokingSessionId(null);
    }
  }

  if (!initialized) {
    return (
      <section className="hero">
        <div className={`card ${styles.centerCard}`}>
          <span className="pill">Account Center</span>
          <h1>Restoring your TrafficSMS session</h1>
          <p className="muted">Preparing your subscription, security, and saved location data.</p>
        </div>
      </section>
    );
  }

  if (!isAuthenticated || !session?.accessToken || !accountUser) {
    return null;
  }

  return (
    <section className="hero">
      <div className={styles.heroCard}>
        <div>
          <span className="pill">TrafficSMS Account Center</span>
          <h1 className={styles.title}>Manage subscription access, saved commute data, and every active device from one place.</h1>
          <p className={styles.subtitle}>
            Signed in as <strong>{accountUser.email}</strong>. Session state is{' '}
            <strong>{isRefreshing ? 'refreshing' : 'active'}</strong>, and billing data is{' '}
            <strong>{isLoading ? 'syncing' : 'current'}</strong>.
          </p>
        </div>
        <div className={styles.heroActions}>
          <Link className="cta" href="/pricing">
            View plans
          </Link>
          <button className="ghostButton" type="button" onClick={() => void handleReconcileBilling()} disabled={billingAction !== null}>
            {billingAction === 'reconcile' ? 'Reconciling...' : 'Reconcile billing'}
          </button>
        </div>
      </div>

      {pageMessage ? <div className="statusMessage">{pageMessage}</div> : null}
      {pageError ? <div className="errorMessage">{pageError}</div> : null}

      <div className={styles.summaryGrid}>
        <article className={`card ${styles.metricCard}`}>
          <span className={styles.metricLabel}>Plan</span>
          <strong className={styles.metricValue}>{subscription?.plan ?? accountUser.subscription_plan ?? 'free'}</strong>
          <span className="muted">Status: {subscription?.status ?? accountUser.subscription_status}</span>
        </article>

        <article className={`card ${styles.metricCard}`}>
          <span className={styles.metricLabel}>Remaining SMS</span>
          <strong className={styles.metricValue}>{subscription?.usage.remaining_sms ?? 0}</strong>
          <span className="muted">Allowance: {subscription?.usage.sms_allowance ?? 0} per billing period</span>
        </article>

        <article className={`card ${styles.metricCard}`}>
          <span className={styles.metricLabel}>Renewal</span>
          <strong className={styles.metricValueSmall}>{formatDateTime(subscription?.renewal_date ?? null)}</strong>
          <span className="muted">Grace ends: {formatDateTime(subscription?.grace_period_end ?? null)}</span>
        </article>

        <article className={`card ${styles.metricCard}`}>
          <span className={styles.metricLabel}>Verification</span>
          <strong className={styles.metricValueSmall}>
            {accountUser.email_verified ? 'Email verified' : 'Email unverified'}
          </strong>
          <span className="muted">
            {accountUser.phone_verified ? 'Phone verified' : 'Phone verification pending'}
          </span>
        </article>
      </div>

      <div className={styles.mainGrid}>
        <article className={`card ${styles.panel}`}>
          <div className={styles.panelHeader}>
            <div>
              <h2>Subscription and usage</h2>
              <p className="muted">Stripe status, quota tracking, and access state for your current billing cycle.</p>
            </div>
          </div>

          {billingMessage ? <div className="statusMessage">{billingMessage}</div> : null}
          {billingError ? <div className="errorMessage">{billingError}</div> : null}

          <div className={styles.detailGrid}>
            <div>
              <span className={styles.detailLabel}>Current period</span>
              <strong>{formatDateTime(subscription?.current_period_start ?? null)}</strong>
              <span className="muted">to {formatDateTime(subscription?.current_period_end ?? null)}</span>
            </div>
            <div>
              <span className={styles.detailLabel}>Web access</span>
              <strong>{subscription?.web_access_enabled ? 'Enabled' : 'Restricted'}</strong>
              <span className="muted">Trial end: {formatDateTime(subscription?.trial_end ?? null)}</span>
            </div>
            <div>
              <span className={styles.detailLabel}>SMS used</span>
              <strong>
                {subscription?.usage.sms_used ?? 0} / {subscription?.usage.sms_allowance ?? 0}
              </strong>
              <span className="muted">Progress: {formatPercent(subscription?.usage.progress_ratio ?? 0)}</span>
            </div>
            <div>
              <span className={styles.detailLabel}>Reset timestamp</span>
              <strong>{formatDateTime(subscription?.usage.reset_at ?? null)}</strong>
              <span className="muted">Cancel at period end: {subscription?.cancel_at_period_end ? 'Yes' : 'No'}</span>
            </div>
          </div>

          <div className={styles.progressBlock}>
            <div className={styles.progressHeader}>
              <span>Usage progress</span>
              <strong>{formatPercent(subscription?.usage.progress_ratio ?? 0)}</strong>
            </div>
            <progress
              className={styles.progressBar}
              max={100}
              value={Math.round((subscription?.usage.progress_ratio ?? 0) * 100)}
            />
          </div>

          <div className="actionRow">
            <button className="cta" type="button" onClick={() => void handleManageSubscription()} disabled={billingAction !== null}>
              {billingAction === 'portal' ? 'Opening...' : 'Open Stripe portal'}
            </button>
            <button className="ghostButton" type="button" onClick={() => void handlePlanChange()} disabled={billingAction !== null}>
              {billingAction === 'plan'
                ? 'Updating...'
                : subscription?.plan === 'free'
                  ? 'Upgrade plan'
                  : `Switch to ${nextPlan}`}
            </button>
            <button className="ghostButton" type="button" onClick={() => void handleCancelSubscription()} disabled={billingAction !== null}>
              {billingAction === 'cancel' ? 'Saving...' : 'Cancel at period end'}
            </button>
          </div>
        </article>

        <article className={`card ${styles.panel}`}>
          <div className={styles.panelHeader}>
            <div>
              <h2>Verification and identity</h2>
              <p className="muted">Track email verification, pending email changes, and phone verification state.</p>
            </div>
          </div>

          {verificationMessage ? <div className="statusMessage">{verificationMessage}</div> : null}
          {verificationError ? <div className="errorMessage">{verificationError}</div> : null}

          <div className={styles.verificationList}>
            <div className={styles.verificationItem}>
              <span className={styles.detailLabel}>Email</span>
              <strong>{accountUser.email}</strong>
              <span className="muted">{accountUser.email_verified ? 'Verified' : 'Verification required'}</span>
            </div>
            <div className={styles.verificationItem}>
              <span className={styles.detailLabel}>Pending email</span>
              <strong>{accountUser.pending_email ?? 'No change pending'}</strong>
              <span className="muted">Confirm the token issued to the new address to finalize the change.</span>
            </div>
            <div className={styles.verificationItem}>
              <span className={styles.detailLabel}>Phone</span>
              <strong>{accountUser.phone_e164 ?? 'Not set'}</strong>
              <span className="muted">
                {accountUser.phone_verified
                  ? 'Verified'
                  : `Pending verification request timestamp: ${formatDateTime(accountUser.phone_verification_requested_at)}`}
              </span>
            </div>
          </div>

          {!accountUser.email_verified ? (
            <div className="actionRow">
              <button className="cta" type="button" onClick={() => void handleResendVerification()} disabled={verificationBusy}>
                {verificationBusy ? 'Sending...' : 'Resend verification email'}
              </button>
            </div>
          ) : null}
        </article>

        <article className={`card ${styles.panel}`}>
          <div className={styles.panelHeader}>
            <div>
              <h2>Saved places and routes</h2>
              <p className="muted">Home, work, gym, and school shortcuts feed your TrafficSMS commute commands.</p>
            </div>
          </div>

          <div className={styles.routeGrid}>
            <div>
              <span className={styles.detailLabel}>Home</span>
              <strong>{accountUser.home_location ?? 'Not saved yet'}</strong>
            </div>
            <div>
              <span className={styles.detailLabel}>Work</span>
              <strong>{accountUser.work_location ?? 'Not saved yet'}</strong>
            </div>
            <div>
              <span className={styles.detailLabel}>Gym</span>
              <strong>{accountUser.gym_location ?? 'Not saved yet'}</strong>
            </div>
            <div>
              <span className={styles.detailLabel}>School</span>
              <strong>{accountUser.school_location ?? 'Not saved yet'}</strong>
            </div>
          </div>

          <div className={styles.routesCard}>
            <span className={styles.detailLabel}>Saved routes ready now</span>
            {derivedRoutes.length === 0 ? (
              <p className="muted">Add at least two saved places to unlock commute-ready route combinations in the dashboard.</p>
            ) : (
              <ul className={styles.routeList}>
                {derivedRoutes.map((routeLabel) => (
                  <li key={routeLabel}>{routeLabel}</li>
                ))}
              </ul>
            )}
          </div>
        </article>

        <article className={`card ${styles.panel}`}>
          <div className={styles.panelHeader}>
            <div>
              <h2>Edit profile</h2>
              <p className="muted">Keep your saved locations and region defaults current for commute and route shortcuts.</p>
            </div>
          </div>

          {profileMessage ? <div className="statusMessage">{profileMessage}</div> : null}
          {profileError ? <div className="errorMessage">{profileError}</div> : null}

          <form className={styles.form} onSubmit={handleProfileSubmit}>
            <div className={styles.formGrid}>
              <label className={styles.field}>
                <span>Home</span>
                <input
                  className="input"
                  value={profileForm.home_location}
                  onChange={(event) => setProfileForm((current) => ({ ...current, home_location: event.target.value }))}
                  placeholder="Corona, CA"
                />
              </label>
              <label className={styles.field}>
                <span>Work</span>
                <input
                  className="input"
                  value={profileForm.work_location}
                  onChange={(event) => setProfileForm((current) => ({ ...current, work_location: event.target.value }))}
                  placeholder="Anaheim, CA"
                />
              </label>
              <label className={styles.field}>
                <span>Gym</span>
                <input
                  className="input"
                  value={profileForm.gym_location}
                  onChange={(event) => setProfileForm((current) => ({ ...current, gym_location: event.target.value }))}
                  placeholder="Riverside, CA"
                />
              </label>
              <label className={styles.field}>
                <span>School</span>
                <input
                  className="input"
                  value={profileForm.school_location}
                  onChange={(event) => setProfileForm((current) => ({ ...current, school_location: event.target.value }))}
                  placeholder="Fullerton, CA"
                />
              </label>
              <label className={styles.field}>
                <span>Default state</span>
                <input
                  className="input"
                  value={profileForm.default_state}
                  onChange={(event) => setProfileForm((current) => ({ ...current, default_state: event.target.value.toUpperCase() }))}
                  maxLength={2}
                  placeholder="CA"
                />
              </label>
              <label className={styles.field}>
                <span>Default country</span>
                <input
                  className="input"
                  value={profileForm.default_country}
                  onChange={(event) => setProfileForm((current) => ({ ...current, default_country: event.target.value.toUpperCase() }))}
                  maxLength={2}
                  placeholder="US"
                />
              </label>
            </div>

            <div className="actionRow">
              <button className="cta" type="submit" disabled={profileBusy}>
                {profileBusy ? 'Saving...' : 'Save profile'}
              </button>
            </div>
          </form>
        </article>

        <article className={`card ${styles.panel}`}>
          <div className={styles.panelHeader}>
            <div>
              <h2>Security controls</h2>
              <p className="muted">Rotate credentials, update contact points, and clear every active session when needed.</p>
            </div>
          </div>

          {securityMessage ? <div className="statusMessage">{securityMessage}</div> : null}
          {securityError ? <div className="errorMessage">{securityError}</div> : null}

          <div className={styles.securityStack}>
            <form className={styles.formSection} onSubmit={handleChangePassword}>
              <h3>Change password</h3>
              <div className={styles.formGrid}>
                <label className={styles.field}>
                  <span>Current password</span>
                  <input
                    className="input"
                    type="password"
                    value={passwordForm.current_password}
                    onChange={(event) => setPasswordForm((current) => ({ ...current, current_password: event.target.value }))}
                    required
                  />
                </label>
                <label className={styles.field}>
                  <span>New password</span>
                  <input
                    className="input"
                    type="password"
                    value={passwordForm.new_password}
                    onChange={(event) => setPasswordForm((current) => ({ ...current, new_password: event.target.value }))}
                    required
                  />
                </label>
              </div>
              <button className="ghostButton" type="submit" disabled={securityAction !== null}>
                {securityAction === 'password' ? 'Updating...' : 'Update password'}
              </button>
            </form>

            <form className={styles.formSection} onSubmit={handleChangeEmail}>
              <h3>Change email</h3>
              <div className={styles.formGrid}>
                <label className={styles.field}>
                  <span>New email</span>
                  <input
                    className="input"
                    type="email"
                    value={emailForm.new_email}
                    onChange={(event) => setEmailForm((current) => ({ ...current, new_email: event.target.value }))}
                    required
                  />
                </label>
                <label className={styles.field}>
                  <span>Current password</span>
                  <input
                    className="input"
                    type="password"
                    value={emailForm.current_password}
                    onChange={(event) => setEmailForm((current) => ({ ...current, current_password: event.target.value }))}
                    required
                  />
                </label>
              </div>
              <button className="ghostButton" type="submit" disabled={securityAction !== null}>
                {securityAction === 'email' ? 'Submitting...' : 'Request email change'}
              </button>
            </form>

            <form className={styles.formSection} onSubmit={handleChangePhone}>
              <h3>Change phone</h3>
              <div className={styles.formGrid}>
                <label className={styles.field}>
                  <span>Phone number</span>
                  <input
                    className="input"
                    value={phoneForm.phone_number}
                    onChange={(event) => setPhoneForm((current) => ({ ...current, phone_number: event.target.value }))}
                    placeholder="+17145551234"
                    required
                  />
                </label>
                <label className={styles.field}>
                  <span>Current password</span>
                  <input
                    className="input"
                    type="password"
                    value={phoneForm.current_password}
                    onChange={(event) => setPhoneForm((current) => ({ ...current, current_password: event.target.value }))}
                    required
                  />
                </label>
              </div>
              <button className="ghostButton" type="submit" disabled={securityAction !== null}>
                {securityAction === 'phone' ? 'Updating...' : 'Update phone'}
              </button>
            </form>

            <div className={styles.formSection}>
              <h3>Global session control</h3>
              <p className="muted">Immediately revoke every session and require a fresh sign-in on all devices.</p>
              <button className="ghostButton" type="button" onClick={() => void handleLogoutAll()} disabled={securityAction !== null}>
                {securityAction === 'logout-all' ? 'Signing out...' : 'Logout all devices'}
              </button>
            </div>
          </div>
        </article>

        <article className={`card ${styles.panel}`}>
          <div className={styles.panelHeader}>
            <div>
              <h2>Recent login sessions</h2>
              <p className="muted">See where your account is active and revoke a single device without logging out everywhere.</p>
            </div>
          </div>

          {sessions.length === 0 ? (
            <p className="muted">No active refresh-token sessions are currently stored for this account.</p>
          ) : (
            <div className={styles.sessionList}>
              {sessions.map((sessionItem) => (
                <div className={styles.sessionItem} key={sessionItem.id}>
                  <div>
                    <div className={styles.sessionTitle}>
                      <strong>{sessionItem.device_name ?? 'Unknown device'}</strong>
                      {sessionItem.is_current ? <span className={styles.currentBadge}>Current</span> : null}
                    </div>
                    <div className="muted">
                      {sessionItem.ip_address ?? 'IP unavailable'} | Last used {formatDateTime(sessionItem.last_used_at ?? sessionItem.created_at)}
                    </div>
                    <div className="muted">
                      Created {formatDateTime(sessionItem.created_at)} | Expires {formatDateTime(sessionItem.expires_at)}
                    </div>
                    {sessionItem.user_agent ? <div className={styles.userAgent}>{sessionItem.user_agent}</div> : null}
                  </div>
                  <button
                    className="ghostButton"
                    type="button"
                    onClick={() => void handleRevokeSession(sessionItem)}
                    disabled={revokingSessionId !== null}
                  >
                    {revokingSessionId === sessionItem.id ? 'Revoking...' : sessionItem.is_current ? 'Revoke this session' : 'Revoke'}
                  </button>
                </div>
              ))}
            </div>
          )}
        </article>

        <article className={`card ${styles.panel} ${styles.fullWidth}`}>
          <div className={styles.panelHeader}>
            <div>
              <h2>Billing history</h2>
              <p className="muted">Stripe checkout, plan changes, cancellations, invoices, and reconciliation activity.</p>
            </div>
          </div>

          {history.length === 0 ? (
            <p className="muted">No billing events have been recorded for this account yet.</p>
          ) : (
            <div className={styles.historyList}>
              {history.map((event) => (
                <div className={styles.historyItem} key={`${event.event_type}-${event.occurred_at}-${event.source}`}>
                  <div>
                    <strong>{event.message ?? event.event_type}</strong>
                    <div className="muted">
                      {formatDateTime(event.occurred_at)} | {event.status ?? 'n/a'} | {event.source}
                    </div>
                  </div>
                  <div className={styles.historyAmount}>{formatMoney(event.amount_cents, event.currency)}</div>
                </div>
              ))}
            </div>
          )}
        </article>
      </div>
    </section>
  );
}
