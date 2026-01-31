"""
Integration test fixtures for Fin project.

Provides CLI test runner, database session with patched SessionLocal,
and mocked scrapers for testing full command flows.
"""

import pytest
from datetime import datetime, date
from typing import List
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from db.models import Base, Account, Transaction, SyncHistory, CategoryMapping
from scrapers.credit_cards.cal_credit_card_client import (
    Transaction as CALTransaction,
    CardAccount,
    TransactionStatus,
    TransactionType,
    Installments,
)


# ==================== CLI Runner ====================

@pytest.fixture
def cli_runner():
    """Typer CLI test runner with isolated environment."""
    return CliRunner()


# ==================== Database Fixtures ====================

@pytest.fixture
def integration_db_engine():
    """Create isolated in-memory SQLite database for integration tests."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def integration_db_session(integration_db_engine):
    """Create a database session for integration testing."""
    Session = sessionmaker(bind=integration_db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def patched_session_local(integration_db_session):
    """
    Patch SessionLocal to return our test session.
    This ensures CLI commands use the test database.
    """
    with patch("db.database.SessionLocal") as mock_session_local:
        mock_session_local.return_value = integration_db_session
        yield mock_session_local


@pytest.fixture
def patched_db_exists():
    """Patch database existence check to return True."""
    with patch("db.database.check_database_exists", return_value=True):
        yield


# ==================== Sample Data Builders ====================

def build_cal_transaction(
    description: str = "WOLT DELIVERY",
    amount: float = 50.0,
    category: str = "מזון",
    status: TransactionStatus = TransactionStatus.COMPLETED,
    transaction_date: str = None,
) -> CALTransaction:
    """Build a CAL transaction for mocking scraper responses."""
    if transaction_date is None:
        transaction_date = datetime.now().isoformat()

    return CALTransaction(
        date=transaction_date,
        processed_date=transaction_date,
        original_amount=-amount,  # Negative for debit
        original_currency="ILS",
        charged_amount=-amount,
        charged_currency="ILS",
        description=description,
        status=status,
        transaction_type=TransactionType.NORMAL,
        identifier=f"TXN-{hash(description) % 100000}" if status == TransactionStatus.COMPLETED else None,
        memo="",
        category=category,
        installments=None,
    )


def build_card_account(
    account_number: str = "1234",
    card_unique_id: str = "CAL-CARD-123",
    transactions: List[CALTransaction] = None,
) -> CardAccount:
    """Build a CardAccount for mocking scraper responses."""
    if transactions is None:
        transactions = [
            build_cal_transaction("WOLT DELIVERY", 50.0, "מזון"),
            build_cal_transaction("NETFLIX", 49.90, "בידור"),
        ]
    return CardAccount(
        account_number=account_number,
        card_unique_id=card_unique_id,
        transactions=transactions,
    )


# ==================== Mock Scraper Fixtures ====================

@pytest.fixture
def mock_cal_scraper():
    """
    Mock CAL scraper to return fake transactions.

    Returns transactions without hitting the actual CAL website.
    """
    with patch("services.credit_card_service.CALCreditCardScraper") as mock_cls:
        scraper_instance = MagicMock()
        scraper_instance.scrape.return_value = [
            build_card_account(
                account_number="1234",
                card_unique_id="CAL-CARD-123",
                transactions=[
                    build_cal_transaction("WOLT DELIVERY", 50.0, "מזון"),
                    build_cal_transaction("NETFLIX", 49.90, "בידור"),
                    build_cal_transaction("SUPERMARKET", 200.0, "סופרמרקט"),
                ],
            )
        ]
        mock_cls.return_value = scraper_instance
        yield mock_cls


@pytest.fixture
def mock_cal_scraper_multi_card():
    """Mock CAL scraper with multiple cards."""
    with patch("services.credit_card_service.CALCreditCardScraper") as mock_cls:
        scraper_instance = MagicMock()
        scraper_instance.scrape.return_value = [
            build_card_account(
                account_number="1234",
                card_unique_id="CAL-CARD-123",
                transactions=[
                    build_cal_transaction("WOLT DELIVERY", 50.0, "מזון"),
                ],
            ),
            build_card_account(
                account_number="5678",
                card_unique_id="CAL-CARD-456",
                transactions=[
                    build_cal_transaction("AMAZON", 150.0, "קניות"),
                ],
            ),
        ]
        mock_cls.return_value = scraper_instance
        yield mock_cls


@pytest.fixture
def mock_cal_scraper_empty():
    """Mock CAL scraper that returns no cards."""
    with patch("services.credit_card_service.CALCreditCardScraper") as mock_cls:
        scraper_instance = MagicMock()
        scraper_instance.scrape.return_value = []
        mock_cls.return_value = scraper_instance
        yield mock_cls


@pytest.fixture
def mock_cal_scraper_error():
    """Mock CAL scraper that raises an error."""
    with patch("services.credit_card_service.CALCreditCardScraper") as mock_cls:
        scraper_instance = MagicMock()
        scraper_instance.scrape.side_effect = Exception("Login failed: Invalid credentials")
        mock_cls.return_value = scraper_instance
        yield mock_cls


@pytest.fixture
def mock_max_scraper():
    """Mock Max scraper to return fake transactions."""
    with patch("services.credit_card_service.MaxCreditCardScraper") as mock_cls:
        scraper_instance = MagicMock()
        scraper_instance.scrape.return_value = [
            build_card_account(
                account_number="9999",
                card_unique_id=None,
                transactions=[
                    build_cal_transaction("CAFE NERO", 35.0, "מסעדות"),
                    build_cal_transaction("IKEA", 500.0, "ריהוט"),
                ],
            )
        ]
        mock_cls.return_value = scraper_instance
        yield mock_cls


@pytest.fixture
def mock_isracard_scraper():
    """Mock Isracard scraper to return fake transactions (no categories)."""
    with patch("services.credit_card_service.IsracardCreditCardScraper") as mock_cls:
        scraper_instance = MagicMock()
        scraper_instance.scrape.return_value = [
            build_card_account(
                account_number="7777",
                card_unique_id=None,
                transactions=[
                    build_cal_transaction("GOOGLE PLAY", 29.90, None),  # Isracard doesn't provide categories
                    build_cal_transaction("SPOTIFY", 19.90, None),
                ],
            )
        ]
        mock_cls.return_value = scraper_instance
        yield mock_cls


# ==================== Mock Credentials ====================

@pytest.fixture
def mock_credentials():
    """
    Mock credentials loading to return test credentials.

    Note: Uses List format for multi-account support.
    """
    with patch("config.settings.load_credentials") as mock_load:
        credentials = MagicMock()

        # Credit cards as lists (multi-account support)
        cal_account = MagicMock()
        cal_account.username = "test_user"
        cal_account.password = "test_pass"
        cal_account.label = None
        credentials.cal = [cal_account]

        max_account = MagicMock()
        max_account.username = "max_user"
        max_account.password = "max_pass"
        max_account.label = None
        credentials.max = [max_account]

        isracard_account = MagicMock()
        isracard_account.username = "123456789:123456"
        isracard_account.password = "isracard_pass"
        isracard_account.label = None
        credentials.isracard = [isracard_account]

        # Brokers
        credentials.excellence = MagicMock(username="", password="")
        credentials.meitav = MagicMock(username="", password="")

        # Pensions
        credentials.migdal = []
        credentials.phoenix = []

        # Email
        credentials.email = MagicMock(address="test@test.com", password="email_pass")

        mock_load.return_value = credentials
        yield mock_load


@pytest.fixture
def mock_credentials_empty():
    """Mock credentials with no configured accounts."""
    with patch("config.settings.load_credentials") as mock_load:
        credentials = MagicMock()
        credentials.cal = []
        credentials.max = []
        credentials.isracard = []
        credentials.excellence = MagicMock(username="", password="")
        credentials.meitav = MagicMock(username="", password="")
        credentials.migdal = []
        credentials.phoenix = []
        credentials.email = MagicMock(address="", password="")
        mock_load.return_value = credentials
        yield mock_load


@pytest.fixture
def mock_select_accounts():
    """Mock account selection for sync commands."""
    with patch("config.settings.select_accounts_to_sync") as mock_select:
        def select_accounts(institution, filters=None):
            account = MagicMock()
            account.username = "test_user"
            account.password = "test_pass"
            account.label = None
            return [(0, account)]

        mock_select.side_effect = select_accounts
        yield mock_select


# ==================== Test Data Factory Functions ====================

def create_test_account(
    session: Session,
    account_type: str = "credit_card",
    institution: str = "cal",
    account_number: str = "1234",
    account_name: str = None,
) -> Account:
    """Factory function to create a test account."""
    account = Account(
        account_type=account_type,
        institution=institution,
        account_number=account_number,
        account_name=account_name or f"{institution.upper()} Test Account",
        last_synced_at=datetime.utcnow(),
    )
    session.add(account)
    session.commit()
    return account


def create_test_transaction(
    session: Session,
    account: Account,
    description: str = "Test Transaction",
    amount: float = 100.0,
    raw_category: str = None,
    category: str = None,
    user_category: str = None,
    transaction_date: date = None,
    status: str = "completed",
) -> Transaction:
    """Factory function to create a test transaction."""
    txn = Transaction(
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
    session.add(txn)
    session.commit()
    return txn


def create_test_category_mapping(
    session: Session,
    provider: str,
    raw_category: str,
    unified_category: str,
) -> CategoryMapping:
    """Factory function to create a category mapping."""
    mapping = CategoryMapping(
        provider=provider,
        raw_category=raw_category,
        unified_category=unified_category,
    )
    session.add(mapping)
    session.commit()
    return mapping


def create_test_sync_history(
    session: Session,
    sync_type: str = "credit_card",
    institution: str = "cal",
    status: str = "success",
) -> SyncHistory:
    """Factory function to create a sync history record."""
    history = SyncHistory(
        sync_type=sync_type,
        institution=institution,
        status=status,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )
    session.add(history)
    session.commit()
    return history
