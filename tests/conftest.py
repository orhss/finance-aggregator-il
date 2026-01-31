"""
Pytest fixtures for Fin project tests.

Provides in-memory SQLite database and common test data factories.
"""

import pytest
from datetime import datetime, date
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from db.models import (
    Base,
    Account,
    Transaction,
    Balance,
    CategoryMapping,
    MerchantMapping,
    Tag,
    TransactionTag,
    SyncHistory,
)


@pytest.fixture
def db_engine():
    """Create in-memory SQLite database engine."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """Create a database session for testing."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


# ==================== Account Factories ====================

@pytest.fixture
def sample_account(db_session: Session) -> Account:
    """Create a sample credit card account."""
    account = Account(
        account_type="credit_card",
        institution="cal",
        account_number="1234",
        account_name="Test Card",
        last_synced_at=datetime.utcnow()
    )
    db_session.add(account)
    db_session.commit()
    return account


@pytest.fixture
def sample_accounts(db_session: Session) -> dict:
    """Create sample accounts for different institutions."""
    accounts = {
        "cal": Account(
            account_type="credit_card",
            institution="cal",
            account_number="1234",
            account_name="CAL Card",
            last_synced_at=datetime.utcnow()
        ),
        "max": Account(
            account_type="credit_card",
            institution="max",
            account_number="5678",
            account_name="Max Card",
            last_synced_at=datetime.utcnow()
        ),
        "isracard": Account(
            account_type="credit_card",
            institution="isracard",
            account_number="9012",
            account_name="Isracard",
            last_synced_at=datetime.utcnow()
        ),
    }
    for account in accounts.values():
        db_session.add(account)
    db_session.commit()
    return accounts


def create_account(
    db_session: Session,
    account_type: str = "credit_card",
    institution: str = "cal",
    account_number: str = "1234",
    account_name: Optional[str] = None,
) -> Account:
    """Factory function to create an account."""
    account = Account(
        account_type=account_type,
        institution=institution,
        account_number=account_number,
        account_name=account_name or f"{institution.upper()} Account",
        last_synced_at=datetime.utcnow()
    )
    db_session.add(account)
    db_session.commit()
    return account


# ==================== Transaction Factories ====================

@pytest.fixture
def sample_transaction(db_session: Session, sample_account: Account) -> Transaction:
    """Create a sample transaction."""
    transaction = Transaction(
        account_id=sample_account.id,
        transaction_date=date.today(),
        description="Test Transaction",
        original_amount=100.0,
        original_currency="ILS",
        charged_amount=100.0,
        charged_currency="ILS",
        status="completed",
        raw_category="סופרמרקט",
    )
    db_session.add(transaction)
    db_session.commit()
    return transaction


def create_transaction(
    db_session: Session,
    account: Account,
    description: str = "Test Transaction",
    amount: float = 100.0,
    transaction_date: Optional[date] = None,
    raw_category: Optional[str] = None,
    category: Optional[str] = None,
    user_category: Optional[str] = None,
    status: str = "completed",
) -> Transaction:
    """Factory function to create a transaction."""
    transaction = Transaction(
        account_id=account.id,
        transaction_date=transaction_date or date.today(),
        description=description,
        original_amount=amount,
        original_currency="ILS",
        charged_amount=amount,
        charged_currency="ILS",
        status=status,
        raw_category=raw_category,
        category=category,
        user_category=user_category,
    )
    db_session.add(transaction)
    db_session.commit()
    return transaction


# ==================== Category Mapping Factories ====================

@pytest.fixture
def sample_category_mapping(db_session: Session) -> CategoryMapping:
    """Create a sample category mapping."""
    mapping = CategoryMapping(
        provider="cal",
        raw_category="סופרמרקט",
        unified_category="groceries"
    )
    db_session.add(mapping)
    db_session.commit()
    return mapping


def create_category_mapping(
    db_session: Session,
    provider: str,
    raw_category: str,
    unified_category: str,
) -> CategoryMapping:
    """Factory function to create a category mapping."""
    mapping = CategoryMapping(
        provider=provider,
        raw_category=raw_category,
        unified_category=unified_category
    )
    db_session.add(mapping)
    db_session.commit()
    return mapping


# ==================== Merchant Mapping Factories ====================

@pytest.fixture
def sample_merchant_mapping(db_session: Session) -> MerchantMapping:
    """Create a sample merchant mapping."""
    mapping = MerchantMapping(
        pattern="NETFLIX",
        category="subscriptions",
        match_type="startswith"
    )
    db_session.add(mapping)
    db_session.commit()
    return mapping


def create_merchant_mapping(
    db_session: Session,
    pattern: str,
    category: str,
    provider: Optional[str] = None,
    match_type: str = "startswith",
) -> MerchantMapping:
    """Factory function to create a merchant mapping."""
    mapping = MerchantMapping(
        pattern=pattern,
        category=category,
        provider=provider,
        match_type=match_type
    )
    db_session.add(mapping)
    db_session.commit()
    return mapping


# ==================== Tag Factories ====================

@pytest.fixture
def sample_tag(db_session: Session) -> Tag:
    """Create a sample tag."""
    tag = Tag(name="groceries")
    db_session.add(tag)
    db_session.commit()
    return tag


def create_tag(db_session: Session, name: str) -> Tag:
    """Factory function to create a tag."""
    tag = Tag(name=name)
    db_session.add(tag)
    db_session.commit()
    return tag


def tag_transaction(
    db_session: Session,
    transaction: Transaction,
    tag: Tag,
) -> TransactionTag:
    """Factory function to tag a transaction."""
    txn_tag = TransactionTag(
        transaction_id=transaction.id,
        tag_id=tag.id
    )
    db_session.add(txn_tag)
    db_session.commit()
    return txn_tag


# ==================== Balance Factories ====================

def create_balance(
    db_session: Session,
    account: Account,
    total_amount: float,
    balance_date: Optional[date] = None,
    profit_loss: Optional[float] = None,
    profit_loss_percentage: Optional[float] = None,
) -> Balance:
    """Factory function to create a balance."""
    balance = Balance(
        account_id=account.id,
        balance_date=balance_date or date.today(),
        total_amount=total_amount,
        profit_loss=profit_loss,
        profit_loss_percentage=profit_loss_percentage,
    )
    db_session.add(balance)
    db_session.commit()
    return balance


# ==================== Sync History Factories ====================

def create_sync_history(
    db_session: Session,
    sync_type: str = "credit_card",
    institution: str = "cal",
    status: str = "success",
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
) -> SyncHistory:
    """Factory function to create a sync history record."""
    sync = SyncHistory(
        sync_type=sync_type,
        institution=institution,
        status=status,
        started_at=started_at or datetime.utcnow(),
        completed_at=completed_at or datetime.utcnow(),
    )
    db_session.add(sync)
    db_session.commit()
    return sync
