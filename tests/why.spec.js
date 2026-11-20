// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

// /why/ pages: one reason each, with its limits, indexable in every
// locale (vauchi/private#1313).

import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

const locales = ["en", "de", "es", "fr", "it"];
const topics = ["no-directory", "change-your-number"];
const prefixOf = (locale) => (locale === "en" ? "/" : `/${locale}/`);

function jsonLd(page) {
  return page
    .locator('script[type="application/ld+json"]')
    .allTextContents()
    .then((blocks) => blocks.map((block) => JSON.parse(block)));
}

for (const locale of locales) {
  const prefix = prefixOf(locale);
  const copy = JSON.parse(readFileSync(`i18n/${locale}.json`, "utf8"));

  for (const slug of ["", ...topics.map((topic) => `${topic}/`)]) {
    const path = `${prefix}why/${slug}`;
    const url = `https://vauchi.app${path}`;

    test(`${path} is an indexable page with its own metadata`, async ({ page }) => {
      const response = await page.goto(path);
      expect(response.status()).toBe(200);
      await expect(page.locator("html")).toHaveAttribute("lang", locale);
      await expect(page.locator("h1")).toHaveCount(1);
      await expect(page.locator('meta[name="robots"]')).toHaveCount(0);
      await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", url);
      await expect(page.locator('meta[property="og:url"]')).toHaveAttribute("content", url);
      await expect(page.locator('link[rel="alternate"][hreflang]')).toHaveCount(locales.length + 1);
      const description = await page.locator('meta[name="description"]').getAttribute("content");
      expect(description.length).toBeGreaterThanOrEqual(120);
      expect(description.length).toBeLessThanOrEqual(160);
      const webPage = (await jsonLd(page)).find((block) => block["@type"] === "WebPage");
      expect(webPage.description).toBe(description);
      expect(webPage.url).toBe(url);
      await expect(page.locator("[data-why-notice]")).toHaveText(copy["whypage.notice"]);
      await expect(page.locator('a[rel="author"]')).toHaveText("Mattia Egloff");
      await expect(page.locator("[data-why-byline]")).toContainText(copy["whypage.ai_assisted"]);
      expect(webPage.headline).toBe(await page.locator("h1").textContent());
      expect(webPage.mainEntityOfPage).toBe(url);
    });
  }

  for (const topic of topics) {
    test(`${prefix}why/${topic}/ states its limits and answers its questions`, async ({ page }) => {
      await page.goto(`${prefix}why/${topic}/`);
      await expect(page.locator("h1")).toHaveText(copy[`whypage.${topic}.heading`]);
      const limits = page.locator("[data-why-limits] li");
      await expect(limits).toHaveCount(3);
      await expect(limits.first()).toHaveText(copy[`whypage.${topic}.limit1`]);
      const faq = (await jsonLd(page)).find((block) => block["@type"] === "FAQPage");
      expect(faq.mainEntity.map((q) => q.name)).toEqual([1, 2, 3].map((n) => copy[`whypage.${topic}.q${n}`]));
      expect(faq.mainEntity.map((q) => q.acceptedAnswer.text)).toEqual([1, 2, 3].map((n) => copy[`whypage.${topic}.a${n}`]));
      await expect(page.getByRole("link", { name: copy["whypage.cta"] })).toHaveAttribute("href", `${prefix}#waitlist`);
    });
  }

  test(`${prefix}why/ links every reason`, async ({ page }) => {
    await page.goto(`${prefix}why/`);
    for (const topic of topics) {
      await expect(page.getByRole("link", { name: copy[`whypage.${topic}.heading`] })).toHaveAttribute("href", `${prefix}why/${topic}/`);
    }
  });

  test(`${prefix} footer links the reasons`, async ({ page }) => {
    await page.goto(prefix);
    await expect(page.locator("[data-why-link]")).toHaveAttribute("href", `${prefix}why/`);
  });
}

test("sitemap-pages.xml lists every /why/ page in every locale", async ({ request }) => {
  const body = await (await request.get("/sitemap-pages.xml")).text();
  for (const locale of locales) {
    for (const slug of ["", ...topics.map((topic) => `${topic}/`)]) {
      expect(body).toContain(`<loc>https://vauchi.app${prefixOf(locale)}why/${slug}</loc>`);
    }
  }
});
