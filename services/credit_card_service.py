"""
Credit card data synchronization service.
Integrates credit card scrapers with database storage.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.exc import IntegrityError

from db.models import Account, Transaction as DBTransaction
from config.constants import AccountType, Institution, SyncType
from config.settings import get_card_holder_name
from services.base_service import BaseSyncService
from services.tag_service import TagService
from scrapers.credit_cards.cal_credit_card_client import (
    CALCreditCardScraper,
    CALCredentials,
    Transaction,
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


class CreditCardService(BaseSyncService):
    """
    Service for synchronizing credit card data with the database.
    Inherits common database operations from BaseSyncService.
    """

    def sync_cal(
        self,
        username: str,
        password: str,
        months_back: int = 3,
        months_forward: int = 1,
        headless: bool = True
    ) -> CreditCardSyncResult:
        """
        Sync CAL credit card data.

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

        try:
            with self.sync_transaction(SyncType.CREDIT_CARD, Institution.CAL) as sync_record:
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
                    # Get or create account in database (no commit - handled by context)
                    db_account = self.get_or_create_account(
                        account_type=AccountType.CREDIT_CARD,
                        institution=Institution.CAL,
                        account_number=card_account.account_number,
                        account_name=f"CAL Card ****{card_account.account_number}",
                        card_unique_id=card_account.card_unique_id
                    )
                    result.cards_synced += 1

                    # Save transactions (no commit per transaction - handled by context)
                    for transaction in card_account.transactions:
                        if self._save_transaction(db_account, transaction):
                            result.transactions_added += 1
                        else:
                            result.transactions_updated += 1

                # Update sync record
                sync_record.records_added = result.transactions_added
                sync_record.records_updated = result.transactions_updated

                result.success = True

        except Exception as e:
            result.error_message = str(e)

        return result

    def _save_transaction(
        self,
        account: Account,
        transaction: Transaction
    ) -> bool:
        """
        Save transaction to database with deduplication.

        Handles three scenarios:
        1. Completed transaction with ID: Match by transaction_id
        2. Pending transaction (no ID): Match by date + merchant + amount
        3. Pending → Completed transition: Match completed txn to existing pending record

        Does NOT commit - relies on transaction management from sync_transaction.

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
        transaction_id = transaction.identifier if transaction.identifier else None

        existing_transaction = None

        if transaction_id:
            # Scenario 1: Has transaction_id - try exact match first
            existing_transaction = self.db.query(DBTransaction).filter(
                DBTransaction.account_id == account.id,
                DBTransaction.transaction_id == transaction_id
            ).first()

            # Scenario 3: If not found and this is completed, check for matching pending transaction
            # This handles the pending → completed transition
            if not existing_transaction and transaction.status.value == 'completed':
                existing_transaction = self.db.query(DBTransaction).filter(
                    DBTransaction.account_id == account.id,
                    DBTransaction.transaction_date == transaction_date,
                    DBTransaction.description == transaction.description,
                    DBTransaction.original_amount == transaction.original_amount,
                    DBTransaction.status == 'pending'
                ).first()
        else:
            # Scenario 2: No transaction_id (pending) - match on date + merchant + amount
            existing_transaction = self.db.query(DBTransaction).filter(
                DBTransaction.account_id == account.id,
                DBTransaction.transaction_date == transaction_date,
                DBTransaction.description == transaction.description,
                DBTransaction.original_amount == transaction.original_amount
            ).first()

        if existing_transaction:
            # Update existing transaction (handles both update and pending→completed transition)
            existing_transaction.transaction_id = transaction_id  # Sets ID when pending→completed
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

        self.db.add(db_transaction)
        self.db.flush()  # Get the transaction ID before committing

        # Auto-tag new transaction
        try:
            tag_service = TagService(session=self.db)
            tags_to_add = []

            # Tag with category
            if transaction.category:
                tags_to_add.append(transaction.category)

            # Tag with card holder name if configured
            if account.account_number:
                holder_name = get_card_holder_name(account.account_number)
                if holder_name:
                    tags_to_add.append(holder_name)

            if tags_to_add:
                tag_service.tag_transaction(db_transaction.id, tags_to_add)
        except Exception:
            pass  # Don't fail sync if tagging fails

        return True

    def get_card_transactions(
        self,
        institution: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get credit card transactions.

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

        query = query.filter(Account.account_type == AccountType.CREDIT_CARD)

        if institution:
            query = query.filter(Account.institution == institution)

        if status:
            query = query.filter(DBTransaction.status == status)

        if start_date:
            query = query.filter(DBTransaction.transaction_date >= start_date.date())

        if end_date:
            query = query.filter(DBTransaction.transaction_date <= end_date.date())

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