/** SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me> */
/** SPDX-License-Identifier: GPL-3.0-or-later */

(function () {
  'use strict';

  function showStatusBanner() {
    const banner = document.getElementById('waitlist-message');
    if (!banner) return;

    const params = new URLSearchParams(window.location.search);
    const status = params.get('waitlist');
    if (!status) return;

    const text = banner.getAttribute('data-msg-' + status);
    if (!text) return;

    banner.textContent = text;
    banner.className = 'waitlist-message waitlist-message--' + status;
    banner.hidden = false;

    // Clean the query string so a refresh doesn't replay the message.
    if (window.history && window.history.replaceState) {
      const url = new URL(window.location.href);
      url.searchParams.delete('waitlist');
      window.history.replaceState({}, '', url.toString());
    }
  }

  function wirePendingState() {
    const form = document.querySelector('.waitlist-form');
    if (!form) return;

    form.addEventListener('submit', function () {
      const button = form.querySelector('.waitlist-button');
      if (!button) return;
      // Disabling inside the submit handler does not block the
      // already-started submission; it only prevents double-clicks.
      button.disabled = true;
      button.setAttribute('aria-busy', 'true');
      const loadingLabel = button.getAttribute('data-label-loading');
      if (loadingLabel) button.textContent = loadingLabel;
    });
  }

  showStatusBanner();
  wirePendingState();
})();
