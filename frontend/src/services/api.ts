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
export const clearSession = (): void => {
  _accessToken = null;
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
      clearSession();
      window.dispatchEvent(new CustomEvent('auth:logout'));
    }
    return Promise.reject(error);
  }
);

export default api;
export { API_BASE_URL };

