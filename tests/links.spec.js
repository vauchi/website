// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

// /links/: projects that share Vauchi's values, each with a plain
// description and how it fits Vauchi, in every locale (vauchi/private#1379).

import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

const locales = ["en", "de", "es", "fr", "it"];
const prefixOf = (locale) => (locale === "en" ? "/" : `/${locale}/`);

const entries = {
  eff: "https://www.eff.org/",
  noyb: "https://noyb.eu/",
  edri: "https://edri.org/",
  fsf: "https://www.fsf.org/",
  digiges: "https://www.digitale-gesellschaft.ch/",
  ccc: "https://www.ccc.de/en/",
  signal: "https://signal.org/",
  briar: "https://briarproject.org/",
  deltachat: "https://delta.chat/",
  matrix: "https://matrix.org/",
  threema: "https://threema.com/",
  firefox: "https://www.mozilla.org/firefox/",
  ublockorigin: "https://github.com/gorhill/uBlock",
  thunderbird: "https://www.thunderbird.net/",
  posteo: "https://posteo.de/en",
  mailboxorg: "https://mailbox.org/en/",
  keepassxc: "https://keepassxc.org/",
  openstreetmap: "https://www.openstreetmap.org/",
  wikipedia: "https://www.wikipedia.org/",
  cryptpad: "https://cryptpad.org/",
  jitsi: "https://jitsi.org/jitsi-meet/",
  nextcloud: "https://nextcloud.com/",
  davx5: "https://www.davx5.com/",
  privacyguides: "https://www.privacyguides.org/",
  fdroid: "https://f-droid.org/",
  torproject: "https://www.torproject.org/",
  grapheneos: "https://grapheneos.org/",
  nlnet: "https://nlnet.nl/",
  sovereigntech: "https://www.sovereign.tech/",
  prototypefund: "https://prototypefund.de/en/",
  nextgraph: "https://nextgraph.org/",
  mastodon: "https://joinmastodon.org/",
  indieweb: "https://indieweb.org/",
  typeups: "https://www.typeups.com/",
};

for (const locale of locales) {
  const prefix = prefixOf(locale);
  const url = `https://vauchi.app${prefix}links/`;
  const copy = JSON.parse(readFileSync(`i18n/${locale}.json`, "utf8"));

  test(`${prefix}links/ is an indexable page with its own metadata`, async ({ page }) => {
    const response = await page.goto(`${prefix}links/`);
    expect(response.status()).toBe(200);
    await expect(page.locator("html")).toHaveAttribute("lang", locale);
    await expect(page.locator("h1")).toHaveText(copy["linkspage.heading"]);
    await expect(page.locator('meta[name="robots"]')).toHaveCount(0);
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", url);
    await expect(page.locator('link[rel="alternate"][hreflang]')).toHaveCount(locales.length + 1);
    const description = await page.locator('meta[name="description"]').getAttribute("content");
    expect(description.length).toBeGreaterThanOrEqual(120);
    expect(description.length).toBeLessThanOrEqual(160);
    await expect(page.locator("[data-links-disclaimer]")).toHaveText(copy["linkspage.disclaimer"]);
    await expect(page.locator("[data-links-checked]")).toHaveText(copy["linkspage.checked"]);
    await expect(page.locator("[data-links-checked] time")).toHaveAttribute("datetime", "2026-11-24");
    await expect(page.locator("[data-links-suggest]")).toContainText(copy["linkspage.suggest"]);
    await expect(page.locator("[data-links-suggest] a")).toHaveAttribute("href", "mailto:hello@vauchi.app");
  });

  test(`${prefix}links/ links every project with what it is and how it fits`, async ({ page }) => {
    await page.goto(`${prefix}links/`);
    for (const [id, href] of Object.entries(entries)) {
      const entry = page.locator(`[data-link-entry="${id}"]`);
      await expect(entry.locator("a").first()).toHaveAttribute("href", href);
      await expect(entry.locator("[data-link-about]")).toHaveText(copy[`linkspage.${id}.about`]);
      await expect(entry.locator("[data-link-fit]")).toContainText(copy[`linkspage.${id}.fit`]);
    }
    await expect(page.locator("[data-link-entry]")).toHaveCount(Object.keys(entries).length);
  });

  test(`${prefix} footer links the projects page`, async ({ page }) => {
    await page.goto(prefix);
    await expect(page.locator("[data-links-link]")).toHaveAttribute("href", `${prefix}links/`);
  });

  for (const slug of ["", "no-directory/", "change-your-number/", "beyond-social-network/", "one-exchange/"]) {
    test(`${prefix}why/${slug} links the projects page`, async ({ page }) => {
      await page.goto(`${prefix}why/${slug}`);
      await expect(page.locator("[data-links-link]")).toHaveAttribute("href", `${prefix}links/`);
    });
  }
}

test("sitemap-pages.xml lists /links/ in every locale", async ({ request }) => {
  const body = await (await request.get("/sitemap-pages.xml")).text();
  for (const locale of locales) {
    expect(body).toContain(`<loc>https://vauchi.app${prefixOf(locale)}links/</loc>`);
  }
});
