"""
Pension data synchronization service.
Integrates pension scrapers with database storage.
"""

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
import re

from db.models import Account, Balance
from config.constants import AccountType, Institution, SyncType
from services.base_service import BaseSyncService, SyncResult
from scrapers.pensions.migdal_pension_client import (
    MigdalEmailMFARetriever,
    MigdalSeleniumMFAAutomator
)
from scrapers.pensions.phoenix_pension_client import (
    PhoenixEmailMFARetriever,
    PhoenixSeleniumMFAAutomator
)
from scrapers.base.email_retriever import EmailConfig, MFAConfig


class PensionService(BaseSyncService):
    """
    Service for synchronizing pension data with the database.
    Inherits common database operations from BaseSyncService.
    """

    def sync_migdal(
        self,
        user_id: str,
        email_address: str,
        email_password: str,
        headless: bool = True
    ) -> SyncResult:
        """
        Sync Migdal pension data.

        Args:
            user_id: Migdal user ID
            email_address: Email for MFA
            email_password: Email password (app password)
            headless: Run browser in headless mode (default: True)

        Returns:
            SyncResult with sync operation details
        """
        result = SyncResult()
        automator = None

        try:
            with self.sync_transaction(SyncType.PENSION, Institution.MIGDAL) as sync_record:
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
                    'id_selector': "input#username[type='number']",
                    'login_button_selector': 'button[type="submit"]',
                    'email_label_selector': 'label[for="otpToEmail"]',
                    'continue_button_selector': 'button.form-btn'
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
                        pension_account = self.get_or_create_account(
                            account_type=AccountType.PENSION,
                            institution=Institution.MIGDAL,
                            account_number=user_id,
                            account_name="Migdal Pension"
                        )
                        result.accounts_synced += 1

                        if self.save_balance(pension_account, pension_amount):
                            result.balances_added += 1
                        else:
                            result.balances_updated += 1

                if financial_data.get('keren_histalmut_balance'):
                    keren_amount = self._parse_amount(financial_data['keren_histalmut_balance'])
                    if keren_amount is not None:
                        keren_account = self.get_or_create_account(
                            account_type=AccountType.SAVINGS,
                            institution=Institution.MIGDAL,
                            account_number=f"{user_id}_keren",
                            account_name="Migdal Keren Hishtalmut"
                        )
                        result.accounts_synced += 1

                        if self.save_balance(keren_account, keren_amount):
                            result.balances_added += 1
                        else:
                            result.balances_updated += 1

                # Update sync record
                sync_record.records_added = result.balances_added
                sync_record.records_updated = result.balances_updated

                result.success = True

        except Exception as e:
            result.error_message = str(e)

        finally:
            if automator:
                automator.cleanup()

        return result

    def sync_phoenix(
        self,
        user_id: str,
        email_address: str,
        email_password: str,
        headless: bool = True
    ) -> SyncResult:
        """
        Sync Phoenix pension data.

        Args:
            user_id: Phoenix user ID
            email_address: Email for MFA
            email_password: Email password (app password)
            headless: Run browser in headless mode (default: True)

        Returns:
            SyncResult with sync operation details
        """
        result = SyncResult()
        automator = None

        try:
            with self.sync_transaction(SyncType.PENSION, Institution.PHOENIX) as sync_record:
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
                    'mfa_field': 'input[name="otpCode"]',
                    'mfa_submit_button': 'button[type="submit"]'
                }

                success = automator.login(site_url, credentials, selectors)
                if not success:
                    raise Exception("Failed to login to Phoenix")

                # Extract financial data
                financial_data = automator.extract_financial_data()
                result.financial_data = financial_data

                # Parse and save individual balances
                if financial_data.get('pension_balance'):
                    pension_amount = self._parse_amount(financial_data['pension_balance'])
                    if pension_amount is not None:
                        pension_account = self.get_or_create_account(
                            account_type=AccountType.PENSION,
                            institution=Institution.PHOENIX,
                            account_number=user_id,
                            account_name="Phoenix Pension"
                        )
                        result.accounts_synced += 1
                        if self.save_balance(pension_account, pension_amount):
                            result.balances_added += 1
                        else:
                            result.balances_updated += 1

                if financial_data.get('keren_histalmut_balance'):
                    keren_amount = self._parse_amount(financial_data['keren_histalmut_balance'])
                    if keren_amount is not None:
                        keren_account = self.get_or_create_account(
                            account_type=AccountType.SAVINGS,
                            institution=Institution.PHOENIX,
                            account_number=f"{user_id}_keren",
                            account_name="Phoenix Keren Hishtalmut"
                        )
                        result.accounts_synced += 1
                        if self.save_balance(keren_account, keren_amount):
                            result.balances_added += 1
                        else:
                            result.balances_updated += 1

                if financial_data.get('managers_insurance_balance'):
                    insurance_amount = self._parse_amount(financial_data['managers_insurance_balance'])
                    if insurance_amount is not None:
                        insurance_account = self.get_or_create_account(
                            account_type=AccountType.PENSION,
                            institution=Institution.PHOENIX,
                            account_number=f"{user_id}_insurance",
                            account_name="Phoenix Managers Insurance"
                        )
                        result.accounts_synced += 1
                        if self.save_balance(insurance_account, insurance_amount):
                            result.balances_added += 1
                        else:
                            result.balances_updated += 1

                if financial_data.get('gemel_balance'):
                    gemel_amount = self._parse_amount(financial_data['gemel_balance'])
                    if gemel_amount is not None:
                        gemel_account = self.get_or_create_account(
                            account_type=AccountType.SAVINGS,
                            institution=Institution.PHOENIX,
                            account_number=f"{user_id}_gemel",
                            account_name="Phoenix Gemel"
                        )
                        result.accounts_synced += 1
                        if self.save_balance(gemel_account, gemel_amount):
                            result.balances_added += 1
                        else:
                            result.balances_updated += 1

                # Update sync record
                sync_record.records_added = result.balances_added
                sync_record.records_updated = result.balances_updated

                result.success = True

        except Exception as e:
            result.error_message = str(e)

        finally:
            if automator:
                automator.cleanup()

        return result

    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """
        Parse amount from string (e.g., "₪123,456" or "123456").

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
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    def get_pension_balances(
        self,
        institution: Optional[str] = None,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get recent balances for pension accounts.

        Args:
            institution: Optional institution filter ('migdal', 'phoenix')
            limit: Maximum number of records per account

        Returns:
            List of balance dictionaries
        """
        balances = self.get_balances_by_type(
            AccountType.PENSION, institution=institution, limit=limit
        )

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