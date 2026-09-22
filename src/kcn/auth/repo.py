"""Autenticación sencilla: registro central de usuarios + BD por usuario."""

from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
from pathlib import Path

_ITER = 200_000


def data_dir() -> Path:
    d = Path(os.environ.get("KCN_DATA_DIR", str(Path.home() / ".kcn")))
    d.mkdir(parents=True, exist_ok=True)
    return d


def users_db_path() -> Path:
    return data_dir() / "users.db"


def normalize(username: str) -> str:
    return (username or "").strip().lower()


def user_db_path(username: str) -> Path:
    d = data_dir() / "users"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{normalize(username)}.db"


def invite_code() -> str:
    return os.environ.get("KCN_INVITE_CODE", "KCN-INVITA")


_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id       INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    salt     TEXT NOT NULL,
    pwd_hash TEXT NOT NULL,
    created  TEXT
);
"""


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(users_db_path()))
    c.row_factory = sqlite3.Row
    c.executescript(_SCHEMA)
    c.commit()
    return c


def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _ITER).hex()


def user_exists(username: str) -> bool:
    c = _conn()
    try:
        return c.execute("SELECT 1 FROM users WHERE username = ?",
                         (normalize(username),)).fetchone() is not None
    finally:
        c.close()


def create_user(username: str, password: str) -> str:
    u = normalize(username)
    if not u or not password:
        raise ValueError("Usuario y contraseña obligatorios.")
    salt = secrets.token_hex(16)
    c = _conn()
    try:
        c.execute("INSERT INTO users (username, salt, pwd_hash, created) VALUES (?, ?, ?, datetime('now'))",
                  (u, salt, _hash(password, salt)))
        c.commit()
    except sqlite3.IntegrityError:
        raise ValueError("Ese usuario ya existe.")
    finally:
        c.close()
    return u


def verify_user(username: str, password: str) -> bool:
    c = _conn()
    try:
        r = c.execute("SELECT salt, pwd_hash FROM users WHERE username = ?",
                      (normalize(username),)).fetchone()
    finally:
        c.close()
    if not r:
        return False
    return secrets.compare_digest(_hash(password, r["salt"]), r["pwd_hash"])
