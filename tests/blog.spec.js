// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

import { test, expect } from "@playwright/test";

// The blog is built by Zola into public/blog/ (see .gitlab-ci.yml
// test:e2e before_script; production builds it in the Dockerfile).
// These tests assert the launch article so they fail loudly if the
// zola build step is missing or produced an empty site.

const LAUNCH_ARTICLE = {
  slug: "eu-interoperability-contact-layer",
  title: "Leave any platform without losing your people",
  date: "July 10, 2026",
};

// Newest post. The index is sorted by date descending, so this one leads.
const LATEST_ARTICLE = {
  slug: "never-meant-to-be-permanent",
  title: "Your contact details were never meant to be permanent",
  date: "August 02, 2026",
};

test("blog index lists both articles with dates and links", async ({
  page,
}) => {
  await page.goto("/blog/");
  await expect(page).toHaveTitle("Vauchi Blog");
  for (const article of [LAUNCH_ARTICLE, LATEST_ARTICLE]) {
    const link = page.locator(`a[href*="${article.slug}"]`);
    await expect(link).toHaveText(article.title);
    // Scope the date to its own row rather than asserting on .first() —
    // that coupled the test to publication order and broke the moment a
    // newer post landed.
    const row = page.locator(".post-list li", { has: link });
    await expect(row.locator(".date")).toHaveText(article.date);
  }
  // Newest first.
  await expect(page.locator(".post-list .date").first()).toHaveText(
    LATEST_ARTICLE.date
  );
});

test("the newest article renders in full", async ({ page }) => {
  await page.goto(`/blog/${LATEST_ARTICLE.slug}/`);
  await expect(page.locator("article h1")).toHaveText(LATEST_ARTICLE.title);
  await expect(page.locator("article .meta").first()).toContainText(
    LATEST_ARTICLE.date
  );
  // The mutual-adoption limit is the one a reader must not miss.
  await expect(page.locator("article")).toContainText(
    "It only works with people who also use it"
  );
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
