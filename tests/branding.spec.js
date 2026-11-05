// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

import { test, expect } from "@playwright/test";

for (const path of ["/", "/blog/", "/docs/", "/spec/"]) {
  test(`shared favicon on ${path}`, async ({ page, request }) => {
    test.skip(!process.env.BASE_URL && ["/docs/", "/spec/"].includes(path), "Combined preview only");
    await page.goto(path);
    const icons = page.locator('link[rel~="icon"][href$="favicon.ico"]');
    await expect(icons).toHaveCount(1);
    await expect(page.locator('link[rel~="icon"][href$="favicon.svg"], link[rel~="icon"][href$="favicon.png"]')).toHaveCount(0);
    const icon = await request.get(new URL(await icons.getAttribute("href"), page.url()).href);
    const landing = await request.get("/favicon.ico");
    expect(icon.status()).toBe(200);
    expect(Buffer.compare(await icon.body(), await landing.body())).toBe(0);
  });
}

test("waitlist management retains the shared theme and accessible form", async ({ page }) => {
  const origin = process.env.BASE_URL || "http://127.0.0.1:3002";
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.addInitScript(() => localStorage.setItem("vauchi-theme", "dracula"));
  await page.goto(`${origin}/waitlist/manage?lang=en`);
  await expect(page.locator('link[rel="icon"]')).toHaveAttribute("href", "/favicon.ico");
  await expect(page.locator("header #theme-menu-toggle")).toBeInViewport();
  await expect(page.locator("body")).toHaveCSS("background-color", "rgb(40, 42, 54)");
  await expect(page.getByRole("textbox", { name: "Email address" })).toBeVisible();
  await page.locator("#mode-toggle").click();
  expect(await page.evaluate(() => localStorage.getItem("vauchi-theme"))).toBe("default-light");
  await expect(page.locator("body")).toHaveCSS("background-color", "rgb(255, 255, 255)");
  expect(errors).toEqual([]);
});

test("reading the management page does not consume the mail request limit", async ({ request }) => {
  test.skip(!process.env.BASE_URL, "Production nginx preview only");
  for (let visit = 0; visit < 6; visit++) {
    const response = await request.get("/waitlist/manage?lang=en");
    expect(response.status()).toBe(200);
  }
});
