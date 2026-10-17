# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

import hashlib
import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_api_helpers import api


class MailCapture:
    messages = []
    failure = None

    def __init__(self, *_args, **_kwargs):
        pass

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


class ServiceLogPrivacy(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.enterContext(patch.multiple(
            api,
            DB_PATH=str(Path(directory.name) / "waitlist.db"),
            SMTP_PASSWORD="synthetic-smtp-password",
            ADMIN_API_KEY="synthetic-export-key",
        ))
        MailCapture.messages = []
        MailCapture.failure = None
        self.enterContext(patch.object(api.smtplib, "SMTP", MailCapture))
        self.client = api.app.test_client()

    def test_smtp_failure_does_not_log_request_identity_or_exception_details(self):
        address = "alice@example.test"
        request_ip = "192.0.2.42"
        reusable_token = "synthetic-mail-authorization-secret"
        MailCapture.failure = OSError(f"SMTP failure for {address}: {reusable_token}")

        with self.assertLogs(api.app.logger, level=logging.INFO) as captured:
            response = self.client.post(
                "/waitlist/join",
                data={"email": address},
                headers={"X-Forwarded-For": request_ip},
            )

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["Location"], "https://vauchi.app/?waitlist=error#waitlist")
        self.assertEqual(len(MailCapture.messages), 1)
        self.assertEqual(MailCapture.messages[0]["To"], address)
        text = "\n".join(captured.output)
        email_hash = hashlib.sha256(address.encode()).hexdigest()
        for sensitive in (address, request_ip, email_hash, reusable_token):
            with self.subTest(sensitive=sensitive):
                self.assertNotIn(sensitive, text)
        self.assertEqual(
            [(r.levelname, r.getMessage()) for r in captured.records],
            [("ERROR", "Waitlist confirmation delivery failed")],
        )
