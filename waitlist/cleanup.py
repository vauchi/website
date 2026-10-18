# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Expire active waitlist data without requiring website traffic."""

import os
import signal
import sys
from threading import Event

from api import store


def main():
    raw = os.environ.get("WAITLIST_CLEANUP_SECONDS", "300")
    if not raw.isascii() or not raw.isdigit() or not 60 <= int(raw) <= 3600:
        print("WAITLIST_CLEANUP_SECONDS must be an integer from 60 to 3600", file=sys.stderr)
        return 2
    interval = int(raw)
    stopped = Event()
    signal.signal(signal.SIGTERM, lambda *_args: stopped.set())
    signal.signal(signal.SIGINT, lambda *_args: stopped.set())
    while not stopped.is_set():
        try:
            store().cleanup()
        except Exception:
            print("Waitlist expiry failed", file=sys.stderr, flush=True)
            return 1
        print("Waitlist expiry pass complete", flush=True)
        stopped.wait(interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
