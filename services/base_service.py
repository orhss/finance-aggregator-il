"""
Base service class with common database operations.
Provides transaction management and shared methods for all sync services.
"""

from contextlib import contextmanager
from datetime import datetime, date
from typing import Optional, Generator
from sqlalchemy.orm import Session

from db.models import Account, Balance, SyncHistory
from config.constants import SyncStatus


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