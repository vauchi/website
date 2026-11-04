// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

const service = "http://127.0.0.1:3002";

for (const locale of ["en", "de", "fr", "it", "es"]) {
  for (const javaScriptEnabled of [true, false]) {
    test(`confirmation settles without scripts: ${locale}, JS ${javaScriptEnabled}`, async ({ browser, request }) => {
      test.skip(!!process.env.BASE_URL, "Captured email fixture is local only");
      const text = JSON.parse(readFileSync(`i18n/${locale}.json`, "utf8"));
      const email = `confirm-${locale}-${javaScriptEnabled}@example.test`;
      const joined = await request.post(`${service}/waitlist/join`, {
        form: { email, lang: locale }, maxRedirects: 0,
      });
      expect(joined.status()).toBe(303);
      const outbox = await request.get(`${service}/__test/outbox`);
      const mail = (await outbox.json()).find(message => message.to === email);
      expect(mail).toBeDefined();
      const confirmation = mail.body.match(/http:\/\/[^\s]+\/waitlist\/confirm\?[^\s]+/)[0];
      const context = await browser.newContext({ javaScriptEnabled, locale: "de-DE" });
      const page = await context.newPage();
      if (javaScriptEnabled) await page.clock.install();
      const requests = [];
      const navigations = [];
      page.on("request", req => requests.push(req.url()));
      page.on("framenavigated", frame => {
        if (frame === page.mainFrame()) navigations.push(frame.url());
      });
      const result = await page.goto(confirmation, { waitUntil: "networkidle" });
      expect(result.status()).toBe(200);
      expect(result.request().redirectedFrom()).toBeNull();
      await expect(page.locator("html")).toHaveAttribute("lang", locale);
      await expect(page.getByRole("status")).toHaveText(text["waitlist.message.confirmed"]);
      await expect(page.locator("script, iframe, meta[http-equiv=refresh]")).toHaveCount(0);
      expect(await page.evaluate(() => document.readyState)).toBe("complete");
      await page.locator("style").evaluateAll(nodes => nodes.forEach(node => node.remove()));
      await expect(page.getByRole("status")).toBeVisible();
      if (javaScriptEnabled) await page.clock.fastForward(120_000);
      expect(requests).toEqual([confirmation]);
      expect(navigations).toEqual([confirmation]);
      await expect(page.getByRole("status")).toHaveText(text["waitlist.message.confirmed"]);
      const prefix = locale === "en" ? "/" : `/${locale}/`;
      await expect(page.getByRole("link", { name: text["footer.text_version"], exact: true }))
        .toHaveAttribute("href", `${service}${prefix}text/`);
      await context.close();
    });
  }
}

test("invalid confirmation is a stable result without JavaScript", async ({ browser }) => {
  test.skip(!!process.env.BASE_URL, "Local service only");
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  const response = await page.goto(`${service}/waitlist/confirm?token=synthetic-invalid&lang=en`);
  expect(response.status()).toBe(200);
  await expect(page.getByRole("status")).toHaveText("That confirmation link is invalid or expired.");
  await expect(page.locator("script")).toHaveCount(0);
  await context.close();
});
