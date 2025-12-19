"""
Broker data synchronization service
Integrates broker scrapers with database storage
"""

from datetime import datetime, date
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from db.models import Account, Balance, SyncHistory
from scrapers.brokers.excellence_broker_client import (
    ExtraDeProAPIClient,
    BrokerClientFactory
)
from scrapers.base.broker_base import (
    LoginCredentials,
    AccountInfo,
    BalanceInfo,
    BrokerAPIError
)


class BrokerSyncResult:
    """Result of a broker sync operation"""

    def __init__(self):
        self.success = False
        self.accounts_synced = 0
        self.balances_added = 0
        self.error_message: Optional[str] = None
        self.sync_history_id: Optional[int] = None


class BrokerService:
    """
    Service for synchronizing broker data with the database
    """

    def __init__(self, db_session: Session):
        """
        Initialize broker service

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    def sync_excellence(
        self,
        username: str,
        password: str,
        currency: str = "ILS"
    ) -> BrokerSyncResult:
        """
        Sync Excellence broker data

        Args:
            username: Excellence username
            password: Excellence password
            currency: Currency for balance retrieval (default: ILS)

        Returns:
            BrokerSyncResult with sync operation details
        """
        result = BrokerSyncResult()
        sync_record = None

        try:
            # Create sync history record
            sync_record = SyncHistory(
                sync_type="broker",
                institution="excellence",
                status="in_progress",
                started_at=datetime.utcnow()
            )
            self.db.add(sync_record)
            self.db.commit()
            result.sync_history_id = sync_record.id

            # Create credentials and client
            credentials = LoginCredentials(user=username, password=password)
            client = BrokerClientFactory.create_client("extradepro", credentials)

            # Login
            client.login()

            # Get accounts
            broker_accounts = client.get_accounts()

            if not broker_accounts:
                raise BrokerAPIError("No accounts found for Excellence broker")

            # Process each account
            for broker_account in broker_accounts:
                # Get or create account in database
                db_account = self._get_or_create_account(
                    account_type="broker",
                    institution="excellence",
                    account_number=broker_account.key,
                    account_name=broker_account.name
                )
                result.accounts_synced += 1

                # Get balance
                balance_info = client.get_balance(broker_account, currency)

                # Save balance to database
                if self._save_balance(db_account, balance_info, currency):
                    result.balances_added += 1

            # Logout
            client.logout()

            # Update sync record
            sync_record.status = "success"
            sync_record.completed_at = datetime.utcnow()
            sync_record.records_added = result.balances_added
            sync_record.records_updated = result.accounts_synced
            self.db.commit()

            result.success = True

        except Exception as e:
            result.error_message = str(e)
            if sync_record:
                sync_record.status = "failed"
                sync_record.completed_at = datetime.utcnow()
                sync_record.error_message = str(e)
                self.db.commit()

        return result

    def _get_or_create_account(
        self,
        account_type: str,
        institution: str,
        account_number: str,
        account_name: Optional[str] = None
    ) -> Account:
        """
        Get existing account or create new one

        Args:
            account_type: Type of account ('broker', 'pension', 'credit_card')
            institution: Institution name
            account_number: Account number
            account_name: Optional account name

        Returns:
            Account model instance
        """
        # Try to find existing account
        account = self.db.query(Account).filter(
            Account.account_type == account_type,
            Account.institution == institution,
            Account.account_number == account_number
        ).first()

        if account:
            # Update last synced time
            account.last_synced_at = datetime.utcnow()
            if account_name:
                account.account_name = account_name
            self.db.commit()
            return account

        # Create new account
        account = Account(
            account_type=account_type,
            institution=institution,
            account_number=account_number,
            account_name=account_name,
            last_synced_at=datetime.utcnow()
        )
        self.db.add(account)
        self.db.commit()

        return account

    def _save_balance(
        self,
        account: Account,
        balance_info: BalanceInfo,
        currency: str = "ILS"
    ) -> bool:
        """
        Save balance information to database

        Args:
            account: Account model instance
            balance_info: Balance information from scraper
            currency: Currency of the balance

        Returns:
            True if new balance was added, False if updated existing
        """
        today = date.today()

        # Check if balance for today already exists
        existing_balance = self.db.query(Balance).filter(
            Balance.account_id == account.id,
            Balance.balance_date == today
        ).first()

        if existing_balance:
            # Update existing balance
            existing_balance.total_amount = balance_info.total_amount
            existing_balance.available = balance_info.available
            existing_balance.used = balance_info.used
            existing_balance.blocked = balance_info.blocked
            existing_balance.profit_loss = balance_info.profit_loss
            existing_balance.profit_loss_percentage = balance_info.profit_loss_percentage
            existing_balance.currency = currency
            self.db.commit()
            return False

        # Create new balance record
        balance = Balance(
            account_id=account.id,
            balance_date=today,
            total_amount=balance_info.total_amount,
            available=balance_info.available,
            used=balance_info.used,
            blocked=balance_info.blocked,
            profit_loss=balance_info.profit_loss,
            profit_loss_percentage=balance_info.profit_loss_percentage,
            currency=currency
        )
        self.db.add(balance)
        self.db.commit()

        return True

    def get_account_balances(
        self,
        institution: Optional[str] = None,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get recent balances for accounts

        Args:
            institution: Optional institution filter
            limit: Maximum number of records per account

        Returns:
            List of balance dictionaries
        """
        query = self.db.query(Balance).join(Account)

        if institution:
            query = query.filter(Account.institution == institution)

        query = query.filter(Account.account_type == "broker")
        query = query.order_by(Balance.balance_date.desc())
        query = query.limit(limit)

        balances = query.all()

        return [
            {
                "account_id": b.account_id,
                "account_number": b.account.account_number,
                "institution": b.account.institution,
                "date": b.balance_date.isoformat(),
                "total_amount": b.total_amount,
                "profit_loss": b.profit_loss,
                "profit_loss_percentage": b.profit_loss_percentage,
                "currency": b.currency
            }
            for b in balances
        ]