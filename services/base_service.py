"""
Base service class with common database operations.
Provides transaction management and shared methods for all sync services.
"""

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, Generator, List, Dict, Any
from sqlalchemy.orm import Session

from db.models import Account, Balance, SyncHistory
from db.database import get_db
from config.constants import SyncStatus


class SessionMixin:
    """
    Mixin providing session management for services.

    Provides lazy session creation and proper cleanup. Use for services
    that don't inherit from BaseSyncService (e.g., CategoryService, TagService).

    Usage:
        class MyService(SessionMixin):
            def do_something(self):
                self.session.query(...)

        # With external session (no cleanup needed)
        service = MyService(session=existing_session)

        # With auto-created session (call close() when done)
        service = MyService()
        try:
            service.do_something()
        finally:
            service.close()
    """

    def __init__(self, session: Optional[Session] = None):
        """
        Initialize with optional session.

        Args:
            session: SQLAlchemy session (if None, creates one lazily)
        """
        self._session = session
        self._owns_session = session is None

    @property
    def session(self) -> Session:
        """Get or create session."""
        if self._session is None:
            self._session = next(get_db())
        return self._session

    def close(self):
        """Close session if owned by this instance."""
        if self._owns_session and self._session:
            self._session.close()
            self._session = None


@dataclass
class SyncResult:
    """
    Generic sync operation result.

    Consolidates BrokerSyncResult, PensionSyncResult, and CreditCardSyncResult
    into a single class with optional type-specific fields.

    Usage:
        result = SyncResult()
        result.success = True
        result.accounts_synced = 2
        result.balances_added = 3
    """

    # Common fields
    success: bool = False
    error_message: Optional[str] = None
    sync_history_id: Optional[int] = None

    # Count fields (use appropriate ones based on sync type)
    accounts_synced: int = 0
    cards_synced: int = 0
    balances_added: int = 0
    balances_updated: int = 0
    transactions_added: int = 0
    transactions_updated: int = 0

    # Type-specific optional fields
    financial_data: Optional[Dict[str, Any]] = None  # Pension
    unmapped_categories: List[Dict[str, Any]] = field(default_factory=list)  # Credit Card


class BaseSyncService:
    """
    Base class for sync services.
    Provides common database operations and transaction management.
    """

    def __init__(self, db_session: Session):
        """
        Initialize service with database session.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    @contextmanager
    def sync_transaction(
        self,
        sync_type: str,
        institution: str
    ) -> Generator[SyncHistory, None, None]:
        """
        Context manager for atomic sync operations.

        Creates sync history record, handles commit on success,
        rollback on failure. The sync record is always saved
        (even on failure) to maintain history.

        Args:
            sync_type: Type of sync ('broker', 'pension', 'credit_card')
            institution: Institution name

        Yields:
            SyncHistory record

        Example:
            with self.sync_transaction('broker', 'excellence') as sync_record:
                # Do sync operations - no commits needed
                sync_record.records_added = 10
            # Commit happens automatically on success
        """
        sync_record = SyncHistory(
            sync_type=sync_type,
            institution=institution,
            status=SyncStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )
        self.db.add(sync_record)
        self.db.flush()  # Get ID without committing

        try:
            yield sync_record
            sync_record.status = SyncStatus.SUCCESS
            sync_record.completed_at = datetime.utcnow()
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            # Re-create sync record after rollback to save failure status
            sync_record = SyncHistory(
                sync_type=sync_type,
                institution=institution,
                status=SyncStatus.FAILED,
                started_at=sync_record.started_at,
                completed_at=datetime.utcnow(),
                error_message=str(e)
            )
            self.db.add(sync_record)
            self.db.commit()
            raise

    def get_or_create_account(
        self,
        account_type: str,
        institution: str,
        account_number: str,
        account_name: Optional[str] = None,
        card_unique_id: Optional[str] = None
    ) -> Account:
        """
        Get existing account or create new one.

        Does NOT commit - relies on transaction management from sync_transaction.

        Args:
            account_type: Type of account ('broker', 'pension', 'credit_card', 'savings')
            institution: Institution name
            account_number: Account number
            account_name: Optional account name
            card_unique_id: Optional card unique ID (credit cards only)

        Returns:
            Account model instance
        """
        account = self.db.query(Account).filter(
            Account.account_type == account_type,
            Account.institution == institution,
            Account.account_number == account_number
        ).first()

        if account:
            account.last_synced_at = datetime.utcnow()
            if account_name:
                account.account_name = account_name
            if card_unique_id:
                account.card_unique_id = card_unique_id
            return account

        account = Account(
            account_type=account_type,
            institution=institution,
            account_number=account_number,
            account_name=account_name,
            card_unique_id=card_unique_id,
            last_synced_at=datetime.utcnow()
        )
        self.db.add(account)
        self.db.flush()  # Get ID without committing
        return account

    def save_balance(
        self,
        account: Account,
        total_amount: float,
        balance_date: Optional[date] = None,
        **kwargs
    ) -> bool:
        """
        Save or update balance for an account.

        Does NOT commit - relies on transaction management from sync_transaction.

        Args:
            account: Account model instance
            total_amount: Total balance amount
            balance_date: Date of balance (defaults to today)
            **kwargs: Additional balance fields (available, used, blocked,
                      profit_loss, profit_loss_percentage, currency, etc.)

        Returns:
            True if new balance created, False if updated existing
        """
        if balance_date is None:
            balance_date = date.today()

        existing = self.db.query(Balance).filter(
            Balance.account_id == account.id,
            Balance.balance_date == balance_date
        ).first()

        if existing:
            existing.total_amount = total_amount
            for key, value in kwargs.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            return False

        balance = Balance(
            account_id=account.id,
            balance_date=balance_date,
            total_amount=total_amount,
            **{k: v for k, v in kwargs.items() if hasattr(Balance, k)}
        )
        self.db.add(balance)
        return True

    def get_balances_by_type(
        self,
        account_type: str,
        institution: Optional[str] = None,
        limit: int = 100
    ) -> List[Balance]:
        """
        Get balances for a specific account type.

        Args:
            account_type: Type of account ('broker', 'pension', 'credit_card', 'savings')
            institution: Optional institution filter
            limit: Maximum number of records to return

        Returns:
            List of Balance model instances, ordered by date descending
        """
        query = self.db.query(Balance).join(Account)

        query = query.filter(Account.account_type == account_type)

        if institution:
            query = query.filter(Account.institution == institution)

        query = query.order_by(Balance.balance_date.desc())
        query = query.limit(limit)

        return query.all()