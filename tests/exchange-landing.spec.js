// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

import { test, expect } from "@playwright/test";

// /x is where an exchange link lands for someone without the app
// (vauchi/private#277). Everything the exchange needs is in the URL
// fragment, which never reaches a server; the page reads it locally,
// names the sender and offers to open the app, and makes no requests of
// its own.

const PK = "A".repeat(43);
const N = "B".repeat(43);

function b64url(text) {
  return Buffer.from(text, "utf8").toString("base64url");
}

test("names the sender from the fragment", async ({ page }) => {
  await page.goto(`/x#pk=${PK}&n=${N}&nm=${b64url("Zoë")}`);
  await expect(page.locator("h1")).toHaveText(
    "Zoë wants to share their contact card with you"
  );
});

test("falls back to a generic line without a name", async ({ page }) => {
  await page.goto(`/x#pk=${PK}&n=${N}`);
  await expect(page.locator("h1")).toHaveText(
    "Someone wants to share their contact card with you"
  );
});

test("a name is shown as text, never as markup", async ({ page }) => {
  const hostile = '<img src=x onerror="window.pwned=1">';
  await page.goto(`/x#pk=${PK}&n=${N}&nm=${b64url(hostile)}`);
  await expect(page.locator("h1")).toContainText(hostile);
  await expect(page.locator("h1 img")).toHaveCount(0);
  expect(await page.evaluate(() => window.pwned)).toBeUndefined();
});

test("offers to open the installed app with the same exchange", async ({
  page,
}) => {
  await page.goto(`/x#pk=${PK}&n=${N}&nm=${b64url("Zoë")}`);
  await expect(page.locator("#open-app")).toHaveAttribute(
    "href",
    `vauchi://exchange?pk=${PK}&n=${N}`
  );
});

test("makes no request beyond its own static files", async ({ page }) => {
  const requests = [];
  page.on("request", (request) => requests.push(request));
  await page.goto(`/x#pk=${PK}&n=${N}&nm=${b64url("Zoë")}`);
  await page.waitForLoadState("networkidle");
  const origin = new URL(page.url()).origin;
  for (const request of requests) {
    expect(new URL(request.url()).origin, request.url()).toBe(origin);
    expect(["document", "script", "stylesheet", "image", "font"]).toContain(
      request.resourceType()
    );
    // The fragment is never part of a request.
    expect(request.url()).not.toContain("pk=");
  }
});

test("iOS universal links claim /x and nothing else", async ({ request }) => {
  const response = await request.get("/.well-known/apple-app-site-association", {
    maxRedirects: 0,
  });
  expect(response.status()).toBe(200);
  const aasa = await response.json();
  expect(aasa.applinks.details).toEqual([
    {
      appIDs: ["L2853TNSJ4.app.vauchi.ios"],
      components: [{ "/": "/x" }, { "/": "/x/" }],
    },
  ]);
});

test("a scanned exchange QR asks to scan again from the app", async ({
  page,
}) => {
  // The QR form carries a live, in-person exchange that expires in about a
  // minute; vauchi://exchange cannot take it, so there is no app link.
  await page.goto(`/x#q=${"C".repeat(232)}`);
  await expect(page.locator("h1")).toHaveText(
    "Someone wants to share their contact card with you"
  );
  await expect(page.locator("#open-app")).toBeHidden();
  await expect(page.locator("#scan-hint")).toBeVisible();
});
