// SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
// SPDX-License-Identifier: GPL-3.0-or-later

(function () {
  // Load translatable strings from JSON config block
  var i18nEl = document.getElementById("player-i18n");
  var i18n = i18nEl ? JSON.parse(i18nEl.textContent) : {};

  // Read current theme color from CSS variable
  function themeColor(name) {
    return getComputedStyle(document.documentElement)
      .getPropertyValue(name)
      .trim();
  }

  var DURATIONS = [
    4500, 8000, 8500, 7000, 9000, 8000, 8500, 8000, 8000, 9500,
  ];
  var TOTAL = DURATIONS.length;
  var SCENE_NAMES = i18n.scene_names || [
    "Intro",
    "The Problem",
    "Contact Exchange",
    "Exchanged",
    "Silent Updates",
    "Platform Freedom",
    "Granular Privacy",
    "Physical Recovery",
    "Zero Platform",
    "Outro",
  ];

  var current = 0;
  var playing = false;
  var progress = 0;
  var timer = null;
  var ticker = null;
  var hasPlayedOnce = false;

  var prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;

  var player = document.getElementById("player");
  var scenes = document.querySelectorAll(".v-scene");
  var controls = document.getElementById("controls");

  // Build dot navigation (no play button, no progress bar)
  var dots = [];
  for (var i = 0; i < TOTAL; i++) {
    var dot = document.createElement("button");
    dot.className = "v-dot-btn";
    dot.setAttribute(
      "aria-label",
      "Go to scene " + (i + 1) + ": " + SCENE_NAMES[i]
    );
    dot.dataset.index = i;
    dot.onclick = function () {
      var idx = parseInt(this.dataset.index);
      current = idx;
      hasPlayedOnce = true;
      playing = false;
      clearTimeout(timer);
      clearInterval(ticker);
      startScene();
    };
    controls.appendChild(dot);
    dots.push(dot);
  }

  function updateDots() {
    for (var i = 0; i < dots.length; i++) {
      if (i === current) {
        dots[i].style.width = "24px";
        dots[i].style.background = "var(--accent)";
        dots[i].style.borderColor = "var(--accent)";
        dots[i].style.opacity = "1";
      } else if (i < current) {
        dots[i].style.width = "10px";
        dots[i].style.background = "color-mix(in srgb, var(--accent) 40%, transparent)";
        dots[i].style.borderColor = "var(--accent)";
        dots[i].style.opacity = "0.7";
      } else {
        dots[i].style.width = "10px";
        dots[i].style.background = "transparent";
        dots[i].style.borderColor = "var(--border)";
        dots[i].style.opacity = "0.7";
      }
    }
  }

  function showScene(idx) {
    for (var i = 0; i < scenes.length; i++) {
      if (i === idx) scenes[i].classList.add("active");
      else scenes[i].classList.remove("active");
    }
    updateDots();
  }

  function updateProgress() {
    // Progress is now shown via dot highlight only
  }

  function updateSceneState() {
    if (current === 2) {
      var qr = document.getElementById("qr2");
      var pair = document.getElementById("pair2");
      var pairLabel = document.getElementById("pair2-label");
      var scan = document.getElementById("scan2");
      if (progress > 0.25) {
        if (qr) qr.classList.add("active");
        if (scan) scan.classList.add("active");
      } else {
        if (qr) qr.classList.remove("active");
        if (scan) scan.classList.remove("active");
      }
      if (progress > 0.55) {
        if (pair) {
          pair.classList.add("done");
          pair.textContent = "\u2713";
        }
        if (pairLabel) {
          pairLabel.textContent = i18n.txt_paired || "paired";
          pairLabel.style.color = "var(--success)";
        }
      } else {
        if (pair) {
          pair.classList.remove("done");
          pair.textContent = "\u27F7";
        }
        if (pairLabel) {
          pairLabel.textContent = i18n.txt_scanning || "scanning";
          pairLabel.style.color = "var(--text-secondary)";
        }
      }
    }
    if (current === 4) {
      var s4a = document.getElementById("status4a");
      var s4b = document.getElementById("status4b");
      var d4a = document.getElementById("detail4a");
      var d4b = document.getElementById("detail4b");
      var sb4a = document.getElementById("sub4a");
      var sb4b = document.getElementById("sub4b");
      var c4a = document.getElementById("card4a");
      var c4b = document.getElementById("card4b");
      var a4a = document.getElementById("arrow4a");
      var a4b = document.getElementById("arrow4b");

      if (progress > 0.25) {
        if (s4a) {
          s4a.textContent = i18n.txt_saved || "\u2713 saved";
          s4a.style.color = "var(--success)";
        }
        if (d4a) {
          d4a.textContent = "+1 555-9999";
          d4a.style.color = "var(--success)";
        }
        if (sb4a) {
          sb4a.textContent = "you@newjob.com";
          sb4a.style.color = "var(--success)";
        }
        if (c4a) c4a.classList.add("glow");
      } else {
        if (s4a) {
          s4a.textContent = i18n.txt_editing || "editing...";
          s4a.style.color = "var(--text-secondary)";
        }
        if (d4a) {
          d4a.textContent = "+1 555-0123";
          d4a.style.color = "var(--text-secondary)";
        }
        if (sb4a) {
          sb4a.textContent = "you@email.com";
          sb4a.style.color = "var(--text-secondary)";
        }
        if (c4a) c4a.classList.remove("glow");
      }
      if (a4a)
        a4a
          .querySelector("path")
          .setAttribute(
            "stroke",
            progress > 0.5
              ? themeColor("--accent")
              : themeColor("--text-secondary")
          );
      if (a4b)
        a4b
          .querySelector("path")
          .setAttribute(
            "stroke",
            progress > 0.65
              ? themeColor("--accent")
              : themeColor("--text-secondary")
          );
      if (progress > 0.65) {
        if (s4b) {
          s4b.textContent = i18n.txt_auto_synced || "\u2713 auto-synced";
          s4b.style.color = "var(--success)";
        }
        if (d4b) {
          d4b.textContent = "+1 555-9999";
          d4b.style.color = "var(--success)";
        }
        if (sb4b) {
          sb4b.textContent = "you@newjob.com";
          sb4b.style.color = "var(--success)";
        }
        if (c4b) c4b.classList.add("glow");
      } else {
        if (s4b) {
          s4b.textContent = i18n.txt_waiting || "waiting...";
          s4b.style.color = "var(--text-secondary)";
        }
        if (d4b) {
          d4b.textContent = "+1 555-0123";
          d4b.style.color = "var(--text-secondary)";
        }
        if (sb4b) {
          sb4b.textContent = "you@email.com";
          sb4b.style.color = "var(--text-secondary)";
        }
        if (c4b) c4b.classList.remove("glow");
      }
    }
    if (current === 7) {
      var a6a = document.getElementById("arrow6a");
      var a6b = document.getElementById("arrow6b");
      var ri = document.getElementById("recovery-icon");
      var rl = document.getElementById("recovery-label");
      if (a6a)
        a6a
          .querySelector("path")
          .setAttribute(
            "stroke",
            progress > 0.3
              ? themeColor("--accent")
              : themeColor("--text-secondary")
          );
      if (a6b)
        a6b
          .querySelector("path")
          .setAttribute(
            "stroke",
            progress > 0.7
              ? themeColor("--success")
              : themeColor("--text-secondary")
          );
      for (var ti = 0; ti < 3; ti++) {
        var t = document.getElementById("trust" + ti);
        if (t) {
          if (progress > 0.4 + ti * 0.1) t.classList.add("lit");
          else t.classList.remove("lit");
        }
      }
      if (ri) {
        if (progress > 0.7) {
          ri.className = "v-icon-box green";
          if (rl) {
            rl.textContent = i18n.txt_restored || "\u2713 restored";
            rl.style.color = "var(--success)";
          }
        } else {
          ri.className = "v-icon-box neutral";
          if (rl) {
            rl.textContent = i18n.txt_new_device || "new device";
            rl.style.color = "var(--text-secondary)";
          }
        }
      }
    }
  }

  function startScene() {
    progress = 0;
    showScene(current);
    clearTimeout(timer);
    clearInterval(ticker);
    if (!playing) return;

    var dur = DURATIONS[current];
    var step = 40;

    ticker = setInterval(function () {
      progress = Math.min(progress + step / dur, 1);
      updateProgress();
      updateSceneState();
    }, step);

    timer = setTimeout(function () {
      clearInterval(ticker);
      if (current < TOTAL - 1) {
        current++;
        startScene();
      } else {
        playing = false;
      }
    }, dur);
  }

  function togglePlay() {
    if (!playing && current === TOTAL - 1) {
      current = 0;
      hasPlayedOnce = true;
      playing = true;
      startScene();
    } else if (!playing && !hasPlayedOnce && current === 0) {
      hasPlayedOnce = true;
      playing = true;
      current = 1;
      startScene();
    } else {
      playing = !playing;
      if (playing) startScene();
      else {
        clearTimeout(timer);
        clearInterval(ticker);
      }
    }
  }

  function goTo(i) {
    current = i;
    hasPlayedOnce = true;
    playing = true;
    startScene();
  }

  // Keyboard navigation
  player.addEventListener("keydown", function (e) {
    if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      e.preventDefault();
      if (current < TOTAL - 1) goTo(current + 1);
    } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      e.preventDefault();
      if (current > 0) goTo(current - 1);
    } else if (e.key === " ") {
      e.preventDefault();
      togglePlay();
    }
  });

  function resumeScene() {
    clearTimeout(timer);
    clearInterval(ticker);
    if (!playing) return;

    var dur = DURATIONS[current];
    var remaining = dur * (1 - progress);
    var step = 40;

    ticker = setInterval(function () {
      progress = Math.min(progress + step / dur, 1);
      updateProgress();
      updateSceneState();
    }, step);

    timer = setTimeout(function () {
      clearInterval(ticker);
      if (current < TOTAL - 1) {
        current++;
        startScene();
      } else {
        playing = false;
        playBtn.textContent = "\u25B6";
        playBtn.setAttribute("aria-label", "Play explainer");
      }
    }, remaining);
  }

  // Pause on hover/focus (WCAG 2.2.2)
  var hoverPaused = false;
  player.addEventListener("mouseenter", function () {
    if (playing) {
      hoverPaused = true;
      clearTimeout(timer);
      clearInterval(ticker);
    }
  });
  player.addEventListener("mouseleave", function () {
    if (hoverPaused && playing) {
      hoverPaused = false;
      resumeScene();
    }
    hoverPaused = false;
  });
  player.addEventListener("focusin", function () {
    if (playing) {
      hoverPaused = true;
      clearTimeout(timer);
      clearInterval(ticker);
    }
  });
  player.addEventListener("focusout", function (e) {
    if (hoverPaused && playing && !player.contains(e.relatedTarget)) {
      hoverPaused = false;
      resumeScene();
    }
  });

  // Click on slide → pause and flash a pause indicator
  var pauseOverlay = document.createElement("div");
  pauseOverlay.style.cssText =
    "position:absolute;inset:0;display:flex;align-items:center;justify-content:center;" +
    "pointer-events:none;opacity:0;transition:opacity 0.3s;z-index:50;";
  var pauseIcon = document.createElement("div");
  pauseIcon.style.cssText =
    "background:rgba(0,0,0,0.5);border-radius:50%;width:80px;height:80px;" +
    "display:flex;align-items:center;justify-content:center;font-size:32px;color:#fff;";
  pauseIcon.textContent = "\u23F8\uFE0E";
  pauseOverlay.appendChild(pauseIcon);
  player.appendChild(pauseOverlay);

  player.addEventListener("click", function (e) {
    // Don't pause if clicking a button, link, or the hero CTA
    if (e.target.closest("button, a, .v-hero-cta, .v-controls")) return;
    if (!playing) return;

    // Pause
    playing = false;
    hasPlayedOnce = true;
    clearTimeout(timer);
    clearInterval(ticker);

    // Flash the pause indicator
    pauseOverlay.style.opacity = "1";
    setTimeout(function () {
      pauseOverlay.style.opacity = "0";
    }, 800);
  });

  // Hero CTA — "Find out how it works" replaces dots on intro
  var heroCta = document.getElementById("hero-play");
  if (heroCta) {
    heroCta.onclick = function () {
      heroCta.style.display = "none";
      controls.style.display = "flex";
      togglePlay();
    };
  }

  // Also show dots (hide CTA) when navigating via dot click or keyboard
  function showDots() {
    if (heroCta) heroCta.style.display = "none";
    controls.style.display = "flex";
  }

  // Init — show intro scene statically (no autoplay)
  showScene(0);
  updateProgress();
})();
