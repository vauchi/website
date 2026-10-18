# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_api_helpers import api


class CapturedMail:
    def __init__(self):
        self.messages = []
        self.failure = None

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
        self.messages.append(message)
        if self.failure:
            raise self.failure


class ServiceTestCase(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.database_path = Path(directory.name) / "waitlist.db"
        self.enterContext(patch.multiple(
            api,
            DB_PATH=str(self.database_path),
            SMTP_PASSWORD="synthetic-smtp-password",
            ADMIN_API_KEY="synthetic-export-key",
        ))
        self.mail = CapturedMail()
        self.enterContext(patch.object(api.smtplib, "SMTP", self.mail))
        self.client = api.app.test_client()
