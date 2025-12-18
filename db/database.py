"""
Database connection and session management
"""

import os
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Base

# Database file location - store in user's home directory or project root
DEFAULT_DB_PATH = Path.home() / ".fin" / "financial_data.db"


def get_database_url(db_path: Path = DEFAULT_DB_PATH) -> str:
    """
    Get SQLite database URL

    Args:
        db_path: Path to SQLite database file

    Returns:
        SQLite connection URL
    """
    return f"sqlite:///{db_path}"


def enable_foreign_keys(dbapi_conn, connection_record):
    """Enable foreign key constraints for SQLite"""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_database_engine(db_path: Path = DEFAULT_DB_PATH):
    """
    Create SQLAlchemy engine

    Args:
        db_path: Path to SQLite database file

    Returns:
        SQLAlchemy Engine instance
    """
    # Ensure directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    database_url = get_database_url(db_path)
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},  # Needed for SQLite
        echo=False  # Set to True for SQL debugging
    )

    # Enable foreign keys for SQLite
    event.listen(engine, "connect", enable_foreign_keys)

    return engine


def init_db(db_path: Path = DEFAULT_DB_PATH) -> Engine:
    """
    Initialize database by creating all tables

    Args:
        db_path: Path to SQLite database file

    Returns:
        SQLAlchemy Engine instance
    """
    engine = create_database_engine(db_path)
    Base.metadata.create_all(bind=engine)
    return engine


def drop_all_tables(db_path: Path = DEFAULT_DB_PATH):
    """
    Drop all tables (use with caution!)

    Args:
        db_path: Path to SQLite database file
    """
    engine = create_database_engine(db_path)
    Base.metadata.drop_all(bind=engine)


# Global session factory
_engine = None
_SessionLocal = None


def get_engine(db_path: Path = DEFAULT_DB_PATH) -> Engine:
    """Get or create global database engine"""
    global _engine
    if _engine is None:
        _engine = create_database_engine(db_path)
    return _engine


def get_session_factory(db_path: Path = DEFAULT_DB_PATH):
    """Get or create global session factory"""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine(db_path)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def SessionLocal(db_path: Path = DEFAULT_DB_PATH) -> Session:
    """
    Create a new database session

    Args:
        db_path: Path to SQLite database file

    Returns:
        SQLAlchemy Session instance
    """
    factory = get_session_factory(db_path)
    return factory()


def get_db(db_path: Path = DEFAULT_DB_PATH) -> Generator[Session, None, None]:
    """
    Dependency for getting database session (for use with FastAPI/CLI)

    Usage:
        with get_db() as db:
            # Use db session
            pass

    Args:
        db_path: Path to SQLite database file

    Yields:
        SQLAlchemy Session instance
    """
    db = SessionLocal(db_path)
    try:
        yield db
    finally:
        db.close()


def check_database_exists(db_path: Path = DEFAULT_DB_PATH) -> bool:
    """
    Check if database file exists

    Args:
        db_path: Path to SQLite database file

    Returns:
        True if database file exists, False otherwise
    """
    return db_path.exists()