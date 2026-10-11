// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

// Exchange-link landing (vauchi/private#277). Reads the exchange from the
// URL fragment — never sent to any server — and makes no network request:
// a link carries pk, n and the optional sender name (nm, base64url UTF-8),
// a scanned QR carries q. The name is written as text only.
(function () {
  "use strict";

  var params = {};
  location.hash
    .replace(/^#/, "")
    .split("&")
    .forEach(function (pair) {
      var at = pair.indexOf("=");
      if (at > 0) params[pair.slice(0, at)] = pair.slice(at + 1);
    });

  function decodeName(value) {
    if (!value || !/^[A-Za-z0-9_-]+$/.test(value)) return "";
    try {
      var b64 = value.replace(/-/g, "+").replace(/_/g, "/");
      var binary = atob(b64 + "===".slice((b64.length + 3) % 4));
      var bytes = new Uint8Array(binary.length);
      for (var i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      return new TextDecoder("utf-8", { fatal: true }).decode(bytes).trim();
    } catch (e) {
      return "";
    }
  }

  var name = decodeName(params.nm);
  if (name) {
    document.getElementById("headline").textContent =
      name + " wants to share their contact card with you";
  }

  // A scanned exchange QR (q=) is a live in-person exchange that expires
  // within minutes; only the app's own scanner can take it.
  if (params.q !== undefined) {
    document.getElementById("open-app").hidden = true;
    document.getElementById("link-hint").hidden = true;
    document.getElementById("scan-hint").hidden = false;
    return;
  }

  // The installed apps already open this form; it carries only the
  // exchange key and nonce, never the name.
  var base64url = /^[A-Za-z0-9_-]+$/;
  if (base64url.test(params.pk || "") && base64url.test(params.n || "")) {
    document
      .getElementById("open-app")
      .setAttribute("href", "vauchi://exchange?pk=" + params.pk + "&n=" + params.n);
  }
})();
