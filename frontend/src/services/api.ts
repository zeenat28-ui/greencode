import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

/**
 * Session storage model
 * ---------------------
 * The access token is deliberately kept in memory only, so an XSS payload cannot
 * simply read it out of localStorage. The refresh token lives in localStorage so a
 * page reload can silently mint a new short-lived access token. A stolen
 * refresh token is a far smaller and far shorter-lived exposure than a
 * long-lived bearer credential in localStorage.
 * 
 * GitHub OAuth access token is kept in session-scoped browser storage, never in localStorage.
 * Dashboard API calls send it via X-GitHub-Token without persisting it. Explicit
 * Alexa pairing is the exception: it encrypts a copy at rest for repository audits.
 */
const REFRESH_TOKEN_KEY = 'greencode_refresh_token';
export const GITHUB_CONNECT_STATE_KEY = 'greencode_github_connect_state';

let _accessToken: string | null = null;
let _refreshToken: string | null = null;
let _githubToken: string | null = null;
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

/** OAuth access token for GitHub API requests; scoped to this browser tab session. */
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
  // Attach the GitHub OAuth token only to repository and Alexa pairing requests.
  const ghTok = getGitHubToken();
  if (ghTok && config.url) {
    const url = config.url;
    const needsGithubToken = 
      url.includes('/api/scan') ||
      url.includes('/api/alexa/') ||
      url.startsWith('/github/') ||
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
  '/api/auth/github/authorize',
  '/api/auth/github/oauth',
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
      if (!refreshToken) {
        clearSession();
        window.dispatchEvent(new CustomEvent('auth:logout'));
        return Promise.reject(error);
      }
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
      } catch (refreshError: unknown) {
        // Network and server failures are temporary; preserve the refresh token.
        if (axios.isAxiosError(refreshError) && refreshError.response?.status === 401) {
          clearSession();
          window.dispatchEvent(new CustomEvent('auth:logout'));
        }
        return Promise.reject(error);
      }
    }
    return Promise.reject(error);
  }
);

export default api;
export { API_BASE_URL };