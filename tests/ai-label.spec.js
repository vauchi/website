// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

import { test, expect } from "@playwright/test";

async function circlePixels(image) {
  return image.evaluate((element) => {
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 100;
    const context = canvas.getContext("2d");
    context.drawImage(element, 0, 0, 100, 100);
    return {
      top: [...context.getImageData(50, 3, 1, 1).data],
      corner: [...context.getImageData(0, 0, 1, 1).data],
    };
  });
}

test("AI disclosure follows the chosen theme across toggles and reloads", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "light" });
  await page.addInitScript(() => {
    if (!localStorage.getItem("vauchi-theme")) localStorage.setItem("vauchi-theme", "default-light");
  });
  await page.goto("/blog/eu-interoperability-contact-layer/");
  await expect(page.locator('#theme-menu [data-theme-id="default-dark"]')).toHaveCount(1);

  const light = page.locator(".ai-label-for-light");
  const dark = page.locator(".ai-label-for-dark");
  await expect(light).toBeVisible();
  await expect(dark).toBeHidden();
  await expect(light).toHaveJSProperty("complete", true);
  expect(await circlePixels(light)).toEqual({ top: [0, 0, 0, 255], corner: [0, 0, 0, 0] });

  await page.locator("#mode-toggle").click();
  await expect(dark).toBeVisible();
  await expect(light).toBeHidden();
  await expect(dark).toHaveJSProperty("complete", true);
  expect(await circlePixels(dark)).toEqual({ top: [255, 255, 255, 255], corner: [0, 0, 0, 0] });
  await expect(page.locator(".byline")).toContainText("Drafted with AI assistance.");

  await page.reload();
  await expect(dark).toBeVisible();
  await expect(light).toBeHidden();

  await page.emulateMedia({ colorScheme: "dark" });
  await page.locator("#mode-toggle").click();
  await expect(light).toBeVisible();
  await expect(dark).toBeHidden();
});
