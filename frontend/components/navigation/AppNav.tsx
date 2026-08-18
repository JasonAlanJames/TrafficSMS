'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState } from 'react';

import { useAuth } from '../auth/AuthProvider';
import styles from './appNav.module.css';

function isActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export default function AppNav() {
  const pathname = usePathname();
  const router = useRouter();
  const { initialized, isAuthenticated, isRefreshing, user, logout } = useAuth();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  async function handleLogout() {
    setIsLoggingOut(true);

    try {
      await logout();
      router.push('/login');
    } finally {
      setIsLoggingOut(false);
    }
  }

  return (
    <nav className={styles.nav}>
      <div className={styles.brandBlock}>
        <Link className={styles.brand} href="/">
          TrafficSMS
        </Link>
        <span className={styles.tagline}>Live roadway intelligence, built for SMS-first commuters.</span>
      </div>

      <div className={styles.links}>
        <Link className={isActive(pathname, '/pricing') ? styles.linkActive : styles.link} href="/pricing">
          Pricing
        </Link>
        <Link className={isActive(pathname, '/sms-opt-in') ? styles.linkActive : styles.link} href="/sms-opt-in">
          Register
        </Link>
        <Link className={isActive(pathname, '/dashboard') ? styles.linkActive : styles.link} href="/dashboard">
          Dashboard
        </Link>

        {!initialized ? (
          <span className={styles.statusPill}>Loading session...</span>
        ) : isAuthenticated ? (
          <div className={styles.sessionRow}>
            <span className={styles.statusPill}>
              {isRefreshing ? 'Refreshing session' : user?.email ?? 'Signed in'}
            </span>
            <button
              className={styles.button}
              type="button"
              onClick={() => void handleLogout()}
              disabled={isLoggingOut}
            >
              {isLoggingOut ? 'Signing out...' : 'Sign out'}
            </button>
          </div>
        ) : (
          <Link className={styles.button} href="/login">
            Sign in
          </Link>
        )}
      </div>
    </nav>
  );
}
