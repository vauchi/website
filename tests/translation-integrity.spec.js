// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

import { test, expect } from "@playwright/test";

// English reference strings — if these appear in non-EN pages, translation is missing.
// Update these if the EN i18n values change.
const EN_TITLE = "Vauchi - Privacy-First Contact Exchange";
const EN_DESCRIPTION =
  "Exchange contacts once, they update themselves. End-to-end encrypted, no accounts, open source.";
const EN_SCENE1_HEADING =
  "Your address book is a graveyard of dead contacts.";
const EN_FOOTER_TAGLINE = "Auditable";

const NON_EN_LOCALES = [
  { lang: "fr", path: "/fr/" },
  { lang: "de", path: "/de/" },
  { lang: "it", path: "/it/" },
];

const ALL_LOCALES = [{ lang: "en", path: "/" }, ...NON_EN_LOCALES];

// ============================================================
// Structural tests — apply to ALL locales including English
// ============================================================

for (const { lang, path } of ALL_LOCALES) {
  test.describe(`[${lang.toUpperCase()}] ${path} — structure`, () => {
    test("no unresolved template placeholders", async ({ page }) => {
      await page.goto(path);
      const html = await page.content();
      expect(html).not.toContain("{{");
      expect(html).not.toContain("}}");
      expect(html).not.toContain("{%");
      expect(html).not.toContain("%}");
    });

    test("html lang attribute matches locale", async ({ page }) => {
      await page.goto(path);
      const htmlLang = await page.getAttribute("html", "lang");
      expect(htmlLang).toBe(lang);
    });

    test("page has a non-empty title with Vauchi", async ({ page }) => {
      await page.goto(path);
      const title = await page.title();
      expect(title.length).toBeGreaterThan(5);
      expect(title).toContain("Vauchi");
    });

    test("meta description exists and is non-empty", async ({ page }) => {
      await page.goto(path);
      const desc = await page.getAttribute(
        'meta[name="description"]',
        "content"
      );
      expect(desc).toBeTruthy();
      expect(desc.length).toBeGreaterThan(20);
    });

    test("all 10 scenes exist", async ({ page }) => {
      await page.goto(path);
      const scenes = await page.locator("[data-scene]").count();
      expect(scenes).toBe(10);
    });

    test("CTA button exists with non-empty text", async ({ page }) => {
      await page.goto(path);
      const cta = page.locator("#hero-play");
      await expect(cta).toBeVisible();
      const text = await cta.textContent();
      expect(text.trim().length).toBeGreaterThan(3);
    });

    test("has Open Graph meta tags", async ({ page }) => {
      await page.goto(path);
      const ogTitle = await page.getAttribute(
        'meta[property="og:title"]',
        "content"
      );
      expect(ogTitle).toBeTruthy();
    });
  });
}

// ============================================================
// Translation tests — non-English pages must NOT show English
// ============================================================

for (const { lang, path } of NON_EN_LOCALES) {
  test.describe(`[${lang.toUpperCase()}] ${path} — translation`, () => {
    test("title is translated (not English)", async ({ page }) => {
      await page.goto(path);
      const title = await page.title();
      expect(title).not.toBe(EN_TITLE);
      expect(title).toContain("Vauchi");
    });

    test("meta description is translated", async ({ page }) => {
      await page.goto(path);
      const desc = await page.getAttribute(
        'meta[name="description"]',
        "content"
      );
      expect(desc).not.toBe(EN_DESCRIPTION);
    });

    test("scene 1 heading is translated", async ({ page }) => {
      await page.goto(path);
      const heading = page.locator('[data-scene="1"] .v-heading');
      const text = await heading.textContent();
      expect(text.trim()).not.toBe(EN_SCENE1_HEADING);
      expect(text.trim().length).toBeGreaterThan(10);
    });

    test("footer tagline is translated", async ({ page }) => {
      await page.goto(path);
      const footer = page.locator("footer");
      const text = await footer.textContent();
      // "Auditable" is English — should be translated
      expect(text).not.toContain(EN_FOOTER_TAGLINE);
    });

    test("auto-redirect script is NOT present", async ({ page }) => {
      await page.goto(path);
      const html = await page.content();
      // The language redirect script should only be on the EN page
      expect(html).not.toContain("vauchi-lang-checked");
    });
  });
}
