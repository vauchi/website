// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

import { test, expect } from "@playwright/test";
import { readdirSync } from "node:fs";

const locales = ["", "de/", "es/", "fr/", "it/"];
const paths = locales.flatMap(locale => [`/${locale}`, `/${locale}text/`]);
for (const directory of ["landing", "blog"]) {
  for (const file of readdirSync(`public/${directory}`, { recursive: true })) {
    if (file.endsWith("index.html") && !file.startsWith("admin/")) {
      paths.push(`/${directory}/${file.slice(0, -10)}`);
    }
  }
}

for (const path of paths) {
  test(`one accessible page heading and image alternatives on ${path}`, async ({ page }) => {
    const response = await page.goto(path);
    expect(response.status()).toBe(200);
    await expect(page.locator("h1")).toHaveCount(1);
    await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);
    await expect(page.locator("img:not([alt]), img[alt='']")).toHaveCount(0);
  });
}
