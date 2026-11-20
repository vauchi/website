// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

// Indexable pages carry a search-snippet-sized description and the same
// keywords in their meta tags and SoftwareApplication JSON-LD
// (vauchi/private#1308). Variant landing pages are noindex and keep their
// campaign line as description; variant.spec.js owns them.

import { test, expect } from "@playwright/test";

const locales = ["", "de/", "es/", "fr/", "it/"];

for (const prefix of locales) {
  for (const path of [`/${prefix}`, `/${prefix}text/`]) {
    test(`${path} description fits search snippets (120-160 characters)`, async ({ page }) => {
      await page.goto(path);
      const description = await page.locator('meta[name="description"]').getAttribute("content");
      expect(description.length).toBeGreaterThanOrEqual(120);
      expect(description.length).toBeLessThanOrEqual(160);
    });
  }

  test(`/${prefix} keywords match its SoftwareApplication JSON-LD`, async ({ page }) => {
    await page.goto(`/${prefix}`);
    const keywords = await page.locator('meta[name="keywords"]').getAttribute("content");
    expect(keywords.split(", ").length).toBeGreaterThanOrEqual(5);
    const scripts = await page.locator('script[type="application/ld+json"]').allTextContents();
    const application = scripts.map((s) => JSON.parse(s)).find((d) => d["@type"] === "SoftwareApplication");
    expect(application.keywords).toBe(keywords);
  });
}
