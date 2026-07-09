/** SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me> */
/** SPDX-License-Identifier: GPL-3.0-or-later */

(function () {
  'use strict';

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
})();
