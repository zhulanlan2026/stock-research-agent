import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './',
  timeout: 30_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: 'http://localhost:5173',
    headless: true,
  },
});
