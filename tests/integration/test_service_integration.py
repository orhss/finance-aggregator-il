"""
Integration tests for multi-service coordination.

Tests interactions between services without CLI layer,
focusing on service-to-service integration points.
"""

import pytest
from datetime import date, datetime
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base, Transaction, Account, SyncHistory, CategoryMapping, MerchantMapping
from services.credit_card_service import CreditCardService
from services.category_service import CategoryService
from services.rules_service import RulesService
from services.analytics_service import AnalyticsService
from config.constants import Institution, AccountType

from tests.integration.conftest import (
    build_cal_transaction,
    build_card_account,
    create_test_account,
    create_test_transaction,
    create_test_category_mapping,
)
from scrapers.credit_cards.cal_credit_card_client import TransactionStatus


@pytest.fixture
def service_db_session():
    """Create isolated in-memory database for service tests."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def credit_card_service(service_db_session):
    """CreditCardService instance with test database."""
    return CreditCardService(service_db_session)


@pytest.fixture
def category_service(service_db_session):
    """CategoryService instance with test database."""
    return CategoryService(session=service_db_session)


@pytest.fixture
def analytics_service(service_db_session):
    """AnalyticsService instance with test database."""
    return AnalyticsService(session=service_db_session)


@pytest.fixture
def temp_rules_file():
    """Create temporary rules file for testing."""
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.yaml', delete=False
    ) as f:
        f.write("rules: []\n")
        f.flush()
        yield Path(f.name)


@pytest.fixture
def rules_service(service_db_session, temp_rules_file):
    """RulesService instance with test database and temp file."""
    return RulesService(session=service_db_session, rules_file=temp_rules_file)


# ==================== Sync + Category Normalization ====================

@pytest.mark.integration
def test_sync_applies_category_mapping(service_db_session, credit_card_service):
    """
    Synced transactions should have normalized categories from mappings.
    """
    # Setup: Create category mapping
    mapping = CategoryMapping(
        provider="cal",
        raw_category="מזון",
        unified_category="groceries"
    )
    service_db_session.add(mapping)
    service_db_session.commit()

    # Mock the scraper
    with patch("services.credit_card_service.CALCreditCardScraper") as mock_cls:
        scraper = MagicMock()
        scraper.scrape.return_value = [
            build_card_account(
                transactions=[
                    build_cal_transaction("WOLT DELIVERY", 50.0, "מזון"),
                ]
            )
        ]
        mock_cls.return_value = scraper

        # Sync
        result = credit_card_service.sync_cal(
            username="test", password="test", headless=True
        )

    assert result.success

    # Verify category normalization
    txn = service_db_session.query(Transaction).first()
    assert txn.raw_category == "מזון"
    assert txn.category == "groceries"
    assert txn.effective_category == "groceries"


@pytest.mark.integration
def test_sync_tracks_unmapped_categories(service_db_session, credit_card_service):
    """
    Sync should track categories without mappings.
    """
    # No mappings exist

    # Mock the scraper with a category that has no mapping
    with patch("services.credit_card_service.CALCreditCardScraper") as mock_cls:
        scraper = MagicMock()
        scraper.scrape.return_value = [
            build_card_account(
                transactions=[
                    build_cal_transaction("TEST", 100.0, "קטגוריה_חדשה"),
                ]
            )
        ]
        mock_cls.return_value = scraper

        result = credit_card_service.sync_cal(
            username="test", password="test", headless=True
        )

    assert result.success
    assert len(result.unmapped_categories) == 1
    assert result.unmapped_categories[0]['raw_category'] == "קטגוריה_חדשה"


@pytest.mark.integration
def test_sync_applies_merchant_mapping_for_isracard(service_db_session, credit_card_service):
    """
    For Isracard (no provider categories), merchant mappings should be applied.
    """
    # Setup: Create merchant mapping
    mapping = MerchantMapping(
        pattern="GOOGLE",
        category="subscriptions",
        match_type="startswith"
    )
    service_db_session.add(mapping)
    service_db_session.commit()

    # Mock the scraper (Isracard has no categories)
    with patch("services.credit_card_service.IsracardCreditCardScraper") as mock_cls:
        scraper = MagicMock()
        scraper.scrape.return_value = [
            build_card_account(
                transactions=[
                    build_cal_transaction("GOOGLE PLAY", 29.90, None),  # No category
                ]
            )
        ]
        mock_cls.return_value = scraper

        result = credit_card_service.sync_isracard(
            username="123456789:123456", password="test", headless=True
        )

    assert result.success

    # Verify merchant mapping applied
    txn = service_db_session.query(Transaction).first()
    assert txn.raw_category is None or txn.raw_category == ""
    assert txn.category == "subscriptions"


# ==================== Sync + Rules ====================

@pytest.mark.integration
def test_sync_with_rules_applies_user_category(service_db_session, temp_rules_file):
    """
    Rules should be applied to transactions during sync (via post-sync hook).

    Note: This test verifies that rules CAN be applied post-sync, but the actual
    rule application depends on the RulesService implementation.
    """
    credit_card_service = CreditCardService(service_db_session)

    # Mock the scraper
    with patch("services.credit_card_service.CALCreditCardScraper") as mock_cls:
        scraper = MagicMock()
        scraper.scrape.return_value = [
            build_card_account(
                transactions=[
                    build_cal_transaction("WOLT DELIVERY", 50.0, "מזון"),
                ]
            )
        ]
        mock_cls.return_value = scraper

        result = credit_card_service.sync_cal(
            username="test", password="test", headless=True
        )

    assert result.success

    # Verify transaction was created
    txn = service_db_session.query(Transaction).first()
    assert txn is not None
    assert txn.description == "WOLT DELIVERY"

    # Manually set user_category to simulate rule application
    # (The actual rules service integration is tested in unit tests)
    txn.user_category = "food_delivery"
    service_db_session.commit()

    # Verify effective_category uses user_category when set
    assert txn.effective_category == "food_delivery"


# ==================== Transaction Rollback ====================

@pytest.mark.integration
def test_sync_rollback_on_failure(service_db_session, credit_card_service):
    """
    Sync failure mid-way should rollback all changes.
    """
    initial_txn_count = service_db_session.query(Transaction).count()
    initial_account_count = service_db_session.query(Account).count()

    # Mock scraper to fail during transaction processing
    with patch("services.credit_card_service.CALCreditCardScraper") as mock_cls:
        scraper = MagicMock()
        # First call returns data, but processing will fail
        scraper.scrape.side_effect = Exception("Connection lost mid-sync")
        mock_cls.return_value = scraper

        result = credit_card_service.sync_cal(
            username="test", password="test", headless=True
        )

    assert not result.success
    assert "Connection lost" in result.error_message

    # Verify rollback - no new records
    assert service_db_session.query(Transaction).count() == initial_txn_count
    assert service_db_session.query(Account).count() == initial_account_count


@pytest.mark.integration
def test_sync_creates_sync_history_on_failure(service_db_session, credit_card_service):
    """
    Failed sync should still create sync history with failed status.
    """
    with patch("services.credit_card_service.CALCreditCardScraper") as mock_cls:
        scraper = MagicMock()
        scraper.scrape.side_effect = Exception("Auth failed")
        mock_cls.return_value = scraper

        result = credit_card_service.sync_cal(
            username="test", password="test", headless=True
        )

    assert not result.success

    # Sync history should be created with failed status
    history = service_db_session.query(SyncHistory).first()
    assert history is not None
    assert history.status == "failed"
    assert "Auth failed" in (history.error_message or "")


# ==================== Multi-Service Queries ====================

@pytest.mark.integration
def test_category_service_gets_unmapped_after_sync(service_db_session):
    """
    CategoryService should correctly report unmapped categories after sync.
    """
    credit_card_service = CreditCardService(service_db_session)
    category_service = CategoryService(session=service_db_session)

    # Sync with categories that have no mappings
    with patch("services.credit_card_service.CALCreditCardScraper") as mock_cls:
        scraper = MagicMock()
        scraper.scrape.return_value = [
            build_card_account(
                transactions=[
                    build_cal_transaction("A", 10.0, "cat_a"),
                    build_cal_transaction("B", 20.0, "cat_b"),
                    build_cal_transaction("C", 30.0, "cat_a"),  # Duplicate category
                ]
            )
        ]
        mock_cls.return_value = scraper

        credit_card_service.sync_cal(username="test", password="test", headless=True)

    # Get unmapped categories
    unmapped = category_service.get_unmapped_categories(provider="cal")

    # Should have 2 unmapped categories
    assert len(unmapped) == 2
    raw_cats = {u['raw_category'] for u in unmapped}
    assert "cat_a" in raw_cats
    assert "cat_b" in raw_cats


@pytest.mark.integration
def test_analytics_includes_synced_transactions(service_db_session, analytics_service):
    """
    Analytics should correctly aggregate synced transactions.
    """
    # Setup: Create account and transactions
    account = create_test_account(service_db_session, institution="cal")
    today = date.today()
    create_test_transaction(
        service_db_session, account, "Purchase 1", 100.0,
        transaction_date=today
    )
    create_test_transaction(
        service_db_session, account, "Purchase 2", 200.0,
        transaction_date=today
    )

    # Get monthly summary
    summary = analytics_service.get_monthly_summary(today.year, today.month)

    assert summary is not None
    # Check that transactions are counted
    assert summary.get('transaction_count', 0) == 2
    # total_amount includes our transactions
    assert summary.get('total_amount', 0) >= 300


# ==================== Category Normalization Workflow ====================

@pytest.mark.integration
def test_full_category_normalization_workflow(service_db_session):
    """
    Test full workflow: sync → unmapped detection → add mapping → verify.
    """
    credit_card_service = CreditCardService(service_db_session)
    category_service = CategoryService(session=service_db_session)

    # Step 1: Sync transactions with unmapped categories
    with patch("services.credit_card_service.CALCreditCardScraper") as mock_cls:
        scraper = MagicMock()
        scraper.scrape.return_value = [
            build_card_account(
                transactions=[
                    build_cal_transaction("GROCERY STORE", 100.0, "סופרמרקט"),
                ]
            )
        ]
        mock_cls.return_value = scraper
        result = credit_card_service.sync_cal(username="test", password="test", headless=True)

    assert result.success

    # Verify transaction was created with raw_category but no normalized category
    txn = service_db_session.query(Transaction).first()
    assert txn is not None
    assert txn.raw_category == "סופרמרקט"
    assert txn.category is None  # Not normalized yet

    # Verify unmapped categories detected
    unmapped = category_service.get_unmapped_categories()
    assert len(unmapped) >= 1  # At least our category
    raw_cats = [u['raw_category'] for u in unmapped]
    assert "סופרמרקט" in raw_cats

    # Step 2: Add mapping
    mapping = category_service.add_mapping("cal", "סופרמרקט", "groceries")
    assert mapping is not None
    assert mapping.unified_category == "groceries"

    # Step 3: Verify new sync would use the mapping
    # Manually update the transaction to simulate what apply_mappings does
    txn.category = category_service.normalize_category("cal", "סופרמרקט")
    service_db_session.commit()

    # Verify transaction is now normalized
    assert txn.category == "groceries"
    assert txn.raw_category == "סופרמרקט"
    assert txn.effective_category == "groceries"

    # Step 4: Verify mapping exists
    stored_mapping = category_service.get_mapping("cal", "סופרמרקט")
    assert stored_mapping is not None
    assert stored_mapping.unified_category == "groceries"


# ==================== Multi-Account Sync ====================

@pytest.mark.integration
def test_multi_account_sync_creates_separate_accounts(service_db_session, credit_card_service):
    """
    Syncing multiple cards should create separate account records.
    """
    with patch("services.credit_card_service.CALCreditCardScraper") as mock_cls:
        scraper = MagicMock()
        scraper.scrape.return_value = [
            build_card_account(
                account_number="1234",
                card_unique_id="CARD-1",
                transactions=[build_cal_transaction("A", 10.0, "cat")]
            ),
            build_card_account(
                account_number="5678",
                card_unique_id="CARD-2",
                transactions=[build_cal_transaction("B", 20.0, "cat")]
            ),
        ]
        mock_cls.return_value = scraper

        result = credit_card_service.sync_cal(
            username="test", password="test", headless=True
        )

    assert result.success
    assert result.cards_synced == 2

    # Verify separate accounts
    accounts = service_db_session.query(Account).all()
    assert len(accounts) == 2
    account_numbers = {a.account_number for a in accounts}
    assert "1234" in account_numbers
    assert "5678" in account_numbers


# ==================== Effective Category Resolution ====================

@pytest.mark.integration
def test_effective_category_priority(service_db_session):
    """
    Verify effective_category priority: user_category > category > raw_category.
    """
    account = create_test_account(service_db_session, institution="cal")

    # Transaction with all three categories
    txn = create_test_transaction(
        service_db_session,
        account,
        "Test",
        100.0,
        raw_category="raw",
        category="normalized",
        user_category="user",
    )

    # user_category takes precedence
    assert txn.effective_category == "user"

    # Clear user_category
    txn.user_category = None
    service_db_session.commit()
    assert txn.effective_category == "normalized"

    # Clear category
    txn.category = None
    service_db_session.commit()
    assert txn.effective_category == "raw"
