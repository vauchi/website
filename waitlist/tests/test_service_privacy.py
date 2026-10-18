# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

import hashlib
import logging
from service_fixture import ServiceTestCase, api


class ServiceLogPrivacy(ServiceTestCase):

    def test_smtp_failure_does_not_log_request_identity_or_exception_details(self):
        address = "alice@example.test"
        request_ip = "192.0.2.42"
        reusable_token = "synthetic-mail-authorization-secret"
        self.mail.failure = OSError(f"SMTP failure for {address}: {reusable_token}")

        with self.assertLogs(api.app.logger, level=logging.INFO) as captured:
            response = self.client.post(
                "/waitlist/join",
                data={"email": address},
                headers={"X-Forwarded-For": request_ip},
            )

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["Location"], "https://vauchi.app/?waitlist=error#waitlist")
        self.assertEqual(len(self.mail.messages), 1)
        self.assertEqual(self.mail.messages[0]["To"], address)
        text = "\n".join(captured.output)
        email_hash = hashlib.sha256(address.encode()).hexdigest()
        for sensitive in (address, request_ip, email_hash, reusable_token):
            with self.subTest(sensitive=sensitive):
                self.assertNotIn(sensitive, text)
        self.assertEqual(
            [(r.levelname, r.getMessage()) for r in captured.records],
            [("ERROR", "Waitlist confirmation delivery failed")],
        )
