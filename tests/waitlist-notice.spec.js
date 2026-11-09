// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

for (const locale of ["en", "de", "fr", "it", "es"]) {
  test(`signup notice links to its privacy policy without scripts in ${locale}`, async ({ browser }) => {
    const text = JSON.parse(readFileSync(`i18n/${locale}.json`, "utf8"));
    const context = await browser.newContext({ javaScriptEnabled: false, locale: "en-US" });
    try {
      const page = await context.newPage();
      await page.goto(new URL(locale === "en" ? "/" : `/${locale}/`,
        process.env.BASE_URL || "http://localhost:3000").href);
      const notice = page.locator("#waitlist .waitlist-privacy");
      await expect(notice).toContainText(text["waitlist.privacy_note"]);
      const policy = notice.getByRole("link", { name: text["footer.privacy"], exact: true });
      await expect(policy).toHaveAttribute("href", "https://vauchi.app/docs/legal/privacy-policy.html");
      await expect(policy).toBeVisible();
    } finally {
      await context.close();
    }
  });
}
