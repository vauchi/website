# SPDX-FileCopyrightText: 2026 Mattia Egloff <mattia.egloff@pm.me>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Transactional active-store lifecycle for one optional mail campaign."""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import re
import sqlite3


def retention_days(value, maximum):
    if isinstance(value, bool) or not str(value).isascii() or not str(value).isdigit():
        raise ValueError("Waitlist retention must be a positive integer number of days")
    result = int(value)
    if not 1 <= result <= maximum:
        raise ValueError(f"Waitlist retention must be between 1 and {maximum} days")
    return result


def token_hash(token):
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        return None
    return hashlib.sha256(token.encode()).hexdigest()


class WaitlistStore:
    def __init__(self, path, encrypt, decrypt, *, clock=None, pending_days=7, confirmed_days=365):
        self.path = str(path)
        self.encrypt = encrypt
        self.decrypt = decrypt
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.pending_days = retention_days(pending_days, 30)
        self.confirmed_days = retention_days(confirmed_days, 365)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def transaction(self):
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA secure_delete = ON")
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def now(self):
        value = self.clock()
        if value.tzinfo is None:
            raise ValueError("Waitlist clock must include a timezone")
        return value.astimezone(timezone.utc)

    @staticmethod
    def email_hash(email):
        return hashlib.sha256(email.strip().lower().encode()).hexdigest()

    def initialize(self):
        with self.transaction() as connection:
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(waitlist)")}
            plaintext = "email" in columns and "email_hash" not in columns
            if plaintext:
                connection.execute("ALTER TABLE waitlist RENAME TO waitlist_old")
            connection.execute("""CREATE TABLE IF NOT EXISTS waitlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_hash TEXT NOT NULL UNIQUE,
                email_ciphertext TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('pending', 'confirmed')),
                token_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                confirmed_at TEXT,
                withdrawal_hash TEXT,
                withdrawal_ciphertext TEXT
            )""")
            if not plaintext and columns:
                for name in ("withdrawal_hash", "withdrawal_ciphertext"):
                    if name not in columns:
                        connection.execute(f"ALTER TABLE waitlist ADD COLUMN {name} TEXT")
            if plaintext:
                for row in connection.execute("SELECT * FROM waitlist_old"):
                    email = row["email"].strip().lower()
                    connection.execute("""INSERT INTO waitlist
                        (email_hash, email_ciphertext, status, token_hash, created_at, confirmed_at)
                        VALUES (?, ?, ?, ?, ?, ?)""", (
                        self.email_hash(email), self.encrypt(email), row["status"],
                        row["token_hash"], row["created_at"], row["confirmed_at"],
                    ))
                connection.execute("DROP TABLE waitlist_old")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_waitlist_token ON waitlist(token_hash)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_waitlist_withdrawal ON waitlist(withdrawal_hash)")
            connection.execute("""CREATE TABLE IF NOT EXISTS campaign (
                id INTEGER PRIMARY KEY CHECK(id = 1), closed INTEGER NOT NULL CHECK(closed IN (0, 1))
            )""")
            connection.execute("INSERT OR IGNORE INTO campaign (id, closed) VALUES (1, 0)")
            self.expire(connection)

    def expire(self, connection):
        now = self.now()
        pending = (now - timedelta(days=self.pending_days)).isoformat()
        confirmed = (now - timedelta(days=self.confirmed_days)).isoformat()
        return connection.execute("""DELETE FROM waitlist WHERE
            (status = 'pending' AND (julianday(created_at) IS NULL OR julianday(created_at) <= julianday(?)))
            OR (status = 'confirmed' AND (julianday(confirmed_at) IS NULL OR julianday(confirmed_at) <= julianday(?)))
            """, (pending, confirmed)).rowcount

    def cleanup(self):
        with self.transaction() as connection:
            return self.expire(connection)

    def enroll(self, email, confirmation, withdrawal):
        email = email.strip().lower()
        with self.transaction() as connection:
            self.expire(connection)
            if connection.execute("SELECT closed FROM campaign WHERE id = 1").fetchone()[0]:
                return "closed", None
            hashed_email = self.email_hash(email)
            row = connection.execute("SELECT * FROM waitlist WHERE email_hash = ?", (hashed_email,)).fetchone()
            if row:
                if row["withdrawal_ciphertext"]:
                    withdrawal = self.decrypt(row["withdrawal_ciphertext"])
                connection.execute("""UPDATE waitlist SET withdrawal_hash = ?, withdrawal_ciphertext = ?
                    WHERE email_hash = ?""", (token_hash(withdrawal), self.encrypt(withdrawal), hashed_email))
                if row["status"] == "pending":
                    connection.execute("UPDATE waitlist SET token_hash = ? WHERE email_hash = ?",
                        (token_hash(confirmation), hashed_email))
                return row["status"], withdrawal
            connection.execute("""INSERT INTO waitlist
                (email_hash, email_ciphertext, status, token_hash, created_at, withdrawal_hash, withdrawal_ciphertext)
                VALUES (?, ?, 'pending', ?, ?, ?, ?)""", (
                hashed_email, self.encrypt(email), token_hash(confirmation),
                self.now().isoformat(timespec="seconds"), token_hash(withdrawal), self.encrypt(withdrawal),
            ))
            return "pending", withdrawal

    def confirm(self, token):
        hashed = token_hash(token)
        if hashed is None:
            return False
        with self.transaction() as connection:
            self.expire(connection)
            result = connection.execute("""UPDATE waitlist SET status = 'confirmed', confirmed_at = ?, token_hash = ''
                WHERE token_hash = ? AND status = 'pending'""",
                (self.now().isoformat(timespec="seconds"), hashed))
            return result.rowcount == 1

    def withdraw(self, token):
        hashed = token_hash(token)
        if hashed is None:
            return
        with self.transaction() as connection:
            self.expire(connection)
            connection.execute("DELETE FROM waitlist WHERE withdrawal_hash = ?", (hashed,))

    def management(self, email, new_token):
        with self.transaction() as connection:
            self.expire(connection)
            row = connection.execute("SELECT * FROM waitlist WHERE email_hash = ?",
                (self.email_hash(email),)).fetchone()
            if row is None:
                return None
            if row["withdrawal_ciphertext"]:
                token = self.decrypt(row["withdrawal_ciphertext"])
            else:
                token = new_token
                connection.execute("""UPDATE waitlist SET withdrawal_hash = ?, withdrawal_ciphertext = ?
                    WHERE id = ?""", (token_hash(token), self.encrypt(token), row["id"]))
            return self.decrypt(row["email_ciphertext"]), token

    def export_confirmed(self):
        with self.transaction() as connection:
            self.expire(connection)
            return [{"email": self.decrypt(row["email_ciphertext"]), "status": row["status"],
                     "created_at": row["created_at"], "confirmed_at": row["confirmed_at"]}
                for row in connection.execute("SELECT * FROM waitlist WHERE status = 'confirmed' ORDER BY created_at, id")]

    def close_campaign(self):
        with self.transaction() as connection:
            connection.execute("UPDATE campaign SET closed = 1 WHERE id = 1")
            connection.execute("DELETE FROM waitlist")
