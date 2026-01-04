"""
Isracard Credit Card Scraper
Automated transaction extraction for Israeli Isracard credit cards
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

logger = logging.getLogger(__name__)


# Configuration
@dataclass
class IsracardCredentials:
    """Isracard login credentials"""
    user_id: str  # ID number
    password: str
    card_6_digits: str  # Last 6 digits of card


# Transaction Enums and Models
class TransactionStatus(Enum):
    """Transaction status"""
    COMPLETED = "completed"


class TransactionType(Enum):
    """Transaction type"""
    NORMAL = "normal"  # Regular charge
    INSTALLMENTS = "installments"  # Payment plan


@dataclass
class Installments:
    """Installment information"""
    number: int  # Current installment number
    total: int  # Total number of installments


@dataclass
class Transaction:
    """Standardized transaction model"""
    date: str  # ISO format transaction date
    processed_date: str  # ISO format processing/debit date
    original_amount: float  # Original transaction amount
    original_currency: str  # Original currency
    charged_amount: float  # Amount charged in account currency
    charged_currency: str  # Account currency
    description: str  # Merchant name
    status: TransactionStatus
    transaction_type: TransactionType
    identifier: Optional[int] = None  # Transaction ID
    memo: Optional[str] = None
    category: Optional[str] = None
    installments: Optional[Installments] = None


@dataclass
class CardAccount:
    """Card account with transactions"""
    account_number: str  # Card number
    index: int  # Card index for API calls
    transactions: List[Transaction]


# Exceptions
class IsracardScraperError(Exception):
    """Base exception for Isracard scraper errors"""
    pass


class IsracardLoginError(IsracardScraperError):
    """Login failed"""
    pass


class IsracardAPIError(IsracardScraperError):
    """API request failed"""
    pass


class IsracardChangePasswordError(IsracardScraperError):
    """Password change required"""
    pass


class IsracardCreditCardScraper:
    """
    Automated scraper for Isracard credit card transactions.

    Uses Selenium to establish session and makes API calls to fetch transaction data.
    """

    # Constants
    COUNTRY_CODE = '212'
    ID_TYPE = '1'
    INSTALLMENTS_KEYWORD = 'תשלום'
    DATE_FORMAT = '%d/%m/%Y'

    SHEKEL_CURRENCY_KEYWORD = 'ש"ח'
    ALT_SHEKEL_CURRENCY = 'שח'
    SHEKEL_CURRENCY = 'ILS'

    # Rate limiting
    SLEEP_BETWEEN_REQUESTS = 1.0  # seconds
    TRANSACTIONS_BATCH_SIZE = 10

    def __init__(
        self,
        credentials: IsracardCredentials,
        base_url: str,
        company_code: str,
        headless: bool = True,
        fetch_categories: bool = False
    ):
        """
        Initialize Isracard scraper.

        Args:
            credentials: Login credentials
            base_url: Base URL for the company (e.g., https://digital.isracard.co.il)
            company_code: Company code for API calls
            headless: Run browser in headless mode
            fetch_categories: Fetch additional category information (slower)
        """
        self.credentials = credentials
        self.base_url = base_url
        self.company_code = company_code
        self.headless = headless
        self.fetch_categories = fetch_categories
        self.driver = None
        self.services_url = f"{base_url}/services/ProxyRequestHandler.ashx"

    def setup_driver(self):
        """Setup Chrome WebDriver"""
        logger.info("Setting up Chrome WebDriver...")
        options = Options()
        if self.headless:
            logger.debug("Running in headless mode")
            options.add_argument('--headless')
        else:
            logger.debug("Running in visible mode")

        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36')

        logger.debug("Initializing Chrome driver...")
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(10)
        logger.info("Chrome driver initialized successfully")

    def cleanup(self):
        """Clean up resources"""
        logger.debug("Starting cleanup process...")
        if self.driver:
            logger.debug("Closing Chrome driver...")
            self.driver.quit()
            logger.info("Chrome driver closed successfully")
        else:
            logger.debug("No Chrome driver to close")
        logger.debug("Cleanup completed")

    def get_cookies(self) -> Dict[str, str]:
        """Get cookies as dictionary"""
        cookies = {}
        for cookie in self.driver.get_cookies():
            cookies[cookie['name']] = cookie['value']
        return cookies

    def api_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        method: str = 'GET'
    ) -> Dict[str, Any]:
        """
        Make API request with browser cookies.

        Args:
            endpoint: API endpoint path or full URL
            params: Query parameters
            data: POST data
            method: HTTP method

        Returns:
            API response as dictionary
        """
        # Build URL
        if endpoint.startswith('http'):
            url = endpoint
        else:
            url = f"{self.services_url}?{endpoint}" if '=' in endpoint else self.services_url
            if params:
                url += '&' + '&'.join(f"{k}={v}" for k, v in params.items())

        cookies = self.get_cookies()

        # Add headers to match browser requests
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': f'{self.base_url}/personalarea/Login',
            'Origin': self.base_url,
            'Content-Type': 'application/json;charset=UTF-8',
        }

        try:
            if method == 'POST':
                response = requests.post(url, json=data, cookies=cookies, headers=headers, timeout=30)
            else:
                response = requests.get(url, cookies=cookies, headers=headers, timeout=30)

            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            raise IsracardAPIError(f"API request failed: {e}")

    def login(self) -> bool:
        """
        Perform login to Isracard website.

        Returns:
            True if login successful

        Raises:
            IsracardLoginError: If login fails
            IsracardChangePasswordError: If password change required
        """
        try:
            if not self.driver:
                self.setup_driver()

            logger.info(f"Step 1/4: Navigating to {self.base_url}...")
            login_url = f"{self.base_url}/personalarea/Login"
            self.driver.get(login_url)

            # Wait for page to load and establish session
            # Need to wait longer to ensure cookies and session are established
            logger.debug("Waiting for session establishment...")
            time.sleep(5)

            logger.info("Step 2/4: Validating credentials...")

            # Step 1: Validate ID and card suffix
            validate_params = {
                'reqName': 'ValidateIdData'
            }
            validate_data = {
                'id': self.credentials.user_id,
                'cardSuffix': self.credentials.card_6_digits,
                'countryCode': self.COUNTRY_CODE,
                'idType': self.ID_TYPE,
                'checkLevel': '1',
                'companyCode': self.company_code,
            }

            logger.debug("Sending validation request...")
            validate_result = self.api_request(
                'reqName=ValidateIdData',
                data=validate_data,
                method='POST'
            )

            # Check validation response
            if not validate_result or not validate_result.get('Header') or validate_result['Header'].get('Status') != '1':
                raise IsracardLoginError("Unknown error during validation")

            if 'ValidateIdDataBean' not in validate_result:
                raise IsracardLoginError("Validation failed - no ValidateIdDataBean in response")

            validate_bean = validate_result['ValidateIdDataBean']
            return_code = validate_bean.get('returnCode')

            logger.debug(f"Validation return code: {return_code}")

            if return_code == '4':
                raise IsracardChangePasswordError("Password change required")

            if return_code != '1':
                raise IsracardLoginError(f"Validation failed with return code: {return_code}")

            # Step 2: Perform login
            logger.info("Step 3/4: Logging in...")
            user_name = validate_bean.get('userName')
            if not user_name:
                raise IsracardLoginError("No userName in validation response")

            login_data = {
                'KodMishtamesh': user_name,
                'MisparZihuy': self.credentials.user_id,
                'Sisma': self.credentials.password,
                'cardSuffix': self.credentials.card_6_digits,
                'countryCode': self.COUNTRY_CODE,
                'idType': self.ID_TYPE,
            }

            logger.debug("Sending login request...")
            login_result = self.api_request(
                'reqName=performLogonI',
                data=login_data,
                method='POST'
            )

            logger.debug(f"Login response status: {login_result.get('status')}")

            if not login_result:
                raise IsracardLoginError("No response from login request")

            status = login_result.get('status')

            if status == '1':
                logger.info("Step 4/4: Login successful!")
                return True
            elif status == '3':
                raise IsracardChangePasswordError("Password change required")
            else:
                raise IsracardLoginError("Invalid password or credentials")

        except IsracardChangePasswordError:
            raise
        except IsracardLoginError:
            raise
        except TimeoutException as e:
            raise IsracardLoginError(f"Timeout during login: {e}")
        except Exception as e:
            raise IsracardLoginError(f"Login failed: {e}")

    def convert_currency(self, currency_str: str) -> str:
        """Convert currency string to standard code"""
        if currency_str in [self.SHEKEL_CURRENCY_KEYWORD, self.ALT_SHEKEL_CURRENCY]:
            return self.SHEKEL_CURRENCY
        return currency_str

    def get_installments_info(self, more_info: Optional[str]) -> Optional[Installments]:
        """Extract installment information from moreInfo field"""
        if not more_info or self.INSTALLMENTS_KEYWORD not in more_info:
            return None

        import re
        matches = re.findall(r'\d+', more_info)
        if len(matches) >= 2:
            return Installments(
                number=int(matches[0]),
                total=int(matches[1])
            )

        return None

    def get_transaction_type(self, more_info: Optional[str]) -> TransactionType:
        """Determine transaction type"""
        if self.get_installments_info(more_info):
            return TransactionType.INSTALLMENTS
        return TransactionType.NORMAL

    def convert_transaction(self, txn: Dict[str, Any], processed_date: str) -> Transaction:
        """
        Convert raw API transaction to Transaction object.

        Args:
            txn: Raw transaction data from API
            processed_date: Default processed date for the transaction

        Returns:
            Transaction object
        """
        is_outbound = txn.get('dealSumOutbound', False)

        # Get transaction date
        txn_date_str = txn.get('fullPurchaseDateOutbound') if is_outbound else txn.get('fullPurchaseDate')
        if txn_date_str:
            txn_date = datetime.strptime(txn_date_str, self.DATE_FORMAT)
        else:
            txn_date = datetime.now()

        # Get processed date
        if txn.get('fullPaymentDate'):
            current_processed_date = datetime.strptime(txn['fullPaymentDate'], self.DATE_FORMAT).isoformat()
        else:
            current_processed_date = processed_date

        # Get amounts
        original_amount = txn.get('dealSumOutbound') if is_outbound else txn.get('dealSum', 0)
        charged_amount = txn.get('paymentSumOutbound') if is_outbound else txn.get('paymentSum', 0)

        # Get currencies
        original_currency = self.convert_currency(
            txn.get('currentPaymentCurrency') or txn.get('currencyId', self.SHEKEL_CURRENCY)
        )
        charged_currency = self.convert_currency(txn.get('currencyId', self.SHEKEL_CURRENCY))

        # Get identifier
        identifier_str = txn.get('voucherNumberRatzOutbound') if is_outbound else txn.get('voucherNumberRatz')
        identifier = int(identifier_str) if identifier_str and identifier_str != '000000000' else None

        # Get description
        description = txn.get('fullSupplierNameOutbound') if is_outbound else txn.get('fullSupplierNameHeb', '')

        # Get installments
        more_info = txn.get('moreInfo', '')
        installments = self.get_installments_info(more_info)

        return Transaction(
            transaction_type=self.get_transaction_type(more_info),
            identifier=identifier,
            date=txn_date.isoformat(),
            processed_date=current_processed_date,
            original_amount=-original_amount,  # Negative for expenses
            original_currency=original_currency,
            charged_amount=-charged_amount,  # Negative for expenses
            charged_currency=charged_currency,
            description=description,
            memo=more_info,
            installments=installments,
            status=TransactionStatus.COMPLETED,
        )

    def convert_transactions(self, txns: List[Dict[str, Any]], processed_date: str) -> List[Transaction]:
        """Convert list of raw transactions to Transaction objects"""
        # Filter out invalid transactions
        filtered_txns = [
            txn for txn in txns
            if txn.get('dealSumType') != '1'
            and txn.get('voucherNumberRatz') != '000000000'
            and txn.get('voucherNumberRatzOutbound') != '000000000'
        ]

        return [self.convert_transaction(txn, processed_date) for txn in filtered_txns]

    def fetch_accounts_for_month(self, year: int, month: int) -> List[Dict[str, Any]]:
        """
        Fetch accounts (cards) for a specific month.

        Args:
            year: Year
            month: Month (1-12)

        Returns:
            List of account dictionaries
        """
        billing_date = f"{year}-{month:02d}-01"

        params = {
            'reqName': 'DashboardMonth',
            'actionCode': '0',
            'billingDate': billing_date,
            'format': 'Json'
        }

        logger.debug(f"Fetching accounts for {year}-{month:02d}...")
        data = self.api_request(self.services_url, params=params)

        if not data or data.get('Header', {}).get('Status') != '1':
            return []

        dashboard_bean = data.get('DashboardMonthBean')
        if not dashboard_bean or 'cardsCharges' not in dashboard_bean:
            return []

        cards_charges = dashboard_bean['cardsCharges']
        accounts = []

        for card_charge in cards_charges:
            billing_date_str = card_charge.get('billingDate', '')
            if billing_date_str:
                processed_date = datetime.strptime(billing_date_str, self.DATE_FORMAT).isoformat()
            else:
                processed_date = datetime.now().isoformat()

            accounts.append({
                'index': int(card_charge.get('cardIndex', 0)),
                'accountNumber': card_charge.get('cardNumber', ''),
                'processedDate': processed_date,
            })

        return accounts

    def fetch_transactions_for_month(
        self,
        year: int,
        month: int,
        start_date: datetime
    ) -> Dict[str, CardAccount]:
        """
        Fetch transactions for a specific month.

        Args:
            year: Year
            month: Month (1-12)
            start_date: Filter transactions after this date

        Returns:
            Dictionary mapping account numbers to CardAccount objects
        """
        # Fetch accounts first
        accounts = self.fetch_accounts_for_month(year, month)
        if not accounts:
            logger.debug(f"No accounts found for {year}-{month:02d}")
            return {}

        # Fetch transactions
        params = {
            'reqName': 'CardsTransactionsList',
            'month': f"{month:02d}",
            'year': str(year),
            'requiredDate': 'N',
        }

        # Rate limiting
        time.sleep(self.SLEEP_BETWEEN_REQUESTS)

        logger.debug(f"Fetching transactions for {year}-{month:02d}...")
        data = self.api_request(self.services_url, params=params)

        if not data or data.get('Header', {}).get('Status') != '1':
            logger.debug(f"No transaction data for {year}-{month:02d}")
            return {}

        cards_bean = data.get('CardsTransactionsListBean')
        if not cards_bean:
            return {}

        # Process transactions for each account
        account_txns: Dict[str, CardAccount] = {}

        for account in accounts:
            account_index = account['index']
            account_number = account['accountNumber']
            processed_date = account['processedDate']

            # Get transactions for this card index
            index_key = f"Index{account_index}"
            if index_key not in cards_bean:
                continue

            current_card_txns_list = cards_bean[index_key].get('CurrentCardTransactions', [])

            all_txns: List[Transaction] = []

            for txn_group in current_card_txns_list:
                # Process Israel transactions
                if 'txnIsrael' in txn_group and txn_group['txnIsrael']:
                    txns = self.convert_transactions(txn_group['txnIsrael'], processed_date)
                    all_txns.extend(txns)

                # Process abroad transactions
                if 'txnAbroad' in txn_group and txn_group['txnAbroad']:
                    txns = self.convert_transactions(txn_group['txnAbroad'], processed_date)
                    all_txns.extend(txns)

            # Filter by start date
            filtered_txns = [
                t for t in all_txns
                if datetime.fromisoformat(t.date) >= start_date
            ]

            if filtered_txns:
                account_txns[account_number] = CardAccount(
                    account_number=account_number,
                    index=account_index,
                    transactions=filtered_txns
                )

        return account_txns

    def fetch_transaction_category(
        self,
        account_index: int,
        transaction: Transaction,
        year: int,
        month: int
    ) -> Transaction:
        """
        Fetch additional category information for a transaction.

        Args:
            account_index: Card index
            transaction: Transaction object
            year: Year
            month: Month

        Returns:
            Updated transaction with category
        """
        if not transaction.identifier:
            return transaction

        params = {
            'reqName': 'PirteyIska_204',
            'CardIndex': str(account_index),
            'shovarRatz': str(transaction.identifier),
            'moedChiuv': f"{month:02d}{year}",
        }

        logger.debug(f"Fetching category for transaction {transaction.identifier}")

        try:
            data = self.api_request(self.services_url, params=params)

            if data and 'PirteyIska_204Bean' in data:
                raw_category = data['PirteyIska_204Bean'].get('sector', '')
                if raw_category:
                    transaction.category = raw_category.strip()
        except Exception as e:
            logger.warning(f"Failed to fetch category for transaction {transaction.identifier}: {e}")

        return transaction

    def fetch_categories_for_account(
        self,
        account: CardAccount,
        year: int,
        month: int
    ) -> CardAccount:
        """
        Fetch categories for all transactions in an account.

        Args:
            account: CardAccount object
            year: Year
            month: Month

        Returns:
            Updated CardAccount with categories
        """
        updated_txns: List[Transaction] = []

        # Process in batches to avoid rate limiting
        for i in range(0, len(account.transactions), self.TRANSACTIONS_BATCH_SIZE):
            batch = account.transactions[i:i + self.TRANSACTIONS_BATCH_SIZE]

            for txn in batch:
                updated_txn = self.fetch_transaction_category(account.index, txn, year, month)
                updated_txns.append(updated_txn)

            # Rate limiting between batches
            if i + self.TRANSACTIONS_BATCH_SIZE < len(account.transactions):
                time.sleep(self.SLEEP_BETWEEN_REQUESTS)

        account.transactions = updated_txns
        return account

    def fetch_transactions(
        self,
        start_date: Optional[datetime] = None,
        months_back: int = 12,
        months_forward: int = 1
    ) -> List[CardAccount]:
        """
        Fetch all transactions for all cards.

        Args:
            start_date: Start date for fetching transactions (default: 12 months ago)
            months_back: Number of months to fetch backwards
            months_forward: Number of months to fetch forward

        Returns:
            List of CardAccount objects with transactions
        """
        # Calculate date range
        if start_date is None:
            start_date = datetime.now() - timedelta(days=months_back * 30)

        end_date = datetime.now() + timedelta(days=months_forward * 30)

        # Limit to 1 year back (Isracard limitation)
        max_start_date = datetime.now() - timedelta(days=365)
        if start_date < max_start_date:
            logger.warning(f"Start date limited to 1 year back: {max_start_date.date()}")
            start_date = max_start_date

        logger.info(f"Fetching transactions from {start_date.date()} to {end_date.date()}")

        # Fetch transactions by month
        combined_accounts: Dict[str, CardAccount] = {}

        current_date = end_date
        months_data = []  # For category fetching

        while current_date >= start_date:
            month = current_date.month
            year = current_date.year

            month_accounts = self.fetch_transactions_for_month(year, month, start_date)
            months_data.append((year, month, month_accounts))

            # Merge transactions into combined_accounts
            for account_number, account in month_accounts.items():
                if account_number not in combined_accounts:
                    combined_accounts[account_number] = account
                else:
                    # Append transactions to existing account
                    combined_accounts[account_number].transactions.extend(account.transactions)

            # Move to previous month
            if current_date.month == 1:
                current_date = current_date.replace(year=current_date.year - 1, month=12, day=1)
            else:
                current_date = current_date.replace(month=current_date.month - 1, day=1)

        # Fetch categories if enabled
        if self.fetch_categories:
            logger.info("Fetching transaction categories...")
            for year, month, month_accounts in months_data:
                for account_number in month_accounts:
                    if account_number in combined_accounts:
                        logger.debug(f"Fetching categories for card {account_number}, month {year}-{month:02d}")
                        combined_accounts[account_number] = self.fetch_categories_for_account(
                            combined_accounts[account_number],
                            year,
                            month
                        )

        # Convert to list and sort transactions
        accounts = []
        for account in combined_accounts.values():
            # Sort by date
            account.transactions.sort(key=lambda t: t.date, reverse=True)

            logger.info(f"Found {len(account.transactions)} transactions for card {account.account_number}")
            accounts.append(account)

        return accounts

    def scrape(
        self,
        start_date: Optional[datetime] = None,
        months_back: int = 12,
        months_forward: int = 1
    ) -> List[CardAccount]:
        """
        Complete scraping flow: login and fetch transactions.

        Args:
            start_date: Start date for fetching transactions
            months_back: Number of months to fetch backwards (default: 12)
            months_forward: Number of months to fetch forward (default: 1)

        Returns:
            List of CardAccount objects with transactions
        """
        try:
            logger.info("Starting Isracard credit card scraper...")

            # Login
            self.login()

            # Fetch transactions
            accounts = self.fetch_transactions(start_date, months_back, months_forward)

            return accounts

        finally:
            self.cleanup()


def main():
    """Main entry point for Isracard Credit Card Scraper"""
    import argparse
    import os
    from dotenv import load_dotenv
    from scrapers.config.logging_config import add_logging_args, setup_logging_from_args

    parser = argparse.ArgumentParser(description="Isracard Credit Card Transaction Scraper")
    add_logging_args(parser)
    parser.add_argument("--months-back", type=int, default=3, help="Months of history to fetch (default: 3)")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--fetch-categories", action="store_true", help="Fetch transaction categories (slower)")
    parser.add_argument(
        "--company",
        choices=["isracard", "amex"],
        default="isracard",
        help="Company to scrape (default: isracard)"
    )
    parser.add_argument("--user-id", help="User ID (ID number)")
    parser.add_argument("--password", help="Password")
    parser.add_argument("--card-6-digits", help="Last 6 digits of card")
    args = parser.parse_args()

    setup_logging_from_args(args)
    load_dotenv()

    # Company-specific configuration
    if args.company == "isracard":
        base_url = "https://digital.isracard.co.il"
        company_code = "11"
        env_prefix = "ISRACARD"
    else:  # amex
        base_url = "https://he.americanexpress.co.il"
        company_code = "7"
        env_prefix = "AMEX"

    # Get credentials from CLI args or environment variables
    user_id = args.user_id or os.getenv(f"{env_prefix}_USER_ID", "")
    password = args.password or os.getenv(f"{env_prefix}_PASSWORD", "")
    card_6_digits = args.card_6_digits or os.getenv(f"{env_prefix}_CARD_6_DIGITS", "")

    if not user_id or not password or not card_6_digits:
        parser.error("Credentials required: provide via CLI arguments or environment variables")

    credentials = IsracardCredentials(
        user_id=user_id,
        password=password,
        card_6_digits=card_6_digits
    )

    scraper = IsracardCreditCardScraper(
        credentials=credentials,
        base_url=base_url,
        company_code=company_code,
        headless=args.headless,
        fetch_categories=args.fetch_categories
    )

    try:
        accounts = scraper.scrape(months_back=args.months_back)

        for account in accounts:
            print(f"\n{'='*60}")
            print(f"Card: {account.account_number}")
            print(f"Total transactions: {len(account.transactions)}")
            print(f"{'='*60}")

            for txn in account.transactions[:10]:  # Show first 10
                print(f"{txn.date[:10]} | {txn.description:30} | {txn.charged_amount:>10.2f} {txn.original_currency} | {txn.status.value}")
                if txn.installments:
                    print(f"           Installment {txn.installments.number}/{txn.installments.total}")
                if txn.category:
                    print(f"           Category: {txn.category}")

    except IsracardChangePasswordError as e:
        print(f"Password change required: {e}")
    except IsracardLoginError as e:
        print(f"Login error: {e}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()