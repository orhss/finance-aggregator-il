"""
CAL Credit Card Scraper
Automated transaction extraction for Israeli CAL (Visa CAL) credit cards
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
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)


# Configuration
@dataclass
class CALCredentials:
    """CAL login credentials"""
    username: str
    password: str


# Transaction Enums and Models
class TransactionStatus(Enum):
    """Transaction status"""
    PENDING = "pending"
    COMPLETED = "completed"


class TransactionType(Enum):
    """Transaction type"""
    NORMAL = "normal"  # Regular charge
    INSTALLMENTS = "installments"  # Payment plan
    CREDIT = "credit"  # Refund


class TrnTypeCode(Enum):
    """CAL transaction type codes"""
    REGULAR = "5"
    CREDIT = "6"
    INSTALLMENTS = "8"
    STANDING_ORDER = "9"


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
    charged_currency: Optional[str]  # Account currency (None for pending)
    description: str  # Merchant name
    status: TransactionStatus
    transaction_type: TransactionType
    identifier: Optional[str] = None  # Transaction ID (None for pending)
    memo: Optional[str] = None
    category: Optional[str] = None
    installments: Optional[Installments] = None


@dataclass
class CardAccount:
    """Card account with transactions"""
    account_number: str  # Last 4 digits
    card_unique_id: str
    transactions: List[Transaction]


# Exceptions
class CALScraperError(Exception):
    """Base exception for CAL scraper errors"""
    pass


class CALLoginError(CALScraperError):
    """Login failed"""
    pass


class CALAuthorizationError(CALScraperError):
    """Authorization token extraction failed"""
    pass


class CALAPIError(CALScraperError):
    """API request failed"""
    pass


class CALCreditCardScraper:
    """
    Automated scraper for CAL (Visa CAL) credit card transactions.

    Uses Selenium to handle login and extract authorization tokens,
    then makes API calls to fetch transaction data.
    """

    BASE_URL = "https://www.cal-online.co.il/"
    SSO_AUTH_ENDPOINT = "https://connect.cal-online.co.il/col-rest/calconnect/authentication/SSO"
    TRANSACTIONS_ENDPOINT = "https://api.cal-online.co.il/Transactions/api/transactionsDetails/getCardTransactionsDetails"
    PENDING_ENDPOINT = "https://api.cal-online.co.il/Transactions/api/approvals/getClearanceRequests"

    X_SITE_ID = "09031987-273E-2311-906C-8AF85B17C8D9"

    def __init__(self, credentials: CALCredentials, headless: bool = True):
        self.credentials = credentials
        self.headless = headless
        self.driver = None
        self.authorization_token: Optional[str] = None
        self.cards: List[Dict[str, str]] = []

    def setup_driver(self):
        """Setup Chrome WebDriver with request interception"""
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

        # Enable performance logging to capture network requests
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

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

    def wait_for_iframe(self, timeout: int = 10) -> Any:
        """Wait for and switch to login iframe"""
        logger.debug("Waiting for login iframe...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                src = iframe.get_attribute("src")
                if src and "connect" in src:
                    logger.debug(f"Found login iframe: {src}")
                    self.driver.switch_to.frame(iframe)
                    return iframe
            time.sleep(0.5)

        raise CALLoginError("Failed to find login iframe after 10 seconds")

    def login(self) -> bool:
        """
        Perform login to CAL website.

        Returns:
            True if login successful

        Raises:
            CALLoginError: If login fails
        """
        try:
            if not self.driver:
                self.setup_driver()

            logger.info(f"Step 1/4: Navigating to {self.BASE_URL}...")
            self.driver.get(self.BASE_URL)

            # Click login button
            logger.debug("Waiting for login button...")
            login_btn = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#ccLoginDesktopBtn"))
            )
            logger.debug("Clicking login button...")
            login_btn.click()

            # Wait for and switch to iframe
            self.wait_for_iframe()

            # Click on regular login tab
            logger.debug("Switching to password login tab...")
            regular_login_tab = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#regular-login"))
            )
            regular_login_tab.click()
            time.sleep(1)

            # Enter username
            logger.info("Step 2/4: Entering credentials...")
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[formcontrolname='userName']"))
            )
            username_field.clear()
            username_field.send_keys(self.credentials.username)

            # Enter password
            logger.debug("Entering password...")
            password_field = self.driver.find_element(By.CSS_SELECTOR, "[formcontrolname='password']")
            password_field.clear()
            password_field.send_keys(self.credentials.password)

            # Submit login
            logger.info("Step 3/4: Submitting login form...")
            submit_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_btn.click()

            # Switch back to main content
            self.driver.switch_to.default_content()

            # Wait for dashboard or check for errors
            logger.debug("Waiting for login to complete...")
            time.sleep(5)

            current_url = self.driver.current_url
            logger.debug(f"Current URL: {current_url}")

            # Check for invalid password error
            if "connect" in current_url:
                # Still on login page - check for error
                self.wait_for_iframe()
                try:
                    error_elem = self.driver.find_element(By.CSS_SELECTOR, "div.general-error > div")
                    error_msg = error_elem.text
                    self.driver.switch_to.default_content()
                    raise CALLoginError(f"Login failed: {error_msg}")
                except NoSuchElementException:
                    self.driver.switch_to.default_content()
                    raise CALLoginError("Login failed: Unknown error")

            # Close tutorial popup if present
            if "site-tutorial" in current_url:
                logger.debug("Closing tutorial popup...")
                try:
                    close_btn = self.driver.find_element(By.CSS_SELECTOR, "button.btn-close")
                    close_btn.click()
                    time.sleep(1)
                except NoSuchElementException:
                    pass

            # Extract authorization token
            logger.info("Step 4/4: Extracting session data...")
            self.extract_authorization_token()

            # Extract card information
            logger.debug("Extracting card information...")
            self.extract_card_info()

            logger.info(f"Login successful! Found {len(self.cards)} card(s)")
            return True

        except TimeoutException as e:
            raise CALLoginError(f"Timeout during login: {e}")
        except Exception as e:
            raise CALLoginError(f"Login failed: {e}")

    def extract_authorization_token(self):
        """Extract authorization token from browser logs or session storage"""
        try:
            # Try to get from session storage
            auth_module = self.driver.execute_script(
                "return JSON.parse(sessionStorage.getItem('auth-module'));"
            )

            if auth_module and 'auth' in auth_module and 'calConnectToken' in auth_module['auth']:
                token = auth_module['auth']['calConnectToken']
                if token and token.strip():
                    self.authorization_token = f"CALAuthScheme {token}"
                    logger.debug("Authorization token extracted from session storage")
                    return

            # Fallback: Parse performance logs
            logs = self.driver.get_log('performance')
            for entry in logs:
                try:
                    log = json.loads(entry['message'])
                    message = log.get('message', {})
                    method = message.get('method', '')

                    if method == 'Network.requestWillBeSent':
                        params = message.get('params', {})
                        request = params.get('request', {})
                        url = request.get('url', '')

                        if self.SSO_AUTH_ENDPOINT in url:
                            headers = request.get('headers', {})
                            auth_header = headers.get('Authorization') or headers.get('authorization')
                            if auth_header:
                                self.authorization_token = auth_header
                                logger.debug("Authorization token extracted from network logs")
                                return
                except:
                    continue

            raise CALAuthorizationError("Failed to extract authorization token")

        except Exception as e:
            raise CALAuthorizationError(f"Error extracting authorization token: {e}")

    def extract_card_info(self):
        """Extract card information from session storage"""
        try:
            init_data = self.driver.execute_script(
                "return JSON.parse(sessionStorage.getItem('init'));"
            )

            if not init_data or 'result' not in init_data or 'cards' not in init_data['result']:
                raise CALScraperError("Failed to extract card information from session storage")

            cards = init_data['result']['cards']
            self.cards = [
                {
                    'cardUniqueId': card['cardUniqueId'],
                    'last4Digits': card['last4Digits']
                }
                for card in cards
            ]

            logger.debug(f"Extracted {len(self.cards)} card(s): {[c['last4Digits'] for c in self.cards]}")

        except Exception as e:
            raise CALScraperError(f"Error extracting card info: {e}")

    def get_api_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        if not self.authorization_token:
            raise CALAuthorizationError("No authorization token available")

        return {
            'Authorization': self.authorization_token,
            'X-Site-Id': self.X_SITE_ID,
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'Origin': 'https://www.cal-online.co.il',
            'Referer': 'https://www.cal-online.co.il/',
            'Accept-Language': 'he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7',
            'Sec-Fetch-Site': 'same-site',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
        }

    def fetch_completed_transactions(
        self,
        card_unique_id: str,
        month: int,
        year: int
    ) -> Dict[str, Any]:
        """
        Fetch completed transactions for a specific card and month.

        Args:
            card_unique_id: Unique card identifier
            month: Month (1-12)
            year: Year (e.g., 2024)

        Returns:
            API response with transaction data
        """
        payload = {
            'cardUniqueId': card_unique_id,
            'month': str(month),
            'year': str(year)
        }

        try:
            response = requests.post(
                self.TRANSACTIONS_ENDPOINT,
                headers=self.get_api_headers(),
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if data.get('statusCode') != 1:
                raise CALAPIError(f"API error: {data.get('title', 'Unknown error')}")

            return data

        except requests.RequestException as e:
            raise CALAPIError(f"Failed to fetch completed transactions: {e}")

    def fetch_pending_transactions(self, card_unique_ids: List[str]) -> Optional[Dict[str, Any]]:
        """
        Fetch pending transactions for cards.

        Args:
            card_unique_ids: List of card unique identifiers

        Returns:
            API response with pending transaction data, or None if no pending transactions
        """
        payload = {'cardUniqueIDArray': card_unique_ids}

        try:
            response = requests.post(
                self.PENDING_ENDPOINT,
                headers=self.get_api_headers(),
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            # Status code 1 = success, 96 = no pending transactions
            if data.get('statusCode') == 1:
                return data
            elif data.get('statusCode') == 96:
                logger.debug("No pending transactions found")
                return None
            else:
                logger.warning(f"Unexpected status code for pending transactions: {data.get('statusCode')}")
                return None

        except requests.RequestException as e:
            logger.warning(f"Failed to fetch pending transactions: {e}")
            return None

    def convert_transactions(
        self,
        completed_data_list: List[Dict[str, Any]],
        pending_data: Optional[Dict[str, Any]] = None
    ) -> List[Transaction]:
        """
        Convert raw API data to Transaction objects.

        Args:
            completed_data_list: List of monthly completed transaction data
            pending_data: Pending transaction data

        Returns:
            List of Transaction objects
        """
        transactions = []

        # Process pending transactions
        if pending_data and 'result' in pending_data and 'cardsList' in pending_data['result']:
            for card_data in pending_data['result']['cardsList']:
                for txn in card_data.get('authDetalisList', []):
                    transactions.append(self._convert_pending_transaction(txn))

        # Process completed transactions
        for month_data in completed_data_list:
            if 'result' not in month_data or 'bankAccounts' not in month_data['result']:
                continue

            for bank_account in month_data['result']['bankAccounts']:
                # Regular debit dates
                for debit_date in bank_account.get('debitDates', []):
                    for txn in debit_date.get('transactions', []):
                        transactions.append(self._convert_completed_transaction(txn))

                # Immediate debits
                immediate_debits = bank_account.get('immidiateDebits', {})
                for debit_day in immediate_debits.get('debitDays', []):
                    for txn in debit_day.get('transactions', []):
                        transactions.append(self._convert_completed_transaction(txn))

        return transactions

    def _convert_pending_transaction(self, txn: Dict[str, Any]) -> Transaction:
        """Convert pending transaction from API format"""
        txn_type_code = txn.get('trnTypeCode', '')
        num_payments = txn.get('numberOfPayments', 0)

        # Determine transaction type
        if txn_type_code in [TrnTypeCode.REGULAR.value, TrnTypeCode.STANDING_ORDER.value]:
            transaction_type = TransactionType.NORMAL
        else:
            transaction_type = TransactionType.INSTALLMENTS

        # Calculate amounts
        original_amount = txn.get('trnAmt', 0)
        if txn_type_code == TrnTypeCode.CREDIT.value:
            original_amount = original_amount  # Positive for credit
        else:
            original_amount = -original_amount  # Negative for debit

        charged_amount = -txn.get('trnAmt', 0)  # Pending transactions always negative

        purchase_date = datetime.fromisoformat(txn.get('trnPurchaseDate', '').replace('Z', '+00:00'))

        result = Transaction(
            identifier=None,  # No ID for pending
            transaction_type=transaction_type,
            status=TransactionStatus.PENDING,
            date=purchase_date.isoformat(),
            processed_date=purchase_date.isoformat(),
            original_amount=original_amount,
            original_currency=txn.get('trnCurrencySymbol', 'ILS'),
            charged_amount=charged_amount,
            charged_currency=None,  # Unknown for pending
            description=txn.get('merchantName', ''),
            memo='',
            category=txn.get('branchCodeDesc', ''),
        )

        if num_payments > 0:
            result.installments = Installments(number=1, total=num_payments)

        return result

    def _convert_completed_transaction(self, txn: Dict[str, Any]) -> Transaction:
        """Convert completed transaction from API format"""
        txn_type_code = txn.get('trnTypeCode', '')
        num_payments = txn.get('numOfPayments', 0)
        cur_payment = txn.get('curPaymentNum', 1)

        # Determine transaction type
        if txn_type_code in [TrnTypeCode.REGULAR.value, TrnTypeCode.STANDING_ORDER.value]:
            transaction_type = TransactionType.NORMAL
        else:
            transaction_type = TransactionType.INSTALLMENTS

        # Calculate amounts
        original_amount = txn.get('trnAmt', 0)
        if txn_type_code == TrnTypeCode.CREDIT.value:
            original_amount = original_amount  # Positive for credit
        else:
            original_amount = -original_amount  # Negative for debit

        charged_amount = -txn.get('amtBeforeConvAndIndex', 0)

        purchase_date = datetime.fromisoformat(txn.get('trnPurchaseDate', '').replace('Z', '+00:00'))
        debit_date = datetime.fromisoformat(txn.get('debCrdDate', '').replace('Z', '+00:00'))

        # Adjust date for installments (add months for each installment)
        if num_payments > 0 and cur_payment > 1:
            # Add months based on installment number
            month_offset = cur_payment - 1
            adjusted_date = purchase_date.replace(
                month=purchase_date.month + month_offset
            ) if purchase_date.month + month_offset <= 12 else purchase_date.replace(
                year=purchase_date.year + (purchase_date.month + month_offset - 1) // 12,
                month=(purchase_date.month + month_offset - 1) % 12 + 1
            )
        else:
            adjusted_date = purchase_date

        result = Transaction(
            identifier=txn.get('trnIntId'),
            transaction_type=transaction_type,
            status=TransactionStatus.COMPLETED,
            date=adjusted_date.isoformat(),
            processed_date=debit_date.isoformat(),
            original_amount=original_amount,
            original_currency=txn.get('trnCurrencySymbol', 'ILS'),
            charged_amount=charged_amount,
            charged_currency=txn.get('debCrdCurrencySymbol', 'ILS'),
            description=txn.get('merchantName', ''),
            memo=str(txn.get('transTypeCommentDetails', '')),
            category=txn.get('branchCodeDesc', ''),
        )

        if num_payments > 0:
            result.installments = Installments(number=cur_payment, total=num_payments)

        return result

    def fetch_transactions(
        self,
        start_date: Optional[datetime] = None,
        months_back: int = 18,
        months_forward: int = 1
    ) -> List[CardAccount]:
        """
        Fetch all transactions for all cards.

        Args:
            start_date: Start date for fetching transactions (default: 18 months ago)
            months_back: Number of months to fetch backwards
            months_forward: Number of months to fetch forward

        Returns:
            List of CardAccount objects with transactions
        """
        if not self.authorization_token:
            raise CALAuthorizationError("Not logged in - call login() first")

        if not self.cards:
            raise CALScraperError("No cards found")

        # Calculate date range
        if start_date is None:
            start_date = datetime.now() - timedelta(days=months_back * 30)

        end_date = datetime.now() + timedelta(days=months_forward * 30)

        logger.info(f"Fetching transactions from {start_date.date()} to {end_date.date()}")

        accounts = []

        for card in self.cards:
            card_id = card['cardUniqueId']
            last_4 = card['last4Digits']

            logger.info(f"Processing card ending in {last_4}...")

            # Fetch pending transactions
            logger.debug(f"Fetching pending transactions for card {last_4}...")
            pending_data = self.fetch_pending_transactions([card_id])

            # Fetch completed transactions by month
            logger.debug(f"Fetching completed transactions for card {last_4}...")
            completed_data_list = []

            current_date = end_date
            while current_date >= start_date:
                month = current_date.month
                year = current_date.year

                logger.debug(f"  Fetching month {month}/{year}...")
                month_data = self.fetch_completed_transactions(card_id, month, year)
                completed_data_list.append(month_data)

                # Move to previous month
                if current_date.month == 1:
                    current_date = current_date.replace(year=current_date.year - 1, month=12)
                else:
                    current_date = current_date.replace(month=current_date.month - 1)

            # Convert to Transaction objects
            transactions = self.convert_transactions(completed_data_list, pending_data)

            # Filter by date
            transactions = [
                t for t in transactions
                if start_date <= datetime.fromisoformat(t.date) <= end_date
            ]

            logger.info(f"Found {len(transactions)} transactions for card {last_4}")

            accounts.append(CardAccount(
                account_number=last_4,
                card_unique_id=card_id,
                transactions=transactions
            ))

        return accounts

    def scrape(
        self,
        start_date: Optional[datetime] = None,
        months_back: int = 18,
        months_forward: int = 1
    ) -> List[CardAccount]:
        """
        Complete scraping flow: login and fetch transactions.

        Args:
            start_date: Start date for fetching transactions
            months_back: Number of months to fetch backwards (default: 18)
            months_forward: Number of months to fetch forward (default: 1)

        Returns:
            List of CardAccount objects with transactions
        """
        try:
            logger.info("Starting CAL credit card scraper...")

            # Login
            self.login()

            # Fetch transactions
            accounts = self.fetch_transactions(start_date, months_back, months_forward)

            return accounts

        finally:
            self.cleanup()


# Example usage
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    credentials = CALCredentials(
        username=os.getenv("CAL_USERNAME", ""),
        password=os.getenv("CAL_PASSWORD", "")
    )

    scraper = CALCreditCardScraper(credentials, headless=False)

    try:
        accounts = scraper.scrape(months_back=3)

        for account in accounts:
            print(f"\n{'='*60}")
            print(f"Card: ****{account.account_number}")
            print(f"Total transactions: {len(account.transactions)}")
            print(f"{'='*60}")

            for txn in account.transactions[:10]:  # Show first 10
                print(f"{txn.date[:10]} | {txn.description:30} | {txn.charged_amount:>10.2f} {txn.original_currency} | {txn.status.value}")
                if txn.installments:
                    print(f"           Installment {txn.installments.number}/{txn.installments.total}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()