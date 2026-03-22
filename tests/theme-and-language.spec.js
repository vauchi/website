// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

import { test, expect } from "@playwright/test";

const LOCALES = [
  { lang: "en", path: "/" },
  { lang: "fr", path: "/fr/" },
  { lang: "de", path: "/de/" },
  { lang: "it", path: "/it/" },
];

// CSS variable helper — reads computed custom property from :root
async function getCSSVar(page, name) {
  return page.evaluate(
    (prop) => getComputedStyle(document.documentElement).getPropertyValue(prop).trim(),
    `--${name}`
  );
}

// Wait for theme picker to initialise (themes.json loaded, menu populated)
async function waitForThemes(page) {
  await page.waitForFunction(
    () => document.querySelectorAll("#theme-menu [data-theme-id]").length > 0,
    { timeout: 5000 }
  );
}

for (const { lang, path } of LOCALES) {
  test.describe(`[${lang.toUpperCase()}] ${path}`, () => {
    test.beforeEach(async ({ page }) => {
      // Clear localStorage so each test starts fresh
      await page.goto(path);
      await page.evaluate(() => localStorage.removeItem("vauchi-theme"));
      await page.goto(path);
      await waitForThemes(page);
    });

    test("dark/light toggle changes color scheme", async ({ page }) => {
      // Default (no prefers-color-scheme: dark) is a random light theme
      const bgBefore = await getCSSVar(page, "bg-primary");
      expect(bgBefore).toBeTruthy();

      // Toggle button should show sun emoji for light mode
      const toggleBefore = await page.textContent("#mode-toggle");
      expect(toggleBefore).toContain("☀");

      // Click the dark/light toggle — should switch to a dark theme
      await page.click("#mode-toggle");

      // bg-primary must change (different theme applied)
      const bgAfter = await getCSSVar(page, "bg-primary");
      expect(bgAfter).not.toBe(bgBefore);

      // Verify the toggle button changed to moon emoji
      const toggleText = await page.textContent("#mode-toggle");
      expect(toggleText).toContain("🌙");
    });

    test("theme picker applies selected theme", async ({ page }) => {
      const bgBefore = await getCSSVar(page, "bg-primary");

      // Open theme menu
      await page.click("#theme-menu-toggle");
      await expect(page.locator("#theme-menu")).toBeVisible();

      // Select "Dracula" theme
      await page.click('#theme-menu [data-theme-id="dracula"]');

      // Verify CSS variables changed
      const bgAfter = await getCSSVar(page, "bg-primary");
      expect(bgAfter).not.toBe(bgBefore);

      // Verify menu closed
      await expect(page.locator("#theme-menu")).not.toBeVisible();

      // Verify localStorage was updated
      const saved = await page.evaluate(() => localStorage.getItem("vauchi-theme"));
      expect(saved).toBe("dracula");
    });
  });
}
