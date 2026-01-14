"""
Add performance indexes for UI queries.

This migration adds database indexes to optimize frequently used queries
in the Streamlit UI, particularly for filtering and sorting operations.
"""

from sqlalchemy import text
from db.database import get_session


# Index definitions
INDEXES = [
    # Transaction table indexes
    {
        'name': 'idx_transactions_date',
        'sql': 'CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date DESC)'
    },
    {
        'name': 'idx_transactions_status',
        'sql': 'CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)'
    },
    {
        'name': 'idx_transactions_category',
        'sql': 'CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category)'
    },
    {
        'name': 'idx_transactions_user_category',
        'sql': 'CREATE INDEX IF NOT EXISTS idx_transactions_user_category ON transactions(user_category)'
    },
    {
        'name': 'idx_transactions_account',
        'sql': 'CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id)'
    },
    {
        'name': 'idx_transactions_date_account',
        'sql': 'CREATE INDEX IF NOT EXISTS idx_transactions_date_account ON transactions(transaction_date DESC, account_id)'
    },
    {
        'name': 'idx_transactions_date_status',
        'sql': 'CREATE INDEX IF NOT EXISTS idx_transactions_date_status ON transactions(transaction_date DESC, status)'
    },
    {
        'name': 'idx_transactions_created_at',
        'sql': 'CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at DESC)'
    },

    # Balance table indexes
    {
        'name': 'idx_balances_date',
        'sql': 'CREATE INDEX IF NOT EXISTS idx_balances_date ON balances(balance_date DESC)'
    },
    {
        'name': 'idx_balances_account_date',
        'sql': 'CREATE INDEX IF NOT EXISTS idx_balances_account_date ON balances(account_id, balance_date DESC)'
    },

    # Account table indexes
    {
        'name': 'idx_accounts_institution',
        'sql': 'CREATE INDEX IF NOT EXISTS idx_accounts_institution ON accounts(institution)'
    },
    {
        'name': 'idx_accounts_type',
        'sql': 'CREATE INDEX IF NOT EXISTS idx_accounts_type ON accounts(account_type)'
    },
    {
        'name': 'idx_accounts_active',
        'sql': 'CREATE INDEX IF NOT EXISTS idx_accounts_active ON accounts(is_active)'
    },

    # Tag table indexes (for transaction_tags join performance)
    {
        'name': 'idx_transaction_tags_transaction',
        'sql': 'CREATE INDEX IF NOT EXISTS idx_transaction_tags_transaction ON transaction_tags(transaction_id)'
    },
    {
        'name': 'idx_transaction_tags_tag',
        'sql': 'CREATE INDEX IF NOT EXISTS idx_transaction_tags_tag ON transaction_tags(tag_id)'
    },
]


def run_migration(session=None):
    """
    Apply all performance indexes to the database.

    Args:
        session: Optional SQLAlchemy session (creates new one if not provided)

    Returns:
        Number of indexes created
    """
    should_close = False
    if session is None:
        session = get_session()
        should_close = True

    try:
        created_count = 0

        for idx_def in INDEXES:
            try:
                session.execute(text(idx_def['sql']))
                print(f"✓ Created index: {idx_def['name']}")
                created_count += 1
            except Exception as e:
                print(f"✗ Failed to create index {idx_def['name']}: {str(e)}")

        session.commit()
        print(f"\n✓ Migration complete: {created_count}/{len(INDEXES)} indexes created")
        return created_count

    except Exception as e:
        session.rollback()
        print(f"✗ Migration failed: {str(e)}")
        raise

    finally:
        if should_close:
            session.close()


def rollback_migration(session=None):
    """
    Remove all indexes created by this migration.

    Args:
        session: Optional SQLAlchemy session (creates new one if not provided)

    Returns:
        Number of indexes dropped
    """
    should_close = False
    if session is None:
        session = get_session()
        should_close = True

    try:
        dropped_count = 0

        for idx_def in INDEXES:
            try:
                drop_sql = f"DROP INDEX IF EXISTS {idx_def['name']}"
                session.execute(text(drop_sql))
                print(f"✓ Dropped index: {idx_def['name']}")
                dropped_count += 1
            except Exception as e:
                print(f"✗ Failed to drop index {idx_def['name']}: {str(e)}")

        session.commit()
        print(f"\n✓ Rollback complete: {dropped_count}/{len(INDEXES)} indexes dropped")
        return dropped_count

    except Exception as e:
        session.rollback()
        print(f"✗ Rollback failed: {str(e)}")
        raise

    finally:
        if should_close:
            session.close()


def check_indexes(session=None):
    """
    Check which indexes exist in the database.

    Args:
        session: Optional SQLAlchemy session (creates new one if not provided)

    Returns:
        List of existing index names
    """
    should_close = False
    if session is None:
        session = get_session()
        should_close = True

    try:
        # Query SQLite system table for indexes
        result = session.execute(text(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        ))

        existing = [row[0] for row in result]

        print("Existing indexes:")
        for idx_name in existing:
            status = "✓" if idx_name in [idx['name'] for idx in INDEXES] else "?"
            print(f"  {status} {idx_name}")

        missing = [idx['name'] for idx in INDEXES if idx['name'] not in existing]
        if missing:
            print("\nMissing indexes:")
            for idx_name in missing:
                print(f"  ✗ {idx_name}")

        return existing

    finally:
        if should_close:
            session.close()


if __name__ == '__main__':
    """Run migration when executed as a script."""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'rollback':
        print("Rolling back migration...")
        rollback_migration()
    elif len(sys.argv) > 1 and sys.argv[1] == 'check':
        print("Checking indexes...")
        check_indexes()
    else:
        print("Running migration...")
        run_migration()
