"""
Broker data synchronization service.
Integrates broker scrapers with database storage.
"""

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from db.models import Account, Balance
from config.constants import AccountType, Institution, SyncType
from services.base_service import BaseSyncService, SyncResult
from scrapers.brokers.excellence_broker_client import BrokerClientFactory
from scrapers.base.broker_base import LoginCredentials, BrokerAPIError
from scrapers.brokers.meitav_broker_client import (
    MeitavBrokerScraper,
    MeitavCredentials,
    MeitavScraperError
)


class BrokerService(BaseSyncService):
    """
    Service for synchronizing broker data with the database.
    Inherits common database operations from BaseSyncService.
    """

    def sync_excellence(
        self,
        username: str,
        password: str,
        headless: bool = True,
        currency: str = "ILS"
    ) -> SyncResult:
        """
        Sync Excellence broker data.

        Args:
            username: Excellence username
            password: Excellence password
            headless: Run browser in headless mode (default: True)
            currency: Currency for balance retrieval (default: ILS)

        Returns:
            SyncResult with sync operation details
        """
        result = SyncResult()
        client = None

        try:
            with self.sync_transaction(SyncType.BROKER, Institution.EXCELLENCE) as sync_record:
                result.sync_history_id = sync_record.id

                # Create credentials and client
                credentials = LoginCredentials(user=username, password=password)
                from scrapers.brokers.excellence_broker_client import ExtraDeProAPIClient
                client = ExtraDeProAPIClient(credentials, headless=headless)

                # Login
                client.login()

                # Get accounts
                broker_accounts = client.get_accounts()

                if not broker_accounts:
                    raise BrokerAPIError("No accounts found for Excellence broker")

                # Process each account
                for broker_account in broker_accounts:
                    # Get or create account in database (no commit - handled by context)
                    db_account = self.get_or_create_account(
                        account_type=AccountType.BROKER,
                        institution=Institution.EXCELLENCE,
                        account_number=broker_account.key,
                        account_name=broker_account.name
                    )
                    result.accounts_synced += 1

                    # Get balance
                    balance_info = client.get_balance(broker_account, currency)

                    # Save balance to database (no commit - handled by context)
                    is_new = self.save_balance(
                        account=db_account,
                        total_amount=balance_info.total_amount,
                        available=balance_info.available,
                        used=balance_info.used,
                        blocked=balance_info.blocked,
                        profit_loss=balance_info.profit_loss,
                        profit_loss_percentage=balance_info.profit_loss_percentage,
                        currency=currency
                    )

                    if is_new:
                        result.balances_added += 1
                    else:
                        result.balances_updated += 1

                # Logout
                client.logout()

                # Update sync record
                sync_record.records_added = result.balances_added
                sync_record.records_updated = result.balances_updated

                result.success = True

        except Exception as e:
            result.error_message = str(e)
        finally:
            # Ensure browser is closed even on error
            if client:
                try:
                    client.cleanup()
                except Exception:
                    pass

        return result

    def sync_meitav(
        self,
        username: str,
        password: str,
        headless: bool = True,
        currency: str = "ILS"
    ) -> SyncResult:
        """
        Sync Meitav broker data.

        Args:
            username: Meitav card number
            password: Meitav password
            headless: Run browser in headless mode
            currency: Currency for balance retrieval (default: ILS)

        Returns:
            SyncResult with sync operation details
        """
        result = SyncResult()

        try:
            with self.sync_transaction(SyncType.BROKER, Institution.MEITAV) as sync_record:
                result.sync_history_id = sync_record.id

                # Create credentials and scraper
                credentials = MeitavCredentials(username=username, password=password)
                scraper = MeitavBrokerScraper(credentials, headless=headless)

                # Scrape account data
                account_data = scraper.scrape()

                # Get or create account in database
                db_account = self.get_or_create_account(
                    account_type=AccountType.BROKER,
                    institution=Institution.MEITAV,
                    account_number=account_data.account_number,
                    account_name=f"Meitav {account_data.account_number}"
                )
                result.accounts_synced = 1

                # Save balance to database
                is_new = self.save_balance(
                    account=db_account,
                    total_amount=account_data.balance.total_value,
                    available=account_data.balance.cash_balance,
                    used=None,
                    blocked=None,
                    profit_loss=account_data.balance.change_from_cost,
                    profit_loss_percentage=account_data.balance.change_from_cost_percent,
                    currency=currency
                )

                if is_new:
                    result.balances_added = 1
                else:
                    result.balances_updated = 1

                # Update sync record
                sync_record.records_added = result.balances_added
                sync_record.records_updated = result.balances_updated

                result.success = True

        except MeitavScraperError as e:
            result.error_message = str(e)
        except Exception as e:
            result.error_message = str(e)

        return result

    def get_account_balances(
        self,
        institution: Optional[str] = None,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get recent balances for broker accounts.

        Args:
            institution: Optional institution filter
            limit: Maximum number of records per account

        Returns:
            List of balance dictionaries
        """
        balances = self.get_balances_by_type(
            AccountType.BROKER, institution=institution, limit=limit
        )

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