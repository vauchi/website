// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

for (const locale of ["en", "de", "es", "fr", "it"]) {
  test(`primary heading describes Vauchi in ${locale}`, async ({ page }) => {
    const copy = JSON.parse(readFileSync(`i18n/${locale}.json`, "utf8"));
    await page.goto(locale === "en" ? "/" : `/${locale}/`);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy["meta.title"]);
  });
}
