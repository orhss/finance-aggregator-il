"""
Max Credit Card Scraper
Automated transaction extraction for Israeli Max credit cards
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from scrapers.base.selenium_driver import DriverConfig
from scrapers.credit_cards.base_scraper import BaseCreditCardScraper
from scrapers.credit_cards.shared_models import (
    TransactionStatus,
    TransactionType,
    Installments,
    Transaction,
    MaxScraperError,
    MaxLoginError,
    MaxAPIError,
)
from scrapers.credit_cards.shared_helpers import get_cookies, extract_installments

logger = logging.getLogger(__name__)


# Configuration
@dataclass
class MaxCredentials:
    """Max login credentials"""
    username: str
    password: str


# Max-specific enums
class MaxPlanName(Enum):
    """Max transaction plan type names"""
    NORMAL = "רגילה"
    IMMEDIATE_CHARGE = "חיוב עסקות מיידי"
    INTERNET_SHOPPING = "אינטרנט/חו\"ל"
    INSTALLMENTS = "תשלומים"
    MONTHLY_CHARGE = "חיוב חודשי"
    ONE_MONTH_POSTPONED = "דחוי חודש"
    MONTHLY_POSTPONED = "דחוי לחיוב החודשי"
    MONTHLY_PAYMENT = "תשלום חודשי"
    FUTURE_PURCHASE_FINANCING = "מימון לרכישה עתידית"
    MONTHLY_POSTPONED_INSTALLMENTS = "דחוי חודש תשלומים"
    THIRTY_DAYS_PLUS = "עסקת 30 פלוס"
    TWO_MONTHS_POSTPONED = "דחוי חודשיים"
    TWO_MONTHS_POSTPONED_2 = "דחוי 2 ח' תשלומים"
    MONTHLY_CHARGE_PLUS_INTEREST = "חודשי + ריבית"
    CREDIT = "קרדיט"
    CREDIT_OUTSIDE_THE_LIMIT = "קרדיט-מחוץ למסגרת"
    ACCUMULATING_BASKET = "סל מצטבר"
    POSTPONED_TRANSACTION_INSTALLMENTS = "פריסת העסקה הדחויה"
    REPLACEMENT_CARD = "כרטיס חליפי"
    EARLY_REPAYMENT = "פרעון מוקדם"
    MONTHLY_CARD_FEE = "דמי כרטיס"
    CURRENCY_POCKET = "חיוב ארנק מטח"


@dataclass
class CardAccount:
    """Card account with transactions."""
    account_number: str  # Card number (short)
    transactions: List[Transaction]


class MaxCreditCardScraper(BaseCreditCardScraper['MaxCredentials', 'CardAccount']):
    """
    Automated scraper for Max credit card transactions.

    Uses Selenium to handle login and then makes API calls to fetch transaction data.
    """

    BASE_WELCOME_URL = "https://www.max.co.il"
    BASE_API_ACTIONS_URL = "https://onlinelcapi.max.co.il"

    LOGIN_URL = f"{BASE_WELCOME_URL}/homepage/welcome"
    PASSWORD_EXPIRED_URL = f"{BASE_WELCOME_URL}/renew-password"
    SUCCESS_URL = f"{BASE_WELCOME_URL}/homepage/personal"

    TRANSACTIONS_ENDPOINT = f"{BASE_API_ACTIONS_URL}/api/registered/transactionDetails/getTransactionsAndGraphs"
    CATEGORIES_ENDPOINT = f"{BASE_API_ACTIONS_URL}/api/contents/getCategories"

    INVALID_DETAILS_SELECTOR = "#popupWrongDetails"
    LOGIN_ERROR_SELECTOR = "#popupCardHoldersLoginError"

    # Currency codes
    CURRENCY_ILS = 376
    CURRENCY_USD = 840
    CURRENCY_EUR = 978

    def __init__(self, credentials: MaxCredentials, headless: bool = True):
        super().__init__(credentials, headless)
        self.categories: Dict[int, str] = {}

    def wait_for_element(self, selector: str, timeout: int = 10, clickable: bool = False):
        """Wait for element to be present or clickable"""
        condition = EC.element_to_be_clickable if clickable else EC.presence_of_element_located
        return WebDriverWait(self.driver, timeout).until(
            condition((By.CSS_SELECTOR, selector))
        )

    def element_present(self, selector: str) -> bool:
        """Check if element is present on page"""
        try:
            self.driver.find_element(By.CSS_SELECTOR, selector)
            return True
        except NoSuchElementException:
            return False

    def click_button(self, selector: str):
        """Click a button by selector"""
        element = self.wait_for_element(selector, clickable=True)
        element.click()

    def login(self) -> bool:
        """
        Perform login to Max website.

        Returns:
            True if login successful

        Raises:
            MaxLoginError: If login fails
        """
        try:
            if not self.driver:
                self.setup_driver()

            logger.info(f"Step 1/4: Navigating to {self.LOGIN_URL}...")
            self.driver.get(self.LOGIN_URL)

            # Wait for page to load
            logger.debug("Waiting for page to load...")
            self.wait_for_element('.personal-area > a.go-to-personal-area')

            # Close popup if present
            if self.element_present('#closePopup'):
                logger.debug("Closing popup...")
                self.click_button('#closePopup')

            # Click personal area link
            logger.debug("Clicking personal area link...")
            self.click_button('.personal-area > a.go-to-personal-area')

            # Click private login if present
            if self.element_present('.login-link#private'):
                logger.debug("Clicking private login link...")
                self.click_button('.login-link#private')

            # Click password login tab
            logger.debug("Clicking password login tab...")
            self.wait_for_element('#login-password-link', clickable=True)
            self.click_button('#login-password-link')

            # Wait for password login form to be active
            logger.debug("Waiting for password login form...")
            self.wait_for_element('#login-password.tab-pane.active app-user-login-form')

            # Enter username
            logger.info("Step 2/4: Entering credentials...")
            username_field = self.wait_for_element('#user-name')
            username_field.clear()
            username_field.send_keys(self.credentials.username)

            # Enter password
            logger.debug("Entering password...")
            password_field = self.driver.find_element(By.CSS_SELECTOR, '#password')
            password_field.clear()
            password_field.send_keys(self.credentials.password)

            # Submit login
            logger.info("Step 3/4: Submitting login form...")
            submit_btn = self.driver.find_element(By.CSS_SELECTOR, 'app-user-login-form .general-button.send-me-code')
            submit_btn.click()

            # Wait for redirect or error
            logger.debug("Waiting for login to complete...")
            time.sleep(3)

            current_url = self.driver.current_url
            logger.debug(f"Current URL: {current_url}")

            # Check for errors
            if self.element_present(self.INVALID_DETAILS_SELECTOR):
                raise MaxLoginError("Invalid username or password")

            if self.element_present(self.LOGIN_ERROR_SELECTOR):
                raise MaxLoginError("Login error - card holder login failed")

            # Check for password expired
            if self.PASSWORD_EXPIRED_URL in current_url:
                raise MaxLoginError("Password expired - please renew password")

            # Check for success
            if self.SUCCESS_URL not in current_url:
                raise MaxLoginError(f"Login failed - unexpected URL: {current_url}")

            logger.info("Step 4/4: Login successful!")
            return True

        except TimeoutException as e:
            raise MaxLoginError(f"Timeout during login: {e}")
        except Exception as e:
            raise MaxLoginError(f"Login failed: {e}")

    def get_cookies_dict(self) -> Dict[str, str]:
        """Get cookies as dictionary using shared helper"""
        return get_cookies(self.driver)

    def load_categories(self):
        """Load transaction categories from API"""
        try:
            logger.debug("Loading categories...")
            cookies = self.get_cookies_dict()

            response = requests.get(
                self.CATEGORIES_ENDPOINT,
                cookies=cookies,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if 'result' in data and isinstance(data['result'], list):
                for category in data['result']:
                    self.categories[category['id']] = category['name']
                logger.debug(f"{len(self.categories)} categories loaded")
            else:
                logger.warning("No categories found in API response")

        except requests.RequestException as e:
            logger.warning(f"Failed to load categories: {e}")
        except Exception as e:
            logger.warning(f"Error loading categories: {e}")

    def get_transactions_url(self, month: int, year: int) -> str:
        """
        Build transactions API URL for a specific month.

        Args:
            month: Month (1-12)
            year: Year (e.g., 2024)

        Returns:
            Full API URL with query parameters
        """
        date = f"{year}-{month}-01"

        filter_data = {
            "userIndex": -1,  # All account owners
            "cardIndex": -1,  # All cards
            "monthView": True,
            "date": date,
            "dates": {
                "startDate": "0",
                "endDate": "0"
            },
            "bankAccount": {
                "bankAccountIndex": -1,
                "cards": None
            }
        }

        url = f"{self.TRANSACTIONS_ENDPOINT}?filterData={json.dumps(filter_data, separators=(',', ':'))}&firstCallCardIndex=-1"
        return url

    def fetch_transactions_for_month(self, month: int, year: int) -> Dict[str, List[Transaction]]:
        """
        Fetch transactions for a specific month.

        Args:
            month: Month (1-12)
            year: Year (e.g., 2024)

        Returns:
            Dictionary mapping card numbers to transaction lists
        """
        try:
            logger.debug(f"Fetching transactions for {month}/{year}...")
            url = self.get_transactions_url(month, year)
            cookies = self.get_cookies_dict()

            response = requests.get(url, cookies=cookies, timeout=30)
            response.raise_for_status()
            data = response.json()

            transactions_by_card: Dict[str, List[Transaction]] = {}

            # Check if data is valid and has the expected structure
            if not isinstance(data, dict):
                logger.debug(f"Invalid or empty response for {month}/{year}")
                return transactions_by_card

            if 'result' not in data or not isinstance(data['result'], dict):
                logger.debug(f"No result in response for {month}/{year}")
                return transactions_by_card

            if 'transactions' not in data['result']:
                logger.debug(f"No transactions found for {month}/{year}")
                return transactions_by_card

            for raw_txn in data['result']['transactions']:
                # Filter out summary rows without plan type
                if not raw_txn.get('planName'):
                    continue

                card_number = raw_txn.get('shortCardNumber', 'unknown')
                if card_number not in transactions_by_card:
                    transactions_by_card[card_number] = []

                transaction = self._convert_transaction(raw_txn)
                transactions_by_card[card_number].append(transaction)

            return transactions_by_card

        except requests.RequestException as e:
            raise MaxAPIError(f"Failed to fetch transactions for {month}/{year}: {e}")

    def _get_transaction_type(self, plan_name: str, plan_type_id: int) -> TransactionType:
        """Determine transaction type from plan name and type ID"""
        # Clean up plan name
        cleaned_plan = plan_name.replace('\t', ' ').strip()

        # Map plan names to transaction types
        normal_plans = {
            MaxPlanName.IMMEDIATE_CHARGE.value,
            MaxPlanName.NORMAL.value,
            MaxPlanName.MONTHLY_CHARGE.value,
            MaxPlanName.ONE_MONTH_POSTPONED.value,
            MaxPlanName.MONTHLY_POSTPONED.value,
            MaxPlanName.FUTURE_PURCHASE_FINANCING.value,
            MaxPlanName.MONTHLY_PAYMENT.value,
            MaxPlanName.MONTHLY_POSTPONED_INSTALLMENTS.value,
            MaxPlanName.THIRTY_DAYS_PLUS.value,
            MaxPlanName.TWO_MONTHS_POSTPONED.value,
            MaxPlanName.TWO_MONTHS_POSTPONED_2.value,
            MaxPlanName.ACCUMULATING_BASKET.value,
            MaxPlanName.INTERNET_SHOPPING.value,
            MaxPlanName.MONTHLY_CHARGE_PLUS_INTEREST.value,
            MaxPlanName.POSTPONED_TRANSACTION_INSTALLMENTS.value,
            MaxPlanName.REPLACEMENT_CARD.value,
            MaxPlanName.EARLY_REPAYMENT.value,
            MaxPlanName.MONTHLY_CARD_FEE.value,
            MaxPlanName.CURRENCY_POCKET.value,
        }

        installment_plans = {
            MaxPlanName.INSTALLMENTS.value,
            MaxPlanName.CREDIT.value,
            MaxPlanName.CREDIT_OUTSIDE_THE_LIMIT.value,
        }

        if cleaned_plan in normal_plans:
            return TransactionType.NORMAL
        elif cleaned_plan in installment_plans:
            return TransactionType.INSTALLMENTS
        else:
            # Fallback to plan type ID
            if plan_type_id in [2, 3]:
                return TransactionType.INSTALLMENTS
            elif plan_type_id == 5:
                return TransactionType.NORMAL
            else:
                logger.warning(f"Unknown transaction type: {cleaned_plan} (ID: {plan_type_id})")
                return TransactionType.NORMAL

    def _get_installments_info(self, comments: str) -> Optional[Installments]:
        """Extract installment info from comments using shared helper"""
        return extract_installments(comments)

    def _get_charged_currency(self, currency_id: Optional[int]) -> Optional[str]:
        """Convert currency ID to currency code"""
        if currency_id == self.CURRENCY_ILS:
            return "ILS"
        elif currency_id == self.CURRENCY_USD:
            return "USD"
        elif currency_id == self.CURRENCY_EUR:
            return "EUR"
        else:
            return None

    def _get_memo(self, raw_txn: Dict[str, Any]) -> str:
        """Build memo from transaction data"""
        comments = raw_txn.get('comments', '')
        receiver = raw_txn.get('fundsTransferReceiverOrTransfer', '')
        transfer_comment = raw_txn.get('fundsTransferComment', '')

        if receiver:
            memo = f"{comments} {receiver}" if comments else receiver
            return f"{memo}: {transfer_comment}" if transfer_comment else memo

        return comments

    def _convert_transaction(self, raw_txn: Dict[str, Any]) -> Transaction:
        """Convert raw API transaction to Transaction object"""
        # Determine status
        is_pending = raw_txn.get('paymentDate') is None
        status = TransactionStatus.PENDING if is_pending else TransactionStatus.COMPLETED

        # Get dates
        purchase_date = raw_txn.get('purchaseDate', '')
        payment_date = raw_txn.get('paymentDate', purchase_date)

        # Parse dates
        try:
            purchase_dt = datetime.fromisoformat(purchase_date.replace('Z', '+00:00'))
            payment_dt = datetime.fromisoformat(payment_date.replace('Z', '+00:00'))
        except:
            # Fallback for non-ISO dates
            purchase_dt = datetime.now()
            payment_dt = datetime.now()

        # Get transaction type
        plan_name = raw_txn.get('planName', '')
        plan_type_id = raw_txn.get('planTypeId', 0)
        transaction_type = self._get_transaction_type(plan_name, plan_type_id)

        # Get amounts
        original_amount = -float(raw_txn.get('originalAmount', 0))
        charged_amount = -float(raw_txn.get('actualPaymentAmount', 0))

        # Get currencies
        original_currency = raw_txn.get('originalCurrency', 'ILS')
        charged_currency = self._get_charged_currency(raw_txn.get('paymentCurrency'))

        # Get installments
        comments = raw_txn.get('comments', '')
        installments = self._get_installments_info(comments)

        # Build identifier
        arn = raw_txn.get('dealData', {}).get('arn') if raw_txn.get('dealData') else None
        if installments and arn:
            identifier = f"{arn}_{installments.number}"
        else:
            identifier = arn

        # Get category
        category_id = raw_txn.get('categoryId')
        category = self.categories.get(category_id) if category_id else None

        return Transaction(
            identifier=identifier,
            transaction_type=transaction_type,
            status=status,
            date=purchase_dt.isoformat(),
            processed_date=payment_dt.isoformat(),
            original_amount=original_amount,
            original_currency=original_currency,
            charged_amount=charged_amount,
            charged_currency=charged_currency,
            description=raw_txn.get('merchantName', '').strip(),
            memo=self._get_memo(raw_txn),
            category=category,
            installments=installments,
        )

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

        # Max allows up to 4 years back
        max_start_date = datetime.now() - timedelta(days=4 * 365)
        if start_date < max_start_date:
            logger.warning(f"Start date limited to 4 years back: {max_start_date.date()}")
            start_date = max_start_date

        logger.info(f"Fetching transactions from {start_date.date()} to {end_date.date()}")

        # Load categories
        self.load_categories()

        # Fetch transactions by month
        all_transactions: Dict[str, List[Transaction]] = {}

        current_date = end_date
        while current_date >= start_date:
            month = current_date.month
            year = current_date.year

            month_transactions = self.fetch_transactions_for_month(month, year)

            # Merge into all_transactions
            for card_number, transactions in month_transactions.items():
                if card_number not in all_transactions:
                    all_transactions[card_number] = []
                all_transactions[card_number].extend(transactions)

            # Move to previous month (set day=1 to avoid "day out of range" errors)
            if current_date.month == 1:
                current_date = current_date.replace(year=current_date.year - 1, month=12, day=1)
            else:
                current_date = current_date.replace(month=current_date.month - 1, day=1)

        # Filter and sort transactions
        accounts = []
        for card_number, transactions in all_transactions.items():
            # Filter by date
            filtered_txns = [
                t for t in transactions
                if start_date <= datetime.fromisoformat(t.date) <= end_date
            ]

            # Sort by date
            filtered_txns.sort(key=lambda t: t.date, reverse=True)

            logger.info(f"Found {len(filtered_txns)} transactions for card {card_number}")

            accounts.append(CardAccount(
                account_number=card_number,
                transactions=filtered_txns
            ))

        return accounts


def main():
    """Main entry point for Max Credit Card Scraper"""
    import argparse
    import os
    from dotenv import load_dotenv
    from scrapers.config.logging_config import add_logging_args, setup_logging_from_args

    parser = argparse.ArgumentParser(description="Max Credit Card Transaction Scraper")
    add_logging_args(parser)
    parser.add_argument("--months-back", type=int, default=3, help="Months of history to fetch (default: 3)")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    args = parser.parse_args()

    setup_logging_from_args(args)
    load_dotenv()

    credentials = MaxCredentials(
        username=os.getenv("MAX_USERNAME", ""),
        password=os.getenv("MAX_PASSWORD", "")
    )

    scraper = MaxCreditCardScraper(credentials, headless=args.headless)

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

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()