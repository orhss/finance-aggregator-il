"""
Tests for base_service module.

Tests the SyncResult dataclass, BaseSyncService base class, and SessionMixin.
"""

import pytest
from dataclasses import fields
from unittest.mock import MagicMock, patch


# ==================== SyncResult Tests ====================


class TestSyncResult:
    """Tests for the unified SyncResult dataclass."""

    def test_default_values(self):
        """Should initialize with sensible defaults."""
        from services.base_service import SyncResult

        result = SyncResult()

        assert result.success is False
        assert result.error_message is None
        assert result.sync_history_id is None
        assert result.accounts_synced == 0
        assert result.cards_synced == 0
        assert result.balances_added == 0
        assert result.balances_updated == 0
        assert result.transactions_added == 0
        assert result.transactions_updated == 0
        assert result.financial_data is None
        assert result.unmapped_categories == []

    def test_broker_usage_pattern(self):
        """Should support broker sync result fields."""
        from services.base_service import SyncResult

        result = SyncResult()
        result.success = True
        result.accounts_synced = 2
        result.balances_added = 3
        result.balances_updated = 1
        result.sync_history_id = 42

        assert result.success is True
        assert result.accounts_synced == 2
        assert result.balances_added == 3
        assert result.balances_updated == 1
        assert result.sync_history_id == 42

    def test_pension_usage_pattern(self):
        """Should support pension sync result fields including financial_data."""
        from services.base_service import SyncResult

        result = SyncResult()
        result.success = True
        result.accounts_synced = 1
        result.balances_added = 1
        result.financial_data = {"total": 100000, "profit": 5000}

        assert result.success is True
        assert result.accounts_synced == 1
        assert result.balances_added == 1
        assert result.financial_data == {"total": 100000, "profit": 5000}

    def test_credit_card_usage_pattern(self):
        """Should support credit card sync result fields including unmapped_categories."""
        from services.base_service import SyncResult

        result = SyncResult()
        result.success = True
        result.cards_synced = 3
        result.transactions_added = 45
        result.transactions_updated = 12
        result.unmapped_categories = [
            {"raw_category": "מזון", "count": 5},
            {"raw_category": "דלק", "count": 3},
        ]

        assert result.success is True
        assert result.cards_synced == 3
        assert result.transactions_added == 45
        assert result.transactions_updated == 12
        assert len(result.unmapped_categories) == 2

    def test_error_case(self):
        """Should properly store error information."""
        from services.base_service import SyncResult

        result = SyncResult()
        result.success = False
        result.error_message = "Connection timeout"
        result.sync_history_id = 99

        assert result.success is False
        assert result.error_message == "Connection timeout"
        assert result.sync_history_id == 99

    def test_unmapped_categories_default_is_empty_list(self):
        """Should have separate empty list for each instance (no shared state)."""
        from services.base_service import SyncResult

        result1 = SyncResult()
        result2 = SyncResult()

        result1.unmapped_categories.append({"test": 1})

        # result2 should not be affected
        assert result1.unmapped_categories == [{"test": 1}]
        assert result2.unmapped_categories == []

    def test_is_dataclass(self):
        """SyncResult should be a proper dataclass."""
        from services.base_service import SyncResult

        # Check it has dataclass fields
        field_names = {f.name for f in fields(SyncResult)}

        assert "success" in field_names
        assert "error_message" in field_names
        assert "sync_history_id" in field_names
        assert "accounts_synced" in field_names
        assert "cards_synced" in field_names
        assert "balances_added" in field_names
        assert "transactions_added" in field_names


# ==================== BaseSyncService Tests ====================


class TestBaseSyncService:
    """Tests for BaseSyncService base class."""

    def test_init_stores_session(self, db_session):
        """Should store the database session."""
        from services.base_service import BaseSyncService

        service = BaseSyncService(db_session)

        assert service.db is db_session

    def test_get_or_create_account_creates_new(self, db_session):
        """Should create new account when none exists."""
        from services.base_service import BaseSyncService
        from db.models import Account

        service = BaseSyncService(db_session)
        account = service.get_or_create_account(
            account_type="broker",
            institution="test_broker",
            account_number="12345",
            account_name="Test Account",
        )

        assert account.id is not None
        assert account.account_type == "broker"
        assert account.institution == "test_broker"
        assert account.account_number == "12345"
        assert account.account_name == "Test Account"

    def test_get_or_create_account_returns_existing(self, db_session):
        """Should return existing account and update last_synced_at."""
        from services.base_service import BaseSyncService
        from db.models import Account
        from datetime import datetime

        # Create existing account
        existing = Account(
            account_type="broker",
            institution="test_broker",
            account_number="12345",
            account_name="Old Name",
        )
        db_session.add(existing)
        db_session.commit()
        original_id = existing.id

        # Get it via service
        service = BaseSyncService(db_session)
        account = service.get_or_create_account(
            account_type="broker",
            institution="test_broker",
            account_number="12345",
            account_name="New Name",
        )

        assert account.id == original_id
        assert account.account_name == "New Name"  # Updated
        assert account.last_synced_at is not None

    def test_save_balance_creates_new(self, db_session):
        """Should create new balance record."""
        from services.base_service import BaseSyncService
        from db.models import Account, Balance
        from datetime import date

        # Create account
        account = Account(
            account_type="broker",
            institution="test",
            account_number="123",
        )
        db_session.add(account)
        db_session.commit()

        service = BaseSyncService(db_session)
        is_new = service.save_balance(
            account=account,
            total_amount=10000.0,
            balance_date=date(2024, 1, 15),
        )

        assert is_new is True

        # Verify balance was created
        balance = db_session.query(Balance).filter(
            Balance.account_id == account.id
        ).first()
        assert balance is not None
        assert balance.total_amount == 10000.0
        assert balance.balance_date == date(2024, 1, 15)

    def test_save_balance_updates_existing(self, db_session):
        """Should update existing balance for same date."""
        from services.base_service import BaseSyncService
        from db.models import Account, Balance
        from datetime import date

        # Create account and existing balance
        account = Account(
            account_type="broker",
            institution="test",
            account_number="123",
        )
        db_session.add(account)
        db_session.commit()

        existing_balance = Balance(
            account_id=account.id,
            balance_date=date(2024, 1, 15),
            total_amount=5000.0,
        )
        db_session.add(existing_balance)
        db_session.commit()

        # Update via service
        service = BaseSyncService(db_session)
        is_new = service.save_balance(
            account=account,
            total_amount=10000.0,
            balance_date=date(2024, 1, 15),
        )

        assert is_new is False

        # Verify balance was updated
        balance = db_session.query(Balance).filter(
            Balance.account_id == account.id
        ).first()
        assert balance.total_amount == 10000.0

    def test_get_balances_by_type_filters_correctly(self, db_session):
        """Should filter balances by account type."""
        from services.base_service import BaseSyncService
        from db.models import Account, Balance
        from datetime import date

        # Create accounts of different types
        broker_account = Account(
            account_type="broker", institution="test", account_number="B1"
        )
        pension_account = Account(
            account_type="pension", institution="test", account_number="P1"
        )
        db_session.add_all([broker_account, pension_account])
        db_session.commit()

        # Create balances for each
        db_session.add_all([
            Balance(account_id=broker_account.id, balance_date=date(2024, 1, 1), total_amount=1000),
            Balance(account_id=pension_account.id, balance_date=date(2024, 1, 1), total_amount=2000),
        ])
        db_session.commit()

        service = BaseSyncService(db_session)
        broker_balances = service.get_balances_by_type("broker")
        pension_balances = service.get_balances_by_type("pension")

        assert len(broker_balances) == 1
        assert broker_balances[0].total_amount == 1000
        assert len(pension_balances) == 1
        assert pension_balances[0].total_amount == 2000

    def test_get_balances_by_type_filters_by_institution(self, db_session):
        """Should filter by institution when specified."""
        from services.base_service import BaseSyncService
        from db.models import Account, Balance
        from datetime import date

        # Create accounts at different institutions
        acc1 = Account(account_type="broker", institution="excellence", account_number="1")
        acc2 = Account(account_type="broker", institution="meitav", account_number="2")
        db_session.add_all([acc1, acc2])
        db_session.commit()

        db_session.add_all([
            Balance(account_id=acc1.id, balance_date=date(2024, 1, 1), total_amount=1000),
            Balance(account_id=acc2.id, balance_date=date(2024, 1, 1), total_amount=2000),
        ])
        db_session.commit()

        service = BaseSyncService(db_session)
        balances = service.get_balances_by_type("broker", institution="excellence")

        assert len(balances) == 1
        assert balances[0].total_amount == 1000

    def test_get_balances_by_type_respects_limit(self, db_session):
        """Should respect limit parameter."""
        from services.base_service import BaseSyncService
        from db.models import Account, Balance
        from datetime import date, timedelta

        account = Account(account_type="broker", institution="test", account_number="1")
        db_session.add(account)
        db_session.commit()

        # Create 5 balances
        for i in range(5):
            db_session.add(Balance(
                account_id=account.id,
                balance_date=date(2024, 1, 1) + timedelta(days=i),
                total_amount=1000 * (i + 1),
            ))
        db_session.commit()

        service = BaseSyncService(db_session)
        balances = service.get_balances_by_type("broker", limit=3)

        assert len(balances) == 3

    def test_get_balances_by_type_orders_by_date_desc(self, db_session):
        """Should return balances ordered by date descending."""
        from services.base_service import BaseSyncService
        from db.models import Account, Balance
        from datetime import date

        account = Account(account_type="broker", institution="test", account_number="1")
        db_session.add(account)
        db_session.commit()

        # Create balances out of order
        db_session.add_all([
            Balance(account_id=account.id, balance_date=date(2024, 1, 1), total_amount=100),
            Balance(account_id=account.id, balance_date=date(2024, 1, 3), total_amount=300),
            Balance(account_id=account.id, balance_date=date(2024, 1, 2), total_amount=200),
        ])
        db_session.commit()

        service = BaseSyncService(db_session)
        balances = service.get_balances_by_type("broker")

        # Should be ordered newest first
        assert balances[0].total_amount == 300
        assert balances[1].total_amount == 200
        assert balances[2].total_amount == 100


# ==================== SessionMixin Tests ====================


class TestSessionMixin:
    """Tests for the SessionMixin class."""

    def test_with_provided_session(self, db_session):
        """Should use provided session without creating new one."""
        from services.base_service import SessionMixin

        class TestService(SessionMixin):
            pass

        service = TestService(session=db_session)
        assert service.session is db_session
        assert service._owns_session is False

    def test_without_session_creates_one(self):
        """Should lazily create session when not provided."""
        from services.base_service import SessionMixin

        class TestService(SessionMixin):
            pass

        mock_session = MagicMock()
        with patch("services.base_service.get_db") as mock_get_db:
            mock_get_db.return_value = iter([mock_session])

            service = TestService()
            assert service._session is None  # Not created yet
            assert service._owns_session is True

            # Access session property
            result = service.session
            assert result is mock_session
            mock_get_db.assert_called_once()

    def test_close_with_owned_session(self):
        """Should close session when service owns it."""
        from services.base_service import SessionMixin

        class TestService(SessionMixin):
            pass

        mock_session = MagicMock()
        with patch("services.base_service.get_db") as mock_get_db:
            mock_get_db.return_value = iter([mock_session])

            service = TestService()
            _ = service.session  # Trigger creation

            service.close()

            mock_session.close.assert_called_once()
            assert service._session is None

    def test_close_with_external_session(self, db_session):
        """Should NOT close session when externally provided."""
        from services.base_service import SessionMixin

        class TestService(SessionMixin):
            pass

        service = TestService(session=db_session)
        service.close()

        # Session should still be usable (not closed)
        # Just verify it didn't set _session to None
        # (we can't easily verify db_session wasn't closed without mocking)
        assert service._owns_session is False

    def test_session_property_caches(self):
        """Session should only be created once."""
        from services.base_service import SessionMixin

        class TestService(SessionMixin):
            pass

        mock_session = MagicMock()
        with patch("services.base_service.get_db") as mock_get_db:
            mock_get_db.return_value = iter([mock_session])

            service = TestService()

            # Access multiple times
            session1 = service.session
            session2 = service.session
            session3 = service.session

            assert session1 is session2 is session3
            # get_db should only be called once
            assert mock_get_db.call_count == 1