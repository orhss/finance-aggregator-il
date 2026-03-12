"""Auth endpoints: login, refresh."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.auth import create_access_token, create_refresh_token, decode_token
from api.deps import get_db
from api.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from config.settings import is_auth_enabled, load_auth_users

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user. Returns JWT access + refresh tokens.

    If auth is disabled, any credentials succeed (useful for dev).
    """
    if not is_auth_enabled():
        # Auth disabled — issue a token for "anonymous"
        return TokenResponse(
            access_token=create_access_token("anonymous"),
            refresh_token=create_refresh_token("anonymous"),
        )

    users = load_auth_users()
    user_data = users.get(body.username)

    if not user_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # streamlit-authenticator stores bcrypt hashes under credentials.usernames.<user>.password
    import bcrypt

    stored_hash = user_data.get("password", "")
    try:
        valid = bcrypt.checkpw(body.password.encode(), stored_hash.encode())
    except Exception:
        valid = False

    if not valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return TokenResponse(
        access_token=create_access_token(body.username),
        refresh_token=create_refresh_token(body.username),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest):
    """Exchange a refresh token for a new access token."""
    username = decode_token(body.refresh_token, token_type="refresh")
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    return TokenResponse(
        access_token=create_access_token(username),
        refresh_token=create_refresh_token(username),
    )


@router.get("/status")
def auth_status():
    """Return whether authentication is enabled."""
    return {"auth_enabled": is_auth_enabled()}
