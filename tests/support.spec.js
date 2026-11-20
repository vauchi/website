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
      await expect(qr).toHaveAttribute("src", `/support/qr-${guid}.svg`);
      await expect(qr).not.toHaveAttribute("alt", "");
      await expect.poll(() => qr.evaluate((img) => img.naturalWidth)).toBeGreaterThan(0);
    }
  });

  test(`${name}support/ description fits search snippets (120-160 characters)`, async ({ page }) => {
    await page.goto(`/${prefix}support/`);
    const description = await page.locator('meta[name="description"]').getAttribute("content");
    expect(description.length).toBeGreaterThanOrEqual(120);
    expect(description.length).toBeLessThanOrEqual(160);
  });

  test(`${name} footer links to its support page`, async ({ page }) => {
    await page.goto(`/${prefix}`);
    await expect(page.locator("[data-support-page]")).toHaveAttribute("href", `/${prefix}support/`);
  });
}

test("each locale's support page has its own title", async ({ page }) => {
  const titles = new Set();
  for (const prefix of locales) {
    await page.goto(`/${prefix}support/`);
    titles.add(await page.title());
  }
  expect(titles.size).toBe(locales.length);
});
