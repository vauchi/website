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

const MISSION_ARTICLE = {
  slug: "never-meant-to-be-permanent",
  title: "Your contact details were never meant to be permanent",
  date: "August 02, 2026",
};

const UNBUNDLED_ARTICLE = {
  slug: "the-layer-nobody-unbundled",
  title: "The layer nobody unbundled",
  date: "August 21, 2026",
};

// Newest post. The index is sorted by date descending, so this one leads.
const LATEST_ARTICLE = {
  slug: "your-address-book-is-political",
  title: "Your address book is political",
  date: "October 14, 2026",
};

const ALL_ARTICLES = [
  LAUNCH_ARTICLE,
  MISSION_ARTICLE,
  UNBUNDLED_ARTICLE,
  LATEST_ARTICLE,
];

test("blog index lists every article with dates and links", async ({
  page,
}) => {
  await page.goto("/blog/");
  await expect(page).toHaveTitle("Vauchi Blog");
  for (const article of ALL_ARTICLES) {
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
  // The residual trust in us is the limit a reader must not miss.
  await expect(page.locator("article")).toContainText(
    "You still have to trust us a little"
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

// EU AI Act Art. 50(4): AI-assisted public-interest text needs a
// disclosure unless a named person holds editorial responsibility.
test("every article names its responsible editor and AI assistance", async ({
  page,
}) => {
  for (const article of ALL_ARTICLES) {
    await page.goto(`/blog/${article.slug}/`);
    const byline = page.locator("article .byline");
    await expect(byline).toContainText(
      "Reviewed, fact-checked and published by Mattia Egloff"
    );
    await expect(byline).toContainText("Drafted with AI assistance");
  }
});

test("the CMS admin loads its pinned bundle from this site only", async ({
  page,
  request,
}) => {
  const response = await request.get("/blog/admin/");
  expect(response.status()).toBe(200);
  const html = await response.text();
  const scripts = [...html.matchAll(/<script[^>]*src="([^"]+)"/g)].map(
    (match) => match[1]
  );
  expect(scripts).toEqual(["locale.js", "sveltia-cms.js"]);
});

test.describe("CMS interface language in an en-GB browser", () => {
  test.use({ locale: "en-GB" });

  const readPrefs = (page) =>
    page.evaluate(() =>
      JSON.parse(localStorage.getItem("sveltia-cms.prefs") || "null")
    );

  test.beforeEach(async ({ page }) => {
    await page.route(/sveltia-cms\.js$/, (route) =>
      route.fulfill({ contentType: "text/javascript", body: "" })
    );
  });

  test("defaults to the US English built into the bundle", async ({ page }) => {
    await page.goto("/blog/admin/");
    expect(await readPrefs(page)).toEqual({ locale: "en-US" });
  });

  // Sveltia stores "auto" on its first load, so a browser that opened the
  // admin before this default existed carries "auto", not an empty choice.
  test("replaces the stored browser-following choice", async ({ page }) => {
    await page.addInitScript(() =>
      localStorage.setItem(
        "sveltia-cms.prefs",
        JSON.stringify({ locale: "auto", theme: "dark" })
      )
    );
    await page.goto("/blog/admin/");
    expect(await readPrefs(page)).toEqual({ locale: "en-US", theme: "dark" });
  });

  test("keeps a language the editor chose", async ({ page }) => {
    await page.addInitScript(() =>
      localStorage.setItem(
        "sveltia-cms.prefs",
        JSON.stringify({ locale: "de", theme: "dark" })
      )
    );
    await page.goto("/blog/admin/");
    expect(await readPrefs(page)).toEqual({ locale: "de", theme: "dark" });
  });
});

test("the CMS edits blog posts through merge requests", async ({
  request,
}) => {
  const config = await (await request.get("/blog/admin/config.yml")).text();
  expect(config).toContain("repo: vauchi/website");
  expect(config).toContain("auth_type: pkce");
  expect(config).toContain("publish_mode: editorial_workflow");
  expect(config).toContain("folder: blog/content");
  expect(config).toContain("format: toml-frontmatter");
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
