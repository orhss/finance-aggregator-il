"""
FastAPI dependency injection.

Provides DB sessions and service instances, JWT auth guard.
"""

from typing import Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from db.database import get_db as _get_db
from sqlalchemy.orm import Session

from api.auth import decode_token
from config.settings import is_auth_enabled

_bearer = HTTPBearer(auto_error=False)


# ==================== Database ====================

def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session, closing it after the request."""
    yield from _get_db()


# ==================== Auth ====================

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Optional[str]:
    """
    Return the authenticated username.

    If auth is disabled globally (via fin-cli auth disable), always returns "anonymous".
    Otherwise validates the Bearer JWT token.
    """
    if not is_auth_enabled():
        return "anonymous"

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = decode_token(credentials.credentials, token_type="access")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username


CurrentUser = Depends(get_current_user)


# ==================== Service factories ====================

def get_analytics(db: Session = Depends(get_db)):
    from services.analytics_service import AnalyticsService
    return AnalyticsService(session=db)


def get_budget_service(db: Session = Depends(get_db)):
    from services.budget_service import BudgetService
    return BudgetService(session=db)


def get_tag_service(db: Session = Depends(get_db)):
    from services.tag_service import TagService
    return TagService(session=db)


def get_category_service(db: Session = Depends(get_db)):
    from services.category_service import CategoryService
    return CategoryService(session=db)


def get_rules_service(db: Session = Depends(get_db)):
    from services.rules_service import RulesService
    return RulesService(session=db)
