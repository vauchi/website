# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

import configparser
from contextlib import contextmanager
import http.client
import os
from pathlib import Path
import re
import shlex
import subprocess

from test_api_helpers import TEST_KEY

SOURCE = Path(__file__).resolve().parents[1]


def environment(database):
    return dict(os.environ, WAITLIST_DB_PATH=str(database), WAITLIST_ENCRYPTION_KEY=TEST_KEY,
        WAITLIST_ADMIN_API_KEY="synthetic-export-key", WAITLIST_SMTP_HOST="127.0.0.1",
        WAITLIST_SMTP_PORT="1", WAITLIST_SMTP_USER="synthetic@example.test",
        WAITLIST_SMTP_FROM="synthetic@example.test", WAITLIST_SMTP_PASSWORD="synthetic-password",
        WAITLIST_SMTP_STARTTLS="false", WAITLIST_PENDING_DAYS="7", WAITLIST_CONFIRMED_DAYS="365",
        WAITLIST_REDIRECT_BASE_URL="https://vauchi.app/")


@contextmanager
def running_service(database):
    config = configparser.ConfigParser()
    config.read(SOURCE / "supervisord.conf")
    command = shlex.split(config["program:waitlist"]["command"].replace("127.0.0.1:8081", "127.0.0.1:0"))
    process = subprocess.Popen(command, cwd=SOURCE, env=environment(database),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    report = {"port": None, "logs": ""}
    try:
        for line in process.stdout:
            report["logs"] += line
            match = re.search(r"Listening at: http://127\.0\.0\.1:(\d+)", line)
            if match:
                report["port"] = int(match.group(1))
            if "Booting worker with pid" in line and report["port"]:
                break
        else:
            raise RuntimeError("service did not start: " + report["logs"])
        yield report
    finally:
        process.terminate()
        remainder, _ = process.communicate(timeout=10)
        report["logs"] += remainder


def request(port, method, path, *, body=None, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()
