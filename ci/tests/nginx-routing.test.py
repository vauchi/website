# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from queue import Queue
import socket
import subprocess
import tempfile
from threading import Thread
import unittest


class PrivacyRedirectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        root = Path(cls.directory.name)
        root.chmod(0o755)
        cls.access_log = root / "access.log"
        cls.collected = Queue()

        class LegacyCollector(BaseHTTPRequestHandler):
            def do_POST(self):
                cls.collected.put(self.rfile.read(int(self.headers["Content-Length"])))
                self.send_response(202)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *_args):
                pass

        cls.collector = ThreadingHTTPServer(("127.0.0.1", 0), LegacyCollector)
        cls.collector_thread = Thread(target=cls.collector.serve_forever, daemon=True)
        cls.collector_thread.start()
        cls.addClassCleanup(cls.stop_collector)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            cls.port = listener.getsockname()[1]
        source = Path(__file__).resolve().parents[2] / "nginx.conf"
        server = source.read_text().replace("listen 80", f"listen 127.0.0.1:{cls.port}")
        server = server.replace("/usr/share/nginx/html", str(root))
        server = server.replace(
            "http://127.0.0.1:8080", f"http://127.0.0.1:{cls.collector.server_port}"
        )
        config = root / "nginx.conf"
        temp_paths = "".join(
            f"{kind}_temp_path {root}/{kind};\n"
            for kind in ("client_body", "proxy", "fastcgi", "uwsgi", "scgi")
        )
        config.write_text(
            f"daemon off; pid {root}/nginx.pid; error_log stderr notice;\n"
            f"events {{}}\nhttp {{ access_log {cls.access_log}; "
            + temp_paths + server + "\n}\n"
        )
        cls.nginx = subprocess.Popen(
            ["nginx", "-e", "stderr", "-p", str(root), "-c", str(config)],
            stderr=subprocess.PIPE,
            text=True,
        )
        cls.addClassCleanup(cls.stop_nginx)
        messages = []
        for line in cls.nginx.stderr:
            messages.append(line)
            if "start worker process " in line:
                break
        else:
            raise RuntimeError("nginx did not start: " + "".join(messages))

    @classmethod
    def stop_nginx(cls):
        cls.nginx.terminate()
        cls.nginx.wait(timeout=5)
        cls.nginx.stderr.close()

    @classmethod
    def stop_collector(cls):
        cls.collector.shutdown()
        cls.collector.server_close()
        cls.collector_thread.join(timeout=5)

    def test_stale_clients_cannot_submit_behavior_events(self):
        for method in ("POST", "GET", "HEAD"):
            with self.subTest(method=method):
                connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
                try:
                    connection.request(
                        method, "/beacon", body=b'{"v":"a","clicks":2,"dwell_ms":300}',
                        headers={"Host": "vauchi.app", "Content-Type": "application/json"},
                    )
                    response = connection.getresponse()
                    self.assertEqual(response.status, 410)
                    response.read()
                finally:
                    connection.close()
        self.assertTrue(self.collected.empty(), "retired endpoint forwarded visitor events")

    def test_page_requests_do_not_create_an_access_event_stream(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request("GET", "/privacy", headers={"Host": "vauchi.app"})
            response = connection.getresponse()
            self.assertEqual(response.status, 301)
            response.read()
        finally:
            connection.close()
        self.assertEqual(self.access_log.read_text() if self.access_log.exists() else "", "")

    def test_privacy_aliases_redirect_to_generated_mdbook_page(self):
        for path in ("/privacy", "/privacy.html", "/privacy-policy", "/legal/privacy-policy/"):
            for method in ("GET", "HEAD"):
                with self.subTest(path=path, method=method):
                    connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
                    try:
                        connection.request(method, path, headers={"Host": "vauchi.app"})
                        response = connection.getresponse()
                        self.assertEqual(response.status, 301)
                        self.assertEqual(
                            response.getheader("Location"),
                            "https://vauchi.app/docs/legal/privacy-policy.html",
                        )
                        response.read()
                    finally:
                        connection.close()


if __name__ == "__main__":
    unittest.main()
