from typing import List, Optional
import json
import logging
import os
import random
import time
from dotenv import load_dotenv

import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from scrapers.base.broker_base import AccountInfo, BalanceInfo, LoginCredentials, BrokerAPIClient
from scrapers.base.selenium_driver import SeleniumDriver, DriverConfig

load_dotenv()
logger = logging.getLogger(__name__)

# Exceptions
class BrokerAPIError(Exception):
    """Base exception for broker API errors"""
    pass


class AuthenticationError(BrokerAPIError):
    """Raised when authentication fails"""
    pass


class AccountError(BrokerAPIError):
    """Raised when account operations fail"""
    pass


class BalanceError(BrokerAPIError):
    """Raised when balance operations fail"""
    pass


# Concrete Implementation for ExtradeProAPI using Selenium
class ExtraDeProAPIClient(BrokerAPIClient):
    """
    Concrete implementation for ExtradePro broker API.
    Uses Selenium for login (to handle popups) and API calls for data.
    """

    BASE_URL = "https://extradepro.xnes.co.il"
    API_URL = "https://extradepro.xnes.co.il/api/v2/json2"

    def __init__(self, credentials: LoginCredentials, headless: bool = True):
        super().__init__(credentials)
        self.headless = headless
        self._selenium_driver: Optional[SeleniumDriver] = None
        self.driver = None  # Will be set by setup_driver
        self.api_session = requests.Session()
        self._headers = {
            'accept': 'application/json, text/plain, */*',
            'content-type': 'application/json; charset=UTF-8',
            'csession': str(random.random()),
            'origin': self.BASE_URL,
            'referer': f'{self.BASE_URL}/login',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'
        }

    def setup_driver(self):
        """Setup Chrome WebDriver using centralized SeleniumDriver"""
        config = DriverConfig(
            headless=self.headless,
            user_agent=self._headers["user-agent"],
            enable_performance_logging=True  # Needed to capture session key from network logs
        )
        self._selenium_driver = SeleniumDriver(config)
        self.driver = self._selenium_driver.setup()

    def cleanup(self):
        """Clean up resources"""
        if self._selenium_driver:
            self._selenium_driver.cleanup()
            self._selenium_driver = None
        self.driver = None
        self.session_key = None
        self.accounts = []

    def _human_delay(self, min_sec: float = 1.0, max_sec: float = 2.0) -> None:
        """Add a randomized delay to mimic human behavior"""
        time.sleep(random.uniform(min_sec, max_sec))

    def _dismiss_popups(self, max_attempts: int = 5):
        """
        Dismiss any popups like 'בואו נתחיל!' (Let's start!), release notes, etc.
        Tries multiple times since popups may appear at different moments.
        """
        for attempt in range(max_attempts):
            try:
                popup_found = False

                # Method 1: Find any button containing the Hebrew text "בואו נתחיל"
                try:
                    buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'בואו נתחיל')]")
                    for btn in buttons:
                        if btn.is_displayed():
                            logger.debug(f"Found popup button with Hebrew text, dismissing...")
                            btn.click()
                            popup_found = True
                            self._human_delay(0.5, 1.0)
                            break
                except Exception:
                    pass

                # Method 2: Try CSS selectors if XPath didn't work
                if not popup_found:
                    popup_selectors = [
                        "button.close-button",
                        "button.app-button.close-button",
                        ".release-notes-body button",
                    ]
                    for selector in popup_selectors:
                        try:
                            buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            for btn in buttons:
                                if btn.is_displayed() and btn.is_enabled():
                                    logger.debug(f"Found popup with selector '{selector}', dismissing...")
                                    btn.click()
                                    popup_found = True
                                    self._human_delay(0.5, 1.0)
                                    break
                            if popup_found:
                                break
                        except Exception:
                            continue

                if not popup_found:
                    # No popup found, we're done
                    logger.debug("No more popups found")
                    break

            except Exception as e:
                logger.debug(f"Popup dismiss attempt {attempt + 1} failed: {e}")
                break

    def login(self) -> str:
        """
        Authenticate with ExtradePro using Selenium.
        Handles popups and extracts session key.
        """
        try:
            if not self.driver:
                self.setup_driver()

            logger.info(f"Navigating to {self.BASE_URL}/login...")
            self.driver.get(f"{self.BASE_URL}/login")
            self._human_delay(1.0, 2.0)

            # Wait for username field
            logger.debug("Waiting for login form...")
            username_field = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[formcontrolname='username'], input[name='username'], input#username, input[type='text']"))
            )

            # Enter username with human-like typing
            logger.info("Entering credentials...")
            username_field.clear()
            for char in self.credentials.user:
                username_field.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))

            self._human_delay(0.3, 0.6)

            # Find and fill password field
            password_field = self.driver.find_element(By.CSS_SELECTOR, "input[formcontrolname='password'], input[name='password'], input#password, input[type='password']")
            password_field.clear()
            for char in self.credentials.password:
                password_field.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))

            self._human_delay(0.5, 1.0)

            # Click login button
            logger.info("Submitting login...")
            login_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], button.login-button")
            login_btn.click()

            # Wait for login to complete - wait for URL to change or dashboard element
            logger.debug("Waiting for login to complete...")
            try:
                WebDriverWait(self.driver, 15).until(
                    lambda d: "/login" not in d.current_url or "dashboard" in d.current_url or "main" in d.current_url
                )
            except TimeoutException:
                logger.warning("Timeout waiting for dashboard, continuing anyway...")

            self._human_delay(2.0, 3.0)

            # Dismiss any post-login popups
            self._dismiss_popups()

            # Wait for page to fully load after popup dismissed
            self._human_delay(2.0, 3.0)

            # Extract session key from localStorage or sessionStorage
            logger.info("Extracting session data...")
            session_key = self._extract_session_key()

            # Log what we found for debugging
            if session_key:
                display_key = f"{session_key[:20]}..." if len(session_key) > 20 else session_key
                logger.info(f"Session key found: {display_key}")

            if not session_key:
                # Log all storage for debugging
                all_local = self.driver.execute_script("return JSON.stringify(localStorage);")
                all_session = self.driver.execute_script("return JSON.stringify(sessionStorage);")
                logger.error(f"localStorage: {all_local}")
                logger.error(f"sessionStorage: {all_session}")
                raise AuthenticationError("Failed to obtain session key after login")

            self.session_key = session_key
            self._headers["session"] = session_key

            # Transfer cookies from Selenium to requests session
            self._transfer_cookies()

            logger.info("Login successful!")
            return session_key

        except TimeoutException as e:
            raise AuthenticationError(f"Timeout during login: {e}")
        except Exception as e:
            raise AuthenticationError(f"Login failed: {e}")

    def _extract_session_key(self) -> Optional[str]:
        """Extract session key from network logs (login API response)"""
        import json as json_module

        # Get performance logs and look for login response
        try:
            logs = self.driver.get_log('performance')
            for log in logs:
                try:
                    message = json_module.loads(log['message'])
                    method = message.get('message', {}).get('method', '')

                    # Look for Network.responseReceived for login endpoint
                    if method == 'Network.responseReceived':
                        params = message.get('message', {}).get('params', {})
                        response = params.get('response', {})
                        url = response.get('url', '')

                        if '/api/v2/json2/login' in url:
                            request_id = params.get('requestId')
                            # Get the response body
                            try:
                                body = self.driver.execute_cdp_cmd(
                                    'Network.getResponseBody',
                                    {'requestId': request_id}
                                )
                                response_text = body.get('body', '')
                                response_json = json_module.loads(response_text)
                                session_key = response_json.get('Login', {}).get('SessionKey')
                                if session_key:
                                    logger.debug(f"Found session key from login API response")
                                    return session_key
                            except Exception as e:
                                logger.debug(f"Could not get response body: {e}")
                                continue
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"Could not get performance logs: {e}")

        # Fallback: Try localStorage/sessionStorage
        try:
            session_data = self.driver.execute_script(
                "return localStorage.getItem('session') || localStorage.getItem('sessionKey');"
            )
            if session_data:
                return session_data
        except Exception:
            pass

        try:
            session_data = self.driver.execute_script(
                "return sessionStorage.getItem('session') || sessionStorage.getItem('sessionKey');"
            )
            if session_data:
                return session_data
        except Exception:
            pass

        return None

    def _transfer_cookies(self):
        """Transfer cookies from Selenium to requests session"""
        if self.driver:
            for cookie in self.driver.get_cookies():
                self.api_session.cookies.set(
                    cookie['name'],
                    cookie['value'],
                    domain=cookie.get('domain', ''),
                    path=cookie.get('path', '/')
                )

    def get_accounts(self) -> List[AccountInfo]:
        """Retrieve user accounts from ExtradePro API"""
        if not self.session_key:
            raise AuthenticationError("Must login first")

        self._human_delay(1.0, 2.0)

        url = f"{self.API_URL}/accounts"
        params = {"key": self.session_key}  # Session key required as query parameter
        response = self.api_session.get(url, headers=self._headers, params=params)
        response.raise_for_status()
        response_data = response.json()

        user_accounts = response_data.get("UserAccounts", {}).get("UserAccount", [])
        if not user_accounts:
            raise AccountError("No user accounts found")

        self.accounts = [
            AccountInfo(key=account.get("-key", ""))
            for account in user_accounts
        ]

        return self.accounts

    def get_balance(self, account: AccountInfo, currency: str = "ILS") -> BalanceInfo:
        """Get account balance from ExtradePro API"""
        if not self.session_key:
            raise AuthenticationError("Must login first")

        # API requires at least 1000ms between requests
        self._human_delay(1.2, 1.5)

        url = f"{self.API_URL}/account/view/balances"
        params = {
            "account": account.key,
            "fields": "Balance,Available,Used,Blocked,IsBlocked,IsMargin,IsShorting,IsForeign",
            "currency": currency,
            "key": self.session_key  # Session key required as query parameter
        }

        response = self.api_session.get(url, headers=self._headers, params=params)

        # Log response for debugging
        logger.debug(f"Balance API response status: {response.status_code}")
        logger.debug(f"Balance API response: {response.text[:500] if response.text else 'empty'}")

        response.raise_for_status()
        response_data = response.json()

        view_data = response_data.get("View", {}).get("Account", {})
        if not view_data:
            raise BalanceError("Failed to retrieve balance information")

        return BalanceInfo(
            total_amount=float(view_data.get('MorningValue', 0)),
            profit_loss=view_data.get('AveragePriceNisProfitLoss'),
            profit_loss_percentage=view_data.get('AveragePriceNisProfitLossPercentage'),
            blocked=view_data.get('Blocked'),
            is_blocked=view_data.get('IsBlocked'),
            is_margin=view_data.get('IsMargin'),
            is_shorting=view_data.get('IsShorting'),
            is_foreign=view_data.get('IsForeign')
        )

    def logout(self) -> bool:
        """Logout and cleanup"""
        self.cleanup()
        return True


# Factory Pattern for creating broker clients
class BrokerClientFactory:
    """Factory for creating broker API clients"""

    _clients = {
        'extradepro': ExtraDeProAPIClient
    }

    @classmethod
    def create_client(cls, broker_name: str, credentials: LoginCredentials) -> BrokerAPIClient:
        """Create a broker client instance"""
        if broker_name.lower() not in cls._clients:
            raise ValueError(f"Unsupported broker: {broker_name}")

        client_class = cls._clients[broker_name.lower()]
        return client_class(credentials)


# Facade Pattern - Simplified interface
class BrokerService:
    """Simplified facade for broker operations"""

    def __init__(self, broker_name: str, credentials: LoginCredentials):
        self.client = BrokerClientFactory.create_client(broker_name, credentials)

    def get_total_balance(self, currency: str = "ILS") -> float:
        """Get total balance with simplified interface"""
        try:
            # Login
            self.client.login()

            # Get accounts
            accounts = self.client.get_accounts()
            if not accounts:
                raise AccountError("No accounts available")

            # Get balance for first account
            balance = self.client.get_balance(accounts[0], currency)

            return balance.total_amount

        finally:
            # Always logout
            self.client.logout()


# Usage Example
def main():
    """Example usage of the broker API client"""
    # Create credentials
    credentials = LoginCredentials(os.getenv("EXELLENCE_USER_NAME"), password=os.getenv("EXELLENCE_PASSWORD"))

    # Method 1: Using the service facade
    broker_service = BrokerService("extradepro", credentials)
    total_amount = broker_service.get_total_balance()
    print(f"Total Amount: {total_amount}")

    # Method 2: Using the client directly
    client = BrokerClientFactory.create_client("extradepro", credentials)
    try:
        client.login()
        accounts = client.get_accounts()
        balance = client.get_balance(accounts[0])
        print(f"Balance Details: {balance}")
    finally:
        client.logout()


if __name__ == "__main__":
    main()
