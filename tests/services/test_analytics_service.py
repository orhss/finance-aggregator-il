"""
Tests for AnalyticsService.

Tests account queries, transaction filtering, balance retrieval,
statistics aggregation, and category/tag breakdowns.
"""

import pytest
from datetime import date, datetime, timedelta

from services.analytics_service import AnalyticsService
from db.models import Account, Transaction, Balance
from tests.conftest import (
    create_account,
    create_transaction,
    create_balance,
    create_tag,
    tag_transaction,
    create_sync_history,
)


# ==================== Fixtures ====================

@pytest.fixture
def analytics_service(db_session):
    """AnalyticsService instance with test database session."""
    return AnalyticsService(session=db_session)


@pytest.fixture
def sample_account(db_session):
    """Create a sample credit card account."""
    return create_account(db_session, institution="cal", account_number="1234")


# ==================== Account Methods ====================

def test_get_all_accounts_empty(analytics_service):
    """Should return empty list when no accounts exist."""
    accounts = analytics_service.get_all_accounts()
    assert accounts == []


def test_get_all_accounts_returns_all(db_session, analytics_service):
    """Should return all active accounts."""
    create_account(db_session, institution="cal", account_number="1234")
    create_account(db_session, institution="max", account_number="5678")

    accounts = analytics_service.get_all_accounts()

    assert len(accounts) == 2


@pytest.mark.parametrize("active_only,expected_count", [
    pytest.param(True, 1, id="active_only"),
    pytest.param(False, 2, id="include_inactive"),
])
def test_get_all_accounts_active_filter(db_session, analytics_service, active_only, expected_count):
    """Should filter inactive accounts based on flag."""
    create_account(db_session, account_number="1234")
    inactive = create_account(db_session, account_number="5678")
    inactive.is_active = False
    db_session.commit()

    accounts = analytics_service.get_all_accounts(active_only=active_only)

    assert len(accounts) == expected_count


@pytest.mark.parametrize("account_id,should_find", [
    pytest.param(1, True, id="existing_account"),
    pytest.param(99999, False, id="not_found"),
])
def test_get_account_by_id(db_session, analytics_service, account_id, should_find):
    """Should return account by ID or None if not found."""
    create_account(db_session)  # Creates account with id=1

    result = analytics_service.get_account_by_id(account_id)

    if should_find:
        assert result is not None
    else:
        assert result is None


def test_get_accounts_by_type(db_session, analytics_service):
    """Should filter accounts by type."""
    create_account(db_session, account_type="credit_card", account_number="1234")
    create_account(db_session, account_type="broker", account_number="5678")

    accounts = analytics_service.get_accounts_by_type("credit_card")

    assert len(accounts) == 1
    assert accounts[0].account_type == "credit_card"


def test_get_accounts_by_institution(db_session, analytics_service):
    """Should filter accounts by institution."""
    create_account(db_session, institution="cal", account_number="1234")
    create_account(db_session, institution="max", account_number="5678")

    accounts = analytics_service.get_accounts_by_institution("cal")

    assert len(accounts) == 1
    assert accounts[0].institution == "cal"


# ==================== Transaction Methods ====================

def test_get_transactions_empty(analytics_service):
    """Should return empty list when no transactions exist."""
    transactions = analytics_service.get_transactions()
    assert transactions == []


def test_get_transactions_all(db_session, analytics_service, sample_account):
    """Should return all transactions."""
    create_transaction(db_session, sample_account, description="TXN1")
    create_transaction(db_session, sample_account, description="TXN2")

    transactions = analytics_service.get_transactions()

    assert len(transactions) == 2


def test_get_transactions_by_account(db_session, analytics_service):
    """Should filter transactions by account ID."""
    account1 = create_account(db_session, account_number="1234")
    account2 = create_account(db_session, account_number="5678")
    create_transaction(db_session, account1, description="TXN1")
    create_transaction(db_session, account2, description="TXN2")

    transactions = analytics_service.get_transactions(account_id=account1.id)

    assert len(transactions) == 1
    assert transactions[0].description == "TXN1"


def test_get_transactions_by_date_range(db_session, analytics_service, sample_account):
    """Should filter transactions by date range."""
    today = date.today()
    yesterday = today - timedelta(days=1)
    last_week = today - timedelta(days=7)

    create_transaction(db_session, sample_account, transaction_date=today)
    create_transaction(db_session, sample_account, transaction_date=yesterday)
    create_transaction(db_session, sample_account, transaction_date=last_week)

    transactions = analytics_service.get_transactions(from_date=yesterday)

    assert len(transactions) == 2


@pytest.mark.parametrize("status,expected_count", [
    pytest.param("pending", 1, id="pending_only"),
    pytest.param("completed", 1, id="completed_only"),
])
def test_get_transactions_by_status(db_session, analytics_service, sample_account, status, expected_count):
    """Should filter transactions by status."""
    create_transaction(db_session, sample_account, status="completed")
    create_transaction(db_session, sample_account, status="pending")

    transactions = analytics_service.get_transactions(status=status)

    assert len(transactions) == expected_count


def test_get_transactions_by_institution(db_session, analytics_service):
    """Should filter transactions by institution."""
    cal_account = create_account(db_session, institution="cal", account_number="1234")
    max_account = create_account(db_session, institution="max", account_number="5678")
    create_transaction(db_session, cal_account)
    create_transaction(db_session, max_account)

    transactions = analytics_service.get_transactions(institution="cal")

    assert len(transactions) == 1


def test_get_transactions_by_tags(db_session, analytics_service, sample_account):
    """Should filter transactions by tags (AND logic)."""
    txn1 = create_transaction(db_session, sample_account, description="TXN1")
    txn2 = create_transaction(db_session, sample_account, description="TXN2")

    tag1 = create_tag(db_session, "food")
    tag2 = create_tag(db_session, "delivery")
    tag_transaction(db_session, txn1, tag1)
    tag_transaction(db_session, txn1, tag2)  # Has both
    tag_transaction(db_session, txn2, tag1)  # Has only one

    transactions = analytics_service.get_transactions(tags=["food", "delivery"])

    assert len(transactions) == 1
    assert transactions[0].id == txn1.id


def test_get_transactions_untagged_only(db_session, analytics_service, sample_account):
    """Should filter to only untagged transactions."""
    tagged = create_transaction(db_session, sample_account, description="TAGGED")
    untagged = create_transaction(db_session, sample_account, description="UNTAGGED")

    tag = create_tag(db_session, "test")
    tag_transaction(db_session, tagged, tag)

    transactions = analytics_service.get_transactions(untagged_only=True)

    assert len(transactions) == 1
    assert transactions[0].description == "UNTAGGED"


def test_get_transaction_count(db_session, analytics_service, sample_account):
    """Should return correct transaction count."""
    create_transaction(db_session, sample_account)
    create_transaction(db_session, sample_account)

    count = analytics_service.get_transaction_count()

    assert count == 2


# ==================== Balance Methods ====================

def test_get_latest_balances_empty(analytics_service):
    """Should return empty list when no balances exist."""
    balances = analytics_service.get_latest_balances()
    assert balances == []


def test_get_latest_balances_returns_latest(db_session, analytics_service, sample_account):
    """Should return latest balance for each account."""
    today = date.today()
    yesterday = today - timedelta(days=1)

    create_balance(db_session, sample_account, total_amount=1000, balance_date=yesterday)
    create_balance(db_session, sample_account, total_amount=1500, balance_date=today)

    balances = analytics_service.get_latest_balances()

    assert len(balances) == 1
    account, balance = balances[0]
    assert balance.total_amount == 1500


def test_get_balance_history(db_session, analytics_service, sample_account):
    """Should return balance history for account."""
    today = date.today()
    for i in range(3):
        create_balance(db_session, sample_account, total_amount=1000 + i * 100, balance_date=today - timedelta(days=i))

    history = analytics_service.get_balance_history(sample_account.id)

    assert len(history) == 3
    # Should be ordered by date ascending
    assert history[0].balance_date < history[2].balance_date


def test_get_balance_history_date_range(db_session, analytics_service, sample_account):
    """Should filter balance history by date range."""
    today = date.today()
    create_balance(db_session, sample_account, total_amount=1000, balance_date=today)
    create_balance(db_session, sample_account, total_amount=900, balance_date=today - timedelta(days=7))
    create_balance(db_session, sample_account, total_amount=800, balance_date=today - timedelta(days=14))

    history = analytics_service.get_balance_history(sample_account.id, from_date=today - timedelta(days=7))

    assert len(history) == 2


# ==================== Statistics ====================

def test_get_overall_stats(db_session, analytics_service, sample_account):
    """Should return overall statistics."""
    create_transaction(db_session, sample_account)
    create_transaction(db_session, sample_account, status="pending")
    create_balance(db_session, sample_account, total_amount=5000)
    create_sync_history(db_session, status="success")

    stats = analytics_service.get_overall_stats()

    assert stats["total_accounts"] == 1
    assert stats["total_transactions"] == 2
    assert stats["pending_transactions"] == 1
    assert stats["total_balance"] == 5000
    assert stats["last_sync"] is not None


def test_get_overall_stats_empty(analytics_service):
    """Should handle empty database."""
    stats = analytics_service.get_overall_stats()

    assert stats["total_accounts"] == 0
    assert stats["total_transactions"] == 0
    assert stats["total_balance"] == 0
    assert stats["last_sync"] is None


def test_get_monthly_summary(db_session, analytics_service, sample_account):
    """Should return monthly transaction summary."""
    today = date.today()
    create_transaction(db_session, sample_account, amount=100, transaction_date=today, status="completed")
    create_transaction(db_session, sample_account, amount=200, transaction_date=today, status="pending")

    summary = analytics_service.get_monthly_summary(today.year, today.month)

    assert summary["year"] == today.year
    assert summary["month"] == today.month
    assert summary["transaction_count"] == 2
    assert summary["total_amount"] == 300
    assert summary["by_status"]["completed"] == 1
    assert summary["by_status"]["pending"] == 1


# ==================== Category Breakdown ====================

def test_get_category_breakdown(db_session, analytics_service, sample_account):
    """Should return spending breakdown by category."""
    create_transaction(db_session, sample_account, amount=100, category="groceries")
    create_transaction(db_session, sample_account, amount=150, category="groceries")
    create_transaction(db_session, sample_account, amount=50, category="entertainment")

    breakdown = analytics_service.get_category_breakdown()

    assert "groceries" in breakdown
    assert breakdown["groceries"]["count"] == 2
    assert breakdown["groceries"]["total_amount"] == 250


def test_get_category_breakdown_uncategorized(db_session, analytics_service, sample_account):
    """Should handle uncategorized transactions."""
    create_transaction(db_session, sample_account, amount=100)  # No category

    breakdown = analytics_service.get_category_breakdown()

    assert "Uncategorized" in breakdown


def test_get_category_breakdown_uses_effective_category(db_session, analytics_service, sample_account):
    """Should use user_category when set."""
    create_transaction(db_session, sample_account, category="original", user_category="override")

    breakdown = analytics_service.get_category_breakdown()

    assert "override" in breakdown
    assert "original" not in breakdown


def test_get_category_breakdown_date_range(db_session, analytics_service, sample_account):
    """Should filter by date range."""
    today = date.today()
    create_transaction(db_session, sample_account, transaction_date=today, category="recent")
    create_transaction(db_session, sample_account, transaction_date=today - timedelta(days=30), category="old")

    breakdown = analytics_service.get_category_breakdown(from_date=today - timedelta(days=7))

    assert "recent" in breakdown
    assert "old" not in breakdown


# ==================== Tag Breakdown ====================

def test_get_tag_breakdown(db_session, analytics_service, sample_account):
    """Should return spending breakdown by tag."""
    txn1 = create_transaction(db_session, sample_account, amount=100)
    txn2 = create_transaction(db_session, sample_account, amount=200)
    txn3 = create_transaction(db_session, sample_account, amount=50)  # Untagged

    tag = create_tag(db_session, "food")
    tag_transaction(db_session, txn1, tag)
    tag_transaction(db_session, txn2, tag)

    breakdown = analytics_service.get_tag_breakdown()

    assert "food" in breakdown
    assert breakdown["food"]["count"] == 2
    assert "(untagged)" in breakdown
    assert breakdown["(untagged)"]["count"] == 1


def test_get_monthly_tag_breakdown(db_session, analytics_service, sample_account):
    """Should return tag breakdown for specific month."""
    today = date.today()
    txn = create_transaction(db_session, sample_account, amount=100, transaction_date=today)
    tag = create_tag(db_session, "test")
    tag_transaction(db_session, txn, tag)

    breakdown = analytics_service.get_monthly_tag_breakdown(today.year, today.month)

    assert "test" in breakdown


# ==================== Sync History ====================

def test_get_sync_history(db_session, analytics_service):
    """Should return sync history records."""
    create_sync_history(db_session, institution="cal", status="success")
    create_sync_history(db_session, institution="max", status="failed")

    history = analytics_service.get_sync_history()

    assert len(history) == 2


@pytest.mark.parametrize("institution,status,expected_count", [
    pytest.param("cal", "success", 1, id="filter_both"),
    pytest.param("cal", None, 2, id="filter_institution_only"),
    pytest.param(None, "success", 2, id="filter_status_only"),
])
def test_get_sync_history_filtered(db_session, analytics_service, institution, status, expected_count):
    """Should filter sync history by institution and status."""
    create_sync_history(db_session, institution="cal", status="success")
    create_sync_history(db_session, institution="cal", status="failed")
    create_sync_history(db_session, institution="max", status="success")

    history = analytics_service.get_sync_history(institution=institution, status=status)

    assert len(history) == expected_count


def test_get_sync_history_limit(db_session, analytics_service):
    """Should respect limit parameter."""
    for _ in range(5):
        create_sync_history(db_session)

    history = analytics_service.get_sync_history(limit=3)

    assert len(history) == 3
