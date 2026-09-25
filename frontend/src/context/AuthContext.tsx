import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { User, AuthResponse } from '../types';
import api from '../services/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (login: string, password: string) => Promise<void>;
  signup: (email: string, username: string, password: string, fullName?: string, githubToken?: string) => Promise<void>;
  githubSignin: (githubToken: string) => Promise<void>;
  logout: () => void;
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
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const storedToken = localStorage.getItem('greencode_token');
    const storedUser = localStorage.getItem('greencode_user');
    if (storedToken && storedUser) {
      setToken(storedToken);
      setUser(JSON.parse(storedUser));
      api.defaults.headers.common.Authorization = `Bearer ${storedToken}`;
    }
    setIsLoading(false);

    const handleLogout = () => logout();
    window.addEventListener('auth:logout', handleLogout);
    return () => window.removeEventListener('auth:logout', handleLogout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = async (login: string, password: string) => {
    const resp = await api.post<AuthResponse>('/api/auth/signin', { login, password });
    const { access_token, user: userData } = resp.data;
    localStorage.setItem('greencode_token', access_token);
    localStorage.setItem('greencode_user', JSON.stringify(userData));
    api.defaults.headers.common.Authorization = `Bearer ${access_token}`;
    setToken(access_token);
    setUser(userData);
  };

  const signup = async (email: string, username: string, password: string, fullName?: string, githubToken?: string) => {
    const resp = await api.post<AuthResponse>('/api/auth/signup', {
      email, username, password, full_name: fullName, github_token: githubToken,
    });
    const { access_token, user: userData } = resp.data;
    localStorage.setItem('greencode_token', access_token);
    localStorage.setItem('greencode_user', JSON.stringify(userData));
    api.defaults.headers.common.Authorization = `Bearer ${access_token}`;
    setToken(access_token);
    setUser(userData);
  };

  const githubSignin = async (githubToken: string) => {
    const resp = await api.post<AuthResponse>('/api/auth/github', { github_token: githubToken });
    const { access_token, user: userData } = resp.data;
    localStorage.setItem('greencode_token', access_token);
    localStorage.setItem('greencode_user', JSON.stringify(userData));
    api.defaults.headers.common.Authorization = `Bearer ${access_token}`;
    setToken(access_token);
    setUser(userData);
  };

  const logout = () => {
    localStorage.removeItem('greencode_token');
    localStorage.removeItem('greencode_user');
    api.defaults.headers.common.Authorization = '';
    setToken(null);
    setUser(null);
  };

  const refreshUser = async () => {
    if (!user?.id) return;
    const resp = await api.get<User>(`/api/auth/user/${user.id}`);
    setUser(resp.data);
    localStorage.setItem('greencode_user', JSON.stringify(resp.data));
  };

  return (
    <AuthContext.Provider value={{
      user, token, isAuthenticated: !!token, isLoading,
      login, signup, githubSignin, logout, refreshUser,
    }}>
      {children}
    </AuthContext.Provider>
  );
};
