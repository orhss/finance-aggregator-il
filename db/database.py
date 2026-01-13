"""
Database connection and session management
"""

import os
from pathlib import Path
from typing import Generator
import logging
from sqlalchemy import create_engine, event, text, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Base

logger = logging.getLogger(__name__)

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


def get_session(db_path: Path = DEFAULT_DB_PATH) -> Session:
    """
    Get a new database session (alias for SessionLocal for convenience)

    Args:
        db_path: Path to SQLite database file

    Returns:
        SQLAlchemy Session instance
    """
    return SessionLocal(db_path)


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


def get_db_path() -> Path:
    """
    Get the database file path

    Returns:
        Path to the database file
    """
    return DEFAULT_DB_PATH


def migrate_tags_schema(db_path: Path = DEFAULT_DB_PATH) -> dict:
    """
    Migrate database schema to add tagging support.
    Safe to run multiple times (idempotent).

    Adds:
    - user_category column to transactions table
    - tags table
    - transaction_tags table

    Args:
        db_path: Path to SQLite database file

    Returns:
        Dict with migration results: {added_columns: [], created_tables: []}
    """
    engine = get_engine(db_path)
    results = {"added_columns": [], "created_tables": []}

    with engine.connect() as conn:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        # Add user_category column to transactions if needed
        if 'transactions' in existing_tables:
            cols = {c['name'] for c in inspector.get_columns('transactions')}
            if 'user_category' not in cols:
                conn.execute(text("ALTER TABLE transactions ADD COLUMN user_category VARCHAR(100)"))
                results["added_columns"].append("transactions.user_category")
                logger.info("Added user_category column to transactions")

        # Create tags table if not exists
        if 'tags' not in existing_tables:
            conn.execute(text("""
                CREATE TABLE tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            results["created_tables"].append("tags")
            logger.info("Created tags table")

        # Create transaction_tags table if not exists
        if 'transaction_tags' not in existing_tables:
            conn.execute(text("""
                CREATE TABLE transaction_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
                    UNIQUE(transaction_id, tag_id)
                )
            """))
            conn.execute(text("CREATE INDEX idx_transaction_tags_transaction ON transaction_tags(transaction_id)"))
            conn.execute(text("CREATE INDEX idx_transaction_tags_tag ON transaction_tags(tag_id)"))
            results["created_tables"].append("transaction_tags")
            logger.info("Created transaction_tags table")

        conn.commit()

    if results["added_columns"] or results["created_tables"]:
        logger.info(f"Migration completed: {results}")
    else:
        logger.info("Database already up to date")

    return results