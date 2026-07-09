// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

import { test, expect } from "@playwright/test";

const LOCALES = [
  { lang: "en", path: "/" },
  { lang: "fr", path: "/fr/" },
  { lang: "de", path: "/de/" },
  { lang: "it", path: "/it/" },
  { lang: "es", path: "/es/" },
];

const EN_HEADING = "Join the waitlist";

for (const { lang, path } of LOCALES) {
  test.describe(`[${lang.toUpperCase()}] ${path} waitlist form`, () => {
    test("waitlist form is present and posts to /waitlist/join", async ({ page }) => {
      await page.goto(path);

      const form = page.locator(".waitlist-form");
      await expect(form).toBeVisible();
      await expect(form).toHaveAttribute("action", "/waitlist/join");
      await expect(form).toHaveAttribute("method", "POST");

      const emailInput = form.locator('input[type="email"]');
      await expect(emailInput).toBeVisible();
      await expect(emailInput).toHaveAttribute("required", "");

      const button = form.locator('button[type="submit"]');
      await expect(button).toBeVisible();
      await expect(button).not.toBeEmpty();

      const banner = page.locator("#waitlist-message");
      await expect(banner).toBeHidden();
      await expect(banner).toHaveAttribute("data-msg-joined");
      await expect(banner).toHaveAttribute("data-msg-confirmed");
    });

    test("waitlist heading is non-empty", async ({ page }) => {
      await page.goto(path);
      const heading = page.locator("#waitlist-heading");
      const text = await heading.textContent();
      expect(text.trim().length).toBeGreaterThan(3);
    });
  });
}

// Non-English pages must not show the English heading.
for (const { lang, path } of LOCALES.filter((l) => l.lang !== "en")) {
  test(`[${lang.toUpperCase()}] ${path} waitlist heading is translated`, async ({ page }) => {
    await page.goto(path);
    const heading = page.locator("#waitlist-heading");
    const text = await heading.textContent();
    expect(text.trim()).not.toBe(EN_HEADING);
  });
}
