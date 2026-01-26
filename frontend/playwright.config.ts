import { defineConfig } from '@playwright/test'

const url = 'http://127.0.0.1:5184'
if (!process.env.API_PROXY_TARGET) throw new Error('Run browser tests with backend/scripts/verify_workspace.py.')

export default defineConfig({
  testDir: './e2e',
  outputDir: '.local/playwright-results',
  workers: 1,
  use: { baseURL: url, channel: process.platform === 'win32' ? 'msedge' : 'chromium' },
  webServer: {
    command: 'node node_modules/vite/bin/vite.js --port 5184 --strictPort',
    url,
    reuseExistingServer: false,
  },
})
