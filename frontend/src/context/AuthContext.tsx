import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { User } from '../types';
import { authService } from '../services/greencodeApi';
import { getRefreshToken, clearSession, setGitHubToken } from '../services/api';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  /** Legacy: PAT-based GitHub sign-in (still works for direct PAT entry) */
  connectGitHub: (githubToken: string) => Promise<User>;
  /** Real GitHub OAuth2 code exchange (popup/redirect flow) */
  loginWithGitHubCode: (code: string, redirectUri?: string) => Promise<User>;
  /** Email + password login */
  loginWithEmail: (emailOrUsername: string, password: string) => Promise<User>;
  /** Email + password registration */
  registerWithEmail: (email: string, password: string, fullName?: string) => Promise<User>;
  /** Google Identity Services ID token verification */
  loginWithGoogleToken: (idToken: string) => Promise<User>;
  /** Google OAuth2 code exchange */
  loginWithGoogleCode: (code: string, redirectUri?: string) => Promise<User>;
  forgotPassword: (email: string) => Promise<{ success: boolean; message: string; reset_token?: string }>;
  resetPassword: (token: string, newPassword: string) => Promise<{ success: boolean; message: string }>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  /**
   * Restore the session on first load.
   *
   * The access token lives only in memory, so after a page reload it is gone.
   * The persisted refresh token is exchanged for a fresh access token, which the
   * axios interceptor stores automatically.
   */
  useEffect(() => {
    let cancelled = false;

    const restore = async () => {
      const refreshToken = getRefreshToken();
      if (!refreshToken) {
        if (!cancelled) {
          setUser(null);
          setIsLoading(false);
        }
        return;
      }
      try {
        const res = await authService.refresh(refreshToken);
        if (!cancelled && res.data.user) {
          setUser(res.data.user);
        }
      } catch {
        // Expired or revoked refresh token — start from a clean slate.
        if (!cancelled) {
          clearSession();
          setUser(null);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    restore();

    // The axios interceptor fires this when a refresh cannot recover the session.
    const handleForcedLogout = () => {
      clearSession();
      setUser(null);
      setIsLoading(false);
      navigate('/login', { replace: true });
    };
    window.addEventListener('auth:logout', handleForcedLogout);
    return () => {
      cancelled = true;
      window.removeEventListener('auth:logout', handleForcedLogout);
    };
  }, [navigate]);

  // ---------------------------------------------------------------------------
  // Auth actions
  // ---------------------------------------------------------------------------

  /** Legacy PAT-based GitHub sign-in */
  const connectGitHub = useCallback(async (githubToken: string) => {
    const res = await authService.signInWithGitHub(githubToken);
    setGitHubToken(githubToken);
    setUser(res.data.user);
    return res.data.user;
  }, []);

  /** Real GitHub OAuth2 code exchange (popup/redirect callback) */
  const loginWithGitHubCode = useCallback(async (code: string, redirectUri?: string) => {
    const res = await authService.exchangeGitHubOAuth(code, redirectUri);
    setUser(res.data.user);
    return res.data.user;
  }, []);

  /** Email + password login */
  const loginWithEmail = useCallback(async (emailOrUsername: string, password: string) => {
    const res = await authService.login(emailOrUsername, password);
    setUser(res.data.user);
    return res.data.user;
  }, []);

  /** Email + password registration */
  const registerWithEmail = useCallback(async (email: string, password: string, fullName?: string) => {
    const res = await authService.register({ email, password, full_name: fullName });
    setUser(res.data.user);
    return res.data.user;
  }, []);

  /**
   * Google Identity Services real flow.
   * idToken is the `credential` field from the GSI callback — a signed Google JWT.
   * The backend verifies it against Google's tokeninfo endpoint.
   */
  const loginWithGoogleToken = useCallback(async (idToken: string) => {
    const res = await authService.exchangeGoogleOAuth(undefined, idToken);
    setUser(res.data.user);
    return res.data.user;
  }, []);

  const loginWithGoogleCode = useCallback(async (code: string, redirectUri?: string) => {
    const res = await authService.exchangeGoogleOAuth(code, undefined, redirectUri);
    setUser(res.data.user);
    return res.data.user;
  }, []);

  const forgotPassword = useCallback(async (email: string) => {
    const res = await authService.forgotPassword(email);
    return res.data;
  }, []);

  const resetPassword = useCallback(async (token: string, newPassword: string) => {
    const res = await authService.resetPassword(token, newPassword);
    return res.data;
  }, []);

  const logout = useCallback(async () => {
    try {
      await authService.logout();
    } catch {
      // Best effort
    }
    clearSession();
    setUser(null);
    navigate('/login', { replace: true });
  }, [navigate]);

  const refreshUser = useCallback(async () => {
    if (!user?.id) return;
    const res = await authService.getUser(user.id);
    setUser(res.data);
  }, [user?.id]);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        connectGitHub,
        loginWithGitHubCode,
        loginWithEmail,
        registerWithEmail,
        loginWithGoogleToken,
        loginWithGoogleCode,
        forgotPassword,
        resetPassword,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
