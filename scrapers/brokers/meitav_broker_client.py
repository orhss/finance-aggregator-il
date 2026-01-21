"""
Meitav Broker Scraper
Automated balance and holdings extraction for Meitav Dash (Spark) broker accounts
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional, List

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from scrapers.base.selenium_driver import SeleniumDriver, DriverConfig

logger = logging.getLogger(__name__)


# Configuration
@dataclass
class MeitavCredentials:
    """Meitav login credentials"""
    username: str  # Card number (מספר כרטיס)
    password: str


@dataclass
class MeitavBalance:
    """Account balance information"""
    total_value: float  # שווי נוכחי בש"ח
    daily_profit_loss: float  # רווח והפסד יומי
    daily_change_percent: float  # שינוי ב-%
    cash_balance: float  # סה"כ מזומנים למטבע
    cash_currency: str  # Currency of cash balance
    income_to_receive: float  # הכנסה לקבל
    change_from_cost: float  # שינוי מעלות
    change_from_cost_percent: float  # שינוי מעלות %
    margin_balance: Optional[float] = None  # יתרת בטחונות


@dataclass
class MeitavHolding:
    """Individual holding/security"""
    name: str
    symbol: Optional[str]
    quantity: float
    current_price: float
    current_value: float
    cost_basis: Optional[float] = None
    profit_loss: Optional[float] = None
    profit_loss_percent: Optional[float] = None


@dataclass
class MeitavAccount:
    """Complete account information"""
    account_number: str
    balance: MeitavBalance
    holdings: List[MeitavHolding]


# Exceptions
class MeitavScraperError(Exception):
    """Base exception for Meitav scraper errors"""
    pass


class MeitavLoginError(MeitavScraperError):
    """Login failed"""
    pass


class MeitavDataExtractionError(MeitavScraperError):
    """Data extraction failed"""
    pass


class MeitavBrokerScraper:
    """
    Automated scraper for Meitav Dash (Spark) broker accounts.

    Uses Selenium to handle login and extract account data from the web interface.
    """

    LOGIN_URL = "https://sparkmeitav.ordernet.co.il/#/auth"

    # Selectors for login
    USERNAME_SELECTOR = "input[name='username']"
    PASSWORD_SELECTOR = "input#password"
    LOGIN_BUTTON_SELECTOR = "button#btnSubmit"

    # Selectors for post-login popups
    ENTER_SYSTEM_BUTTON_SELECTOR = "button.btn.btn-primary[ng-click='vm.close()']"
    OK_BUTTON_SELECTOR = "button.btn.btn-primary[ng-click='vm.ok()']"
    CLOSE_CONTINUE_BUTTON_SELECTOR = "button.btn.fmr-btn[ng-click='vm.cancel()']"
    READ_BUTTON_SELECTOR = "button[ng-click*='read'], button:contains('קרא')"  # "קרא" button

    # Selectors for financial data
    SUMMARY_PANEL_SELECTOR = "div.label-presenter"
    PANEL_ITEM_SELECTOR = "div.label-presenter-item-container"
    PANEL_HEADING_SELECTOR = "div.panel-heading"
    PANEL_BODY_SELECTOR = "div.panel-body"

    # Holdings table selector (from your CSS path)
    HOLDINGS_CONTAINER_SELECTOR = "div.tab-pane.active dr-tab-module div.panel-body"

    def __init__(self, credentials: MeitavCredentials, headless: bool = True):
        self.credentials = credentials
        self.headless = headless
        self._selenium_driver: Optional[SeleniumDriver] = None
        self.driver = None  # Will be set by setup_driver
        self.account_number: Optional[str] = None

    def setup_driver(self):
        """Setup Chrome WebDriver using centralized SeleniumDriver"""
        config = DriverConfig(
            headless=self.headless,
            extra_arguments=['--lang=he-IL']  # Hebrew language support
        )
        self._selenium_driver = SeleniumDriver(config)
        self.driver = self._selenium_driver.setup()

    def cleanup(self):
        """Clean up resources"""
        logger.debug("Starting cleanup process...")
        if self._selenium_driver:
            self._selenium_driver.cleanup()
            self._selenium_driver = None
        self.driver = None
        logger.debug("Cleanup completed")

    def _type_human_like(self, element, text: str, delay: float = 0.05):
        """Type text character by character with human-like delays"""
        for char in text:
            element.send_keys(char)
            time.sleep(delay)

    def _click_button_if_exists(self, selectors: List[str], timeout: float = 3) -> bool:
        """
        Try to click a button using multiple possible selectors.
        Returns True if a button was found and clicked.
        """
        for selector in selectors:
            try:
                button = WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                button.click()
                logger.debug(f"Clicked button with selector: {selector}")
                return True
            except TimeoutException:
                continue
            except NoSuchElementException:
                continue
        return False

    def _handle_post_login_popups(self, max_attempts: int = 5):
        """
        Handle various popups that may appear after login.
        These include: login confirmation, notifications, announcements, etc.
        """
        logger.info("Handling post-login popups...")

        popup_selectors = [
            # "קרא" (Read) button - dismisses popup permanently
            "button[ng-click*='read']",
            # "כניסה למערכת" (Enter system) button
            "button.btn.btn-primary[ng-click='vm.close()']",
            # "אישור" (OK) button
            "button.btn.btn-primary[ng-click='vm.ok()']",
            # "סגור והמשך" (Close and continue) button
            "button.btn.fmr-btn[ng-click='vm.cancel()']",
            # Generic close buttons
            "button.close",
            "button[aria-label='Close']",
        ]

        for attempt in range(max_attempts):
            popup_found = False

            for selector in popup_selectors:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            button_text = button.text.strip()
                            logger.debug(f"Found popup button: '{button_text}' with selector: {selector}")
                            button.click()
                            popup_found = True
                            time.sleep(1)  # Wait for popup to close
                            break
                    if popup_found:
                        break
                except Exception as e:
                    logger.debug(f"Error checking selector {selector}: {e}")
                    continue

            if not popup_found:
                logger.debug(f"No more popups found after {attempt + 1} attempts")
                break

            time.sleep(0.5)

        logger.info("Finished handling popups")

    def login(self) -> bool:
        """
        Perform login to Meitav website.

        Returns:
            True if login successful

        Raises:
            MeitavLoginError: If login fails
        """
        try:
            if not self.driver:
                self.setup_driver()

            logger.info(f"Step 1/4: Navigating to {self.LOGIN_URL}...")
            self.driver.get(self.LOGIN_URL)

            # Wait for page to load
            time.sleep(2)

            # Enter username (card number)
            logger.info("Step 2/4: Entering credentials...")
            username_field = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.USERNAME_SELECTOR))
            )
            username_field.clear()
            self._type_human_like(username_field, self.credentials.username)

            # Enter password
            logger.debug("Entering password...")
            password_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.PASSWORD_SELECTOR))
            )
            password_field.clear()
            self._type_human_like(password_field, self.credentials.password)

            # Click login button
            logger.info("Step 3/4: Submitting login form...")
            login_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.LOGIN_BUTTON_SELECTOR))
            )
            login_button.click()

            # Wait for login to complete (at least 10 seconds as specified)
            logger.debug("Waiting for login to complete...")
            time.sleep(10)

            # Handle the "כניסה למערכת" (Enter system) popup
            logger.info("Step 4/4: Handling login confirmation...")
            try:
                # Look for the account number in the popup to extract it
                account_elem = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "div.info-item-body.highlighted-text"
                )
                self.account_number = account_elem.text.strip()
                logger.debug(f"Extracted account number: {self.account_number}")
            except NoSuchElementException:
                logger.debug("Could not extract account number from popup")

            # Click "כניסה למערכת" button
            enter_button_clicked = self._click_button_if_exists(
                [self.ENTER_SYSTEM_BUTTON_SELECTOR],
                timeout=5
            )

            if not enter_button_clicked:
                logger.warning("Could not find 'Enter System' button, continuing anyway...")

            time.sleep(2)

            # Handle any additional popups
            self._handle_post_login_popups()

            # Verify we're logged in by checking for dashboard elements
            time.sleep(3)

            current_url = self.driver.current_url
            logger.debug(f"Current URL after login: {current_url}")

            if "auth" in current_url.lower():
                # Still on login page - login might have failed
                raise MeitavLoginError("Login appears to have failed - still on auth page")

            logger.info("Login successful!")
            return True

        except TimeoutException as e:
            raise MeitavLoginError(f"Timeout during login: {e}")
        except MeitavLoginError:
            raise
        except Exception as e:
            raise MeitavLoginError(f"Login failed: {e}")

    def _parse_number(self, text: str) -> float:
        """Parse a number from text, handling Hebrew formatting"""
        if not text:
            return 0.0
        # Remove commas and any non-numeric characters except decimal point and minus
        cleaned = text.replace(',', '').replace('₪', '').replace('%', '').strip()
        # Handle Hebrew minus sign
        cleaned = cleaned.replace('−', '-')
        try:
            return float(cleaned)
        except ValueError:
            logger.warning(f"Could not parse number from: '{text}'")
            return 0.0

    def extract_balance(self) -> MeitavBalance:
        """
        Extract account balance information from the dashboard.

        Returns:
            MeitavBalance with account summary data

        Raises:
            MeitavDataExtractionError: If extraction fails
        """
        logger.info("Extracting balance information...")

        try:
            # Wait for the summary panel to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.SUMMARY_PANEL_SELECTOR))
            )

            # Find all panel items
            panel_items = self.driver.find_elements(By.CSS_SELECTOR, self.PANEL_ITEM_SELECTOR)

            # Initialize balance data
            balance_data = {
                'total_value': 0.0,
                'daily_profit_loss': 0.0,
                'daily_change_percent': 0.0,
                'cash_balance': 0.0,
                'cash_currency': 'ILS',
                'income_to_receive': 0.0,
                'change_from_cost': 0.0,
                'change_from_cost_percent': 0.0,
                'margin_balance': None,
            }

            # Field mapping (Hebrew to English)
            field_mapping = {
                'שווי נוכחי': 'total_value',
                'רווח והפסד יומי': 'daily_profit_loss',
                'שינוי ב-%': 'daily_change_percent',
                'סה"כ מזומנים': 'cash_balance',
                'הכנסה לקבל': 'income_to_receive',
                'שינוי מעלות %': 'change_from_cost_percent',
                'שינוי מעלות': 'change_from_cost',
                'יתרת בטחונות': 'margin_balance',
            }

            for item in panel_items:
                try:
                    # Get heading text
                    heading = item.find_element(By.CSS_SELECTOR, self.PANEL_HEADING_SELECTOR)
                    heading_text = heading.text.strip()

                    # Get body/value
                    body = item.find_element(By.CSS_SELECTOR, self.PANEL_BODY_SELECTOR)
                    # Try to get the span with actual value
                    try:
                        value_elem = body.find_element(By.CSS_SELECTOR, "span")
                        value_text = value_elem.get_attribute("title") or value_elem.text
                    except NoSuchElementException:
                        value_text = body.text

                    value_text = value_text.strip()

                    logger.debug(f"Found field: '{heading_text}' = '{value_text}'")

                    # Map to balance data
                    for hebrew_key, english_key in field_mapping.items():
                        if hebrew_key in heading_text:
                            if english_key == 'daily_change_percent' or english_key == 'change_from_cost_percent':
                                # Remove % sign before parsing
                                value = self._parse_number(value_text.replace('%', ''))
                            else:
                                value = self._parse_number(value_text)
                            balance_data[english_key] = value
                            logger.debug(f"Mapped {hebrew_key} -> {english_key} = {value}")
                            break

                except Exception as e:
                    logger.debug(f"Error processing panel item: {e}")
                    continue

            logger.info(f"Extracted balance: Total value = {balance_data['total_value']:,.2f} ILS")

            return MeitavBalance(**balance_data)

        except TimeoutException:
            raise MeitavDataExtractionError("Timeout waiting for balance data to load")
        except Exception as e:
            raise MeitavDataExtractionError(f"Failed to extract balance: {e}")

    def extract_holdings(self) -> List[MeitavHolding]:
        """
        Extract individual holdings from the portfolio.

        Note: This requires navigating to or finding the holdings table.
        The implementation depends on the actual page structure.

        Returns:
            List of MeitavHolding objects
        """
        logger.info("Extracting holdings information...")
        holdings = []

        try:
            # The holdings are in a table within the tab content
            # This selector is based on the CSS path you provided
            holdings_container = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "div.tab-pane.active"
                ))
            )

            # Look for table rows in the holdings area
            # The actual structure may vary - this is a common pattern
            rows = holdings_container.find_elements(By.CSS_SELECTOR, "tr, div.row")

            for row in rows:
                try:
                    # Extract holding data from row
                    cells = row.find_elements(By.CSS_SELECTOR, "td, div.cell, span")
                    if len(cells) >= 3:
                        holding = MeitavHolding(
                            name=cells[0].text.strip(),
                            symbol=None,
                            quantity=self._parse_number(cells[1].text) if len(cells) > 1 else 0,
                            current_price=self._parse_number(cells[2].text) if len(cells) > 2 else 0,
                            current_value=self._parse_number(cells[3].text) if len(cells) > 3 else 0,
                        )
                        if holding.name:
                            holdings.append(holding)
                except Exception as e:
                    logger.debug(f"Error processing holding row: {e}")
                    continue

            logger.info(f"Extracted {len(holdings)} holdings")

        except TimeoutException:
            logger.warning("Could not find holdings container - returning empty list")
        except Exception as e:
            logger.warning(f"Error extracting holdings: {e}")

        return holdings

    def scrape(self) -> MeitavAccount:
        """
        Complete scraping flow: login and extract all account data.

        Returns:
            MeitavAccount with balance and holdings
        """
        try:
            logger.info("Starting Meitav broker scraper...")

            # Login
            self.login()

            # Wait for dashboard to fully load
            time.sleep(3)

            # Extract balance
            balance = self.extract_balance()

            # Extract holdings (optional - may not be available on all views)
            holdings = self.extract_holdings()

            account = MeitavAccount(
                account_number=self.account_number or "Unknown",
                balance=balance,
                holdings=holdings
            )

            logger.info(f"Scraping complete for account {account.account_number}")
            return account

        finally:
            self.cleanup()


def main():
    """Main entry point for Meitav Broker Scraper"""
    import argparse
    import os
    from dotenv import load_dotenv

    parser = argparse.ArgumentParser(description="Meitav Broker Account Scraper")
    parser.add_argument("--headless", action="store_true", default=True, help="Run browser in headless mode")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="Run browser in visible mode")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    load_dotenv()

    # Try loading from config system first, fallback to env vars
    username = None
    password = None

    try:
        from config.settings import load_credentials
        creds = load_credentials()
        if creds.meitav.username and creds.meitav.password:
            username = creds.meitav.username
            password = creds.meitav.password
            logger.info("Loaded credentials from config system")
    except Exception as e:
        logger.debug(f"Could not load from config: {e}")

    # Fallback to environment variables
    if not username or not password:
        username = os.getenv("MEITAV_USERNAME", "")
        password = os.getenv("MEITAV_PASSWORD", "")

    if not username or not password:
        print("Error: Meitav credentials not configured")
        print("Configure via: fin-cli config setup")
        print("Or set MEITAV_USERNAME and MEITAV_PASSWORD environment variables")
        return

    credentials = MeitavCredentials(
        username=username,
        password=password
    )

    scraper = MeitavBrokerScraper(credentials, headless=args.headless)

    try:
        account = scraper.scrape()

        print(f"\n{'='*60}")
        print(f"Account: {account.account_number}")
        print(f"{'='*60}")
        print(f"\nBalance Summary:")
        print(f"  Total Value:           {account.balance.total_value:>15,.2f} ILS")
        print(f"  Daily P&L:             {account.balance.daily_profit_loss:>15,.2f} ILS")
        print(f"  Daily Change:          {account.balance.daily_change_percent:>15.2f}%")
        print(f"  Cash Balance:          {account.balance.cash_balance:>15,.2f} {account.balance.cash_currency}")
        print(f"  Income to Receive:     {account.balance.income_to_receive:>15,.2f} ILS")
        print(f"  Change from Cost:      {account.balance.change_from_cost:>15,.2f} ILS")
        print(f"  Change from Cost %:    {account.balance.change_from_cost_percent:>15.2f}%")
        if account.balance.margin_balance is not None:
            print(f"  Margin Balance:        {account.balance.margin_balance:>15,.2f} ILS")

        if account.holdings:
            print(f"\nHoldings ({len(account.holdings)}):")
            for holding in account.holdings[:10]:  # Show first 10
                print(f"  {holding.name:30} | {holding.quantity:>10.2f} | {holding.current_value:>12,.2f}")

    except MeitavLoginError as e:
        print(f"Login Error: {e}")
    except MeitavDataExtractionError as e:
        print(f"Data Extraction Error: {e}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()