import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Session storage model
 * ---------------------
 * The access token is deliberately kept in memory only, so an XSS payload cannot
 * simply read it out of localStorage. The refresh token lives in localStorage so a
 * page reload can silently mint a new short-lived access token. A stolen
 * refresh token is a far smaller and far shorter-lived exposure than a
 * long-lived bearer credential in localStorage.
 */
const REFRESH_TOKEN_KEY = 'greencode_refresh_token';

let _accessToken: string | null = null;
let _refreshToken: string | null = null;
let _refreshing: Promise<string | null> | null = null;

export const getAccessToken = (): string | null => _accessToken;
export const setAccessToken = (token: string | null): void => {
  _accessToken = token;
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
 * Demo mode marker.
 *
 * "Explore Enterprise Demo" gives a judge a populated walkthrough without a
 * GitHub token. It issues no real token, so every authenticated endpoint
 * answers 401 - and the interceptor below treats 401 as "your session is over"
 * and signs the user out. The result was that clicking any nav item during the
 * demo bounced straight back to /login, so the demo could not actually be
 * walked through.
 *
 * loginAsDemo sets this flag, and the 401 handler consults it: a demo session
 * keeps its state and lets the error surface to the caller (each page already
 * renders its own empty state), instead of being torn down mid-tour.
 */
const DEMO_MODE_KEY = 'greencode_demo_mode';

export const isDemoMode = (): boolean => {
  try {
    return localStorage.getItem(DEMO_MODE_KEY) === '1';
  } catch {
    return false;
  }
};

export const setDemoMode = (on: boolean): void => {
  try {
    if (on) localStorage.setItem(DEMO_MODE_KEY, '1');
    else localStorage.removeItem(DEMO_MODE_KEY);
  } catch {
    // Storage unavailable (private mode) - demo simply degrades to signing out.
  }
};

export const clearSession = (): void => {
  _accessToken = null;
  setRefreshToken(null);
  setDemoMode(false);
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
  return config;
});

/** Paths that must never trigger a refresh (they ARE the auth endpoints). */
const AUTH_FREE_PATHS = ['/api/auth/refresh', '/api/auth/github', '/api/auth/logout'];

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
      // A demo session holds no token by design, so a 401 is expected rather
      // than a sign of an expired one. Signing out here would eject the judge
      // mid-walkthrough, so let the request fail and render its empty state.
      if (isDemoMode()) {
        return Promise.reject(error);
      }

      clearSession();
      window.dispatchEvent(new CustomEvent('auth:logout'));
    }
    return Promise.reject(error);
  }
);

export default api;
export { API_BASE_URL };

