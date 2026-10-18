# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

from contextlib import closing
import csv
from datetime import datetime, timedelta, timezone
import io
import re
import sqlite3
from unittest.mock import patch

from service_fixture import ServiceTestCase, api


class LifecycleRoutes(ServiceTestCase):
    def setUp(self):
        super().setUp()
        self.now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.enterContext(patch.object(api, "_now", lambda: self.now.isoformat(timespec="seconds")))

    def join(self, email="alice@example.test"):
        response = self.client.post("/waitlist/join", data={"email": email})
        self.assertEqual(response.status_code, 303)
        self.assertEqual(self.mail.messages[-1]["To"], email)
        return self.mail.messages[-1].get_content()

    def link(self, body, action):
        match = re.search(rf"https://[^\s]+/waitlist/{action}\?token=([A-Za-z0-9_-]+)", body)
        self.assertIsNotNone(match, f"missing {action} link in captured mail")
        return match.group(0), match.group(1)

    def export(self):
        response = self.client.get("/waitlist/admin/export", headers={
            "Authorization": "Bearer synthetic-export-key",
        })
        self.assertEqual(response.status_code, 200)
        return list(csv.DictReader(io.StringIO(response.get_data(as_text=True))))

    def persisted_count(self):
        # The persisted SQLite schema is the legacy migration/deletion boundary.
        with closing(sqlite3.connect(self.database_path)) as connection:
            return connection.execute("SELECT COUNT(*) FROM waitlist").fetchone()[0]

    def test_export_contains_only_confirmed_eligible_addresses(self):
        self.join("pending@example.test")
        body = self.join("alice@example.test")
        confirm, _ = self.link(body, "confirm")
        response = self.client.get(confirm)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(self.export(), [{
            "email": "alice@example.test", "status": "confirmed",
            "created_at": "2026-01-01T00:00:00+00:00",
            "confirmed_at": "2026-01-01T00:00:00+00:00",
        }])

    def test_pending_expiry_rejects_confirmation_and_removes_active_record(self):
        body = self.join()
        confirm, _ = self.link(body, "confirm")
        self.now += timedelta(days=7)
        response = self.client.get(confirm)
        self.assertEqual(response.headers["Location"], "https://vauchi.app/?waitlist=invalid-token#waitlist")
        self.assertEqual(self.persisted_count(), 0)

    def test_resending_does_not_extend_unconfirmed_retention(self):
        self.join()
        self.now += timedelta(days=6)
        body = self.join()
        confirm, _ = self.link(body, "confirm")
        self.now += timedelta(days=1)
        response = self.client.get(confirm)
        self.assertEqual(response.headers["Location"], "https://vauchi.app/?waitlist=invalid-token#waitlist")
        self.assertEqual(self.persisted_count(), 0)

    def test_confirmed_expiry_removes_announcement_eligibility_and_active_row(self):
        confirm, _ = self.link(self.join(), "confirm")
        self.client.get(confirm)
        self.now += timedelta(days=365)
        self.assertEqual(self.export(), [])
        self.assertEqual(self.persisted_count(), 0)

    def test_get_and_mail_prefetch_do_not_withdraw(self):
        body = self.join()
        confirm, _ = self.link(body, "confirm")
        self.client.get(confirm)
        withdraw, _ = self.link(body, "withdraw")
        for headers in ({}, {"Purpose": "prefetch", "Sec-Purpose": "prefetch"}):
            response = self.client.get(withdraw, headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertIn('method="post"', response.get_data(as_text=True).lower())
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")
            self.assertEqual([r["email"] for r in self.export()], ["alice@example.test"])

    def test_withdrawal_removes_pending_data_and_invalidates_confirmation(self):
        body = self.join()
        confirm, _ = self.link(body, "confirm")
        _, token = self.link(body, "withdraw")
        response = self.client.post("/waitlist/withdraw", data={"token": token})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.persisted_count(), 0)
        response = self.client.get(confirm)
        self.assertEqual(response.headers["Location"], "https://vauchi.app/?waitlist=invalid-token#waitlist")
        self.assertEqual(self.export(), [])

    def test_confirmation_token_cannot_authorize_withdrawal(self):
        _, confirmation = self.link(self.join(), "confirm")
        response = self.client.post("/waitlist/withdraw", data={"token": confirmation})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.persisted_count(), 1)

    def test_invalid_expired_and_replayed_withdrawals_have_one_generic_response(self):
        body = self.join()
        _, token = self.link(body, "withdraw")
        valid = self.client.post("/waitlist/withdraw", data={"token": token})
        self.assertEqual(valid.status_code, 200)
        for invalid in (token, "", "a" * 43, "\x00", "é" * 43, "x" * 4097):
            with self.subTest(token_length=len(invalid)):
                result = self.client.post("/waitlist/withdraw", data={"token": invalid})
                self.assertEqual(result.status_code, valid.status_code)
                self.assertEqual(result.data, valid.data)
        body = self.join()
        _, expired = self.link(body, "withdraw")
        self.now += timedelta(days=7)
        result = self.client.post("/waitlist/withdraw", data={"token": expired})
        self.assertEqual(result.data, valid.data)
        self.assertEqual(self.persisted_count(), 0)

    def test_replayed_withdrawal_cannot_delete_a_new_enrollment(self):
        _, old = self.link(self.join(), "withdraw")
        self.client.post("/waitlist/withdraw", data={"token": old})
        self.join()
        result = self.client.post("/waitlist/withdraw", data={"token": old})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(self.persisted_count(), 1)

    def test_requesting_management_does_not_disclose_registration(self):
        self.join()
        known = self.client.post("/waitlist/manage", data={"email": "alice@example.test"})
        self.assertEqual(known.status_code, 200)
        self.assertEqual(len(self.mail.messages), 2)
        unknown = self.client.post("/waitlist/manage", data={"email": "unknown@example.test"})
        self.assertEqual(unknown.status_code, known.status_code)
        self.assertEqual(unknown.data, known.data)
        self.assertEqual(len(self.mail.messages), 3)
        self.assertEqual(self.mail.messages[-1]["To"], "unknown@example.test")
        self.assertEqual(self.persisted_count(), 1)

    def test_management_requests_preserve_the_original_withdrawal_link(self):
        _, original = self.link(self.join(), "withdraw")
        for _ in range(3):
            response = self.client.post("/waitlist/manage", data={"email": "alice@example.test"})
            self.assertEqual(response.status_code, 200)
        result = self.client.post("/waitlist/withdraw", data={"token": original})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(self.persisted_count(), 0)

    def test_campaign_closure_requires_auth_and_is_idempotent_across_restart(self):
        confirm, _ = self.link(self.join(), "confirm")
        self.client.get(confirm)
        self.assertEqual(self.client.post("/waitlist/admin/close").status_code, 401)
        for _ in range(2):
            response = self.client.post("/waitlist/admin/close", headers={
                "Authorization": "Bearer synthetic-export-key",
            })
            self.assertEqual(response.status_code, 204)
            self.client = api.app.test_client()
        self.assertEqual(self.export(), [])
        self.assertEqual(self.persisted_count(), 0)
        sent = len(self.mail.messages)
        response = self.client.post("/waitlist/join", data={"email": "new@example.test"})
        self.assertEqual(response.headers["Location"], "https://vauchi.app/?waitlist=closed#waitlist")
        self.assertEqual(len(self.mail.messages), sent)
