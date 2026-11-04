// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

import { readFileSync } from "node:fs";
import { test, expect } from "@playwright/test";

const policy = readFileSync("nginx.conf", "utf8").match(
  /add_header Content-Security-Policy "([^"]+)"/
)[1];
const manifest = JSON.parse(readFileSync("public/variants.json", "utf8"));

for (const locale of Object.keys(manifest.locales)) {
  test(`variant initialization respects Trusted Types in ${locale}`, async ({ page }) => {
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.addInitScript(() => {
      sessionStorage.setItem("vauchi-variant", "b");
      window.policyViolations = [];
      document.addEventListener("securitypolicyviolation", (event) => {
        window.policyViolations.push({
          directive: event.violatedDirective,
          source: event.sourceFile,
          line: event.lineNumber,
          sample: event.sample,
        });
      });
    });
    await page.route("**/*", async (route) => {
      if (route.request().resourceType() !== "document") {
        await route.continue();
        return;
      }
      const response = await route.fetch();
      await route.fulfill({
        response,
        headers: { ...response.headers(), "content-security-policy": policy },
      });
    });

    await page.goto(locale === "en" ? "/" : `/${locale}/`);

    const expected = manifest.locales[locale].b;
    await expect(page.locator("body")).toHaveAttribute("data-variant", "b");
    await expect(page.locator("#hero-play")).toHaveText(expected.cta);
    await expect(page.locator("#hero-variant-headline")).toHaveText(expected.headline);
    const organization = JSON.parse(
      await page.locator("#ld-organization").textContent()
    );
    expect(organization.slogan).toBe(expected.headline);
    expect(errors).toEqual([]);
    expect(await page.evaluate(() => window.policyViolations)).toEqual([]);
  });
}
