"""Username and password checks. Passwords are stored as a hash, not plain text."""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User

_USERNAME = re.compile(r"[a-z0-9._-]{3,40}")
_ROUNDS = 200_000


def normalize_username(value: str) -> str:
    name = (value or "").strip().lower()
    if not _USERNAME.fullmatch(name):
        raise ValueError(
            "Username must be 3–40 characters: letters, numbers, dot, underscore, or hyphen."
        )
    return name


def hash_password(password: str) -> str:
    if len(password or "") < 6:
        raise ValueError("Password must be at least 6 characters.")
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), _ROUNDS
    )
    return f"pbkdf2_sha256${_ROUNDS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored or not password:
        return False
    try:
        algo, rounds, salt, digest = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        check = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), int(rounds)
        )
        return hmac.compare_digest(check.hex(), digest)
    except (ValueError, TypeError):
        return False


def username_taken(db: Session, username: str, except_id: int | None = None) -> bool:
    stmt = select(User).where(User.username == username)
    if except_id is not None:
        stmt = stmt.where(User.id != except_id)
    return db.scalar(stmt) is not None


def oldest_unclaimed(db: Session) -> User | None:
    return db.scalar(
        select(User)
        .where(User.password_hash.is_(None))
        .order_by(User.created_at.asc(), User.id.asc())
    )
