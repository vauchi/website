# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

import configparser
import http.client
import os
from pathlib import Path
import shlex
import socket
import subprocess
import tempfile
import unittest

from test_api_helpers import TEST_KEY


class ServiceProcessPrivacy(unittest.TestCase):
    def test_runtime_does_not_log_client_addresses_or_token_bearing_requests(self):
        source = Path(__file__).resolve().parents[1]
        config = configparser.ConfigParser()
        config.read(source / "supervisord.conf")
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        command = shlex.split(config["program:waitlist"]["command"].replace(
            "127.0.0.1:8081", f"127.0.0.1:{port}"
        ))
        with tempfile.TemporaryDirectory() as directory:
            environment = dict(os.environ,
                WAITLIST_DB_PATH=str(Path(directory) / "waitlist.db"),
                WAITLIST_ENCRYPTION_KEY=TEST_KEY,
            )
            process = subprocess.Popen(command, cwd=source, env=environment,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            lines = []
            try:
                for line in process.stdout:
                    lines.append(line)
                    if "Booting worker with pid" in line:
                        break
                else:
                    self.fail("service did not start: " + "".join(lines))
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                try:
                    connection.request("GET", "/waitlist/health?token=synthetic-secret")
                    response = connection.getresponse()
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.read(), b"OK")
                finally:
                    connection.close()
            finally:
                process.terminate()
                remainder, _ = process.communicate(timeout=10)
                lines.append(remainder)
            output = "".join(lines)
            self.assertIn("Listening at:", output)
            self.assertNotIn("synthetic-secret", output)
            self.assertNotIn('"GET /waitlist/', output)
            self.assertNotIn('127.0.0.1 - -', output)
