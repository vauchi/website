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
        (root / "blog" / "admin").mkdir(parents=True)
        (root / "blog" / "admin" / "index.html").write_text("<!doctype html>")
        (root / "blog" / "admin" / "sveltia-cms.js").write_text("")
        (root / "index.html").write_text("<!doctype html>")
        cls.access_log = root / "access.log"
        cls.request_log = root / "request-errors.log"
        cls.collected = Queue()

        class LegacyCollector(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path.startswith("/waitlist/fault"):
                    self.close_connection = True
                    return
                self.send_response(200)
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("Content-Length", "0")
                self.end_headers()

            def do_POST(self):
                body = self.rfile.read(int(self.headers["Content-Length"]))
                if self.path == "/beacon":
                    cls.collected.put(body)
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
        server = server.replace(
            "http://127.0.0.1:8081", f"http://127.0.0.1:{cls.collector.server_port}"
        )
        config = root / "nginx.conf"
        temp_paths = "".join(
            f"{kind}_temp_path {root}/{kind};\n"
            for kind in ("client_body", "proxy", "fastcgi", "uwsgi", "scgi")
        )
        config.write_text(
            f"daemon off; pid {root}/nginx.pid; error_log stderr notice;\n"
            f"events {{}}\nhttp {{ access_log {cls.access_log}; "
            f"error_log {cls.request_log} warn; "
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

    def test_proxy_does_not_weaken_referrer_policy_on_token_pages(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request("GET", "/waitlist/withdraw?token=synthetic-secret", headers={"Host": "vauchi.app"})
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            policies = [value for name, value in response.getheaders() if name.lower() == "referrer-policy"]
            self.assertEqual(set(policies), {"no-referrer"})
            response.read()
        finally:
            connection.close()

    def get_headers(self, path):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request("GET", path, headers={"Host": "vauchi.app"})
            response = connection.getresponse()
            response.read()
            return response.status, {name.lower(): value for name, value in response.getheaders()}
        finally:
            connection.close()

    def test_cms_admin_may_reach_gitlab_but_the_site_may_not(self):
        status, admin = self.get_headers("/blog/admin/")
        self.assertEqual(status, 200)
        policy = admin["content-security-policy"]
        self.assertIn("connect-src 'self' data: https://gitlab.com", policy)
        self.assertIn("script-src 'self';", policy)
        self.assertIn("frame-ancestors 'none'", policy)
        _, site = self.get_headers("/")
        self.assertNotIn("gitlab.com", site["content-security-policy"])
        self.assertIn("require-trusted-types-for 'script'", site["content-security-policy"])

    def test_cms_admin_login_popup_keeps_its_opener(self):
        # Sveltia's GitLab popup returns to /blog/admin/ from gitlab.com and
        # hands the token over via window.opener. Any COOP other than
        # unsafe-none there makes Chromium sever the opener on that
        # cross-origin return, and the popup loops back to the login screen.
        _, admin = self.get_headers("/blog/admin/")
        self.assertEqual(admin["cross-origin-opener-policy"], "unsafe-none")
        _, site = self.get_headers("/")
        self.assertEqual(site["cross-origin-opener-policy"], "same-origin")

    def test_cms_admin_keeps_the_site_security_headers(self):
        for path in ("/blog/admin/", "/blog/admin/sveltia-cms.js"):
            with self.subTest(path=path):
                _, headers = self.get_headers(path)
                self.assertEqual(headers["referrer-policy"], "no-referrer")
                self.assertEqual(headers["x-content-type-options"], "nosniff")
                self.assertIn("max-age=63072000", headers["strict-transport-security"])
                self.assertIn("connect-src 'self' data: https://gitlab.com", headers["content-security-policy"])
                self.assertEqual(headers["cache-control"], "no-store")

    def test_management_requests_use_transient_rate_limiting(self):
        statuses = []
        for _ in range(10):
            connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
            try:
                connection.request("POST", "/waitlist/manage", body=b"email=synthetic%40example.test",
                    headers={"Host": "vauchi.app", "Content-Type": "application/x-www-form-urlencoded"})
                response = connection.getresponse()
                statuses.append(response.status)
                response.read()
            finally:
                connection.close()
        self.assertEqual(statuses[0], 202)
        self.assertIn(503, statuses)

    def test_waitlist_upstream_errors_do_not_log_request_identifiers(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request("GET", "/waitlist/fault?token=synthetic-secret", headers={"Host": "vauchi.app"})
            response = connection.getresponse()
            self.assertEqual(response.status, 502)
            response.read()
        finally:
            connection.close()
        self.assertEqual(self.request_log.read_text() if self.request_log.exists() else "", "")


if __name__ == "__main__":
    unittest.main()
