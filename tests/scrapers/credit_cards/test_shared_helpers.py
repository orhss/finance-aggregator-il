"""
Tests for credit card shared helpers.

These tests verify the behavior of helper functions in shared_helpers.py.
"""

import pytest
from datetime import date, timedelta
from typing import Optional
from dataclasses import dataclass

from scrapers.credit_cards.shared_helpers import (
    iterate_months,
    calculate_date_range,
    filter_transactions_by_date,
    extract_installments,
    get_cookies,
    parse_amount,
)
from scrapers.credit_cards.shared_models import (
    Installments,
    Transaction,
    TransactionStatus,
    TransactionType,
)


# ==================== Test Fixtures ====================

@dataclass
class MockTransaction:
    """Mock Transaction for testing filter function."""
    date: str
    description: str
    amount: float


# ==================== iterate_months Tests ====================

class TestIterateMonths:
    """Test iterate_months helper function."""

    def test_iterate_single_month(self):
        """Single month returns just that month."""
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)

        months = list(iterate_months(start, end))

        assert len(months) == 1
        assert months[0] == (2024, 1)

    def test_iterate_multiple_months_same_year(self):
        """Multiple months in same year."""
        start = date(2024, 1, 1)
        end = date(2024, 3, 15)

        months = list(iterate_months(start, end))

        assert len(months) == 3
        # Returns in reverse order (end to start)
        assert months[0] == (2024, 3)
        assert months[1] == (2024, 2)
        assert months[2] == (2024, 1)

    def test_iterate_across_year_boundary(self):
        """Months spanning year boundary."""
        start = date(2023, 11, 1)
        end = date(2024, 2, 15)

        months = list(iterate_months(start, end))

        assert len(months) == 4
        assert months[0] == (2024, 2)
        assert months[1] == (2024, 1)
        assert months[2] == (2023, 12)
        assert months[3] == (2023, 11)

    def test_iterate_december_to_january(self):
        """December to January edge case."""
        start = date(2023, 12, 1)
        end = date(2024, 1, 15)

        months = list(iterate_months(start, end))

        assert len(months) == 2
        assert months[0] == (2024, 1)
        assert months[1] == (2023, 12)

    def test_iterate_same_day(self):
        """Same start and end date."""
        same_date = date(2024, 6, 15)

        months = list(iterate_months(same_date, same_date))

        assert len(months) == 1
        assert months[0] == (2024, 6)


# ==================== calculate_date_range Tests ====================

class TestCalculateDateRange:
    """Test calculate_date_range helper function."""

    def test_default_range(self):
        """Default 6 months back, 1 month forward."""
        start, end = calculate_date_range(months_back=6)
        today = date.today()

        # Start should be ~6 months ago
        assert (today - start).days >= 170  # ~6 months
        assert (today - start).days <= 190

        # End should be ~1 month ahead
        assert (end - today).days >= 28
        assert (end - today).days <= 35

    def test_custom_months_back(self):
        """Custom months_back value."""
        start, end = calculate_date_range(months_back=3)
        today = date.today()

        assert (today - start).days >= 85  # ~3 months
        assert (today - start).days <= 95

    def test_custom_months_forward(self):
        """Custom months_forward value."""
        start, end = calculate_date_range(months_back=1, months_forward=2)
        today = date.today()

        assert (end - today).days >= 55  # ~2 months
        assert (end - today).days <= 65

    def test_zero_months_forward(self):
        """Zero months forward means end is today."""
        start, end = calculate_date_range(months_back=1, months_forward=0)
        today = date.today()

        assert end == today


# ==================== filter_transactions_by_date Tests ====================

class TestFilterTransactionsByDate:
    """Test filter_transactions_by_date helper function."""

    @pytest.fixture
    def sample_transactions(self):
        """Sample transactions for filtering tests using real Transaction model."""
        return [
            Transaction(
                date="2024-01-10", processed_date="2024-01-12",
                original_amount=100, original_currency="ILS",
                charged_amount=100, charged_currency="ILS",
                description="Before range",
                status=TransactionStatus.COMPLETED,
                transaction_type=TransactionType.NORMAL,
            ),
            Transaction(
                date="2024-02-01", processed_date="2024-02-03",
                original_amount=200, original_currency="ILS",
                charged_amount=200, charged_currency="ILS",
                description="Start boundary",
                status=TransactionStatus.COMPLETED,
                transaction_type=TransactionType.NORMAL,
            ),
            Transaction(
                date="2024-02-15", processed_date="2024-02-17",
                original_amount=300, original_currency="ILS",
                charged_amount=300, charged_currency="ILS",
                description="In range",
                status=TransactionStatus.COMPLETED,
                transaction_type=TransactionType.NORMAL,
            ),
            Transaction(
                date="2024-03-01", processed_date="2024-03-03",
                original_amount=400, original_currency="ILS",
                charged_amount=400, charged_currency="ILS",
                description="End boundary",
                status=TransactionStatus.COMPLETED,
                transaction_type=TransactionType.NORMAL,
            ),
            Transaction(
                date="2024-03-15", processed_date="2024-03-17",
                original_amount=500, original_currency="ILS",
                charged_amount=500, charged_currency="ILS",
                description="After range",
                status=TransactionStatus.COMPLETED,
                transaction_type=TransactionType.NORMAL,
            ),
        ]

    def test_filter_inclusive_boundaries(self, sample_transactions):
        """Filter includes boundary dates."""
        start = date(2024, 2, 1)
        end = date(2024, 3, 1)

        filtered = filter_transactions_by_date(sample_transactions, start, end)

        assert len(filtered) == 3
        descriptions = [t.description for t in filtered]
        assert "Start boundary" in descriptions
        assert "In range" in descriptions
        assert "End boundary" in descriptions

    def test_filter_excludes_outside_range(self, sample_transactions):
        """Filter excludes dates outside range."""
        start = date(2024, 2, 1)
        end = date(2024, 3, 1)

        filtered = filter_transactions_by_date(sample_transactions, start, end)

        descriptions = [t.description for t in filtered]
        assert "Before range" not in descriptions
        assert "After range" not in descriptions

    def test_filter_empty_result(self, sample_transactions):
        """Filter returns empty list when no matches."""
        start = date(2025, 1, 1)
        end = date(2025, 12, 31)

        filtered = filter_transactions_by_date(sample_transactions, start, end)

        assert len(filtered) == 0

    def test_filter_all_match(self, sample_transactions):
        """Filter returns all when all match."""
        start = date(2024, 1, 1)
        end = date(2024, 12, 31)

        filtered = filter_transactions_by_date(sample_transactions, start, end)

        assert len(filtered) == 5

    def test_filter_empty_input(self):
        """Filter handles empty input list."""
        filtered = filter_transactions_by_date([], date(2024, 1, 1), date(2024, 12, 31))
        assert len(filtered) == 0


# ==================== extract_installments Tests ====================

class TestExtractInstallments:
    """Test extract_installments helper function."""

    @pytest.mark.parametrize("raw_string,expected", [
        pytest.param("3/12", (3, 12), id="simple_fraction"),
        pytest.param("1/6", (1, 6), id="first_of_six"),
        pytest.param("12/12", (12, 12), id="last_installment"),
        pytest.param("תשלום 2 מתוך 10", (2, 10), id="hebrew_text"),
        pytest.param("Payment 5 of 8", (5, 8), id="english_text"),
        pytest.param("2 / 4 payments", (2, 4), id="with_spaces"),
    ])
    def test_extract_installments_success(self, raw_string, expected):
        """Extract installments from various formats."""
        result = extract_installments(raw_string)
        assert result is not None
        assert result.number == expected[0]
        assert result.total == expected[1]

    @pytest.mark.parametrize("raw_string", [
        pytest.param("", id="empty_string"),
        pytest.param("Regular payment", id="no_numbers"),
        pytest.param("100 ILS", id="single_number"),
        pytest.param(None, id="none_value"),
    ])
    def test_extract_installments_none(self, raw_string):
        """Return None when no installments found."""
        result = extract_installments(raw_string)
        assert result is None

    def test_extract_installments_first_two_numbers(self):
        """Uses first two numbers found in string."""
        result = extract_installments("3/12 (total 500)")
        assert result.number == 3
        assert result.total == 12


# ==================== get_cookies Tests ====================

class TestGetCookies:
    """Test get_cookies helper function."""

    def test_get_cookies_from_driver(self):
        """Convert driver cookies to dict."""

        class MockDriver:
            def get_cookies(self):
                return [
                    {"name": "session_id", "value": "abc123"},
                    {"name": "auth_token", "value": "xyz789"},
                    {"name": "preference", "value": "dark_mode"},
                ]

        cookies = get_cookies(MockDriver())

        assert cookies == {
            "session_id": "abc123",
            "auth_token": "xyz789",
            "preference": "dark_mode",
        }

    def test_get_cookies_empty(self):
        """Handle empty cookies."""

        class MockDriver:
            def get_cookies(self):
                return []

        cookies = get_cookies(MockDriver())
        assert cookies == {}

    def test_get_cookies_overwrites_duplicates(self):
        """Later cookies with same name overwrite earlier ones."""

        class MockDriver:
            def get_cookies(self):
                return [
                    {"name": "token", "value": "old_value"},
                    {"name": "token", "value": "new_value"},
                ]

        cookies = get_cookies(MockDriver())
        assert cookies["token"] == "new_value"


# ==================== parse_amount Tests ====================

class TestParseAmount:
    """Test amount parsing helpers."""

    @pytest.mark.parametrize("amount_str,expected", [
        pytest.param("100.50", 100.50, id="simple_decimal"),
        pytest.param("1,234.56", 1234.56, id="with_comma"),
        pytest.param("-50.00", -50.00, id="negative"),
        pytest.param("0", 0.0, id="zero"),
        pytest.param("1234", 1234.0, id="integer"),
    ])
    def test_parse_amount_success(self, amount_str, expected):
        """Parse various amount formats."""
        result = parse_amount(amount_str)
        assert result == expected

    @pytest.mark.parametrize("amount_str", [
        pytest.param("", id="empty"),
        pytest.param("N/A", id="not_applicable"),
        pytest.param(None, id="none"),
    ])
    def test_parse_amount_invalid(self, amount_str):
        """Return None for invalid amounts."""
        result = parse_amount(amount_str)
        assert result is None
