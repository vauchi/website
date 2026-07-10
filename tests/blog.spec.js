// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

import { test, expect } from "@playwright/test";

// The blog is built by Zola into public/blog/ (see .gitlab-ci.yml
// test:e2e before_script; production builds it in the Dockerfile).
// These tests assert the launch article so they fail loudly if the
// zola build step is missing or produced an empty site.

const LAUNCH_ARTICLE = {
  slug: "eu-interoperability-contact-layer",
  title: "Interoperability without permission",
};

test("blog index lists the launch article with date and link", async ({
  page,
}) => {
  await page.goto("/blog/");
  await expect(page).toHaveTitle("Vauchi Blog");
  const link = page.locator(`a[href*="${LAUNCH_ARTICLE.slug}"]`);
  await expect(link).toHaveText(LAUNCH_ARTICLE.title);
  await expect(
    page.locator(".post-list .date").first()
  ).toHaveText("July 10, 2026");
});

test("article page renders title, date, and license note", async ({
  page,
}) => {
  await page.goto(`/blog/${LAUNCH_ARTICLE.slug}/`);
  await expect(page.locator("article h1")).toHaveText(LAUNCH_ARTICLE.title);
  await expect(page.locator("article .meta").first()).toContainText(
    "July 10, 2026"
  );
  await expect(
    page.locator('article a[rel~="license"]')
  ).toHaveText("CC BY 4.0");
});

test("atom feed is served and contains the launch article", async ({
  request,
}) => {
  const res = await request.get("/blog/atom.xml");
  expect(res.status()).toBe(200);
  const body = await res.text();
  expect(body).toContain("<feed");
  expect(body).toContain(LAUNCH_ARTICLE.title);
});

test("blog pages advertise the atom feed for autodiscovery", async ({
  page,
}) => {
  await page.goto("/blog/");
  const feedLink = page.locator('link[type="application/atom+xml"]');
  await expect(feedLink).toHaveAttribute("href", /\/blog\/atom\.xml$/);
});

test("landing page footer links to the blog", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator('footer a[href="/blog/"]')).toHaveText("Blog");
});
