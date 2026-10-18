#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Local-only browser fixture: real API/storage, captured SMTP, temporary data."""

import base64
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from flask import Flask, send_from_directory
from werkzeug.serving import WSGIRequestHandler, make_server

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "waitlist"))


class CapturedSMTP:
    def __init__(self, messages):
        self.messages = messages

    def __call__(self, *_args, **_kwargs):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def starttls(self):
        pass

    def login(self, *_args):
        pass

    def send_message(self, message):
        self.messages.append({"to": str(message["To"]), "subject": str(message["Subject"]),
            "body": message.get_content()})


class QuietRequestHandler(WSGIRequestHandler):
    def log(self, *_args, **_kwargs):
        pass


def main():
    with TemporaryDirectory(prefix="vauchi-browser-waitlist-") as directory:
        os.environ.update({
            "WAITLIST_DB_PATH": str(Path(directory) / "waitlist.db"),
            "WAITLIST_ENCRYPTION_KEY": base64.b64encode(os.urandom(32)).decode("ascii"),
            "WAITLIST_ADMIN_API_KEY": "synthetic-browser-export-key",
            "WAITLIST_SMTP_HOST": "127.0.0.1",
            "WAITLIST_SMTP_PORT": "1",
            "WAITLIST_SMTP_PASSWORD": "synthetic-browser-password",
            "WAITLIST_REDIRECT_BASE_URL": "http://127.0.0.1:3002/",
            "WAITLIST_CONFIRMATION_SUBJECT": "",
            "WAITLIST_PENDING_DAYS": "7",
            "WAITLIST_CONFIRMED_DAYS": "365",
        })
        import api

        messages = []
        api.smtplib.SMTP = CapturedSMTP(messages)
        site_app = Flask("waitlist-browser-site", static_folder=None)

        @api.app.get("/__test/outbox")
        def outbox():
            return messages

        @site_app.get("/", defaults={"path": "index.html"})
        @site_app.get("/<path:path>")
        def site(path):
            selected = path + "index.html" if path.endswith("/") else path
            return send_from_directory(ROOT / "public", selected)

        def application(environ, start_response):
            path = environ.get("PATH_INFO", "")
            target = api.app if path.startswith(("/waitlist/", "/__test/")) else site_app
            return target(environ, start_response)

        with make_server("127.0.0.1", 3002, application, request_handler=QuietRequestHandler) as server:
            server.serve_forever()


if __name__ == "__main__":
    main()
