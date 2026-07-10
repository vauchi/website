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

test("join button shows a pending state while the request is in flight", async ({
  page,
}) => {
  // Answer the POST with 204: browsers discard No-Content main-frame
  // navigations and stay on the page, leaving the pending button
  // state assertable. (Holding the route open or aborting it instead
  // wedges Playwright on the navigation / lands on an error page.)
  // The state must change at submit time, not after the server
  // responds — joins block on synchronous SMTP for up to 30s when
  // mail is degraded.
  await page.route("**/waitlist/join", (route) =>
    route.fulfill({ status: 204 })
  );
  await page.goto("/");
  const form = page.locator(".waitlist-form");
  await form.locator('input[name="email"]').fill("probe@example.com");
  const button = form.locator(".waitlist-button");
  // noWaitAfter: the click starts a form navigation our held route
  // never completes; without it the click itself times out.
  await button.click({ noWaitAfter: true });
  await expect(button).toBeDisabled();
  await expect(button).toHaveText("Sending…");
  await expect(button).toHaveAttribute("aria-busy", "true");
});
