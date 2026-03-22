// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

// Theme picker — fetches themes.json, renders picker, applies CSS vars
(function () {
  var THEME_KEY = "vauchi-theme";
  var THEMES_URL = "https://cdn.vauchi.app/v1/themes/themes.json";
  var THEMES_FALLBACK = "/app-files/themes/themes.json";
  var ROOT = document.documentElement;
  var modeToggleBtn = document.getElementById("mode-toggle");
  var menuToggleBtn = document.getElementById("theme-menu-toggle");
  var menu = document.getElementById("theme-menu");
  var darkList = document.getElementById("theme-menu-dark");
  var lightList = document.getElementById("theme-menu-light");
  var themes = [];
  var currentIdx = -1;

  var TOKEN_NAMES = [
    "bg-primary",
    "bg-secondary",
    "bg-tertiary",
    "text-primary",
    "text-secondary",
    "accent",
    "accent-dark",
    "success",
    "error",
    "warning",
    "border",
  ];

  var THEME_PAIRS = {
    "default-dark": "default-light",
    "default-light": "default-dark",
    "catppuccin-mocha": "catppuccin-latte",
    "catppuccin-frappe": "catppuccin-latte",
    "catppuccin-macchiato": "catppuccin-latte",
    "catppuccin-latte": "catppuccin-mocha",
    "solarized-dark": "solarized-light",
    "solarized-light": "solarized-dark",
    "gruvbox-dark": "gruvbox-light",
    "gruvbox-light": "gruvbox-dark",
    dracula: "default-light",
    nord: "default-light",
  };

  // Resolve a semantic token value like "{base}" against primitives
  function resolveColor(theme, token) {
    // v1 format: theme.colors["bg-primary"] = "#1a1a2e"
    if (theme.colors) return theme.colors[token];
    // v2 format: theme.semantic["bg-primary"] = "{base}", theme.primitives["base"] = "#1a1a2e"
    if (theme.semantic && theme.primitives) {
      var ref = theme.semantic[token];
      if (!ref) return null;
      var match = ref.match(/^\{(.+)\}$/);
      return match ? theme.primitives[match[1]] : ref;
    }
    return null;
  }

  function applyTheme(theme) {
    for (var i = 0; i < TOKEN_NAMES.length; i++) {
      var value = resolveColor(theme, TOKEN_NAMES[i]);
      if (value) ROOT.style.setProperty("--" + TOKEN_NAMES[i], value);
    }
    if (modeToggleBtn) {
      modeToggleBtn.textContent =
        theme.mode === "dark" ? "\uD83C\uDF19" : "\u2600\uFE0F";
    }
    updateActiveItem();
  }

  function updateActiveItem() {
    if (!menu) return;
    var items = menu.querySelectorAll("[data-theme-id]");
    for (var i = 0; i < items.length; i++) {
      var isActive =
        themes[currentIdx] &&
        items[i].getAttribute("data-theme-id") === themes[currentIdx].id;
      items[i].style.fontWeight = isActive ? "600" : "normal";
      items[i].style.background = isActive
        ? "var(--bg-tertiary)"
        : "transparent";
    }
  }

  function savePreference(id) {
    try {
      localStorage.setItem(THEME_KEY, id);
    } catch (e) {}
  }

  function getSavedPreference() {
    try {
      return localStorage.getItem(THEME_KEY);
    } catch (e) {
      return null;
    }
  }

  function prefersDark() {
    return (
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches
    );
  }

  function findThemeById(id) {
    for (var i = 0; i < themes.length; i++) {
      if (themes[i].id === id) return i;
    }
    return -1;
  }

  function findDefaultTheme() {
    var mode = prefersDark() ? "dark" : "light";
    // Collect all themes matching the browser's preferred mode
    var candidates = [];
    for (var i = 0; i < themes.length; i++) {
      if (themes[i].mode === mode) candidates.push(i);
    }
    if (candidates.length === 0) return 0;
    // Random pick — each first visit gets a different theme
    return candidates[Math.floor(Math.random() * candidates.length)];
  }

  function toggleDarkLight() {
    var current = themes[currentIdx];
    var pairedId;
    if (current && THEME_PAIRS[current.id]) {
      pairedId = THEME_PAIRS[current.id];
    } else if (current && current.mode === "dark") {
      pairedId = "default-light";
    } else {
      pairedId = "default-dark";
    }
    var idx = findThemeById(pairedId);
    if (idx >= 0) {
      currentIdx = idx;
      applyTheme(themes[idx]);
      savePreference(themes[idx].id);
    }
  }

  function createItem(theme, idx) {
    var btn = document.createElement("button");
    btn.setAttribute("data-theme-id", theme.id);
    btn.style.cssText =
      "display:flex;align-items:center;gap:8px;width:100%;padding:6px 12px;border:none;background:transparent;color:var(--text-primary);cursor:pointer;font-size:0.8rem;text-align:left;font-family:inherit";
    var swatch = document.createElement("span");
    swatch.style.cssText =
      "width:14px;height:14px;border-radius:50%;flex-shrink:0;border:1px solid var(--border)";
    swatch.style.background = resolveColor(theme, "accent") || "var(--accent)";
    btn.appendChild(swatch);
    btn.appendChild(document.createTextNode(theme.name));
    btn.addEventListener("click", function () {
      currentIdx = idx;
      applyTheme(theme);
      savePreference(theme.id);
      toggleMenu(false);
    });
    btn.addEventListener("mouseenter", function () {
      if (themes[currentIdx] && theme.id !== themes[currentIdx].id) {
        btn.style.background = "var(--bg-tertiary)";
      }
    });
    btn.addEventListener("mouseleave", function () {
      var isActive =
        themes[currentIdx] && theme.id === themes[currentIdx].id;
      btn.style.background = isActive
        ? "var(--bg-tertiary)"
        : "transparent";
    });
    return btn;
  }

  function populateMenu() {
    if (!darkList || !lightList) return;
    for (var i = 0; i < themes.length; i++) {
      var item = createItem(themes[i], i);
      if (themes[i].mode === "dark") {
        darkList.appendChild(item);
      } else {
        lightList.appendChild(item);
      }
    }
  }

  var menuOpen = false;
  function toggleMenu(forceState) {
    menuOpen = typeof forceState === "boolean" ? forceState : !menuOpen;
    if (menu) menu.style.display = menuOpen ? "block" : "none";
    if (menuToggleBtn)
      menuToggleBtn.setAttribute("aria-expanded", String(menuOpen));
  }

  if (modeToggleBtn) {
    modeToggleBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      toggleDarkLight();
    });
  }

  if (menuToggleBtn) {
    menuToggleBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      toggleMenu();
    });
  }

  document.addEventListener("click", function (e) {
    if (
      menuOpen &&
      menu &&
      !menu.contains(e.target) &&
      e.target !== modeToggleBtn &&
      e.target !== menuToggleBtn
    ) {
      toggleMenu(false);
    }
  });

  // System theme change listener
  if (window.matchMedia) {
    window
      .matchMedia("(prefers-color-scheme: dark)")
      .addEventListener("change", function () {
        if (!getSavedPreference()) {
          currentIdx = findDefaultTheme();
          if (currentIdx >= 0) applyTheme(themes[currentIdx]);
        }
      });
  }

  // Fetch themes and apply (CDN primary, local fallback)
  function loadThemes(url, fallbackUrl) {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", url, true);
    xhr.timeout = 3000; // Fast fallback if CDN unreachable
    xhr.ontimeout = function () {
      if (fallbackUrl) loadThemes(fallbackUrl, null);
    };
    xhr.onload = function () {
      if (xhr.status === 200) {
        try {
          themes = JSON.parse(xhr.responseText);
        } catch (e) {
          if (fallbackUrl) return loadThemes(fallbackUrl, null);
          return;
        }
        populateMenu();
        var saved = getSavedPreference();
        if (saved) currentIdx = findThemeById(saved);
        if (currentIdx < 0) currentIdx = findDefaultTheme();
        if (currentIdx >= 0) applyTheme(themes[currentIdx]);
      } else if (fallbackUrl) {
        loadThemes(fallbackUrl, null);
      }
    };
    xhr.onerror = function () {
      if (fallbackUrl) loadThemes(fallbackUrl, null);
    };
    xhr.send();
  }
  loadThemes(THEMES_URL, THEMES_FALLBACK);
})();
