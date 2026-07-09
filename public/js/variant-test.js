// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

// Landing-page variant test.
// Randomly swaps the hero copy. If the user has not sent a DNT/GPC opt-out
// signal, it also sends an anonymous beacon with the chosen variant, CTA
// click count, and dwell time when the user leaves.
// No cookies, no fingerprinting, no third-party requests. Respects DNT/GPC.
(function () {
  "use strict";

  var STORAGE_KEY = "vauchi-variant";
  var BEACON_URL = "/beacon";
  var VARIANT_IDS = ["a", "b", "c", "d", "e", "f", "g"];

  function parseI18n() {
    var el = document.getElementById("variant-i18n");
    if (!el) return {};
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return {};
    }
  }

  function hasPrivacySignal() {
    if (navigator.doNotTrack === "1") return true;
    if (navigator.globalPrivacyControl) return true;
    return false;
  }

  function storageGet(key) {
    try {
      return sessionStorage.getItem(key);
    } catch (e) {
      return null;
    }
  }

  function storageSet(key, value) {
    try {
      sessionStorage.setItem(key, value);
    } catch (e) {}
  }

  function pickVariant() {
    var stored = storageGet(STORAGE_KEY);
    if (stored && VARIANT_IDS.indexOf(stored) !== -1) return stored;
    var idx = Math.floor(Math.random() * VARIANT_IDS.length);
    var chosen = VARIANT_IDS[idx];
    storageSet(STORAGE_KEY, chosen);
    return chosen;
  }

  function getVariantStrings(i18n, id) {
    return {
      label: i18n[id + ".label"] || "",
      headline: i18n[id + ".headline"] || "",
      sub: i18n[id + ".sub"] || "",
      cta: i18n[id + ".cta"] || "",
    };
  }

  function applyVariant(id, strings) {
    var body = document.body;
    if (body) body.setAttribute("data-variant", id);

    var defaultBlock = document.getElementById("hero-default-points");
    var variantBlock = document.getElementById("hero-variant-block");
    var label = document.getElementById("hero-variant-label");
    var headline = document.getElementById("hero-variant-headline");
    var sub = document.getElementById("hero-variant-sub");
    var cta = document.getElementById("hero-play");

    if (defaultBlock) defaultBlock.classList.add("hidden");
    if (variantBlock) variantBlock.classList.remove("hidden");
    if (label) label.textContent = strings.label;
    if (headline) headline.textContent = strings.headline;
    if (sub) sub.textContent = strings.sub;
    if (cta && strings.cta) cta.innerHTML = strings.cta;
  }

  function sendBeacon(payload) {
    if (!window.navigator.sendBeacon) return false;
    var blob = new Blob([JSON.stringify(payload)], {
      type: "application/json",
    });
    try {
      return navigator.sendBeacon(BEACON_URL, blob);
    } catch (e) {
      return false;
    }
  }

  function roundMs(ms) {
    return Math.round(ms / 100) * 100;
  }

  function initMetrics(variant) {
    var startTime = Date.now();
    var lastVisibleTime = startTime;
    var totalDwell = 0;
    var clicks = 0;
    var sent = false;

    function recordVisibleTime() {
      var now = Date.now();
      totalDwell += now - lastVisibleTime;
      lastVisibleTime = now;
    }

    function trackClick() {
      clicks += 1;
    }

    function onVisibilityChange() {
      if (document.visibilityState === "hidden") {
        recordVisibleTime();
      } else {
        lastVisibleTime = Date.now();
      }
    }

    function flush() {
      if (sent) return;
      sent = true;
      recordVisibleTime();
      var payload = {
        v: variant,
        clicks: clicks,
        dwell_ms: roundMs(totalDwell),
        path: window.location.pathname,
      };
      sendBeacon(payload);
    }

    document.addEventListener("visibilitychange", onVisibilityChange);
    window.addEventListener("pagehide", flush);
    window.addEventListener("beforeunload", flush);

    // Track primary CTAs: hero play button, app-store style links, footer links.
    var ctaSelectors = [
      "#hero-play",
      "#hero-variant-block .v-link",
      ".links a",
      ".footer a",
    ];
    ctaSelectors.forEach(function (selector) {
      var nodes = document.querySelectorAll(selector);
      for (var i = 0; i < nodes.length; i++) {
        nodes[i].addEventListener("click", trackClick);
      }
    });
  }

  function init() {
    var i18n = parseI18n();
    if (!i18n || Object.keys(i18n).length === 0) return;

    var variant = pickVariant();
    var strings = getVariantStrings(i18n, variant);
    applyVariant(variant, strings);

    // Only collect anonymous metrics when the user has not opted out via
    // DNT or GPC. The variant itself is still shown because it requires no
    // personal data and uses only session-scoped sessionStorage.
    if (!hasPrivacySignal()) {
      initMetrics(variant);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
