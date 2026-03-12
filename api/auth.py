"""
JWT authentication utilities for the FastAPI REST API.

Secret key is auto-generated and stored in ~/.fin/jwt_secret.key.
"""

import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from jose import JWTError, jwt

from config.settings import CONFIG_DIR

# JWT configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 30

_JWT_SECRET_FILE = CONFIG_DIR / "jwt_secret.key"


def _get_or_create_secret() -> str:
    """Load JWT secret from disk, generating one if not present."""
    if _JWT_SECRET_FILE.exists():
        return _JWT_SECRET_FILE.read_text().strip()

    _JWT_SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    secret = secrets.token_hex(32)
    _JWT_SECRET_FILE.write_text(secret)
    _JWT_SECRET_FILE.chmod(0o600)
    return secret


SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or _get_or_create_secret()


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {"sub": subject, "exp": expire, "type": "access"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(subject: str) -> str:
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str, token_type: str = "access") -> Optional[str]:
    """
    Decode and validate JWT token.
    Returns subject (username) or None if invalid.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != token_type:
            return None
        return payload.get("sub")
    except JWTError:
        return None
