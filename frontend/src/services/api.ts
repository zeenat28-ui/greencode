import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const isVercel = typeof window !== 'undefined' && window.location.hostname.includes('vercel.app');
const isLocal8000 = typeof window !== 'undefined' && (window.location.port === '8000' || window.location.host.includes(':8000'));
const API_BASE_URL = import.meta.env.VITE_API_URL || (isVercel || isLocal8000 ? '' : 'http://127.0.0.1:8000');

/**
 * Session storage model
 * ---------------------
 * The access token is deliberately kept in memory only, so an XSS payload cannot
 * simply read it out of localStorage. The refresh token lives in localStorage so a
 * page reload can silently mint a new short-lived access token. A stolen
 * refresh token is a far smaller and far shorter-lived exposure than a
 * long-lived bearer credential in localStorage.
 * 
 * ZERO-KNOWLEDGE: GitHub token is ALSO kept in memory only - NEVER in localStorage.
 * It is sent with each request via X-GitHub-Token header. Server NEVER stores it.
 */
const REFRESH_TOKEN_KEY = 'greencode_refresh_token';

let _accessToken: string | null = null;
let _refreshToken: string | null = null;
let _githubToken: string | null = null;  // ZERO-KNOWLEDGE: GitHub PAT in memory only
let _refreshing: Promise<string | null> | null = null;

export const getAccessToken = (): string | null => _accessToken;
export const setAccessToken = (token: string | null): void => {
  _accessToken = token;
};

/**
 * Build the Authorization header for a *raw* `fetch()` call.
 *
 * The access token is intentionally kept in memory only (see the note above),
 * so there is no `localStorage` entry to read. Pages that call `fetch()`
 * directly instead of going through the axios instance must therefore ask for
 * the header here - otherwise the request goes out unauthenticated and the
 * backend answers 401.
 */
export const authHeaders = (extra: Record<string, string> = {}): Record<string, string> => {
  const headers: Record<string, string> = { ...extra };
  const token = getAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
};
export const getRefreshToken = (): string | null => {
  if (_refreshToken) return _refreshToken;
  try {
    _refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
  } catch {
    _refreshToken = null;
  }
  return _refreshToken;
};
export const setRefreshToken = (token: string | null): void => {
  _refreshToken = token;
  try {
    if (token) localStorage.setItem(REFRESH_TOKEN_KEY, token);
    else localStorage.removeItem(REFRESH_TOKEN_KEY);
  } catch {
    // Storage unavailable (private mode) - session simply won't survive reloads.
  }
};

/** 
 * ZERO-KNOWLEDGE: GitHub token stored in browser session memory only (sessionStorage).
 * Never written to localStorage, never persisted to database.
 * Survives page reloads within the tab, automatically cleared on logout or tab close.
 */
const GH_SESSION_KEY = 'greencode_gh_token';

export const getGitHubToken = (): string | null => {
  if (_githubToken) return _githubToken;
  try {
    _githubToken = sessionStorage.getItem(GH_SESSION_KEY);
  } catch {
    _githubToken = null;
  }
  return _githubToken;
};

export const setGitHubToken = (token: string | null): void => {
  _githubToken = token;
  try {
    if (token) sessionStorage.setItem(GH_SESSION_KEY, token);
    else sessionStorage.removeItem(GH_SESSION_KEY);
  } catch {
    // sessionStorage unavailable
  }
};

export const clearSession = (): void => {
  _accessToken = null;
  _githubToken = null;
  try {
    sessionStorage.removeItem(GH_SESSION_KEY);
  } catch {
    // ignore
  }
  setRefreshToken(null);
};

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // GitHub audits of large repos can take a while.
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (_accessToken) {
    config.headers.Authorization = `Bearer ${_accessToken}`;
  }
  // ZERO-KNOWLEDGE: Attach GitHub token to requests that need it
  const ghTok = getGitHubToken();
  if (ghTok && config.url) {
    const url = config.url;
    const needsGithubToken = 
      url.includes('/api/scan') ||
      url.includes('/github/') ||
      url.includes('/api/dynamic/analyze');
    if (needsGithubToken) {
      config.headers['X-GitHub-Token'] = ghTok;
    }
  }
  return config;
});

/** Paths that must never trigger a refresh (they ARE the auth endpoints). */
const AUTH_FREE_PATHS = [
  '/api/auth/refresh',
  '/api/auth/github',
  '/api/auth/login',
  '/api/auth/register',
  '/api/auth/google',
  '/api/auth/forgot-password',
  '/api/auth/reset-password',
  '/api/auth/logout',
];

api.interceptors.response.use(
  (response) => {
    const data = response.data as Record<string, unknown> | undefined;
    if (data && typeof data === 'object') {
      if (data.access_token) setAccessToken(data.access_token as string);
      if (data.refresh_token) setRefreshToken(data.refresh_token as string);
    }
    return response;
  },
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;
    const status = error.response?.status;
    const isAuthEndpoint = AUTH_FREE_PATHS.some((p) => original?.url?.includes(p));

    if (status === 401 && original && !original._retried && !isAuthEndpoint) {
      const refreshToken = getRefreshToken();
      if (refreshToken) {
        original._retried = true;
        try {
          // De-duplicate concurrent refreshes into a single in-flight request.
          if (!_refreshing) {
            _refreshing = axios
              .post<{ access_token: string; refresh_token: string }>(
                `${API_BASE_URL}/api/auth/refresh`,
                { refresh_token: refreshToken },
              )
              .then((res) => {
                setAccessToken(res.data.access_token);
                setRefreshToken(res.data.refresh_token);
                return res.data.access_token as string;
              })
              .finally(() => {
                _refreshing = null;
              });
          }
          const freshToken = await _refreshing;
          if (freshToken) {
            original.headers.Authorization = `Bearer ${freshToken}`;
            return api.request(original);
          }
        } catch {
          clearSession();
        }
      }
      clearSession();
      window.dispatchEvent(new CustomEvent('auth:logout'));
    }
    return Promise.reject(error);
  }
);

export default api;
export { API_BASE_URL };