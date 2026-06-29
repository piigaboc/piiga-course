import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { api, LOGOUT_EVENT } from '../../lib/api';
import { tokenStore } from '../../lib/tokenStore';
import type {
  LoginResponse,
  MfaVerifyResponse,
  User,
} from '../../lib/types';

export interface LoginResult {
  mfa_required: boolean;
  mfa_token?: string;
}

export interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<LoginResult>;
  verifyMfa: (mfaToken: string, code: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(() => Boolean(tokenStore.get()));
  const mounted = useRef(true);

  const loadMe = useCallback(async () => {
    try {
      const me = await api.get<User>('/auth/me');
      if (mounted.current) setUser(me);
    } catch {
      tokenStore.clear();
      if (mounted.current) setUser(null);
    } finally {
      if (mounted.current) setIsLoading(false);
    }
  }, []);

  // Rehydrate from a persisted token on mount.
  useEffect(() => {
    mounted.current = true;
    if (tokenStore.get()) {
      void loadMe();
    } else {
      setIsLoading(false);
    }
    return () => {
      mounted.current = false;
    };
  }, [loadMe]);

  // React to a global logout (401 from the api layer, or another tab).
  useEffect(() => {
    const onLogout = () => setUser(null);
    window.addEventListener(LOGOUT_EVENT, onLogout);
    const unsub = tokenStore.subscribe((token) => {
      if (!token) setUser(null);
    });
    return () => {
      window.removeEventListener(LOGOUT_EVENT, onLogout);
      unsub();
    };
  }, []);

  const login = useCallback(
    async (email: string, password: string): Promise<LoginResult> => {
      const res = await api.post<LoginResponse>(
        '/auth/login',
        { email, password },
        { auth: false },
      );
      if (!res.mfa_required && res.access_token) {
        tokenStore.set(res.access_token);
        await loadMe();
        return { mfa_required: false };
      }
      return { mfa_required: true, mfa_token: res.mfa_token };
    },
    [loadMe],
  );

  const verifyMfa = useCallback(
    async (mfaToken: string, code: string): Promise<void> => {
      const res = await api.post<MfaVerifyResponse>(
        '/auth/mfa/verify',
        { mfa_token: mfaToken, code },
        { auth: false },
      );
      tokenStore.set(res.access_token);
      await loadMe();
    },
    [loadMe],
  );

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isLoading,
      login,
      verifyMfa,
      logout,
    }),
    [user, isLoading, login, verifyMfa, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an <AuthProvider>');
  }
  return ctx;
}
