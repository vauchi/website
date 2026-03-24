// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

// Auto-redirect to user's preferred language (no cookies, no tracking).
(function () {
  if (window.location.pathname !== "/") return;
  try {
    if (sessionStorage.getItem("vauchi-lang-checked")) return;
    sessionStorage.setItem("vauchi-lang-checked", "1");
  } catch (e) {
    return;
  }
  var lang = (navigator.language || "").toLowerCase().split("-")[0];
  var supported = { fr: "/fr/", de: "/de/", it: "/it/" };
  if (supported[lang]) window.location.replace(supported[lang]);
})();
