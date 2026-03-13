import os
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from server.services.db import get_cursor

JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 72


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_jwt(user_id: int, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        payload["sub"] = int(payload["sub"])
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Exception):
        return None


def signup(email: str, password: str, display_name: str | None = None) -> dict:
    email = email.strip().lower()
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters")

    pw_hash = hash_password(password)
    with get_cursor() as cur:
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            raise ValueError("An account with this email already exists")
        cur.execute(
            "INSERT INTO users (email, password_hash, display_name) VALUES (%s, %s, %s) RETURNING id, email, display_name, created_at",
            (email, pw_hash, display_name),
        )
        user = cur.fetchone()

    token = create_jwt(user["id"], user["email"])
    _store_session(user["id"], token)
    return {"user": dict(user), "token": token}


def login(email: str, password: str) -> dict:
    email = email.strip().lower()
    with get_cursor() as cur:
        cur.execute("SELECT id, email, password_hash, display_name, created_at FROM users WHERE email = %s", (email,))
        user = cur.fetchone()

    if not user or not verify_password(password, user["password_hash"]):
        raise ValueError("Invalid email or password")

    token = create_jwt(user["id"], user["email"])
    _store_session(user["id"], token)
    user_data = {k: v for k, v in user.items() if k != "password_hash"}
    return {"user": user_data, "token": token}


def get_user_by_id(user_id: int) -> dict | None:
    with get_cursor() as cur:
        cur.execute("SELECT id, email, display_name, created_at FROM users WHERE id = %s", (user_id,))
        return cur.fetchone()


def logout(token: str):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with get_cursor() as cur:
        cur.execute("DELETE FROM user_sessions WHERE token_hash = %s", (token_hash,))


def _store_session(user_id: int, token: str):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS)
    with get_cursor() as cur:
        cur.execute(
            "DELETE FROM user_sessions WHERE user_id = %s AND expires_at < NOW()",
            (user_id,),
        )
        cur.execute(
            "INSERT INTO user_sessions (user_id, token_hash, expires_at) VALUES (%s, %s, %s)",
            (user_id, token_hash, expires),
        )
