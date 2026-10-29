// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

// The waitlist form on a phone (vauchi/private#922): the email field
// must stay a single line, and the outcome of a submission must be
// where the eye is, announced, and in view after the redirect.
import { test, expect, devices } from "@playwright/test";

const PHONES = ["Pixel 7", "iPhone 13"];

for (const phone of PHONES) {
  // The browser stays the project's chromium; only the phone's viewport,
  // scale, touch and user agent are taken from the device profile.
  const { defaultBrowserType, ...profile } = devices[phone];
  test.describe(`[${phone}] waitlist form`, () => {
    test.use(profile);

    test("the email field is one line tall, not a 220px block", async ({ page }) => {
      await page.goto("/");
      const input = page.locator("#waitlist-email");
      await input.scrollIntoViewIfNeeded();
      const inputBox = await input.boundingBox();
      const buttonBox = await page.locator(".waitlist-button").boundingBox();
      expect(inputBox.height).toBeLessThan(80);
      expect(inputBox.height).toBeLessThanOrEqual(buttonBox.height + 16);
      const sectionBox = await page.locator("#waitlist").boundingBox();
      expect(inputBox.width).toBeLessThanOrEqual(sectionBox.width);
    });

    test("after joining, the outcome is shown next to the form, in view and announced", async ({ page }) => {
      await page.goto("/?waitlist=joined#waitlist");
      const banner = page.locator("#waitlist-message");
      await expect(banner).toBeVisible();
      await expect(banner).toHaveAttribute("role", "status");
      const form = page.locator(".waitlist-form");
      const bannerBox = await banner.boundingBox();
      const formBox = await form.boundingBox();
      // Next to the form: directly above it, not at the top of the section.
      expect(formBox.y - (bannerBox.y + bannerBox.height)).toBeLessThan(48);
      const viewport = page.viewportSize();
      expect(bannerBox.y).toBeGreaterThanOrEqual(0);
      expect(bannerBox.y + bannerBox.height).toBeLessThanOrEqual(viewport.height);
    });

    test("a failed submission says so in the same place", async ({ page }) => {
      await page.goto("/?waitlist=error#waitlist");
      const banner = page.locator("#waitlist-message");
      await expect(banner).toBeVisible();
      await expect(banner).toHaveClass(/waitlist-message--error/);
      await expect(banner).not.toBeEmpty();
    });
  });
}
