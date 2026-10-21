"""Single-use email verification and password-reset tokens with SMTP delivery.

This module is opt-in: no SMTP credentials means no email is sent and no token is exposed.
Tokens are stored only as SHA-256 hashes, expire, and are consumed once. Configure HTTPS
and rate limiting at the deployment edge before enabling this on a public service.
"""
from __future__ import annotations

import hashlib
import os
import secrets
import smtplib
import sqlite3
import ssl
import time
from email.message import EmailMessage
from pathlib import Path

from core.auth import AuthManager


class AccountTokenError(RuntimeError):
    pass


def _connect() -> sqlite3.Connection:
    path = Path(os.getenv("MKAOS_ACCOUNT_TOKEN_DB", "./memory/account_tokens.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    conn.execute("""CREATE TABLE IF NOT EXISTS account_tokens (
        token_hash TEXT PRIMARY KEY, username TEXT NOT NULL, purpose TEXT NOT NULL,
        expires_at INTEGER NOT NULL, created_at INTEGER NOT NULL, used_at INTEGER
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS account_token_limits (
        bucket TEXT PRIMARY KEY, window_start INTEGER NOT NULL, count INTEGER NOT NULL
    )""")
    conn.commit()
    return conn


def _send_email(recipient: str, subject: str, body: str) -> None:
    host = os.getenv("MKAOS_SMTP_HOST", "").strip()
    sender = os.getenv("MKAOS_EMAIL_FROM", "").strip()
    username = os.getenv("MKAOS_SMTP_USERNAME", "").strip()
    password = os.getenv("MKAOS_SMTP_PASSWORD", "")
    if not host or not sender or not username or not password:
        raise AccountTokenError("Email delivery is not configured.")
    port = int(os.getenv("MKAOS_SMTP_PORT", "587"))
    if not 1 <= port <= 65535:
        raise AccountTokenError("Invalid SMTP port.")
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=10) as smtp:
        smtp.ehlo()
        smtp.starttls(context=context)
        smtp.ehlo()
        smtp.login(username, password)
        smtp.send_message(message)


def _issue(auth: AuthManager, username: str, purpose: str) -> None:
    username = username.lower().strip()
    user = auth._users.get(username)
    if not user or not user.get("active") or not user.get("email"):
        return
    now = int(time.time())
    bucket = f"{purpose}:{username}"
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT window_start, count FROM account_token_limits WHERE bucket=?", (bucket,)).fetchone()
        if row and now - row[0] < 900 and row[1] >= 3:
            raise AccountTokenError("Too many requests. Try again later.")
        if row and now - row[0] < 900:
            conn.execute("UPDATE account_token_limits SET count=count+1 WHERE bucket=?", (bucket,))
        else:
            conn.execute("INSERT INTO account_token_limits(bucket, window_start, count) VALUES (?, ?, 1) ON CONFLICT(bucket) DO UPDATE SET window_start=excluded.window_start, count=1", (bucket, now))
        conn.execute("UPDATE account_tokens SET used_at=? WHERE username=? AND purpose=? AND used_at IS NULL", (now, username, purpose))
        conn.execute("INSERT INTO account_tokens(token_hash, username, purpose, expires_at, created_at, used_at) VALUES (?, ?, ?, ?, ?, NULL)", (token_hash, username, purpose, now + 1800, now))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    base = os.getenv("MKAOS_PUBLIC_BASE_URL", "").strip().rstrip("/")
    if not base.startswith("https://"):
        raise AccountTokenError("MKAOS_PUBLIC_BASE_URL must be HTTPS for email links.")
    if purpose == "verify":
        url = f"{base}/?account_action=verify&token={token}"
        subject = "MKAOS e-posta adresini doğrula"
        body = f"E-posta adresini doğrulamak için bu bağlantıyı 30 dakika içinde aç:\n{url}\n\nBu isteği sen yapmadıysan bu mesajı yok say."
    else:
        url = f"{base}/?account_action=reset&token={token}"
        subject = "MKAOS parola sıfırlama"
        body = f"Parolanı yenilemek için bu bağlantıyı 30 dakika içinde aç:\n{url}\n\nBu isteği sen yapmadıysan bu mesajı yok say."
    _send_email(user["email"], subject, body)


def request_verification(auth: AuthManager, username: str, email: str) -> None:
    if not auth.set_email(username, email):
        raise AccountTokenError("Invalid account or email address.")
    _issue(auth, username, "verify")


def request_password_reset(auth: AuthManager, username: str) -> None:
    # Public endpoint intentionally gives the same response for unknown users.
    _issue(auth, username, "reset")


def consume_token(auth: AuthManager, token: str, purpose: str, new_password: str | None = None) -> bool:
    if purpose not in {"verify", "reset"} or not isinstance(token, str) or not 24 <= len(token) <= 128:
        return False
    digest = hashlib.sha256(token.encode()).hexdigest()
    now = int(time.time())
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT username, expires_at, used_at FROM account_tokens WHERE token_hash=? AND purpose=?",
            (digest, purpose),
        ).fetchone()
        if not row or row[2] is not None or row[1] < now:
            conn.rollback()
            return False
        username = row[0]
        # Mark single-use before applying mutation; roll back if the mutation fails.
        conn.execute("UPDATE account_tokens SET used_at=? WHERE token_hash=? AND used_at IS NULL", (now, digest))
        if purpose == "verify":
            ok = auth.mark_email_verified(username)
        else:
            ok = bool(new_password and auth.set_password(username, new_password))
        if not ok:
            conn.rollback()
            return False
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
