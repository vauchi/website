// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

import { test, expect } from "@playwright/test";

for (const locale of ["en", "de", "fr", "it", "es"]) {
  const prefix = locale === "en" ? "/" : `/${locale}/`;
  test(`Open Graph locales use their own syntax in ${locale}`, async ({ page, request }) => {
    await page.goto(prefix);
    await expect(page.locator("html")).toHaveAttribute("lang", locale);
    await expect(page.locator('meta[property="og:url"]')).toHaveAttribute("content", `https://vauchi.app${prefix}`);
    await expect(page.locator('meta[property="og:type"]')).toHaveAttribute("content", "website");
    await expect(page.locator('meta[property="og:title"]')).toHaveAttribute("content", await page.title());
    const image = await page.locator('meta[property="og:image"]').getAttribute("content");
    expect(new URL(image).origin).toBe("https://vauchi.app");
    expect((await request.get(new URL(image).pathname)).status()).toBe(200);
    const values = await page.locator('meta[property="og:locale"], meta[property="og:locale:alternate"]').evaluateAll(
      nodes => nodes.map(node => node.content)
    );
    for (const value of values) {
      expect(value).toMatch(/^[a-z]{2}_[A-Z]{2}$/);
    }
  });
}
