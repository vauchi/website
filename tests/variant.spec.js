// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

import { test, expect } from "@playwright/test";

const VARIANTS = ["a", "b", "c", "d", "e", "f", "g"];
const EN_VARIANT_HEADLINES = {
  a: "Your contact card. Your channels. Your rules.",
  b: "No brainrot. No data theft. Just people.",
  c: "Connect on your own terms, across every channel.",
  d: "Exchange contacts, not access to your life.",
  e: "Stop renting your address book.",
  f: "Meet once. Stay in touch forever.",
  g: "The address book that fixes itself.",
};

test.describe("landing-page variant test", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("randomly applies one of the variant messages", async ({ page }) => {
    const variantBlock = page.locator("#hero-variant-block");
    const defaultPoints = page.locator("#hero-default-points");

    await expect(variantBlock).not.toHaveClass(/hidden/);
    await expect(defaultPoints).toHaveClass(/hidden/);

    const headline = await page.textContent("#hero-variant-headline");
    const validHeadlines = Object.values(EN_VARIANT_HEADLINES);
    expect(validHeadlines).toContain(headline.trim());

    const bodyVariant = await page.getAttribute("body", "data-variant");
    expect(VARIANTS).toContain(bodyVariant);
  });

  test("forces a specific variant via sessionStorage", async ({ page }) => {
    await page.context().clearCookies();
    await page.goto("/");
    await page.evaluate(() => sessionStorage.setItem("vauchi-variant", "b"));
    await page.goto("/");

    await expect(page.locator("body")).toHaveAttribute("data-variant", "b");
    const headline = await page.textContent("#hero-variant-headline");
    expect(headline.trim()).toBe(EN_VARIANT_HEADLINES.b);
  });

  test("does not randomize when DNT is enabled", async ({ page }) => {
    await page.addInitScript(() => {
      Object.defineProperty(navigator, "doNotTrack", { value: "1" });
    });
    await page.goto("/");

    const defaultPoints = page.locator("#hero-default-points");
    const variantBlock = page.locator("#hero-variant-block");

    await expect(defaultPoints).not.toHaveClass(/hidden/);
    await expect(variantBlock).toHaveClass(/hidden/);
    await expect(page.locator("body")).not.toHaveAttribute("data-variant", /.*/);
  });

  test("sends an anonymous metrics beacon on page hide", async ({ page }) => {
    await page.addInitScript(() => {
      window.__capturedBeacons = [];
      navigator.sendBeacon = function (url, data) {
        window.__capturedBeacons.push({ url: String(url), data });
        return true;
      };
    });
    await page.goto("/");

    await page.evaluate(() => {
      window.dispatchEvent(new Event("pagehide"));
    });

    const payload = await page.evaluate(() => {
      const beacon = window.__capturedBeacons.find((b) =>
        String(b.url).endsWith("/beacon")
      );
      if (!beacon) return null;
      return beacon.data.text().then((text) => JSON.parse(text));
    });
    expect(VARIANTS).toContain(payload.v);
    expect(typeof payload.clicks).toBe("number");
    expect(typeof payload.dwell_ms).toBe("number");
    expect(payload.dwell_ms).toBeGreaterThanOrEqual(0);
    expect(payload.path).toBe("/");
  });
});
