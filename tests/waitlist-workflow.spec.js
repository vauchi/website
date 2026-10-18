// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

const service = "http://127.0.0.1:3002";
const admin = { Authorization: "Bearer synthetic-browser-export-key" };

for (const locale of ["en", "de", "fr", "it", "es"]) {
  const text = JSON.parse(readFileSync(`i18n/${locale}.json`, "utf8"));
  for (const width of [390, 1440]) {
    test(`local waitlist journey ${locale} ${width}`, async ({ page, request }) => {
      test.skip(!!process.env.BASE_URL, "Synthetic mail fixture is local only");
      const email = `browser-${locale}-${width}@example.test`;
      await page.setViewportSize({ width, height: 844 });
      await page.emulateMedia({ reducedMotion: "reduce" });
      await page.goto(`${service}/${locale === "en" ? "" : locale + "/"}`);
      await page.getByLabel(text["waitlist.email_label"], { exact: true }).fill(email);
      const joined = page.waitForResponse(response => response.url().endsWith("/waitlist/join")
        && response.request().method() === "POST");
      await page.locator('.waitlist-form button[type="submit"]').click();
      expect((await joined).status()).toBe(303);
      await expect(page.locator("#waitlist-message")).toHaveText(text["waitlist.message.joined"]);

      const outbox = await request.get(`${service}/__test/outbox`);
      expect(outbox.status()).toBe(200);
      const messages = (await outbox.json()).filter(message => message.to === email);
      expect(messages).toHaveLength(1);
      expect(messages[0].subject).toBe(text["waitlist.mail.confirm_subject"]);
      const links = messages[0].body.match(/http:\/\/[^\s]+\/waitlist\/[^\s]+/g);
      expect(links).toHaveLength(2);
      const confirmation = links.find(link => link.includes("/confirm?"));
      const withdrawal = links.find(link => link.includes("/withdraw?"));
      await page.goto(confirmation);
      await expect(page.locator("#waitlist-message")).toHaveText(text["waitlist.message.confirmed"]);
      await page.goto(withdrawal);
      await expect(page.locator("html")).toHaveAttribute("lang", locale);
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(text["waitlist.manage.heading"]);
      const before = await request.get(`${service}/waitlist/admin/export`, { headers: admin });
      expect(before.status()).toBe(200);
      expect(await before.text()).toContain(email);
      const remove = page.getByRole("button", { name: text["waitlist.manage.remove"], exact: true });
      await remove.focus();
      await page.keyboard.press("Enter");
      await expect(page.getByRole("status")).toHaveText(text["waitlist.manage.done"]);
      const after = await request.get(`${service}/waitlist/admin/export`, { headers: admin });
      expect(after.status()).toBe(200);
      expect(await after.text()).not.toContain(email);
      await expect(page.getByRole("link", { name: text["waitlist.manage.privacy"], exact: true }))
        .toHaveAttribute("href", "https://vauchi.app/docs/legal/privacy-policy.html");
      expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBe(0);
    });
  }
}
