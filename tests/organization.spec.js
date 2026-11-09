// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

import { test, expect } from "@playwright/test";

for (const path of ["/#organization", "/text/#organization"]) {
  test(`organization anchor explains the person and motivation at ${path}`, async ({ page }) => {
    await page.goto(path);
    const section = page.locator("#organization");
    await expect(section).toBeVisible();
    await expect(section.getByRole("heading", { name: "Who's behind Vauchi?" })).toBeVisible();
    await expect(section).toContainText("For now, Vauchi is a solo project by Mattia Egloff.");
    await expect(section).toContainText("people's networks belong to the people in them");
    await expect(section).toContainText("could he build something complex with AI agents");
    await expect(section).toContainText("software assistants that help write and check code");
  });
}
