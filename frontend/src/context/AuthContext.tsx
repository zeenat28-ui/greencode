import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { User } from '../types';
import { authService } from '../services/greencodeApi';
import { getRefreshToken, clearSession } from '../services/api';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  connectGitHub: (githubToken: string) => Promise<User>;
  exploreAsAuditor: () => void;
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
   * axios interceptor stores automatically. This is what keeps a refresh from
   * logging the user out.
   */
  useEffect(() => {
    let cancelled = false;

    const restore = async () => {
      const stored = localStorage.getItem('greencode_user_session');
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          if (parsed && parsed.username) {
            setUser(parsed);
            setIsLoading(false);
            return;
          }
        } catch {
          localStorage.removeItem('greencode_user_session');
        }
      }

      const refreshToken = getRefreshToken();
      if (!refreshToken) {
        setIsLoading(false);
        return;
      }
      try {
        const res = await authService.refresh(refreshToken);
        if (!cancelled && res.data.user) {
          setUser(res.data.user);
        }
      } catch {
        // Expired or revoked refresh token - start from a clean slate.
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
      localStorage.removeItem('greencode_user_session');
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

  const connectGitHub = useCallback(async (githubToken: string) => {
    const res = await authService.signInWithGitHub(githubToken);
    setUser(res.data.user);
    localStorage.removeItem('greencode_user_session');
    return res.data.user;
  }, []);

  const exploreAsAuditor = useCallback(() => {
    const auditorUser: User = {
      id: 1,
      email: 'auditor@greencode.io',
      username: 'cloud_auditor',
      full_name: 'Lead Sustainability Engineer',
      avatar_url: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=128&q=80',
      github_username: 'zeenat28-ui',
      has_github_token: false,
      role: 'admin',
      is_verified: true,
      created_at: new Date().toISOString(),
    };
    setUser(auditorUser);
    localStorage.setItem('greencode_user_session', JSON.stringify(auditorUser));
    navigate('/dashboard', { replace: true });
  }, [navigate]);

  const logout = useCallback(async () => {
    try {
      await authService.logout();
    } catch {
      // Best effort - the local session is cleared regardless.
    }
    localStorage.removeItem('greencode_user_session');
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
        exploreAsAuditor,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

