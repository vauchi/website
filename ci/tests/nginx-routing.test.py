# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

import http.client
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest


class PrivacyRedirectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        root = Path(cls.directory.name)
        root.chmod(0o755)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            cls.port = listener.getsockname()[1]
        source = Path(__file__).resolve().parents[2] / "nginx.conf"
        server = source.read_text().replace("listen 80", f"listen 127.0.0.1:{cls.port}")
        server = server.replace("/usr/share/nginx/html", str(root))
        config = root / "nginx.conf"
        temp_paths = "".join(
            f"{kind}_temp_path {root}/{kind};\n"
            for kind in ("client_body", "proxy", "fastcgi", "uwsgi", "scgi")
        )
        config.write_text(
            f"daemon off; pid {root}/nginx.pid; error_log stderr notice;\n"
            "events {}\nhttp { access_log off; " + temp_paths + server + "\n}\n"
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
