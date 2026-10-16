// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

import { readFileSync } from "node:fs";
import { test, expect } from "@playwright/test";

const manifest = JSON.parse(
  readFileSync("public/variants.json", "utf8")
);
const profiles = [
  { name: "ordinary", dnt: null, gpc: false },
  { name: "dnt", dnt: "1", gpc: false },
  { name: "gpc", dnt: null, gpc: true },
];

for (const profile of profiles) {
  for (const locale of Object.keys(manifest.locales)) {
    for (const [variant, details] of Object.entries(manifest.variants)) {
      test(`privacy ${profile.name}-${locale}-${variant}`, async ({ page, context }) => {
        const beacons = [];
        const writes = [];
        await page.exposeFunction("observePrivacyBeacon", (url) => beacons.push(url));
        await page.addInitScript(({ dnt, gpc }) => {
          Object.defineProperty(navigator, "doNotTrack", { value: dnt });
          Object.defineProperty(navigator, "globalPrivacyControl", { value: gpc });
          window.privacyBeaconAttempts = [];
          navigator.sendBeacon = (url) => {
            window.privacyBeaconAttempts.push(String(url));
            window.observePrivacyBeacon(String(url));
            return true;
          };
        }, profile);
        await page.route("**/*", async (route) => {
          const request = route.request();
          if (!["GET", "HEAD"].includes(request.method())) {
            writes.push({ method: request.method(), url: request.url() });
            await route.abort();
          } else {
            await route.continue();
          }
        });

        const suffix = locale === manifest.default_locale ? "" : `${locale}/`;
        await page.goto(`/landing/${details.slug}/${suffix}`);
        await expect(page.locator("body")).toHaveAttribute("data-variant", variant);
        await expect(page.locator("#hero-variant-headline")).toBeVisible();
        await page.locator("#hero-play").click();
        const attempts = await page.evaluate(() => {
          document.dispatchEvent(new Event("visibilitychange"));
          window.dispatchEvent(new Event("pagehide"));
          window.dispatchEvent(new Event("beforeunload"));
          return window.privacyBeaconAttempts;
        });
        expect(attempts).toEqual([]);

        await page.goto(locale === manifest.default_locale ? "/" : `/${locale}/`);
        await expect(page.locator("#hero-variant-headline")).toBeVisible();
        const afterNavigation = await page.evaluate(() => {
          window.dispatchEvent(new Event("pagehide"));
          return window.privacyBeaconAttempts;
        });
        expect(afterNavigation).toEqual([]);
        expect(beacons).toEqual([]);
        expect(writes).toEqual([]);
        expect(await context.cookies()).toEqual([]);
      });
    }
  }
}
