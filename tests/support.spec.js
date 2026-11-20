// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

// The support page shows the donation addresses published in funding.json,
// each with its QR code (vauchi/private#1307).

import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

const DONATION_CHANNELS = ["bitcoin-silent-payments", "bitcoin", "monero"];
const funding = JSON.parse(readFileSync("public/funding.json", "utf8"));
const addresses = Object.fromEntries(
  funding.funding.channels
    .filter((channel) => DONATION_CHANNELS.includes(channel.guid))
    .map((channel) => [channel.guid, channel.address]),
);
const locales = ["", "de/", "es/", "fr/", "it/"];

test("funding.json declares every donation channel the page shows", () => {
  expect(Object.keys(addresses).sort()).toEqual([...DONATION_CHANNELS].sort());
});

for (const prefix of locales) {
  const name = prefix || "en/";

  test(`${name}support/ shows each funding.json address with its QR code`, async ({ page }) => {
    const response = await page.goto(`/${prefix}support/`);
    expect(response.status()).toBe(200);
    await expect(page.locator("[data-donation-channel]")).toHaveCount(DONATION_CHANNELS.length);
    for (const guid of DONATION_CHANNELS) {
      const channel = page.locator(`[data-donation-channel="${guid}"]`);
      const address = channel.locator("code");
      await expect(address).toHaveText(addresses[guid]);
      await expect(address).toHaveAttribute("translate", "no");
      const qr = channel.getByRole("img");
      await expect(qr).toHaveAttribute("src", new RegExp(`^/support/qr-${guid}-[0-9a-f]{12}\\.svg$`));
      await expect(qr).not.toHaveAttribute("alt", "");
      await expect.poll(() => qr.evaluate((img) => img.naturalWidth)).toBeGreaterThan(0);
    }
  });

  test(`${name}support/ links the address list signed with Vauchi's key`, async ({ page, request }) => {
    const copy = JSON.parse(readFileSync(`i18n/${prefix ? prefix.slice(0, -1) : "en"}.json`, "utf8"));
    await page.goto(`/${prefix}support/`);
    await expect(page.getByRole("link", { name: copy["support.crypto.signed"] })).toHaveAttribute("href", "/donation-addresses.txt.asc");
    const signed = await request.get("/donation-addresses.txt.asc");
    expect(signed.status()).toBe(200);
    for (const address of Object.values(addresses)) expect(await signed.text()).toContain(address);
  });

  test(`${name}support/ description fits search snippets (120-160 characters)`, async ({ page }) => {
    await page.goto(`/${prefix}support/`);
    const description = await page.locator('meta[name="description"]').getAttribute("content");
    expect(description.length).toBeGreaterThanOrEqual(120);
    expect(description.length).toBeLessThanOrEqual(160);
  });

  test(`${name} footer has a BTC / XMR button to its support page`, async ({ page }) => {
    await page.goto(`/${prefix}`);
    const button = page.locator(".support-links").getByRole("link", { name: "BTC / XMR" });
    await expect(button).toHaveAttribute("href", `/${prefix}support/`);
    await expect(button).toBeVisible();
  });

  test(`${name} footer links to its support page`, async ({ page }) => {
    await page.goto(`/${prefix}`);
    await expect(page.locator("[data-support-page]")).toHaveAttribute("href", `/${prefix}support/`);
  });
}

for (const prefix of locales) {
  test(`${prefix || "en/"}support/ carries link-preview metadata and the shared page style`, async ({ page }) => {
    await page.goto(`/${prefix}support/`);
    const url = `https://vauchi.app/${prefix}support/`;
    const description = await page.locator('meta[name="description"]').getAttribute("content");
    await expect(page.locator('link[rel="stylesheet"][href="/css/page.css"]')).toHaveCount(1);
    await expect(page.locator('meta[property="og:url"]')).toHaveAttribute("content", url);
    await expect(page.locator('meta[property="og:title"]')).toHaveAttribute("content", await page.title());
    await expect(page.locator('meta[property="og:description"]')).toHaveAttribute("content", description);
    await expect(page.locator('meta[property="og:image"]')).toHaveAttribute("content", "https://vauchi.app/social-preview.png");
    await expect(page.locator('meta[name="twitter:card"]')).toHaveAttribute("content", "summary_large_image");
    await expect(page.locator('meta[name="theme-color"]')).toHaveCount(1);
    await expect(page.locator('link[rel="apple-touch-icon"]')).toHaveCount(1);
  });
}

async function backgroundColor(page) {
  return page.evaluate(() => getComputedStyle(document.body).backgroundColor);
}

async function waitForThemes(page) {
  await page.waitForFunction(() => document.querySelectorAll("#theme-menu [data-theme-id]").length > 0);
}

test("the support page switches light and dark like the landing page", async ({ page }) => {
  await page.goto("/support/");
  await page.evaluate(() => localStorage.removeItem("vauchi-theme"));
  await page.goto("/support/");
  await waitForThemes(page);
  const before = await backgroundColor(page);
  await page.click("#mode-toggle");
  await expect.poll(() => backgroundColor(page)).not.toBe(before);
});

test("a theme chosen on the landing page carries over to the support page", async ({ page }) => {
  await page.goto("/");
  await waitForThemes(page);
  await page.click("#theme-menu-toggle");
  await page.click('#theme-menu [data-theme-id="solarized-light"]');
  const landing = await backgroundColor(page);
  await page.goto("/support/");
  await waitForThemes(page);
  await expect.poll(() => backgroundColor(page)).toBe(landing);
});

test("each locale's support page has its own title", async ({ page }) => {
  const titles = new Set();
  for (const prefix of locales) {
    await page.goto(`/${prefix}support/`);
    titles.add(await page.title());
  }
  expect(titles.size).toBe(locales.length);
});
