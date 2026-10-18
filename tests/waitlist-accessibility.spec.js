// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

import { test, expect } from "@playwright/test";

const locales = {
  en: ["Email address", "Leave the waitlist"],
  de: ["E-Mail-Adresse", "Von der Warteliste abmelden"],
  fr: ["Adresse e-mail", "Quitter la liste d’attente"],
  it: ["Indirizzo email", "Esci dalla lista d’attesa"],
  es: ["Dirección de correo electrónico", "Salir de la lista de espera"],
};

for (const [locale, [emailLabel, leaveLabel]] of Object.entries(locales)) {
  for (const width of [390, 1440]) {
    test(`waitlist labels and removal link ${locale} ${width}`, async ({ page }) => {
      await page.setViewportSize({ width, height: 844 });
      await page.emulateMedia({ reducedMotion: "reduce" });
      await page.goto(locale === "en" ? "/" : `/${locale}/`);
      const input = page.getByLabel(emailLabel, { exact: true });
      await expect(input).toBeVisible();
      await expect(input).toHaveAttribute("type", "email");
      await input.focus();
      await page.keyboard.press("Tab");
      await expect(page.locator('.waitlist-form button[type="submit"]')).toBeFocused();
      await expect(page.getByRole("link", { name: leaveLabel, exact: true })).toHaveAttribute("href", `/waitlist/manage?lang=${locale}`);
      expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBe(0);
    });
  }
}
