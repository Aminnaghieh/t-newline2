import { defineConfig, devices } from '@playwright/test';

/**
 * TorobGard E2E configuration.
 *
 * The app is served by the FastAPI backend, which also mounts the built
 * SPA from `backend/static`. The backend must already be running on
 * http://127.0.0.1:8000 (see `start.bat`).
 */
export default defineConfig({
  testDir: './tests/e2e',
  outputDir: './test-results',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 45_000,
  expect: { timeout: 10_000 },
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]],

  use: {
    baseURL: process.env.BASE_URL || 'http://127.0.0.1:8000',
    locale: 'fa-IR',
    timezoneId: 'Asia/Tehran',
    viewport: { width: 1440, height: 900 },
    actionTimeout: 15_000,
    navigationTimeout: 20_000,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    permissions: ['geolocation'],
  },

  projects: [
    {
      name: 'desktop-chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
    },
    {
      name: 'mobile-chromium',
      use: {
        ...devices['Pixel 5'],
        locale: 'fa-IR',
        permissions: ['geolocation'],
      },
    },
  ],
});
