// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

import { test, expect } from "@playwright/test";

for (const path of ["/", "/blog/", "/blog/your-address-book-is-political/"]) {
  test(`SEO and Markdown discovery on ${path}`, async ({ page, request }) => {
    await page.goto(path);
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", `https://vauchi.app${path}`);
    await expect(page.locator('meta[property="og:title"]')).toHaveAttribute("content", await page.title());
    await expect(page.locator('meta[name="twitter:card"]')).toHaveAttribute("content", "summary_large_image");
    const overview = await page.locator('link[rel="describedby"]').getAttribute("href");
    const markdown = await page.locator('link[rel="alternate"][type="text/markdown"]').getAttribute("href");
    const overviewResponse = await request.get(new URL(overview).pathname);
    expect(overviewResponse.status()).toBe(200);
    expect(await overviewResponse.text()).toMatch(/^# Vauchi/);
    const markdownResponse = await request.get(new URL(markdown).pathname);
    expect(markdownResponse.status()).toBe(200);
    expect(await markdownResponse.text()).toMatch(/^# /);
  });
}

test("blog shares the landing theme choice and provides both modes", async ({ page }) => {
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.addInitScript(() => localStorage.setItem("vauchi-theme", "dracula"));
  await page.goto("/blog/");
  await expect(page.locator("header #theme-menu-toggle")).toBeInViewport();
  await expect(page.locator("header #mode-toggle")).toBeInViewport();
  await expect(page.locator('#theme-menu [data-theme-id="dracula"]')).toHaveCount(1);
  expect(await page.evaluate(() => document.documentElement.style.getPropertyValue("--bg-primary").trim())).toBe("#282a36");
  await page.locator("#mode-toggle").click();
  expect(await page.evaluate(() => localStorage.getItem("vauchi-theme"))).toBe("default-light");
  await page.locator("#theme-menu-toggle").click();
  await page.locator('[data-theme-id="nord"]').click();
  expect(await page.evaluate(() => localStorage.getItem("vauchi-theme"))).toBe("nord");
  expect(errors).toEqual([]);
});
