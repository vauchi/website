// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

import { test, expect } from "@playwright/test";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

// i18n JSON is data, not markup: strings must hold real Unicode
// characters, never HTML entities. Entities only render when a string
// happens to pass through innerHTML — variant-test.js injects hero
// strings via textContent, where "&#x2014;" appears literally on
// screen (regression: waitlist variant integration, 2026-07-09).
const ENTITY_PATTERN = /&(#x?[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]*);/;

function collectStrings(value, path, out) {
  if (typeof value === "string") {
    out.push({ path, value });
  } else if (value && typeof value === "object") {
    for (const [key, child] of Object.entries(value)) {
      collectStrings(child, path ? `${path}.${key}` : key, out);
    }
  }
  return out;
}

// Playwright runs specs with CWD at the config root (repo root).
const i18nDir = join(process.cwd(), "i18n");

for (const file of readdirSync(i18nDir).filter((f) => f.endsWith(".json"))) {
  test(`i18n ${file} contains no HTML entities`, () => {
    const data = JSON.parse(readFileSync(join(i18nDir, file), "utf8"));
    const offenders = collectStrings(data, "", []).filter(({ value }) =>
      ENTITY_PATTERN.test(value)
    );
    expect(
      offenders.map(({ path, value }) => `${path}: ${value}`),
      "decode entities to real characters (e.g. &#x2014; -> —)"
    ).toEqual([]);
  });
}
