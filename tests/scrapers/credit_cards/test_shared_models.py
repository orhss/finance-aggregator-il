"""
Tests for credit card shared models.

These tests verify the behavior of models BEFORE extraction to shared_models.py.
They ensure the refactoring doesn't break any existing functionality.
"""

import pytest
from datetime import date
from dataclasses import asdict

# Import from current locations (will be updated after extraction)
from scrapers.credit_cards.cal_credit_card_client import (
    TransactionStatus as CALTransactionStatus,
    TransactionType as CALTransactionType,
    Installments as CALInstallments,
    Transaction as CALTransaction,
    CardAccount as CALCardAccount,
)
from scrapers.credit_cards.max_credit_card_client import (
    TransactionStatus as MaxTransactionStatus,
    TransactionType as MaxTransactionType,
    Installments as MaxInstallments,
    Transaction as MaxTransaction,
    CardAccount as MaxCardAccount,
)
from scrapers.credit_cards.isracard_credit_card_client import (
    TransactionStatus as IsracardTransactionStatus,
    TransactionType as IsracardTransactionType,
    Installments as IsracardInstallments,
    Transaction as IsracardTransaction,
    CardAccount as IsracardCardAccount,
)


# ==================== TransactionStatus Tests ====================

class TestTransactionStatus:
    """Test TransactionStatus enum across all scrapers."""

    def test_cal_transaction_status_values(self):
        """CAL has PENDING and COMPLETED statuses."""
        assert CALTransactionStatus.PENDING.value == "pending"
        assert CALTransactionStatus.COMPLETED.value == "completed"

    def test_max_transaction_status_values(self):
        """Max has PENDING and COMPLETED statuses."""
        assert MaxTransactionStatus.PENDING.value == "pending"
        assert MaxTransactionStatus.COMPLETED.value == "completed"

    def test_isracard_transaction_status_values(self):
        """Isracard uses shared enum (has PENDING but doesn't use it in practice)."""
        assert IsracardTransactionStatus.COMPLETED.value == "completed"
        # Shared enum has PENDING, though Isracard API only returns completed
        assert IsracardTransactionStatus.PENDING.value == "pending"

    def test_status_comparison_across_scrapers(self):
        """Verify COMPLETED value is consistent across scrapers."""
        assert CALTransactionStatus.COMPLETED.value == MaxTransactionStatus.COMPLETED.value
        assert CALTransactionStatus.COMPLETED.value == IsracardTransactionStatus.COMPLETED.value


# ==================== TransactionType Tests ====================

class TestTransactionType:
    """Test TransactionType enum across all scrapers."""

    def test_cal_transaction_type_values(self):
        """CAL has NORMAL, INSTALLMENTS, and CREDIT types."""
        assert CALTransactionType.NORMAL.value == "normal"
        assert CALTransactionType.INSTALLMENTS.value == "installments"
        assert CALTransactionType.CREDIT.value == "credit"

    def test_max_transaction_type_values(self):
        """Max uses shared enum (has CREDIT though typically unused)."""
        assert MaxTransactionType.NORMAL.value == "normal"
        assert MaxTransactionType.INSTALLMENTS.value == "installments"
        # Shared enum has CREDIT for consistency
        assert MaxTransactionType.CREDIT.value == "credit"

    def test_isracard_transaction_type_values(self):
        """Isracard has NORMAL and INSTALLMENTS types."""
        assert IsracardTransactionType.NORMAL.value == "normal"
        assert IsracardTransactionType.INSTALLMENTS.value == "installments"

    def test_type_comparison_across_scrapers(self):
        """Verify common types have consistent values."""
        assert CALTransactionType.NORMAL.value == MaxTransactionType.NORMAL.value
        assert CALTransactionType.NORMAL.value == IsracardTransactionType.NORMAL.value
        assert CALTransactionType.INSTALLMENTS.value == MaxTransactionType.INSTALLMENTS.value


# ==================== Installments Tests ====================

class TestInstallments:
    """Test Installments dataclass across all scrapers."""

    @pytest.mark.parametrize("installments_class", [
        pytest.param(CALInstallments, id="cal"),
        pytest.param(MaxInstallments, id="max"),
        pytest.param(IsracardInstallments, id="isracard"),
    ])
    def test_installments_creation(self, installments_class):
        """Installments can be created with number and total."""
        inst = installments_class(number=3, total=12)
        assert inst.number == 3
        assert inst.total == 12

    @pytest.mark.parametrize("installments_class", [
        pytest.param(CALInstallments, id="cal"),
        pytest.param(MaxInstallments, id="max"),
        pytest.param(IsracardInstallments, id="isracard"),
    ])
    def test_installments_to_dict(self, installments_class):
        """Installments can be converted to dict."""
        inst = installments_class(number=1, total=6)
        d = asdict(inst)
        assert d == {"number": 1, "total": 6}

    def test_installments_edge_cases(self):
        """Test edge cases for installments."""
        # Single payment
        inst = CALInstallments(number=1, total=1)
        assert inst.number == inst.total

        # Last installment
        inst = CALInstallments(number=12, total=12)
        assert inst.number == inst.total


# ==================== Transaction Tests ====================

class TestTransaction:
    """Test Transaction dataclass across all scrapers."""

    @pytest.fixture
    def sample_transaction_data(self):
        """Common transaction data for testing."""
        return {
            "date": "2024-01-15",
            "processed_date": "2024-01-17",
            "original_amount": 100.00,
            "original_currency": "ILS",
            "charged_amount": 100.00,
            "charged_currency": "ILS",
            "description": "Test Merchant",
            "status": CALTransactionStatus.COMPLETED,
            "transaction_type": CALTransactionType.NORMAL,
        }

    def test_cal_transaction_creation(self, sample_transaction_data):
        """CAL transaction can be created with all fields."""
        txn = CALTransaction(**sample_transaction_data)
        assert txn.date == "2024-01-15"
        assert txn.description == "Test Merchant"
        assert txn.original_amount == 100.00
        assert txn.status == CALTransactionStatus.COMPLETED

    def test_cal_transaction_optional_fields(self, sample_transaction_data):
        """CAL transaction has correct optional fields."""
        txn = CALTransaction(**sample_transaction_data)
        assert txn.identifier is None
        assert txn.memo is None
        assert txn.category is None
        assert txn.installments is None

    def test_cal_transaction_with_installments(self, sample_transaction_data):
        """CAL transaction can have installments."""
        sample_transaction_data["installments"] = CALInstallments(number=2, total=6)
        sample_transaction_data["transaction_type"] = CALTransactionType.INSTALLMENTS
        txn = CALTransaction(**sample_transaction_data)
        assert txn.installments is not None
        assert txn.installments.number == 2
        assert txn.installments.total == 6

    def test_max_transaction_creation(self):
        """Max transaction can be created."""
        txn = MaxTransaction(
            date="2024-01-15",
            processed_date="2024-01-17",
            original_amount=50.00,
            original_currency="USD",
            charged_amount=185.00,
            charged_currency="ILS",
            description="Foreign Purchase",
            status=MaxTransactionStatus.COMPLETED,
            transaction_type=MaxTransactionType.NORMAL,
        )
        assert txn.original_currency == "USD"
        assert txn.charged_currency == "ILS"

    def test_isracard_transaction_creation(self):
        """Isracard transaction can be created."""
        txn = IsracardTransaction(
            date="2024-01-15",
            processed_date="2024-01-17",
            original_amount=100.00,
            original_currency="ILS",
            charged_amount=100.00,
            charged_currency="ILS",
            description="Local Store",
            status=IsracardTransactionStatus.COMPLETED,
            transaction_type=IsracardTransactionType.NORMAL,
        )
        assert txn.status == IsracardTransactionStatus.COMPLETED

    def test_transaction_with_category(self, sample_transaction_data):
        """Transaction can have category set."""
        sample_transaction_data["category"] = "groceries"
        txn = CALTransaction(**sample_transaction_data)
        assert txn.category == "groceries"

    def test_transaction_with_memo(self, sample_transaction_data):
        """Transaction can have memo set."""
        sample_transaction_data["memo"] = "Business expense"
        txn = CALTransaction(**sample_transaction_data)
        assert txn.memo == "Business expense"


# ==================== CardAccount Tests ====================

class TestCardAccount:
    """Test CardAccount dataclass across all scrapers."""

    def test_cal_card_account_creation(self):
        """CAL CardAccount can be created."""
        account = CALCardAccount(
            account_number="1234",
            card_unique_id="abc-123-def",
            transactions=[],
        )
        assert account.account_number == "1234"
        assert account.card_unique_id == "abc-123-def"
        assert account.transactions == []

    def test_max_card_account_creation(self):
        """Max CardAccount has simpler structure (no card_unique_id)."""
        account = MaxCardAccount(
            account_number="5678",
            transactions=[],
        )
        assert account.account_number == "5678"
        # Max CardAccount doesn't have card_unique_id (unlike CAL)
        assert not hasattr(account, 'card_unique_id')

    def test_isracard_card_account_creation(self):
        """Isracard CardAccount has index instead of card_unique_id."""
        account = IsracardCardAccount(
            account_number="9012",
            index=0,
            transactions=[],
        )
        assert account.account_number == "9012"
        assert account.index == 0

    def test_card_account_with_transactions(self):
        """CardAccount can hold multiple transactions."""
        txn1 = CALTransaction(
            date="2024-01-15",
            processed_date="2024-01-17",
            original_amount=100.00,
            original_currency="ILS",
            charged_amount=100.00,
            charged_currency="ILS",
            description="Store 1",
            status=CALTransactionStatus.COMPLETED,
            transaction_type=CALTransactionType.NORMAL,
        )
        txn2 = CALTransaction(
            date="2024-01-16",
            processed_date="2024-01-18",
            original_amount=50.00,
            original_currency="ILS",
            charged_amount=50.00,
            charged_currency="ILS",
            description="Store 2",
            status=CALTransactionStatus.COMPLETED,
            transaction_type=CALTransactionType.NORMAL,
        )
        account = CALCardAccount(
            account_number="1234",
            card_unique_id="abc-123",
            transactions=[txn1, txn2],
        )
        assert len(account.transactions) == 2
        assert account.transactions[0].description == "Store 1"
        assert account.transactions[1].description == "Store 2"


# ==================== Cross-Scraper Compatibility Tests ====================

class TestCrossScraperCompatibility:
    """Tests to verify models can be used interchangeably where appropriate."""

    def test_transaction_fields_are_consistent(self):
        """All Transaction classes have the same core fields."""
        core_fields = {
            "date", "processed_date", "original_amount", "original_currency",
            "charged_amount", "charged_currency", "description", "status",
            "transaction_type", "identifier", "memo", "category", "installments"
        }

        cal_fields = set(CALTransaction.__dataclass_fields__.keys())
        max_fields = set(MaxTransaction.__dataclass_fields__.keys())
        isracard_fields = set(IsracardTransaction.__dataclass_fields__.keys())

        assert core_fields.issubset(cal_fields)
        assert core_fields.issubset(max_fields)
        assert core_fields.issubset(isracard_fields)

    def test_installments_are_identical(self):
        """All Installments classes have identical structure."""
        cal_fields = set(CALInstallments.__dataclass_fields__.keys())
        max_fields = set(MaxInstallments.__dataclass_fields__.keys())
        isracard_fields = set(IsracardInstallments.__dataclass_fields__.keys())

        assert cal_fields == max_fields == isracard_fields == {"number", "total"}
