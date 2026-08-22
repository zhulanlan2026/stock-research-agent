import { defineStore } from 'pinia';
import type { components } from '@stock-research/api-types';

import { http, refreshAccessToken, setAccessToken } from '../api/client';

type UserMe = components['schemas']['UserMe'];
type LoginResponse = components['schemas']['LoginResponse'];

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: null as string | null,
    user: null as UserMe | null,
    initialized: false,
  }),
  getters: {
    isAuthenticated: (state) => state.accessToken !== null,
  },
  actions: {
    async login(email: string, password: string): Promise<void> {
      const { data } = await http.post<LoginResponse>('/auth/login', { email, password });
      setAccessToken(data.access_token);
      this.accessToken = data.access_token;
      this.user = data.user;
    },
    async refresh(): Promise<void> {
      const token = await refreshAccessToken();
      this.accessToken = token;
      setAccessToken(token);
      if (token) {
        await this.fetchMe();
      }
    },
    async fetchMe(): Promise<void> {
      const { data } = await http.get<UserMe>('/users/me');
      this.user = data;
    },
    async logout(): Promise<void> {
      try {
        await http.post('/auth/logout');
      } finally {
        setAccessToken(null);
        this.accessToken = null;
        this.user = null;
      }
    },
    async init(): Promise<void> {
      if (this.initialized) {
        return;
      }
      try {
        await this.refresh();
      } finally {
        this.initialized = true;
      }
    },
  },
});
