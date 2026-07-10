#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Self-hosted waitlist API with double-opt-in confirmation emails.

Emails are encrypted at rest with AES-256-GCM. A deterministic SHA-256 hash
of each email is stored alongside the ciphertext so duplicates can be detected
and lookups performed without decrypting.

Endpoints:
    POST /waitlist/join       - submit email, store as pending, send confirmation
    GET  /waitlist/confirm    - confirm email via token
    GET  /waitlist/health     - health check
    GET  /waitlist/admin/export - CSV export (Bearer token required)

Security notes:
    - Confirmation tokens are stored as SHA-256 hashes, never plaintext.
    - Emails are encrypted at rest with AES-256-GCM using a key from
      WAITLIST_ENCRYPTION_KEY.
    - A deterministic SHA-256 email hash is stored for duplicate detection.
    - Audit logs use SHA-256 hashed emails, never plaintext addresses.
    - A hidden honeypot field catches naive bots without revealing itself.
    - The admin export key is compared in constant time.

Environment:
    WAITLIST_DB_PATH          - SQLite path (default: ./waitlist.db)
    WAITLIST_REDIRECT_BASE_URL- Redirect target base (default: https://vauchi.app/)
    WAITLIST_ENCRYPTION_KEY   - Base64-encoded 32-byte AES-256-GCM key (required)
    WAITLIST_SMTP_HOST        - SMTP server (default: mail.vauchi.app)
    WAITLIST_SMTP_PORT        - SMTP port (default: 587)
    WAITLIST_SMTP_USER        - SMTP auth user (default: waitlist@vauchi.app)
    WAITLIST_SMTP_PASSWORD    - SMTP auth password (required to send mail)
    WAITLIST_SMTP_FROM        - From address (default: waitlist@vauchi.app)
    WAITLIST_SMTP_STARTTLS    - Use STARTTLS (default: true)
    WAITLIST_ADMIN_API_KEY    - API key for /admin/export
    WAITLIST_CONFIRMATION_SUBJECT - Optional custom subject line
"""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import os
import re
import smtplib
import sqlite3
from datetime import datetime, timezone
from email.message import EmailMessage
from secrets import compare_digest, token_urlsafe
from urllib.parse import urljoin, urlparse

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from flask import Flask, abort, redirect, request

app = Flask(__name__)

DB_PATH = os.environ.get("WAITLIST_DB_PATH", "./waitlist.db")
REDIRECT_BASE = os.environ.get("WAITLIST_REDIRECT_BASE_URL", "https://vauchi.app/").rstrip("/") + "/"
SMTP_HOST = os.environ.get("WAITLIST_SMTP_HOST", "mail.vauchi.app")
SMTP_PORT = int(os.environ.get("WAITLIST_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("WAITLIST_SMTP_USER", "waitlist@vauchi.app")
SMTP_PASSWORD = os.environ.get("WAITLIST_SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("WAITLIST_SMTP_FROM", "waitlist@vauchi.app")
SMTP_STARTTLS = os.environ.get("WAITLIST_SMTP_STARTTLS", "true").lower() in ("1", "true", "yes")
ADMIN_API_KEY = os.environ.get("WAITLIST_ADMIN_API_KEY", "")
CONFIRMATION_SUBJECT = os.environ.get(
    "WAITLIST_CONFIRMATION_SUBJECT", "Confirm your spot on the Vauchi waitlist"
)

# Simple regex for email validation; final delivery is handled by the MTA.
EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

AESGCM_NONCE_SIZE = 12


def _load_encryption_key() -> bytes:
    """Load and validate the AES-256-GCM key from environment."""
    raw = os.environ.get("WAITLIST_ENCRYPTION_KEY", "")
    if not raw:
        raise RuntimeError("WAITLIST_ENCRYPTION_KEY is required")
    try:
        key = base64.b64decode(raw)
    except Exception as exc:
        raise RuntimeError("WAITLIST_ENCRYPTION_KEY must be base64-encoded") from exc
    if len(key) != 32:
        raise RuntimeError("WAITLIST_ENCRYPTION_KEY must decode to 32 bytes (256 bits)")
    return key


ENCRYPTION_KEY = _load_encryption_key()


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _encrypt(plaintext: str) -> str:
    """Encrypt a string with AES-256-GCM; return base64(nonce || ciphertext)."""
    nonce = os.urandom(AESGCM_NONCE_SIZE)
    ciphertext = AESGCM(ENCRYPTION_KEY).encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def _decrypt(token: str) -> str:
    """Decrypt a value produced by _encrypt. Raises InvalidTag on tampering."""
    data = base64.b64decode(token)
    nonce = data[:AESGCM_NONCE_SIZE]
    ciphertext = data[AESGCM_NONCE_SIZE:]
    return AESGCM(ENCRYPTION_KEY).decrypt(nonce, ciphertext, None).decode("utf-8")


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS waitlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_hash TEXT NOT NULL UNIQUE,
            email_ciphertext TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('pending', 'confirmed')),
            token_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            confirmed_at TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_waitlist_status ON waitlist(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_waitlist_token ON waitlist(token_hash)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_waitlist_email_hash ON waitlist(email_hash)")


def _migrate_plaintext_table(conn: sqlite3.Connection) -> None:
    """Migrate an older plaintext 'email' column to encrypted storage."""
    app.logger.warning("Migrating waitlist table from plaintext to encrypted storage")
    conn.execute("ALTER TABLE waitlist RENAME TO waitlist_old")
    _create_tables(conn)
    for row in conn.execute(
        "SELECT email, status, token_hash, created_at, confirmed_at FROM waitlist_old"
    ):
        conn.execute(
            """
            INSERT INTO waitlist
                (email_hash, email_ciphertext, status, token_hash, created_at, confirmed_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                _hash_email(row["email"]),
                _encrypt(row["email"]),
                row["status"],
                row["token_hash"],
                row["created_at"],
                row["confirmed_at"],
            ),
        )
    conn.execute("DROP TABLE waitlist_old")


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    with _db() as conn:
        old = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='waitlist'"
        ).fetchone()
        if old:
            columns = {
                row[1] for row in conn.execute("PRAGMA table_info(waitlist)")
            }
            if "email" in columns and "email_hash" not in columns:
                _migrate_plaintext_table(conn)
                return
        _create_tables(conn)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _hash(value: str) -> str:
    """Return a stable SHA-256 hex digest of a UTF-8 string."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_token(token: str) -> str:
    return _hash(token)


def _hash_email(email: str) -> str:
    """Hash a normalized email for lookup and privacy-preserving audit logs."""
    return _hash(email.strip().lower())


def _client_ip() -> str:
    """Best-guess client IP, preferring the last X-Forwarded-For entry."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.remote_addr or "unknown"


def _audit(
    action: str,
    email: str | None = None,
    email_hash: str | None = None,
    status: str | None = None,
    extra: dict | None = None,
) -> None:
    """Write a privacy-preserving audit log entry (hashed email, no plaintext)."""
    event = {
        "ts": _now(),
        "action": action,
        "ip": _client_ip(),
        "email_hash": _hash_email(email) if email else email_hash,
        "status": status,
    }
    if extra:
        event.update(extra)
    app.logger.info("waitlist_audit %s", json.dumps(event, separators=(",", ":"), default=str))


def _valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email))


def _safe_redirect_url(raw: str | None) -> str:
    """Return a redirect URL that stays under REDIRECT_BASE."""
    if not raw:
        return REDIRECT_BASE
    parsed = urlparse(raw)
    if parsed.netloc and parsed.netloc != urlparse(REDIRECT_BASE).netloc:
        return REDIRECT_BASE
    return urljoin(REDIRECT_BASE, parsed.path or "/")


def _waitlist_redirect(redirect_url: str, status: str):
    """303 back to the landing page, anchored at the waitlist section
    so the visitor sees the status banner instead of the page top."""
    return redirect(f"{redirect_url}?waitlist={status}#waitlist", code=303)


def _send_confirmation(email: str, token: str) -> None:
    if not SMTP_PASSWORD:
        raise RuntimeError("WAITLIST_SMTP_PASSWORD is not configured")

    confirm_url = urljoin(REDIRECT_BASE, f"/waitlist/confirm?token={token}")
    msg = EmailMessage()
    msg["Subject"] = CONFIRMATION_SUBJECT
    msg["From"] = SMTP_FROM
    msg["To"] = email
    msg.set_content(
        f"Hi,\n\n"
        f"Thanks for your interest in Vauchi.\n\n"
        f"Confirm your spot on the waitlist by opening this link:\n"
        f"{confirm_url}\n\n"
        f"If you did not request this, you can ignore this email.\n\n"
        f"— Vauchi\n"
        f"https://vauchi.app/\n"
    )

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        if SMTP_STARTTLS:
            server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)


@app.route("/waitlist/health", methods=["GET"])
def health() -> str:
    return "OK"


@app.route("/waitlist/join", methods=["POST"])
def join():
    email = (request.form.get("email") or "").strip().lower()
    redirect_url = _safe_redirect_url(request.form.get("redirect"))

    # Honeypot: hidden field should be left blank by real users.
    if request.form.get("website"):
        _audit("join_honeypot", email=email)
        return _waitlist_redirect(redirect_url, "joined")

    if not email or not _valid_email(email):
        _audit("join_invalid", email=email, status="invalid")
        return _waitlist_redirect(redirect_url, "invalid")

    if not SMTP_PASSWORD:
        _audit("join_error", email=email, status="smtp_not_configured")
        app.logger.error("WAITLIST_SMTP_PASSWORD is not set; refusing submission")
        return _waitlist_redirect(redirect_url, "error")

    token = token_urlsafe(32)
    token_hash = _hash_token(token)
    email_hash = _hash_email(email)
    email_ciphertext = _encrypt(email)
    now = _now()

    with _db() as conn:
        existing = conn.execute(
            "SELECT status, token_hash FROM waitlist WHERE email_hash = ?", (email_hash,)
        ).fetchone()

        if existing:
            if existing["status"] == "confirmed":
                _audit("join_duplicate", email=email, status="already_confirmed")
                return _waitlist_redirect(redirect_url, "already-confirmed")
            # Pending: update token and resend confirmation.
            conn.execute(
                "UPDATE waitlist SET token_hash = ?, email_ciphertext = ?, created_at = ? WHERE email_hash = ?",
                (token_hash, email_ciphertext, now, email_hash),
            )
            _audit("join_resend", email=email, status="pending")
        else:
            conn.execute(
                "INSERT INTO waitlist (email_hash, email_ciphertext, status, token_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (email_hash, email_ciphertext, "pending", token_hash, now),
            )
            _audit("join_accepted", email=email, status="pending")

    try:
        _send_confirmation(email, token)
    except Exception as e:
        _audit("join_error", email=email, status="send_failed", extra={"error": type(e).__name__})
        app.logger.error("Failed to send confirmation (email_hash=%s): %s", email_hash, e)
        return _waitlist_redirect(redirect_url, "error")

    return _waitlist_redirect(redirect_url, "joined")


@app.route("/waitlist/confirm", methods=["GET"])
def confirm():
    token = request.args.get("token", "")
    redirect_url = _safe_redirect_url(request.args.get("redirect"))

    if not token:
        _audit("confirm_invalid", status="missing_token")
        return _waitlist_redirect(redirect_url, "invalid-token")

    token_hash = _hash_token(token)
    now = _now()

    with _db() as conn:
        row = conn.execute(
            "SELECT id, status, email_hash FROM waitlist WHERE token_hash = ?", (token_hash,)
        ).fetchone()

        if not row:
            _audit("confirm_invalid", status="unknown_token")
            return _waitlist_redirect(redirect_url, "invalid-token")

        if row["status"] == "confirmed":
            _audit("confirm_duplicate", email_hash=row["email_hash"], status="already_confirmed")
            return _waitlist_redirect(redirect_url, "already-confirmed")

        conn.execute(
            "UPDATE waitlist SET status = 'confirmed', confirmed_at = ? WHERE id = ?",
            (now, row["id"]),
        )
        _audit("confirm_success", email_hash=row["email_hash"], status="confirmed")

    return _waitlist_redirect(redirect_url, "confirmed")


@app.route("/waitlist/admin/export", methods=["GET"])
def export():
    if not ADMIN_API_KEY:
        abort(404)

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or not compare_digest(auth[7:], ADMIN_API_KEY):
        _audit("export_denied", status="invalid_key")
        abort(401)

    _audit("export")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["email", "status", "created_at", "confirmed_at"])

    with _db() as conn:
        for row in conn.execute(
            "SELECT email_ciphertext, status, created_at, confirmed_at FROM waitlist ORDER BY created_at"
        ):
            try:
                email = _decrypt(row["email_ciphertext"])
            except InvalidTag:
                app.logger.error("Failed to decrypt waitlist entry (database tampered or wrong key)")
                continue
            writer.writerow([email, row["status"], row["created_at"], row["confirmed_at"]])

    response = app.make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=vauchi-waitlist.csv"
    return response


@app.before_request
def _ensure_db() -> None:
    # Lazy-init on first request so the volume is mounted before creating the DB.
    init_db()


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8080, debug=False)
