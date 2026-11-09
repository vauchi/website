// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

for (const locale of ["en", "de", "fr", "it", "es"]) {
  const prefix = locale === "en" ? "/" : `/${locale}/`;
  test(`readable versions retain material caveats in ${locale}`, async ({ page, request }) => {
    const copy = JSON.parse(readFileSync(`i18n/${locale}.json`, "utf8"));
    await page.goto(`${prefix}text/`);
    const markdown = await request.get(`${prefix}index.md`);
    expect(markdown.status()).toBe(200);
    const body = await markdown.text();
    for (const key of ["honest.heading", "honest.item1", "honest.item2", "honest.item3", "honest.item4", "honest.note", "organization.heading", "organization.body1", "organization.body2"]) {
      await expect(page.locator("main")).toContainText(copy[key]);
      expect(body).toContain(copy[key]);
    }
  });

  test(`text reading works without scripts or styles in ${locale}`, async ({ browser }) => {
    const copy = JSON.parse(readFileSync(`i18n/${locale}.json`, "utf8"));
    const context = await browser.newContext({ javaScriptEnabled: false });
    const page = await context.newPage();
    await page.goto(`http://localhost:3000${prefix}`);
    await page.locator("footer a[data-text-version]").click();
    await expect(page).toHaveURL(new RegExp(`${prefix}text/$`));
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", `https://vauchi.app${prefix}`);
    await expect(page.locator("html")).toHaveAttribute("lang", locale);
    await expect(page.locator("main h1")).toHaveText("Vauchi");
    await expect(page.locator("main h2")).toHaveCount(7);
    await expect(page.locator("#organization h2")).toHaveText(copy["organization.heading"]);
    await expect(page.locator("script")).toHaveCount(0);
    await page.locator("style, link[rel=stylesheet]").evaluateAll(nodes => nodes.forEach(node => node.remove()));
    await expect(page.locator("main")).toBeVisible();
    await expect(page.locator("body")).not.toContainText(/\uFFFD|\u{1F4F1}|\u{1F464}/u);
    await expect(page.getByRole("link", { name: "Blog", exact: true })).toHaveAttribute("href", "/blog/");
    await expect(page.getByRole("link", { name: "Spec", exact: true })).toHaveAttribute("href", "https://spec.vauchi.app/");
    await context.close();
  });
}

test("unstyled landing page offers prose instead of the decorative player", async ({ page }) => {
  await page.goto("/");
  await page.locator("style, link[rel=stylesheet]").evaluateAll(nodes => nodes.forEach(node => node.remove()));
  await expect(page.locator("#player")).toBeHidden();
  await expect(page.locator(".text-fallback")).toBeVisible();
});

test("email confirmation survives the first language redirect", async ({ browser }) => {
  const context = await browser.newContext({ locale: "de-DE" });
  const page = await context.newPage();
  await page.goto("http://localhost:3000/?waitlist=confirmed#waitlist");
  await expect(page).toHaveURL(/\/de\/#waitlist$/);
  await expect(page.locator("#waitlist-message")).toBeVisible();
  await expect(page.locator("#waitlist-message")).toHaveClass(/--confirmed/);
  await context.close();
});
