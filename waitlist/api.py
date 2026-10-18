#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Optional double-opt-in mail campaign, separate from app identities.

Addresses and reusable withdrawal capabilities are encrypted at rest with
the operator's AES-GCM key. Confirmation tokens are stored only as hashes.
The operator can read/export eligible addresses; this is not end-to-end
encryption. Deleting active records cannot recall mail or old snapshots.
"""

import base64
import csv
from datetime import datetime, timezone
from email.message import EmailMessage
import io
import os
import re
import smtplib
from secrets import compare_digest, token_urlsafe
from urllib.parse import urljoin, urlparse

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from flask import Flask, abort, redirect, render_template_string, request
from werkzeug.exceptions import HTTPException

from storage import WaitlistStore, retention_days

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

DB_PATH = os.environ.get("WAITLIST_DB_PATH", "./waitlist.db")
REDIRECT_BASE = os.environ.get("WAITLIST_REDIRECT_BASE_URL", "https://vauchi.app/").rstrip("/") + "/"
SMTP_HOST = os.environ.get("WAITLIST_SMTP_HOST", "mail.vauchi.app")
SMTP_PORT = int(os.environ.get("WAITLIST_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("WAITLIST_SMTP_USER", "waitlist@vauchi.app")
SMTP_PASSWORD = os.environ.get("WAITLIST_SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("WAITLIST_SMTP_FROM", "waitlist@vauchi.app")
SMTP_STARTTLS = os.environ.get("WAITLIST_SMTP_STARTTLS", "true").lower() in ("1", "true", "yes")
ADMIN_API_KEY = os.environ.get("WAITLIST_ADMIN_API_KEY", "")
CONFIRMATION_SUBJECT = os.environ.get("WAITLIST_CONFIRMATION_SUBJECT", "Confirm your spot on the Vauchi waitlist")
PENDING_DAYS = retention_days(os.environ.get("WAITLIST_PENDING_DAYS", "7"), 30)
CONFIRMED_DAYS = retention_days(os.environ.get("WAITLIST_CONFIRMED_DAYS", "365"), 365)
EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
AESGCM_NONCE_SIZE = 12


def _load_encryption_key():
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


def _encrypt(plaintext):
    nonce = os.urandom(AESGCM_NONCE_SIZE)
    ciphertext = AESGCM(ENCRYPTION_KEY).encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def _decrypt(token):
    data = base64.b64decode(token)
    return AESGCM(ENCRYPTION_KEY).decrypt(data[:AESGCM_NONCE_SIZE], data[AESGCM_NONCE_SIZE:], None).decode("utf-8")


def _hash_email(email):
    return WaitlistStore.email_hash(email)


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def store():
    return WaitlistStore(DB_PATH, _encrypt, _decrypt,
        clock=lambda: datetime.fromisoformat(_now()), pending_days=PENDING_DAYS, confirmed_days=CONFIRMED_DAYS)


def _valid_email(email):
    return len(email) <= 254 and bool(EMAIL_RE.fullmatch(email))


def _safe_redirect_url(raw):
    if not raw:
        return REDIRECT_BASE
    parsed = urlparse(raw)
    if parsed.netloc and parsed.netloc != urlparse(REDIRECT_BASE).netloc:
        return REDIRECT_BASE
    return urljoin(REDIRECT_BASE, parsed.path or "/")


def _waitlist_redirect(redirect_url, status):
    return redirect(f"{redirect_url}?waitlist={status}#waitlist", code=303)


def _send_mail(email, subject, body):
    if not SMTP_PASSWORD:
        raise RuntimeError("WAITLIST_SMTP_PASSWORD is not configured")
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = SMTP_FROM
    message["To"] = email
    message.set_content(body)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        if SMTP_STARTTLS:
            server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(message)


def _withdrawal_mail(email, token):
    link = urljoin(REDIRECT_BASE, f"/waitlist/withdraw?token={token}")
    _send_mail(email, "Manage your Vauchi waitlist request",
        f"You requested a link to leave the Vauchi waitlist.\n\n"
        f"Open this link, then confirm removal:\n{link}\n\n"
        "If you did not request this email, you can ignore it.\n\n— Vauchi\n")


def _confirmation_mail(email, confirmation, withdrawal):
    confirm = urljoin(REDIRECT_BASE, f"/waitlist/confirm?token={confirmation}")
    leave = urljoin(REDIRECT_BASE, f"/waitlist/withdraw?token={withdrawal}")
    _send_mail(email, CONFIRMATION_SUBJECT,
        f"Thanks for your interest in Vauchi.\n\nConfirm your spot:\n{confirm}\n\n"
        f"To leave instead, open this link and confirm removal:\n{leave}\n\n"
        "If you did not request this email, you can ignore it.\n\n— Vauchi\n")


def _management_page(*, token=None, done=False):
    return render_template_string("""<!doctype html><html lang="en"><head>
        <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
        <title>Vauchi waitlist</title></head><body><main><h1>Vauchi waitlist</h1>
        {% if done %}<p>If this request matches an active entry, it has been processed.</p>
        {% elif token is not none %}<p>Confirm that you want to leave the waitlist.</p>
        <form method="post" action="/waitlist/withdraw"><input type="hidden" name="token" value="{{ token }}">
        <button type="submit">Leave the waitlist</button></form>
        {% else %}<p>Enter your email to request a removal link.</p>
        <form method="post" action="/waitlist/manage"><label for="waitlist-email">Email address</label>
        <input id="waitlist-email" type="email" name="email" required maxlength="254">
        <button type="submit">Send removal link</button></form>{% endif %}
        <p><a href="{{ home }}">Back to Vauchi</a></p></main></body></html>""",
        token=token, done=done, home=REDIRECT_BASE)


def _require_admin():
    if not ADMIN_API_KEY:
        abort(404)
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or not compare_digest(auth[7:], ADMIN_API_KEY):
        abort(401)


@app.get("/waitlist/health")
def health():
    return "OK"


@app.post("/waitlist/join")
def join():
    email = (request.form.get("email") or "").strip().lower()
    destination = _safe_redirect_url(request.form.get("redirect"))
    if request.form.get("website"):
        return _waitlist_redirect(destination, "joined")
    if not _valid_email(email):
        return _waitlist_redirect(destination, "invalid")
    if not SMTP_PASSWORD:
        app.logger.error("WAITLIST_SMTP_PASSWORD is not set; refusing submission")
        return _waitlist_redirect(destination, "error")
    confirmation, withdrawal = token_urlsafe(32), token_urlsafe(32)
    status, withdrawal = store().enroll(email, confirmation, withdrawal)
    if status == "closed":
        return _waitlist_redirect(destination, "closed")
    try:
        if status == "confirmed":
            _withdrawal_mail(email, withdrawal)
        else:
            _confirmation_mail(email, confirmation, withdrawal)
    except Exception:
        app.logger.error("Waitlist confirmation delivery failed")
        return _waitlist_redirect(destination, "error")
    return _waitlist_redirect(destination, "joined")


@app.get("/waitlist/confirm")
def confirm():
    successful = store().confirm(request.args.get("token") or "")
    return _waitlist_redirect(_safe_redirect_url(request.args.get("redirect")),
        "confirmed" if successful else "invalid-token")


@app.route("/waitlist/withdraw", methods=["GET", "POST"])
def withdraw():
    if request.method == "GET":
        return _management_page(token=request.args.get("token", ""))
    store().withdraw(request.form.get("token") or "")
    return _management_page(done=True)


@app.route("/waitlist/manage", methods=["GET", "POST"])
def manage():
    if request.method == "GET":
        return _management_page()
    email = (request.form.get("email") or "").strip().lower()
    if _valid_email(email) and not request.form.get("website"):
        token = token_urlsafe(32)
        details = store().management(email, token)
        recipient, token = details if details else (email, token)
        try:
            _withdrawal_mail(recipient, token)
        except Exception:
            app.logger.error("Waitlist management delivery failed")
    return _management_page(done=True)


@app.get("/waitlist/admin/export")
def export():
    _require_admin()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["email", "status", "created_at", "confirmed_at"])
    writer.writeheader()
    writer.writerows(store().export_confirmed())
    response = app.make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=vauchi-waitlist.csv"
    return response


@app.post("/waitlist/admin/close")
def close():
    _require_admin()
    store().close_campaign()
    return "", 204


@app.before_request
def _ensure_db():
    store()


@app.after_request
def _privacy_headers(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'none'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
    return response


@app.errorhandler(Exception)
def _service_error(error):
    if isinstance(error, HTTPException):
        return error
    app.logger.error("Waitlist request failed")
    return "The waitlist request could not be completed. Please try again.", 503


if __name__ == "__main__":
    store()
    app.run(host="127.0.0.1", port=8080, debug=False)
