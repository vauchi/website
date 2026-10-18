# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path
import tempfile
import unittest

from process_fixture import request, running_service


class ServiceProcessPrivacy(unittest.TestCase):
    def test_runtime_does_not_log_client_addresses_or_token_bearing_requests(self):
        with tempfile.TemporaryDirectory() as directory:
            with running_service(Path(directory) / "waitlist.db") as service:
                status, _, body = request(service["port"], "GET", "/waitlist/health?token=synthetic-secret")
                self.assertEqual(status, 200)
                self.assertEqual(body, b"OK")
            output = service["logs"]
            self.assertIn("Listening at:", output)
            self.assertNotIn("synthetic-secret", output)
            self.assertNotIn('"GET /waitlist/', output)
            self.assertNotIn('127.0.0.1 - -', output)

    def test_closed_campaign_survives_an_actual_gunicorn_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "waitlist.db"
            with running_service(database) as first:
                status, _, body = request(first["port"], "POST", "/waitlist/admin/close",
                    headers={"Authorization": "Bearer synthetic-export-key"})
                self.assertEqual((status, body), (204, b""))
            with running_service(database) as restarted:
                status, headers, _ = request(restarted["port"], "POST", "/waitlist/join",
                    body="email=alice%40example.test", headers={"Content-Type": "application/x-www-form-urlencoded"})
                self.assertEqual(status, 303)
                self.assertEqual(headers["Location"], "https://vauchi.app/?waitlist=closed#waitlist")
