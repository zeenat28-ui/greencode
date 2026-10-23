import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { GitHubUser, User } from '../types';
import { authService } from '../services/greencodeApi';
import { getRefreshToken, setRefreshToken, setAccessToken, clearSession, setGitHubToken, getGitHubToken } from '../services/api';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isGitHubConnected: boolean;
  disconnectGitHub: () => void;
  /** Real GitHub OAuth2 code exchange (popup/redirect flow) */
  loginWithGitHubCode: (code: string, redirectUri?: string) => Promise<User>;
  /** Link GitHub repository access to the currently authenticated GreenCode user. */
  connectGitHubOAuth: (code: string, redirectUri?: string) => Promise<GitHubUser>;
  setGitHubAccessToken: (token: string) => void;
  /** Email + password login */
  loginWithEmail: (emailOrUsername: string, password: string) => Promise<User>;
  /** Email + password registration */
  registerWithEmail: (email: string, password: string, fullName?: string) => Promise<User>;
  /** Google OAuth2 code exchange */
  loginWithGoogleCode: (code: string, redirectUri?: string) => Promise<User>;
  forgotPassword: (email: string) => Promise<{ success: boolean; message: string; reset_token?: string }>;
  resetPassword: (token: string, newPassword: string) => Promise<{ success: boolean; message: string }>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

type RefreshResponse = ReturnType<typeof authService.refresh>;
let pendingSessionRestore: { token: string; request: RefreshResponse } | null = null;

function restoreSession(refreshToken: string): RefreshResponse {
  if (pendingSessionRestore?.token === refreshToken) return pendingSessionRestore.request;

  const request = authService.refresh(refreshToken).finally(() => {
    if (pendingSessionRestore?.request === request) pendingSessionRestore = null;
  });
  pendingSessionRestore = { token: refreshToken, request };
  return request;
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
  const [hasGhToken, setHasGhToken] = useState<boolean>(() => !!getGitHubToken());
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
        const res = await restoreSession(refreshToken);
        if (!cancelled && res.data?.user) {
          setUser(res.data.user);
          if (getGitHubToken()) setHasGhToken(true);
        }
      } catch (error: unknown) {
        // Only discard the persisted session when the backend definitively rejects it.
        if (!cancelled && axios.isAxiosError(error) && error.response?.status === 401) {
          clearSession();
          setHasGhToken(false);
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
      setHasGhToken(false);
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

  /** Real GitHub OAuth2 code exchange (popup/redirect callback) */
  const loginWithGitHubCode = useCallback(async (code: string, redirectUri?: string) => {
    const res = await authService.exchangeGitHubOAuth(code, redirectUri);
    if (!res.data.github_token || !res.data.access_token || !res.data.refresh_token || !res.data.user) {
      throw new Error('GitHub sign-in did not return a complete authenticated session.');
    }
    setGitHubToken(res.data.github_token);
    setHasGhToken(true);
    setAccessToken(res.data.access_token);
    setRefreshToken(res.data.refresh_token);
    setUser(res.data.user);
    return res.data.user;
  }, []);

  const connectGitHubOAuth = useCallback(async (code: string, redirectUri?: string) => {
    const res = await authService.connectGitHubOAuth(code, redirectUri);
    if (!res.data.github_token || !res.data.github_user) {
      throw new Error('GitHub connection did not return repository access.');
    }
    setGitHubToken(res.data.github_token);
    setHasGhToken(true);
    return res.data.github_user;
  }, []);

  const setGitHubAccessToken = useCallback((token: string) => {
    const value = token.trim();
    if (!value) throw new Error('A GitHub access token is required.');
    setGitHubToken(value);
    setHasGhToken(true);
  }, []);

  const disconnectGitHub = useCallback(() => {
    setGitHubToken(null);
    setHasGhToken(false);
  }, []);

  /** Email + password login */
  const loginWithEmail = useCallback(async (emailOrUsername: string, password: string) => {
    const res = await authService.login(emailOrUsername, password);
    if (!res.data.user || !res.data.access_token || !res.data.refresh_token) {
      throw new Error('Sign-in did not return an authenticated session.');
    }
    setAccessToken(res.data.access_token);
    setRefreshToken(res.data.refresh_token);
    setGitHubToken(null);
    setHasGhToken(false);
    setUser(res.data.user);
    return res.data.user;
  }, []);

  /** Email + password registration */
  const registerWithEmail = useCallback(async (email: string, password: string, fullName?: string) => {
    const res = await authService.register({ email, password, full_name: fullName });
    if (!res.data.user || !res.data.access_token || !res.data.refresh_token) {
      throw new Error('Registration did not return an authenticated session.');
    }
    setAccessToken(res.data.access_token);
    setRefreshToken(res.data.refresh_token);
    setGitHubToken(null);
    setHasGhToken(false);
    setUser(res.data.user);
    return res.data.user;
  }, []);

  const loginWithGoogleCode = useCallback(async (code: string, redirectUri?: string) => {
    const res = await authService.exchangeGoogleOAuth(code, undefined, redirectUri);
    if (!res.data.user || !res.data.access_token || !res.data.refresh_token) {
      throw new Error('Google sign-in did not return an authenticated session.');
    }
    setAccessToken(res.data.access_token);
    setRefreshToken(res.data.refresh_token);
    setGitHubToken(null);
    setHasGhToken(false);
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
    setHasGhToken(false);
    setUser(null);
    navigate('/login', { replace: true });
  }, [navigate]);

  const refreshUser = useCallback(async () => {
    if (!user?.id) return;
    const res = await authService.getUser(user.id);
    setUser(res.data);
  }, [user?.id]);

  const isGitHubConnected = hasGhToken;

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        isGitHubConnected,
        disconnectGitHub,
        loginWithGitHubCode,
        connectGitHubOAuth,
        setGitHubAccessToken,
        loginWithEmail,
        registerWithEmail,
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
