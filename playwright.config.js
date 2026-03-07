// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

import { defineConfig } from "@playwright/test";

const BASE_URL = process.env.BASE_URL || "http://localhost:3000";
const isExternal = !!process.env.BASE_URL;

export default defineConfig({
  testDir: "./tests",
  timeout: 15_000,
  retries: isExternal ? 1 : 0,
  reporter: process.env.CI
    ? [["junit", { outputFile: "test-results/results.xml" }], ["list"]]
    : [["list"]],
  use: {
    baseURL: BASE_URL,
    headless: true,
  },
  projects: [
    { name: "chromium", use: { browserName: "chromium" } },
  ],
  ...(isExternal
    ? {}
    : {
        webServer: {
          command: "npx serve public -l 3000 --no-clipboard",
          port: 3000,
          reuseExistingServer: !process.env.CI,
        },
      }),
});
