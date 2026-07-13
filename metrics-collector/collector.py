#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Anonymous landing-page metrics collector.

Receives small JSON beacons from the landing-page A/B test, writes them to a
local JSONL log, and pushes aggregate gauges to the Prometheus Pushgateway.
No metrics endpoint is exposed publicly; the collector binds to localhost only.

Endpoints (localhost only):
    POST /beacon           - accept a beacon, return 204
    GET  /metrics/summary  - local debug aggregate stats

Environment:
    METRICS_HOST           - bind host (default: 127.0.0.1)
    METRICS_PORT           - bind port (default: 8080)
    METRICS_LOG_DIR        - JSONL log directory (default: /var/log/vauchi)
    LOG_RETENTION_DAYS     - days to keep daily JSONL logs (default: 30)
    PUSHGATEWAY_URL        - Pushgateway base URL
                             (default: http://vauchi-pushgateway:9091)
    PUSHGATEWAY_JOB        - Pushgateway job name (default: vauchi_landing)
    PUSHGATEWAY_INTERVAL_S - Min seconds between pushes (default: 30)
"""

import hashlib
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

HOST = os.environ.get("METRICS_HOST", "127.0.0.1")
PORT = int(os.environ.get("METRICS_PORT", "8080"))
LOG_DIR = os.environ.get("METRICS_LOG_DIR", "/var/log/vauchi")
LOG_RETENTION_DAYS = int(os.environ.get("LOG_RETENTION_DAYS", "30"))
DAILY_SALT_PATH = os.path.join(LOG_DIR, ".daily-salt")
MAX_BODY_BYTES = 4096

PUSHGATEWAY_URL = os.environ.get(
    "PUSHGATEWAY_URL", "http://vauchi-pushgateway:9091"
)
if urlparse(PUSHGATEWAY_URL).scheme not in ("http", "https"):
    raise SystemExit(
        f"PUSHGATEWAY_URL must be http(s), got: {PUSHGATEWAY_URL!r}"
    )


def _http_only_opener():
    # An opener with ONLY http/https handlers — file://, ftp://, data:// are
    # not installed, so a misconfigured PUSHGATEWAY_URL cannot read local
    # files or reach unexpected schemes (CWE-939). This is the whole push
    # sink; there is no other outbound request path.
    opener = urllib.request.OpenerDirector()
    for handler in (
        urllib.request.HTTPHandler,
        urllib.request.HTTPSHandler,
        urllib.request.HTTPDefaultErrorHandler,
        urllib.request.HTTPErrorProcessor,
        # Any non-http(s) scheme falls through to here and raises a clean
        # URLError instead of silently returning None.
        urllib.request.UnknownHandler,
    ):
        opener.add_handler(handler())
    return opener


_PUSH_OPENER = _http_only_opener()
PUSHGATEWAY_JOB = os.environ.get("PUSHGATEWAY_JOB", "vauchi_landing")
PUSHGATEWAY_INTERVAL_S = int(os.environ.get("PUSHGATEWAY_INTERVAL_S", "30"))

KNOWN_VARIANTS = ["a", "b", "c", "d", "e", "f", "g"]

# Simple in-memory rate limit: max 60 beacons per IP hash per minute.
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX = 60
_rate_limits = {}
_rate_lock = threading.Lock()

# Push state
_push_lock = threading.Lock()
_last_push = 0
_push_pending = False


def is_rate_limited(ip_hash: str) -> bool:
    now = time.time()
    with _rate_lock:
        window_start, count = _rate_limits.get(ip_hash, (0, 0))
        if now - window_start > RATE_LIMIT_WINDOW_SECONDS:
            _rate_limits[ip_hash] = (now, 1)
            return False
        if count >= RATE_LIMIT_MAX:
            return True
        _rate_limits[ip_hash] = (window_start, count + 1)
        return False


def ensure_dirs():
    os.makedirs(LOG_DIR, exist_ok=True)


def daily_salt():
    """Return a salt that rotates daily so hashed IPs cannot be linked across days."""
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if os.path.exists(DAILY_SALT_PATH):
        try:
            with open(DAILY_SALT_PATH, "r", encoding="utf-8") as f:
                stored_day, salt = f.read().strip().split(" ", 1)
            if stored_day == day:
                return salt
        except Exception:
            pass
    salt = hashlib.sha256(os.urandom(32)).hexdigest()[:32]
    with open(DAILY_SALT_PATH, "w", encoding="utf-8") as f:
        f.write(f"{day} {salt}\n")
    return salt


def hash_ip(ip: str) -> str:
    salt = daily_salt()
    return hashlib.sha256(f"{ip}:{salt}".encode("utf-8")).hexdigest()[:16]


def log_path_for_date(day: datetime) -> str:
    """Return the JSONL log path for a given UTC day."""
    return os.path.join(LOG_DIR, f"metrics-{day.strftime('%Y-%m-%d')}.jsonl")


def write_event(record: dict):
    ensure_dirs()
    path = log_path_for_date(datetime.now(timezone.utc))
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def cleanup_old_logs():
    """Delete JSONL log files older than LOG_RETENTION_DAYS."""
    ensure_dirs()
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOG_RETENTION_DAYS)
    removed = 0
    for name in os.listdir(LOG_DIR):
        if not name.startswith("metrics-") or not name.endswith(".jsonl"):
            continue
        try:
            day = datetime.strptime(name[8:18], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if day < cutoff:
            try:
                os.remove(os.path.join(LOG_DIR, name))
                removed += 1
            except OSError:
                pass
    if removed:
        print(f"Cleaned up {removed} old log file(s)", file=sys.stderr)


def load_events(days: int):
    """Yield events from the last N days across daily JSONL files."""
    ensure_dirs()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    today = datetime.now(timezone.utc).date()
    for offset in range(days + 1):
        day = datetime.combine(
            today - timedelta(days=offset), datetime.min.time(), tzinfo=timezone.utc
        )
        path = log_path_for_date(day)
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = ev.get("ts")
                if ts:
                    try:
                        ev_time = datetime.fromisoformat(ts)
                        if ev_time.tzinfo is None:
                            ev_time = ev_time.replace(tzinfo=timezone.utc)
                        if ev_time < cutoff:
                            continue
                    except ValueError:
                        continue
                yield ev


def aggregate(days: int):
    variants = {v: {"sessions": 0, "clicks": 0, "dwell_ms": 0} for v in KNOWN_VARIANTS}
    total_clicks = 0
    sessions = 0
    for ev in load_events(days):
        v = ev.get("v")
        if v not in variants:
            continue
        variants[v]["sessions"] += 1
        variants[v]["clicks"] += ev.get("clicks", 0)
        variants[v]["dwell_ms"] += ev.get("dwell_ms", 0)
        total_clicks += ev.get("clicks", 0)
        sessions += 1

    def avg(values):
        return int(values["dwell_ms"] / values["sessions"]) if values["sessions"] else 0

    return {
        "days": days,
        "sessions": sessions,
        "total_clicks": total_clicks,
        "avg_dwell_ms": avg({"dwell_ms": sum(v["dwell_ms"] for v in variants.values()), "sessions": sessions}),
        "variants": {
            v: {
                "sessions": data["sessions"],
                "clicks": data["clicks"],
                "avg_dwell_ms": avg(data),
                "dwell_ms_sum": data["dwell_ms"],
            }
            for v, data in variants.items()
        },
    }


def render_prometheus_text(data: dict) -> str:
    """Render aggregate landing-page metrics as Prometheus gauges."""
    lines = [
        "# HELP vauchi_landing_sessions Total landing page sessions by variant",
        "# TYPE vauchi_landing_sessions gauge",
    ]
    for v in KNOWN_VARIANTS:
        stats = data["variants"].get(v, {})
        lines.append(f'vauchi_landing_sessions{{v="{v}"}} {stats.get("sessions", 0)}')

    lines.extend([
        "# HELP vauchi_landing_clicks Total primary CTA clicks by variant",
        "# TYPE vauchi_landing_clicks gauge",
    ])
    for v in KNOWN_VARIANTS:
        stats = data["variants"].get(v, {})
        lines.append(f'vauchi_landing_clicks{{v="{v}"}} {stats.get("clicks", 0)}')

    lines.extend([
        "# HELP vauchi_landing_dwell_seconds_count Number of dwell observations by variant",
        "# TYPE vauchi_landing_dwell_seconds_count gauge",
    ])
    for v in KNOWN_VARIANTS:
        stats = data["variants"].get(v, {})
        lines.append(f'vauchi_landing_dwell_seconds_count{{v="{v}"}} {stats.get("sessions", 0)}')

    lines.extend([
        "# HELP vauchi_landing_dwell_seconds_sum Sum of dwell observations by variant",
        "# TYPE vauchi_landing_dwell_seconds_sum gauge",
    ])
    for v in KNOWN_VARIANTS:
        stats = data["variants"].get(v, {})
        lines.append(f'vauchi_landing_dwell_seconds_sum{{v="{v}"}} {stats.get("dwell_ms_sum", 0) / 1000.0:.3f}')

    return "\n".join(lines) + "\n"


def push_to_gateway():
    """Push current aggregate metrics to the Prometheus Pushgateway."""
    global _last_push, _push_pending

    with _push_lock:
        now = time.time()
        if now - _last_push < PUSHGATEWAY_INTERVAL_S:
            _push_pending = True
            return
        _last_push = now
        _push_pending = False

    data = aggregate(365)
    body = render_prometheus_text(data).encode("utf-8")
    url = f"{PUSHGATEWAY_URL.rstrip('/')}/metrics/job/{PUSHGATEWAY_JOB}"

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        # _PUSH_OPENER registers only http/https handlers (see _http_only_opener):
        # file://, ftp://, data:// cannot be reached — the CWE-939 concern B310
        # flags — and PUSHGATEWAY_URL's scheme is validated at module load.
        # nosemgrep: bandit.B310-1
        with _PUSH_OPENER.open(req, timeout=5) as resp:
            resp.read()
    except urllib.error.URLError as e:
        print(f"WARNING: failed to push metrics to {url}: {e}", file=sys.stderr)


def schedule_push():
    """Background thread: push any pending metrics periodically and clean old logs daily."""
    global _last_push, _push_pending
    last_cleanup_day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    while True:
        time.sleep(PUSHGATEWAY_INTERVAL_S)

        # Daily log cleanup.
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != last_cleanup_day:
            cleanup_old_logs()
            last_cleanup_day = today

        with _push_lock:
            if not _push_pending:
                continue
            _push_pending = False
            _last_push = time.time()
        try:
            data = aggregate(365)
            body = render_prometheus_text(data).encode("utf-8")
            url = f"{PUSHGATEWAY_URL.rstrip('/')}/metrics/job/{PUSHGATEWAY_JOB}"
            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            # _PUSH_OPENER registers only http/https handlers (see _http_only_opener):
            # file://, ftp://, data:// cannot be reached — the CWE-939 concern B310
            # flags — and PUSHGATEWAY_URL's scheme is validated at module load.
            # nosemgrep: bandit.B310-1
            with _PUSH_OPENER.open(req, timeout=5) as resp:
                resp.read()
        except urllib.error.URLError as e:
            print(f"WARNING: failed to push metrics to {url}: {e}", file=sys.stderr)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _send_no_content(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _send_method_not_allowed(self):
        self.send_error(405, "Method Not Allowed")

    def do_OPTIONS(self):
        self._send_no_content()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/metrics/summary":
            self.send_error(404)
            return
        qs = parse_qs(parsed.query)
        try:
            days = int(qs.get("days", ["7"])[0])
        except ValueError:
            days = 7
        days = max(1, min(days, 365))
        self._send_json(aggregate(days))

    def do_POST(self):
        if self.path != "/beacon":
            self.send_error(404)
            return

        length = self.headers.get("Content-Length")
        try:
            length = int(length) if length else 0
        except ValueError:
            length = 0
        length = min(length, MAX_BODY_BYTES)

        body = self.rfile.read(length).decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        if not isinstance(payload, dict):
            self.send_error(400, "Invalid payload")
            return

        variant = str(payload.get("v", "unknown"))[:8]
        clicks = int(payload.get("clicks", 0))
        dwell_ms = int(payload.get("dwell_ms", 0))
        path = str(payload.get("path", "/"))[:128]

        client_ip = self.headers.get("X-Forwarded-For", self.client_address[0])
        client_ip = client_ip.split(",")[0].strip()
        ip_hash = hash_ip(client_ip)

        if is_rate_limited(ip_hash):
            self.send_error(429, "Too Many Requests")
            return

        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "v": variant,
            "clicks": max(0, clicks),
            "dwell_ms": max(0, dwell_ms),
            "path": path,
            "ip_hash": ip_hash,
        }
        write_event(record)

        # Push metrics to Prometheus, but not more often than the interval.
        push_to_gateway()

        self._send_no_content()


def main():
    # Restrict created log files to owner-only (nginx user).
    os.umask(0o077)

    ensure_dirs()
    cleanup_old_logs()

    # Start background pusher for any events that arrived during the interval.
    pusher = threading.Thread(target=schedule_push, daemon=True)
    pusher.start()

    server = HTTPServer((HOST, PORT), Handler)
    print(f"Metrics collector listening on {HOST}:{PORT}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
