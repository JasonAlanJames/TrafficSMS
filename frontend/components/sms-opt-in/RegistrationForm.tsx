'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { startTransition, useState, type FormEvent } from 'react';

import { ApiError, register } from '../../lib/api';
import { getPasswordRequirements, getPasswordStrength } from '../../lib/password';
import { formatPhoneInput, normalizeUsPhoneNumber } from '../../lib/phone';
import styles from './smsOptIn.module.css';

type FormState = {
  email: string;
  password: string;
  confirmPassword: string;
  phoneNumber: string;
  smsConsent: boolean;
  marketingConsent: boolean;
};

type FieldName = 'email' | 'password' | 'confirmPassword' | 'phoneNumber' | 'smsConsent';
type FieldErrors = Partial<Record<FieldName, string>>;
type TouchedState = Partial<Record<FieldName, boolean>>;

const initialState: FormState = {
  email: '',
  password: '',
  confirmPassword: '',
  phoneNumber: '',
  smsConsent: false,
  marketingConsent: false,
};

function isValidEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function validateForm(form: FormState): FieldErrors {
  const errors: FieldErrors = {};

  if (!form.email.trim()) {
    errors.email = 'Enter your email address.';
  } else if (!isValidEmail(form.email.trim())) {
    errors.email = 'Enter a valid email address.';
  }

  if (getPasswordRequirements(form.password).some((requirement) => !requirement.satisfied)) {
    errors.password = 'Choose a password that meets all requirements.';
  }

  if (!form.confirmPassword) {
    errors.confirmPassword = 'Confirm your password.';
  } else if (form.confirmPassword !== form.password) {
    errors.confirmPassword = 'Passwords do not match.';
  }

  if (!normalizeUsPhoneNumber(form.phoneNumber)) {
    errors.phoneNumber = 'Enter a valid US mobile number.';
  }

  if (!form.smsConsent) {
    errors.smsConsent = 'You must agree to receive SMS messages to create an account.';
  }

  return errors;
}

function mapRegistrationError(error: unknown): { field?: FieldName; message: string } {
  if (error instanceof ApiError) {
    const message = error.message.toLowerCase();

    if (error.status === 409 || message.includes('already exists') || message.includes('already registered')) {
      return {
        field: 'email',
        message: 'An account with this email already exists.',
      };
    }

    if (message.includes('weak password') || message.includes('password')) {
      return {
        field: 'password',
        message: 'Choose a stronger password that meets every requirement.',
      };
    }

    if (message.includes('phone')) {
      return {
        field: 'phoneNumber',
        message: 'Enter a valid mobile number to continue.',
      };
    }

    return {
      message: error.message || 'Unable to create your account right now.',
    };
  }

  if (error instanceof TypeError) {
    return {
      message: 'We could not reach TrafficSMS. Check your connection and try again.',
    };
  }

  return {
    message: 'Something unexpected happened. Please try again in a moment.',
  };
}

export default function RegistrationForm() {
  const router = useRouter();
  const [form, setForm] = useState<FormState>(initialState);
  const [touched, setTouched] = useState<TouchedState>({});
  const [serverErrors, setServerErrors] = useState<FieldErrors>({});
  const [generalError, setGeneralError] = useState('');
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const requirements = getPasswordRequirements(form.password);
  const passwordStrength = getPasswordStrength(form.password);
  const clientErrors = validateForm(form);
  const normalizedPhoneNumber = normalizeUsPhoneNumber(form.phoneNumber);
  const confirmStarted = form.confirmPassword.length > 0;
  const passwordMatch = confirmStarted && form.confirmPassword === form.password;

  function markTouched(field: FieldName) {
    setTouched((current) => ({ ...current, [field]: true }));
  }

  function updateField<K extends keyof FormState>(field: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [field]: value }));
    setGeneralError('');

    if (field === 'email' || field === 'password' || field === 'confirmPassword' || field === 'phoneNumber' || field === 'smsConsent') {
      setServerErrors((current) => {
        const next = { ...current };
        const errorField = field as FieldName;
        delete next[errorField];

        if (field === 'password') {
          delete next.confirmPassword;
        }

        return next;
      });
    }
  }

  function getDisplayedError(field: FieldName): string | undefined {
    if (serverErrors[field]) {
      return serverErrors[field];
    }

    if (!hasSubmitted && !touched[field]) {
      return undefined;
    }

    return clientErrors[field];
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setHasSubmitted(true);
    setGeneralError('');

    const nextErrors = validateForm(form);

    if (Object.keys(nextErrors).length > 0 || !normalizedPhoneNumber || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setServerErrors({});

    try {
      await register({
        email: form.email.trim(),
        password: form.password,
        phone_number: normalizedPhoneNumber,
        sms_consent: form.smsConsent,
        marketing_consent: form.marketingConsent,
      });

      startTransition(() => {
        router.push('/sms-opt-in/success');
      });
    } catch (error) {
      const mappedError = mapRegistrationError(error);

      if (mappedError.field) {
        setServerErrors({ [mappedError.field]: mappedError.message });
        markTouched(mappedError.field);
      } else {
        setGeneralError(mappedError.message);
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  const passwordError = getDisplayedError('password');
  const confirmError = getDisplayedError('confirmPassword');
  const emailError = getDisplayedError('email');
  const phoneError = getDisplayedError('phoneNumber');
  const smsConsentError = getDisplayedError('smsConsent');

  return (
    <div className={styles.formCard}>
      <div className={styles.formHeader}>
        <span className={styles.formEyebrow}>Registration Card</span>
        <h2 className={styles.formTitle}>Create your free account</h2>
        <p className={styles.formSubtitle}>
          Secure your TrafficSMS login now. Saved routes, preferences, and subscription setup come next after email verification.
        </p>
      </div>

      <form onSubmit={handleSubmit} noValidate aria-describedby={generalError ? 'registration-error' : undefined}>
        <fieldset disabled={isSubmitting} style={{ margin: 0, padding: 0, border: 0 }}>
          <div className={styles.fieldGroup}>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="email">
                Email Address
              </label>
              <input
                id="email"
                className={`${styles.input}${emailError ? ` ${styles.inputError}` : ''}`}
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                value={form.email}
                onBlur={() => markTouched('email')}
                onChange={(event) => updateField('email', event.target.value)}
                aria-invalid={emailError ? 'true' : 'false'}
                aria-describedby={emailError ? 'email-error' : undefined}
              />
              {emailError ? (
                <p className={styles.errorText} id="email-error">
                  {emailError}
                </p>
              ) : null}
            </div>

            <div className={styles.field}>
              <div className={styles.labelRow}>
                <label className={styles.label} htmlFor="password">
                  Password
                </label>
                <span className={styles.fieldHint}>Minimum 8 characters</span>
              </div>
              <input
                id="password"
                className={`${styles.input}${passwordError ? ` ${styles.inputError}` : ''}`}
                type="password"
                autoComplete="new-password"
                placeholder="Create a strong password"
                value={form.password}
                onBlur={() => markTouched('password')}
                onChange={(event) => updateField('password', event.target.value)}
                aria-invalid={passwordError ? 'true' : 'false'}
                aria-describedby={passwordError ? 'password-error' : 'password-help'}
              />
              <div className={styles.passwordPanel} id="password-help">
                <div className={styles.passwordMeterRow}>
                  <span className={styles.strengthLabel}>Password strength</span>
                  <span className={styles.strengthValue}>{passwordStrength.label}</span>
                </div>
                <div className={styles.meter} aria-hidden="true">
                  {[0, 1, 2, 3].map((index) => {
                    let className = styles.meterBar;

                    if (passwordStrength.score > index) {
                      className =
                        passwordStrength.label === 'Strong'
                          ? `${styles.meterBar} ${styles.meterBarActiveStrong}`
                          : passwordStrength.label === 'Fair'
                            ? `${styles.meterBar} ${styles.meterBarActiveFair}`
                            : `${styles.meterBar} ${styles.meterBarActiveWeak}`;
                    }

                    return <span key={index} className={className} />;
                  })}
                </div>
                <ul className={styles.requirementList}>
                  {requirements.map((requirement) => (
                    <li
                      key={requirement.key}
                      className={`${styles.requirementItem}${requirement.satisfied ? ` ${styles.requirementMet}` : ''}`}
                    >
                      <span className={styles.iconBadge} aria-hidden="true">
                        <svg viewBox="0 0 16 16" width="12" height="12" fill="none">
                          <path d="M3 8.2 6.1 11 13 4.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      </span>
                      <span>{requirement.label}</span>
                    </li>
                  ))}
                </ul>
              </div>
              {passwordError ? (
                <p className={styles.errorText} id="password-error">
                  {passwordError}
                </p>
              ) : null}
            </div>

            <div className={styles.field}>
              <label className={styles.label} htmlFor="confirm-password">
                Confirm Password
              </label>
              <input
                id="confirm-password"
                className={`${styles.input}${confirmError ? ` ${styles.inputError}` : ''}`}
                type="password"
                autoComplete="new-password"
                placeholder="Re-enter your password"
                value={form.confirmPassword}
                onBlur={() => markTouched('confirmPassword')}
                onChange={(event) => updateField('confirmPassword', event.target.value)}
                aria-invalid={confirmError ? 'true' : 'false'}
                aria-describedby={confirmError ? 'confirm-password-error' : confirmStarted ? 'confirm-password-status' : undefined}
              />
              {confirmStarted ? (
                <p
                  className={`${styles.matchText}${passwordMatch ? ` ${styles.matchSuccess}` : ` ${styles.matchError}`}`}
                  id="confirm-password-status"
                >
                  {passwordMatch ? 'Passwords Match' : 'Passwords Do Not Match'}
                </p>
              ) : null}
              {confirmError ? (
                <p className={styles.errorText} id="confirm-password-error">
                  {confirmError}
                </p>
              ) : null}
            </div>

            <div className={styles.field}>
              <div className={styles.labelRow}>
                <label className={styles.label} htmlFor="phone-number">
                  Mobile Phone Number
                </label>
                <span className={styles.fieldHint}>Stored as +1 E.164</span>
              </div>
              <input
                id="phone-number"
                className={`${styles.input}${phoneError ? ` ${styles.inputError}` : ''}`}
                type="tel"
                autoComplete="tel"
                inputMode="tel"
                placeholder="(714) 555-1234"
                value={form.phoneNumber}
                onBlur={() => markTouched('phoneNumber')}
                onChange={(event) => updateField('phoneNumber', formatPhoneInput(event.target.value))}
                aria-invalid={phoneError ? 'true' : 'false'}
                aria-describedby={phoneError ? 'phone-error' : 'phone-help'}
              />
              <p className={styles.helperText} id="phone-help">
                US numbers only for now. You do not need to type +1 manually.
              </p>
              {phoneError ? (
                <p className={styles.errorText} id="phone-error">
                  {phoneError}
                </p>
              ) : null}
            </div>

            <div className={styles.consentSection}>
              <h3 className={styles.consentTitle}>SMS Consent Section</h3>

              <div className={styles.checkboxCard}>
                <div className={styles.checkboxRow}>
                  <input
                    id="sms-consent"
                    className={styles.checkbox}
                    type="checkbox"
                    checked={form.smsConsent}
                    onBlur={() => markTouched('smsConsent')}
                    onChange={(event) => updateField('smsConsent', event.target.checked)}
                    aria-invalid={smsConsentError ? 'true' : 'false'}
                    aria-describedby={smsConsentError ? 'sms-consent-error' : 'sms-consent-copy'}
                  />
                  <div>
                    <label className={styles.checkboxLabel} htmlFor="sms-consent">
                      I agree to receive SMS messages from TrafficSMS.
                    </label>
                    <div className={styles.requiredTag}>Required to create your account</div>
                  </div>
                </div>
                {smsConsentError ? (
                  <p className={styles.errorText} id="sms-consent-error">
                    {smsConsentError}
                  </p>
                ) : null}
              </div>

              <div className={styles.disclosure} id="sms-consent-copy">
                By checking the box above and creating an account, you consent to receive SMS messages from TrafficSMS related to your account, requested traffic information, service notifications, subscription status, and customer support. Message frequency varies based on your requests and account activity. Message and data rates may apply. Reply STOP to unsubscribe at any time. Reply HELP for assistance. Consent is not a condition of purchase.
              </div>

              <div className={styles.legalLinks} aria-label="Legal links">
                <a className={styles.legalLink} href="https://trafficsms.com/privacy">
                  Privacy Policy
                </a>
                <a className={styles.legalLink} href="https://trafficsms.com/terms">
                  Terms of Service
                </a>
              </div>

              <div className={styles.checkboxCard}>
                <div className={styles.checkboxRow}>
                  <input
                    id="marketing-consent"
                    className={styles.checkbox}
                    type="checkbox"
                    checked={form.marketingConsent}
                    onChange={(event) => updateField('marketingConsent', event.target.checked)}
                    aria-describedby="marketing-consent-copy"
                  />
                  <label className={styles.checkboxLabel} htmlFor="marketing-consent" id="marketing-consent-copy">
                    Send me occasional product updates and new feature announcements.
                  </label>
                </div>
              </div>
            </div>

            {generalError ? (
              <div className={styles.alert} id="registration-error" role="alert">
                {generalError}
              </div>
            ) : null}

            <div className={styles.submitRow}>
              <button className={styles.button} type="submit" disabled={isSubmitting}>
                <span className={styles.buttonLabel}>
                  {isSubmitting ? <span className={styles.spinner} aria-hidden="true" /> : null}
                  <span>{isSubmitting ? 'Creating Account...' : 'Create Free Account'}</span>
                </span>
              </button>

              <div className={styles.signInRow}>
                <span>Already have an account?</span>
                <Link className={styles.loginLink} href="/login">
                  Sign In
                </Link>
              </div>
            </div>
          </div>
        </fieldset>
      </form>
    </div>
  );
}
