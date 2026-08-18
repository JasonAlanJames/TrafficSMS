import type { AuthenticatedUser, AuthenticationResponse, TokenResponse } from './api';

export type SessionStorageMode = 'local' | 'session';

export type AuthSession = {
  user: AuthenticatedUser;
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
  storage: SessionStorageMode;
};

const STORAGE_KEYS: Record<SessionStorageMode, string> = {
  local: 'trafficsms.auth.local',
  session: 'trafficsms.auth.session',
};

function isBrowser(): boolean {
  return typeof window !== 'undefined';
}

function serializeSession(session: AuthSession): string {
  return JSON.stringify(session);
}

function parseSession(value: string | null): AuthSession | null {
  if (!value) {
    return null;
  }

  try {
    return JSON.parse(value) as AuthSession;
  } catch {
    return null;
  }
}

function getStorage(mode: SessionStorageMode): Storage | null {
  if (!isBrowser()) {
    return null;
  }

  return mode === 'local' ? window.localStorage : window.sessionStorage;
}

export function buildSession(
  auth: AuthenticationResponse | TokenResponse,
  user: AuthenticatedUser,
  storage: SessionStorageMode,
): AuthSession {
  return {
    user,
    accessToken: auth.access_token,
    refreshToken: auth.refresh_token,
    expiresAt: Date.now() + auth.expires_in * 1000,
    storage,
  };
}

export function saveSession(session: AuthSession): void {
  for (const mode of Object.keys(STORAGE_KEYS) as SessionStorageMode[]) {
    getStorage(mode)?.removeItem(STORAGE_KEYS[mode]);
  }

  getStorage(session.storage)?.setItem(STORAGE_KEYS[session.storage], serializeSession(session));
}

export function loadSession(): AuthSession | null {
  for (const mode of ['local', 'session'] as SessionStorageMode[]) {
    const session = parseSession(getStorage(mode)?.getItem(STORAGE_KEYS[mode]) ?? null);

    if (session) {
      return session;
    }
  }

  return null;
}

export function clearSession(): void {
  for (const mode of Object.keys(STORAGE_KEYS) as SessionStorageMode[]) {
    getStorage(mode)?.removeItem(STORAGE_KEYS[mode]);
  }
}

export function isSessionExpiringSoon(session: AuthSession, thresholdMs = 60_000): boolean {
  return session.expiresAt <= Date.now() + thresholdMs;
}
