# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

from contextlib import closing
from datetime import datetime, timezone
import hashlib
import sqlite3

from service_fixture import ServiceTestCase, api
from storage import WaitlistStore


class LifecycleBoundaries(ServiceTestCase):
    def test_malformed_admin_credentials_are_unauthorized_without_internal_errors(self):
        for value in ("Bearer é", "Bearer ", "wrong", "Bearer wrong"):
            with self.subTest(value=value):
                response = self.client.post("/waitlist/admin/close", headers={"Authorization": value})
                self.assertEqual(response.status_code, 401)
                self.assertNotIn(b"synthetic-export-key", response.data)

    def test_encrypted_legacy_records_can_obtain_a_removal_link(self):
        now = api._now()
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("""CREATE TABLE waitlist (
                id INTEGER PRIMARY KEY, email_hash TEXT NOT NULL UNIQUE,
                email_ciphertext TEXT NOT NULL, status TEXT NOT NULL,
                token_hash TEXT NOT NULL, created_at TEXT NOT NULL, confirmed_at TEXT)""")
            connection.execute("INSERT INTO waitlist VALUES (1, ?, ?, 'confirmed', 'old', ?, ?)",
                (hashlib.sha256(b"alice@example.test").hexdigest(), api._encrypt("alice@example.test"), now, now))
            connection.commit()
        result = self.client.post("/waitlist/manage", data={"email": "alice@example.test"})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(self.mail.messages), 1)
        self.assertIn("/waitlist/withdraw?token=", self.mail.messages[0].get_content())
        result = self.client.get("/waitlist/admin/export", headers={"Authorization": "Bearer synthetic-export-key"})
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"alice@example.test,confirmed", result.data)

    def test_plaintext_legacy_schema_migrates_without_losing_eligibility(self):
        now = api._now()
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("""CREATE TABLE waitlist (email TEXT, status TEXT, token_hash TEXT,
                created_at TEXT, confirmed_at TEXT)""")
            connection.execute("INSERT INTO waitlist VALUES ('alice@example.test', 'confirmed', 'old', ?, ?)", (now, now))
            connection.commit()
        response = self.client.get("/waitlist/admin/export", headers={"Authorization": "Bearer synthetic-export-key"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"alice@example.test,confirmed", response.data)
        with closing(sqlite3.connect(self.database_path)) as connection:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(waitlist)")}
            self.assertNotIn("email", columns)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM waitlist").fetchone()[0], 1)

    def test_invalid_retention_is_rejected_before_creating_a_database(self):
        for value in (0, -1, True, "off", "7.5", "９", 366):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    WaitlistStore(self.database_path, api._encrypt, api._decrypt,
                        confirmed_days=value, clock=lambda: datetime.now(timezone.utc))
                self.assertFalse(self.database_path.exists())

    def test_request_size_is_bounded_without_storing_submitted_data(self):
        response = self.client.post("/waitlist/join", data={"email": "a" * 20000})
        self.assertEqual(response.status_code, 413)
        self.assertNotIn(b"a" * 100, response.data)
        with closing(sqlite3.connect(self.database_path)) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM waitlist").fetchone()[0], 0)
