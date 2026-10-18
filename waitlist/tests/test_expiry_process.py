# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

import configparser
from contextlib import closing
from datetime import datetime, timedelta, timezone
import hashlib
import shlex
import sqlite3
import subprocess
from unittest.mock import patch

from process_fixture import SOURCE, environment
from service_fixture import ServiceTestCase, api


class ExpiryProcess(ServiceTestCase):
    def command(self):
        config = configparser.ConfigParser()
        config.read(SOURCE / "supervisord.conf")
        command = config.get("program:waitlist-expiry", "command", fallback=None)
        self.assertIsNotNone(command, "the image must expire records without visitor traffic")
        return shlex.split(command)

    def test_configured_worker_deletes_expired_rows_without_http_traffic(self):
        self.assertEqual(self.client.post("/waitlist/join", data={"email": "current@example.test"}).status_code, 303)
        past = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        with patch.object(api, "_now", lambda: past):
            self.assertEqual(self.client.post("/waitlist/join", data={"email": "old@example.test"}).status_code, 303)
        with closing(sqlite3.connect(self.database_path)) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM waitlist").fetchone()[0], 2)
        process = subprocess.Popen(self.command(), cwd=SOURCE, env=environment(self.database_path),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        output = []
        try:
            for line in process.stdout:
                output.append(line)
                if "Waitlist expiry pass complete" in line:
                    break
            else:
                self.fail("expiry worker did not finish a pass: " + "".join(output))
            with closing(sqlite3.connect(self.database_path)) as connection:
                rows = connection.execute("SELECT email_hash FROM waitlist").fetchall()
            self.assertEqual(rows, [(hashlib.sha256(b"current@example.test").hexdigest(),)])
        finally:
            process.terminate()
            tail, _ = process.communicate(timeout=5)
            output.append(tail)
        self.assertEqual(process.returncode, 0)
        self.assertNotIn("old@example.test", "".join(output))

    def test_invalid_interval_fails_before_database_creation(self):
        command = self.command()
        for value in ("0", "-1", "59", "3601", "off", "1.5", "９"):
            with self.subTest(value=value):
                settings = environment(self.database_path)
                settings["WAITLIST_CLEANUP_SECONDS"] = value
                result = subprocess.run(command, cwd=SOURCE, env=settings,
                    capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 2)
                self.assertIn("WAITLIST_CLEANUP_SECONDS must be an integer from 60 to 3600", result.stderr)
                self.assertFalse(self.database_path.exists())
