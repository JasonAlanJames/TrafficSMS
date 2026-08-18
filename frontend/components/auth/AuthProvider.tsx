'use client';

import {
  createContext,
  startTransition,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import {
  ApiError,
  getCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
  logoutAll as logoutAllRequest,
  refreshAccessToken,
  type AuthenticatedUser,
} from '../../lib/api';
import {
  buildSession,
  clearSession,
  isSessionExpiringSoon,
  loadSession,
  saveSession,
  type AuthSession,
  type SessionStorageMode,
} from '../../lib/auth-session';

type LoginInput = {
  email: string;
  password: string;
  rememberMe: boolean;
};

type AuthContextValue = {
  initialized: boolean;
  isAuthenticated: boolean;
  isRefreshing: boolean;
  session: AuthSession | null;
  user: AuthenticatedUser | null;
  login: (input: LoginInput) => Promise<AuthSession>;
  logout: () => Promise<void>;
  logoutAll: () => Promise<void>;
  refreshSession: () => Promise<AuthSession | null>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function storageModeForRememberMe(rememberMe: boolean): SessionStorageMode {
  return rememberMe ? 'local' : 'session';
}

export default function AuthProvider({ children }: { children: ReactNode }) {
  const [initialized, setInitialized] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [session, setSession] = useState<AuthSession | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function hydrateSession() {
      const stored = loadSession();

      if (!stored) {
        if (!cancelled) {
          setInitialized(true);
        }
        return;
      }

      if (!cancelled) {
        setSession(stored);
      }

      try {
        const current = await ensureSessionIsUsable(stored);

        if (!cancelled) {
          setSession(current);
        }
      } catch {
        if (!cancelled) {
          clearSession();
          setSession(null);
        }
      } finally {
        if (!cancelled) {
          setInitialized(true);
        }
      }
    }

    void hydrateSession();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!session) {
      return;
    }

    const refreshDelay = Math.max(session.expiresAt - Date.now() - 60_000, 5_000);
    const timerId = window.setTimeout(() => {
      void rotateSession(session);
    }, refreshDelay);

    return () => {
      window.clearTimeout(timerId);
    };
  }, [session]);

  async function ensureSessionIsUsable(current: AuthSession): Promise<AuthSession> {
    if (isSessionExpiringSoon(current)) {
      const refreshed = await rotateSession(current);
      if (!refreshed) {
        throw new Error('Unable to refresh session.');
      }
      return refreshed;
    }

    try {
      const user = await getCurrentUser(current.accessToken);
      const next = { ...current, user };
      saveSession(next);
      return next;
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        const refreshed = await rotateSession(current);
        if (!refreshed) {
          throw error;
        }
        return refreshed;
      }

      throw error;
    }
  }

  async function rotateSession(current: AuthSession | null): Promise<AuthSession | null> {
    if (!current) {
      return null;
    }

    setIsRefreshing(true);

    try {
      const tokens = await refreshAccessToken(current.refreshToken);
      const user = await getCurrentUser(tokens.access_token);
      const next = buildSession(tokens, user, current.storage);

      saveSession(next);
      setSession(next);
      return next;
    } catch {
      clearSession();
      setSession(null);
      return null;
    } finally {
      setIsRefreshing(false);
    }
  }

  async function login(input: LoginInput): Promise<AuthSession> {
    const response = await loginRequest({
      email: input.email,
      password: input.password,
      remember_me: input.rememberMe,
    });

    const next = buildSession(
      response,
      response.user,
      storageModeForRememberMe(input.rememberMe),
    );
    saveSession(next);

    startTransition(() => {
      setSession(next);
    });

    return next;
  }

  async function logout(): Promise<void> {
    const current = session;

    clearSession();
    setSession(null);

    if (!current) {
      return;
    }

    try {
      await logoutRequest(current.refreshToken);
    } catch {
      // Local logout still wins if the API is unavailable.
    }
  }

  async function logoutAll(): Promise<void> {
    const current = session;

    clearSession();
    setSession(null);

    if (!current) {
      return;
    }

    try {
      await logoutAllRequest(current.accessToken);
    } catch {
      // Local logout still wins if the API is unavailable.
    }
  }

  async function refreshSession(): Promise<AuthSession | null> {
    return rotateSession(session);
  }

  const value = useMemo<AuthContextValue>(
    () => ({
      initialized,
      isAuthenticated: Boolean(session),
      isRefreshing,
      session,
      user: session?.user ?? null,
      login,
      logout,
      logoutAll,
      refreshSession,
    }),
    [initialized, isRefreshing, session],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);

  if (!value) {
    throw new Error('useAuth must be used within an AuthProvider.');
  }

  return value;
}
