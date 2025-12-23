"""
Pension data synchronization service
Integrates pension scrapers with database storage
"""

from datetime import datetime, date
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
import re

from db.models import Account, Balance, SyncHistory
from scrapers.pensions.migdal_pension_client import (
    MigdalEmailMFARetriever,
    MigdalSeleniumMFAAutomator
)
from scrapers.pensions.phoenix_pension_client import (
    PhoenixEmailMFARetriever,
    PhoenixSeleniumMFAAutomator
)
from scrapers.base.email_retriever import (
    EmailConfig,
    MFAConfig
)


class PensionSyncResult:
    """Result of a pension sync operation"""

    def __init__(self):
        self.success = False
        self.accounts_synced = 0
        self.balances_added = 0
        self.error_message: Optional[str] = None
        self.sync_history_id: Optional[int] = None
        self.financial_data: Optional[Dict[str, Any]] = None


class PensionService:
    """
    Service for synchronizing pension data with the database
    """

    def __init__(self, db_session: Session):
        """
        Initialize pension service

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    def sync_migdal(
        self,
        user_id: str,
        email_address: str,
        email_password: str,
        headless: bool = True
    ) -> PensionSyncResult:
        """
        Sync Migdal pension data

        Args:
            user_id: Migdal user ID
            email_address: Email for MFA
            email_password: Email password (app password)
            headless: Run browser in headless mode (default: True)

        Returns:
            PensionSyncResult with sync operation details
        """
        result = PensionSyncResult()
        sync_record = None
        automator = None

        try:
            # Create sync history record
            sync_record = SyncHistory(
                sync_type="pension",
                institution="migdal",
                status="in_progress",
                started_at=datetime.utcnow()
            )
            self.db.add(sync_record)
            self.db.commit()
            result.sync_history_id = sync_record.id

            # Configure email and MFA
            email_config = EmailConfig(
                email_address=email_address,
                password=email_password
            )

            mfa_config = MFAConfig(
                sender_email="noreply@migdal.co.il",
                sender_name="Migdal",
                code_pattern=r'\b\d{6}\b'
            )

            # Create retriever and automator
            email_retriever = MigdalEmailMFARetriever(email_config, mfa_config)
            automator = MigdalSeleniumMFAAutomator(email_retriever, headless=headless)

            # Login
            site_url = "https://my.migdal.co.il/mymigdal/process/login"
            credentials = {'id': user_id}
            selectors = {
                'id_field': 'input[name="idNumber"]',
                'continue_button': 'button.submit-button'
            }

            success = automator.login(site_url, credentials, selectors)
            if not success:
                raise Exception("Failed to login to Migdal")

            # Extract financial data
            financial_data = automator.extract_financial_data()
            result.financial_data = financial_data

            # Parse and save balances
            if financial_data.get('pension_balance'):
                pension_amount = self._parse_amount(financial_data['pension_balance'])
                if pension_amount is not None:
                    # Get or create pension account
                    pension_account = self._get_or_create_account(
                        account_type="pension",
                        institution="migdal",
                        account_number=user_id,
                        account_name="Migdal Pension"
                    )
                    result.accounts_synced += 1

                    # Save balance
                    if self._save_balance(pension_account, pension_amount):
                        result.balances_added += 1

            if financial_data.get('keren_histalmut_balance'):
                keren_amount = self._parse_amount(financial_data['keren_histalmut_balance'])
                if keren_amount is not None:
                    # Get or create keren account
                    keren_account = self._get_or_create_account(
                        account_type="savings",
                        institution="migdal",
                        account_number=f"{user_id}_keren",
                        account_name="Migdal Keren Hishtalmut"
                    )
                    result.accounts_synced += 1

                    # Save balance
                    if self._save_balance(keren_account, keren_amount):
                        result.balances_added += 1

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

        finally:
            # Cleanup
            if automator:
                automator.cleanup()

        return result

    def sync_phoenix(
        self,
        user_id: str,
        email_address: str,
        email_password: str,
        headless: bool = True
    ) -> PensionSyncResult:
        """
        Sync Phoenix pension data

        Args:
            user_id: Phoenix user ID
            email_address: Email for MFA
            email_password: Email password (app password)
            headless: Run browser in headless mode (default: True)

        Returns:
            PensionSyncResult with sync operation details
        """
        result = PensionSyncResult()
        sync_record = None
        automator = None

        try:
            # Create sync history record
            sync_record = SyncHistory(
                sync_type="pension",
                institution="phoenix",
                status="in_progress",
                started_at=datetime.utcnow()
            )
            self.db.add(sync_record)
            self.db.commit()
            result.sync_history_id = sync_record.id

            # Configure email and MFA
            email_config = EmailConfig(
                email_address=email_address,
                password=email_password
            )

            mfa_config = MFAConfig(
                sender_email="fnxnoreplay@fnx.co.il",
                sender_name="Phoenix",
                code_pattern=r'\b\d{6}\b'
            )

            # Create retriever and automator
            email_retriever = PhoenixEmailMFARetriever(email_config, mfa_config)
            automator = PhoenixSeleniumMFAAutomator(email_retriever, headless=headless)

            # Login
            site_url = "https://my.fnx.co.il/"
            credentials = {
                'id': user_id,
                'email': email_address
            }
            selectors = {
                'id_field': 'input[name="identityNumber"]',
                'email_field': 'input[name="email"]',
                # 'login_button': 'button[type="submit"]',
                'mfa_field': 'input[name="otpCode"]',
                'mfa_submit_button': 'button[type="submit"]'
            }

            success = automator.login(site_url, credentials, selectors)
            if not success:
                raise Exception("Failed to login to Phoenix")

            # Extract financial data
            financial_data = automator.extract_financial_data()
            result.financial_data = financial_data

            # Parse and save balance
            if financial_data.get('total_investments_savings'):
                total_amount = self._parse_amount(financial_data['total_investments_savings'])
                if total_amount is not None:
                    # Get or create account
                    account = self._get_or_create_account(
                        account_type="pension",
                        institution="phoenix",
                        account_number=user_id,
                        account_name="Phoenix Pension"
                    )
                    result.accounts_synced += 1

                    # Save balance
                    if self._save_balance(account, total_amount):
                        result.balances_added += 1

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

        finally:
            # Cleanup
            if automator:
                automator.cleanup()

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
        total_amount: float,
        currency: str = "ILS"
    ) -> bool:
        """
        Save balance information to database

        Args:
            account: Account model instance
            total_amount: Total balance amount
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
            existing_balance.total_amount = total_amount
            existing_balance.currency = currency
            self.db.commit()
            return False

        # Create new balance record
        balance = Balance(
            account_id=account.id,
            balance_date=today,
            total_amount=total_amount,
            currency=currency
        )
        self.db.add(balance)
        self.db.commit()

        return True

    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """
        Parse amount from string (e.g., "₪123,456" or "123456")

        Args:
            amount_str: Amount string

        Returns:
            Float value or None if parsing fails
        """
        if not amount_str:
            return None

        try:
            # Remove currency symbols and commas
            cleaned = re.sub(r'[₪,$\s]', '', amount_str)
            # Convert to float
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    def get_pension_balances(
        self,
        institution: Optional[str] = None,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get recent balances for pension accounts

        Args:
            institution: Optional institution filter ('migdal', 'phoenix')
            limit: Maximum number of records per account

        Returns:
            List of balance dictionaries
        """
        query = self.db.query(Balance).join(Account)

        if institution:
            query = query.filter(Account.institution == institution)

        query = query.filter(Account.account_type == "pension")
        query = query.order_by(Balance.balance_date.desc())
        query = query.limit(limit)

        balances = query.all()

        return [
            {
                "account_id": b.account_id,
                "account_name": b.account.account_name,
                "account_number": b.account.account_number,
                "institution": b.account.institution,
                "date": b.balance_date.isoformat(),
                "total_amount": b.total_amount,
                "currency": b.currency
            }
            for b in balances
        ]