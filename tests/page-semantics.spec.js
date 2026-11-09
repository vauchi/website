// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

import { test, expect } from "@playwright/test";
import { readdirSync } from "node:fs";

function imagesWithoutAlternative(page) {
  return page.locator("img:not([alt]), img[alt='']");
}

test("decorative images with empty alt remain silent", async ({ page }) => {
  await page.setContent('<main><h1>Guide</h1><img src="decoration.svg" alt=""></main>');
  await expect(imagesWithoutAlternative(page)).toHaveCount(0);
  await expect(page.getByRole("img")).toHaveCount(0);
});

test("images missing alt are reported", async ({ page }) => {
  await page.setContent('<main><h1>Guide</h1><img src="contact-card.png"></main>');
  await expect(imagesWithoutAlternative(page)).toHaveCount(1);
});

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
    await expect(imagesWithoutAlternative(page)).toHaveCount(0);
  });
}
