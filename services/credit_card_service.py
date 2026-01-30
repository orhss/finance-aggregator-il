"""
Credit card data synchronization service.
Integrates credit card scrapers with database storage.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from db.models import Account, Transaction as DBTransaction
from config.constants import AccountType, Institution, SyncType
from config.settings import get_card_holder_name
from services.base_service import BaseSyncService
from services.tag_service import TagService
from services.category_service import CategoryService
from scrapers.credit_cards.cal_credit_card_client import (
    CALCreditCardScraper,
    CALCredentials,
    Transaction,
    CALScraperError
)
from scrapers.credit_cards.max_credit_card_client import (
    MaxCreditCardScraper,
    MaxCredentials,
    MaxScraperError
)
from scrapers.credit_cards.isracard_credit_card_client import (
    IsracardCreditCardScraper,
    IsracardCredentials,
    IsracardScraperError
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
        self.unmapped_categories: List[Dict[str, Any]] = []  # [{raw_category, count}, ...]


class CreditCardService(BaseSyncService):
    """
    Service for synchronizing credit card data with the database.
    Inherits common database operations from BaseSyncService.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._category_service: Optional[CategoryService] = None
        self._category_cache: Dict[Tuple[str, str], Optional[str]] = {}
        self._unmapped_categories: Dict[str, int] = {}  # {raw_category: count}
        self._current_institution: Optional[str] = None

    @property
    def category_service(self) -> CategoryService:
        """Lazy-load category service"""
        if self._category_service is None:
            self._category_service = CategoryService(session=self.db)
        return self._category_service

    def _reset_category_tracking(self, institution: str):
        """Reset category tracking for a new sync operation"""
        self._category_cache = {}
        self._unmapped_categories = {}
        self._current_institution = institution

    def _get_unmapped_summary(self) -> List[Dict[str, Any]]:
        """Get summary of unmapped categories from current sync"""
        return [
            {'raw_category': cat, 'count': count}
            for cat, count in sorted(
                self._unmapped_categories.items(),
                key=lambda x: x[1],
                reverse=True
            )
        ]

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
        self._reset_category_tracking(Institution.CAL)

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
                        if self._save_transaction(db_account, transaction, Institution.CAL):
                            result.transactions_added += 1
                        else:
                            result.transactions_updated += 1

                # Update sync record
                sync_record.records_added = result.transactions_added
                sync_record.records_updated = result.transactions_updated

                result.success = True
                result.unmapped_categories = self._get_unmapped_summary()

        except Exception as e:
            result.error_message = str(e)

        return result

    def sync_max(
        self,
        username: str,
        password: str,
        months_back: int = 3,
        months_forward: int = 1,
        headless: bool = True
    ) -> CreditCardSyncResult:
        """
        Sync Max credit card data.

        Args:
            username: Max username
            password: Max password
            months_back: Number of months to fetch backwards (default: 3)
            months_forward: Number of months to fetch forward (default: 1)
            headless: Run browser in headless mode (default: True)

        Returns:
            CreditCardSyncResult with sync operation details
        """
        result = CreditCardSyncResult()
        self._reset_category_tracking(Institution.MAX)

        try:
            with self.sync_transaction(SyncType.CREDIT_CARD, Institution.MAX) as sync_record:
                result.sync_history_id = sync_record.id

                # Create credentials and scraper
                credentials = MaxCredentials(username=username, password=password)
                scraper = MaxCreditCardScraper(credentials, headless=headless)

                # Scrape transactions
                card_accounts = scraper.scrape(months_back=months_back, months_forward=months_forward)

                if not card_accounts:
                    raise MaxScraperError("No card accounts found for Max")

                # Process each card account
                for card_account in card_accounts:
                    # Get or create account in database (no commit - handled by context)
                    db_account = self.get_or_create_account(
                        account_type=AccountType.CREDIT_CARD,
                        institution=Institution.MAX,
                        account_number=card_account.account_number,
                        account_name=f"Max Card {card_account.account_number}",
                        card_unique_id=None  # Max doesn't use card_unique_id
                    )
                    result.cards_synced += 1

                    # Save transactions (no commit per transaction - handled by context)
                    for transaction in card_account.transactions:
                        if self._save_transaction(db_account, transaction, Institution.MAX):
                            result.transactions_added += 1
                        else:
                            result.transactions_updated += 1

                # Update sync record
                sync_record.records_added = result.transactions_added
                sync_record.records_updated = result.transactions_updated

                result.success = True
                result.unmapped_categories = self._get_unmapped_summary()

        except Exception as e:
            result.error_message = str(e)

        return result

    def sync_isracard(
        self,
        username: str,
        password: str,
        months_back: int = 3,
        months_forward: int = 1,
        headless: bool = True
    ) -> CreditCardSyncResult:
        """
        Sync Isracard credit card data.

        Args:
            username: Isracard username in format "user_id:card_6_digits"
            password: Isracard password
            months_back: Number of months to fetch backwards (default: 3)
            months_forward: Number of months to fetch forward (default: 1)
            headless: Run browser in headless mode (default: True)

        Returns:
            CreditCardSyncResult with sync operation details
        """
        result = CreditCardSyncResult()
        self._reset_category_tracking(Institution.ISRACARD)

        try:
            with self.sync_transaction(SyncType.CREDIT_CARD, Institution.ISRACARD) as sync_record:
                result.sync_history_id = sync_record.id

                # Parse username (format: "user_id:card_6_digits")
                if ':' in username:
                    user_id, card_6_digits = username.split(':', 1)
                else:
                    raise IsracardScraperError(
                        "Invalid Isracard username format. Expected 'user_id:card_6_digits' "
                        "(e.g., '123456789:123456')"
                    )

                # Create credentials and scraper
                credentials = IsracardCredentials(
                    user_id=user_id,
                    password=password,
                    card_6_digits=card_6_digits
                )
                scraper = IsracardCreditCardScraper(
                    credentials=credentials,
                    base_url="https://digital.isracard.co.il",
                    company_code="11",
                    headless=headless
                )

                # Scrape transactions
                card_accounts = scraper.scrape(months_back=months_back, months_forward=months_forward)

                if not card_accounts:
                    raise IsracardScraperError("No card accounts found for Isracard")

                # Process each card account
                for card_account in card_accounts:
                    # Get or create account in database (no commit - handled by context)
                    db_account = self.get_or_create_account(
                        account_type=AccountType.CREDIT_CARD,
                        institution=Institution.ISRACARD,
                        account_number=card_account.account_number,
                        account_name=f"Isracard Card {card_account.account_number}",
                        card_unique_id=None  # Isracard doesn't use card_unique_id
                    )
                    result.cards_synced += 1

                    # Save transactions (no commit per transaction - handled by context)
                    for transaction in card_account.transactions:
                        if self._save_transaction(db_account, transaction, Institution.ISRACARD):
                            result.transactions_added += 1
                        else:
                            result.transactions_updated += 1

                # Update sync record
                sync_record.records_added = result.transactions_added
                sync_record.records_updated = result.transactions_updated

                result.success = True
                result.unmapped_categories = self._get_unmapped_summary()

        except Exception as e:
            result.error_message = str(e)

        return result

    def _save_transaction(
        self,
        account: Account,
        transaction: Transaction,
        institution: str
    ) -> bool:
        """
        Save transaction to database with deduplication and category normalization.

        Handles three scenarios:
        1. Completed transaction with ID: Match by transaction_id
        2. Pending transaction (no ID): Match by date + merchant + amount
        3. Pending → Completed transition: Match completed txn to existing pending record

        Category handling:
        - raw_category: Original category from provider (always saved)
        - category: Normalized category from mapping table (if mapping exists)

        Does NOT commit - relies on transaction management from sync_transaction.

        Args:
            account: Account model instance
            transaction: Transaction from scraper
            institution: Institution name for category normalization

        Returns:
            True if new transaction was added, False if existing was updated
        """
        # Parse dates
        transaction_date = datetime.fromisoformat(transaction.date).date()
        processed_date = datetime.fromisoformat(transaction.processed_date).date()

        # Build unique identifier
        transaction_id = transaction.identifier if transaction.identifier else None

        # Normalize category
        raw_category = transaction.category
        normalized_category = None

        if raw_category:
            # Has provider category - try provider mapping
            normalized_category = self.category_service.normalize_category_cached(
                institution, raw_category, self._category_cache
            )
            # Track unmapped categories for reporting
            if not normalized_category:
                self._unmapped_categories[raw_category] = self._unmapped_categories.get(raw_category, 0) + 1
        else:
            # No provider category (e.g., Isracard) - try merchant mapping
            normalized_category = self.category_service.normalize_by_merchant(
                transaction.description, institution
            )

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
            existing_transaction.raw_category = raw_category
            existing_transaction.category = normalized_category
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
            raw_category=raw_category,
            category=normalized_category,
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

            # Tag with effective category (normalized if available, otherwise raw)
            effective_cat = normalized_category or raw_category
            if effective_cat:
                tags_to_add.append(effective_cat)

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
                "raw_category": t.raw_category,
                "category": t.category,
                "effective_category": t.effective_category,
                "installments": f"{t.installment_number}/{t.installment_total}" if t.installment_number else None
            }
            for t in transactions
        ]