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

    const headlineEl = page.locator("#hero-variant-headline");
    await expect(headlineEl).toHaveCount(1);
    const tagName = await headlineEl.evaluate((el) =>
      el.tagName.toLowerCase()
    );
    expect(tagName).toBe("h1");

    const headline = await page.textContent("#hero-variant-headline");
    const validHeadlines = Object.values(EN_VARIANT_HEADLINES);
    expect(validHeadlines).toContain(headline.trim());

    const bodyVariant = await page.getAttribute("body", "data-variant");
    expect(VARIANTS).toContain(bodyVariant);

    const metaVariant = await page.getAttribute(
      'meta[name="vauchi:variant"]',
      "content"
    );
    expect(metaVariant).toBe(bodyVariant);

    const orgScript = await page.locator("#ld-organization").textContent();
    const orgJson = JSON.parse(orgScript);
    expect(orgJson.slogan).toBe(headline.trim());
  });

  test("forces a specific variant via sessionStorage", async ({ page }) => {
    await page.context().clearCookies();
    await page.goto("/");
    await page.evaluate(() => sessionStorage.setItem("vauchi-variant", "b"));
    await page.goto("/");

    await expect(page.locator("body")).toHaveAttribute("data-variant", "b");
    const headline = await page.textContent("#hero-variant-headline");
    expect(headline.trim()).toBe(EN_VARIANT_HEADLINES.b);

    await expect(
      page.locator('meta[name="vauchi:variant"]')
    ).toHaveAttribute("content", "b");

    const orgScript = await page.locator("#ld-organization").textContent();
    const orgJson = JSON.parse(orgScript);
    expect(orgJson.slogan).toBe(EN_VARIANT_HEADLINES.b);
  });

  test("shows variant but does not send beacon when DNT is enabled", async ({ page }) => {
    await page.addInitScript(() => {
      Object.defineProperty(navigator, "doNotTrack", { value: "1" });
      window.__capturedBeacons = [];
      navigator.sendBeacon = function (url, data) {
        window.__capturedBeacons.push({ url: String(url), data });
        return true;
      };
    });
    await page.goto("/");

    const defaultPoints = page.locator("#hero-default-points");
    const variantBlock = page.locator("#hero-variant-block");

    await expect(defaultPoints).toHaveClass(/hidden/);
    await expect(variantBlock).not.toHaveClass(/hidden/);

    const bodyVariant = await page.getAttribute("body", "data-variant");
    expect(VARIANTS).toContain(bodyVariant);

    await page.evaluate(() => {
      window.dispatchEvent(new Event("pagehide"));
    });

    const beaconCount = await page.evaluate(() =>
      window.__capturedBeacons.filter((b) =>
        String(b.url).endsWith("/beacon")
      ).length
    );
    expect(beaconCount).toBe(0);
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

  test("serves a static variants.json manifest for crawlers", async ({ request }) => {
    const res = await request.get("/variants.json");
    expect(res.status()).toBe(200);
    expect(res.headers()["content-type"]).toContain("application/json");

    const manifest = await res.json();
    expect(manifest.default_locale).toBe("en");
    expect(manifest.locales).toHaveProperty("en");
    expect(manifest.variants).toHaveProperty("b");
    expect(manifest.variants.b.slug).toBe("no-brainrot-no-data-theft-just-people");

    const en = manifest.locales.en;
    for (const id of VARIANTS) {
      expect(en).toHaveProperty(id);
      expect(en[id]).toHaveProperty("headline");
      expect(en[id]).toHaveProperty("label");
      expect(en[id]).toHaveProperty("sub");
      expect(en[id]).toHaveProperty("cta");
      expect(en[id].headline).toBe(EN_VARIANT_HEADLINES[id]);
    }
  });

  test("variant landing page has accurate SEO/social meta", async ({ page }) => {
    const slug = "no-brainrot-no-data-theft-just-people";
    const headline = EN_VARIANT_HEADLINES.b;
    const sub = "A contact exchange that respects your attention and your data.";
    const url = `/landing/${slug}/`;

    await page.goto(url);

    await expect(page).toHaveTitle(`${headline} | Vauchi`);
    await expect(page.locator('meta[name="description"]')).toHaveAttribute(
      "content",
      sub
    );
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute(
      "content",
      "noindex"
    );
    await expect(page.locator('meta[property="og:url"]')).toHaveAttribute(
      "content",
      `https://vauchi.app${url}`
    );
    await expect(page.locator('meta[property="og:title"]')).toHaveAttribute(
      "content",
      `${headline} | Vauchi`
    );
    await expect(page.locator('meta[property="og:description"]')).toHaveAttribute(
      "content",
      sub
    );

    const orgScript = await page.locator("#ld-organization").textContent();
    const orgJson = JSON.parse(orgScript);
    expect(orgJson.slogan).toBe(headline);

    await expect(page.locator("body")).toHaveAttribute("data-variant", "b");
    await expect(page.locator("#hero-default-points")).toHaveClass(/hidden/);
    await expect(page.locator("#hero-variant-block")).not.toHaveClass(/hidden/);
    const heroHeadline = await page.textContent("#hero-variant-headline");
    expect(heroHeadline.trim()).toBe(headline);
  });

  test("variant landing page is not overridden by client-side randomization", async ({ page }) => {
    const slug = "the-address-book-that-fixes-itself";
    const url = `/landing/${slug}/`;

    await page.goto(url);
    await page.evaluate(() => sessionStorage.removeItem("vauchi-variant"));
    await page.reload();

    await expect(page.locator("body")).toHaveAttribute("data-variant", "g");
    const heroHeadline = await page.textContent("#hero-variant-headline");
    expect(heroHeadline.trim()).toBe(EN_VARIANT_HEADLINES.g);
  });
});
