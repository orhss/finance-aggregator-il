"""
Credit card data synchronization service
Integrates credit card scrapers with database storage
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from db.models import Account, Transaction as DBTransaction, SyncHistory
from scrapers.credit_cards.cal_credit_card_client import (
    CALCreditCardScraper,
    CALCredentials,
    CardAccount,
    Transaction,
    TransactionStatus,
    TransactionType,
    CALScraperError
)


class CreditCardSyncResult:
    """Result of a credit card sync operation"""

    def __init__(self):
        self.success = False
        self.cards_synced = 0
        self.transactions_added = 0
        self.transactions_updated = 0
        self.error_message: Optional[str] = None
        self.sync_history_id: Optional[int] = None


class CreditCardService:
    """
    Service for synchronizing credit card data with the database
    """

    def __init__(self, db_session: Session):
        """
        Initialize credit card service

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    def sync_cal(
        self,
        username: str,
        password: str,
        months_back: int = 3,
        months_forward: int = 1,
        headless: bool = True
    ) -> CreditCardSyncResult:
        """
        Sync CAL credit card data

        Args:
            username: CAL username
            password: CAL password
            months_back: Number of months to fetch backwards (default: 3)
            months_forward: Number of months to fetch forward (default: 1)
            headless: Run browser in headless mode (default: True)

        Returns:
            CreditCardSyncResult with sync operation details
        """
        result = CreditCardSyncResult()
        sync_record = None

        try:
            # Create sync history record
            sync_record = SyncHistory(
                sync_type="credit_card",
                institution="cal",
                status="in_progress",
                started_at=datetime.utcnow()
            )
            self.db.add(sync_record)
            self.db.commit()
            result.sync_history_id = sync_record.id

            # Create credentials and scraper
            credentials = CALCredentials(username=username, password=password)
            scraper = CALCreditCardScraper(credentials, headless=headless)

            # Scrape transactions
            card_accounts = scraper.scrape(months_back=months_back, months_forward=months_forward)

            if not card_accounts:
                raise CALScraperError("No card accounts found for CAL")

            # Process each card account
            for card_account in card_accounts:
                # Get or create account in database
                db_account = self._get_or_create_account(
                    institution="cal",
                    account_number=card_account.account_number,
                    card_unique_id=card_account.card_unique_id
                )
                result.cards_synced += 1

                # Save transactions
                for transaction in card_account.transactions:
                    if self._save_transaction(db_account, transaction):
                        result.transactions_added += 1
                    else:
                        result.transactions_updated += 1

            # Update sync record
            sync_record.status = "success"
            sync_record.completed_at = datetime.utcnow()
            sync_record.records_added = result.transactions_added
            sync_record.records_updated = result.transactions_updated
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
        institution: str,
        account_number: str,
        card_unique_id: Optional[str] = None
    ) -> Account:
        """
        Get existing account or create new one

        Args:
            institution: Institution name
            account_number: Account number (last 4 digits for cards)
            card_unique_id: Unique card identifier

        Returns:
            Account model instance
        """
        # Try to find existing account
        account = self.db.query(Account).filter(
            Account.account_type == "credit_card",
            Account.institution == institution,
            Account.account_number == account_number
        ).first()

        if account:
            # Update last synced time
            account.last_synced_at = datetime.utcnow()
            if card_unique_id:
                account.card_unique_id = card_unique_id
            self.db.commit()
            return account

        # Create new account
        account = Account(
            account_type="credit_card",
            institution=institution,
            account_number=account_number,
            card_unique_id=card_unique_id,
            account_name=f"CAL Card ****{account_number}",
            last_synced_at=datetime.utcnow()
        )
        self.db.add(account)
        self.db.commit()

        return account

    def _save_transaction(
        self,
        account: Account,
        transaction: Transaction
    ) -> bool:
        """
        Save transaction to database with deduplication

        Args:
            account: Account model instance
            transaction: Transaction from scraper

        Returns:
            True if new transaction was added, False if existing was updated
        """
        # Parse dates
        transaction_date = datetime.fromisoformat(transaction.date).date()
        processed_date = datetime.fromisoformat(transaction.processed_date).date()

        # Build unique identifier
        # For CAL: use transaction_id if available, otherwise use composite key
        transaction_id = transaction.identifier if transaction.identifier else None

        # Check if transaction already exists
        query = self.db.query(DBTransaction).filter(
            DBTransaction.account_id == account.id,
            DBTransaction.transaction_date == transaction_date,
            DBTransaction.description == transaction.description,
            DBTransaction.original_amount == transaction.original_amount
        )

        if transaction_id:
            # If we have a transaction ID, also match on that
            query = query.filter(DBTransaction.transaction_id == transaction_id)

        existing_transaction = query.first()

        if existing_transaction:
            # Update existing transaction
            existing_transaction.processed_date = processed_date
            existing_transaction.charged_amount = transaction.charged_amount
            existing_transaction.charged_currency = transaction.charged_currency
            existing_transaction.status = transaction.status.value
            existing_transaction.transaction_type = transaction.transaction_type.value
            existing_transaction.category = transaction.category
            existing_transaction.memo = transaction.memo

            if transaction.installments:
                existing_transaction.installment_number = transaction.installments.number
                existing_transaction.installment_total = transaction.installments.total

            self.db.commit()
            return False

        # Create new transaction
        db_transaction = DBTransaction(
            account_id=account.id,
            transaction_id=transaction_id,
            transaction_date=transaction_date,
            processed_date=processed_date,
            description=transaction.description,
            original_amount=transaction.original_amount,
            original_currency=transaction.original_currency,
            charged_amount=transaction.charged_amount,
            charged_currency=transaction.charged_currency,
            transaction_type=transaction.transaction_type.value,
            status=transaction.status.value,
            category=transaction.category,
            memo=transaction.memo,
            installment_number=transaction.installments.number if transaction.installments else None,
            installment_total=transaction.installments.total if transaction.installments else None
        )

        try:
            self.db.add(db_transaction)
            self.db.commit()
            return True
        except IntegrityError:
            # Constraint violation - transaction already exists
            self.db.rollback()
            return False

    def get_card_transactions(
        self,
        institution: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get credit card transactions

        Args:
            institution: Optional institution filter
            status: Optional status filter ('pending', 'completed')
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of records

        Returns:
            List of transaction dictionaries
        """
        query = self.db.query(DBTransaction).join(Account)

        # Filter by account type
        query = query.filter(Account.account_type == "credit_card")

        # Apply filters
        if institution:
            query = query.filter(Account.institution == institution)

        if status:
            query = query.filter(DBTransaction.status == status)

        if start_date:
            query = query.filter(DBTransaction.transaction_date >= start_date.date())

        if end_date:
            query = query.filter(DBTransaction.transaction_date <= end_date.date())

        # Order by date descending
        query = query.order_by(DBTransaction.transaction_date.desc())
        query = query.limit(limit)

        transactions = query.all()

        return [
            {
                "id": t.id,
                "account_number": t.account.account_number,
                "institution": t.account.institution,
                "date": t.transaction_date.isoformat(),
                "processed_date": t.processed_date.isoformat() if t.processed_date else None,
                "description": t.description,
                "original_amount": t.original_amount,
                "original_currency": t.original_currency,
                "charged_amount": t.charged_amount,
                "charged_currency": t.charged_currency,
                "status": t.status,
                "transaction_type": t.transaction_type,
                "category": t.category,
                "installments": f"{t.installment_number}/{t.installment_total}" if t.installment_number else None
            }
            for t in transactions
        ]