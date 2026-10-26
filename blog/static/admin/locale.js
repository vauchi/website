// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

// Sveltia CMS builds in only US English and fetches every other interface
// language from unpkg.com, which this page's CSP blocks on purpose. Without
// a stored choice it follows the browser (en-GB, de, ...) and fails, so
// start editors on en-US; a language chosen in Settings is kept.
try {
  const key = "sveltia-cms.prefs";
  const prefs = JSON.parse(localStorage.getItem(key) || "{}") || {};
  if (!prefs.locale) {
    localStorage.setItem(key, JSON.stringify({ ...prefs, locale: "en-US" }));
  }
} catch {
  // Storage unavailable (private mode, blocked): Sveltia falls back itself.
}
