// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

import { test, expect } from "@playwright/test";

test("umbrella metadata preserves the project's multiple license scopes", async ({ page, request }) => {
  await page.goto("/");
  const entities = await page.locator('script[type="application/ld+json"]').evaluateAll(
    nodes => nodes.map(node => JSON.parse(node.textContent))
  );
  expect(entities.map(entity => entity["@type"])).toEqual([
    "Organization", "WebSite", "SoftwareApplication"
  ]);
  expect(entities.find(entity => entity["@type"] === "SoftwareApplication")).not.toHaveProperty("license");
  await expect(page.locator('meta[name="dcterms.license"]')).toHaveCount(0);
  await expect(page.locator('meta[name="dcterms.rights"]')).toHaveAttribute(
    "content", "AGPL-3.0-or-later AND GPL-3.0-or-later"
  );
  const overview = await request.get("/llms.txt");
  expect(overview.status()).toBe(200);
  expect(await overview.text()).toContain("the core library and relays under AGPL-3.0-or-later");
  expect(await overview.text()).toContain("the apps under GPL-3.0-or-later");
});
