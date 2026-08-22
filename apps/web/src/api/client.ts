import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios';

const authEndpoints = ['/auth/login', '/auth/refresh', '/auth/logout'];

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  withCredentials: true,
  timeout: 15000,
});

let accessToken: string | null = null;
let refreshPromise: Promise<string | null> | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

async function doRefresh(): Promise<string | null> {
  try {
    const response = await http.post<{ access_token: string }>('/auth/refresh');
    return response.data.access_token;
  } catch {
    return null;
  }
}

export function refreshAccessToken(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = doRefresh().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

http.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.set('Authorization', `Bearer ${accessToken}`);
  }
  return config;
});

http.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;
    const url = config?.url ?? '';
    const isAuthEndpoint = authEndpoints.some((endpoint) => url.includes(endpoint));

    if (error.response?.status === 401 && config && !config._retry && !isAuthEndpoint) {
      config._retry = true;
      const token = await refreshAccessToken();
      if (token) {
        accessToken = token;
        config.headers.set('Authorization', `Bearer ${token}`);
        return http(config);
      }
      accessToken = null;
      window.location.assign('/login');
    }

    return Promise.reject(error);
  },
);
