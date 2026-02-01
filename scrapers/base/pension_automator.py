"""
Pension Automator Base Class

Provides the foundation for pension site automation with:
- Selenium WebDriver management via SeleniumDriver
- Web interactions via WebActions
- MFA code entry via MFAHandler
- Reusable login flows for different institution patterns

Replaces the deprecated SeleniumMFAAutomatorBase from pension_base.py.
"""

import time
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Dict, Any, List

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from scrapers.base.selenium_driver import SeleniumDriver, DriverConfig
from scrapers.base.web_actions import WebActions
from scrapers.base.mfa_handler import MFAHandler, MFAEntryError
from scrapers.base.email_retriever import EmailMFARetriever

logger = logging.getLogger(__name__)


class PensionAutomatorBase(ABC):
    """
    Base class for pension site automation

    Provides reusable login flows for pension sites with MFA:
    - Migdal pattern: ID → select email MFA → continue → MFA (6 individual fields)
    - Phoenix pattern: ID + email → login → MFA (single field) → submit

    Uses composition of modular components:
    - SeleniumDriver: Browser lifecycle management
    - WebActions: Form filling, button clicking
    - MFAHandler: MFA code entry
    - EmailMFARetriever: Email-based MFA retrieval

    Subclasses only need to implement:
    - extract_financial_data(): Institution-specific data extraction
    """

    def __init__(self, email_retriever: EmailMFARetriever, headless: bool = True):
        """
        Initialize pension automator

        Args:
            email_retriever: Email retriever for MFA codes (institution-specific)
            headless: Whether to run browser in headless mode
        """
        self.email_retriever = email_retriever
        self.headless = headless

        # Composed components (initialized on demand)
        self._selenium_driver: Optional[SeleniumDriver] = None
        self._web_actions: Optional[WebActions] = None
        self._mfa_handler: Optional[MFAHandler] = None

        # Timing configuration (can be overridden by subclasses)
        self.post_login_delay = 5  # Seconds after clicking login
        self.mfa_submission_delay = 5  # Seconds after entering MFA
        self.login_processing_delay = 10  # Seconds after MFA submission

    @property
    def driver(self):
        """Get the underlying WebDriver (for compatibility and data extraction)"""
        if self._selenium_driver:
            return self._selenium_driver.get_driver()
        return None

    def setup_driver(self):
        """Setup Chrome WebDriver and initialize components"""
        logger.info("Setting up Chrome WebDriver...")
        config = DriverConfig(headless=self.headless)
        self._selenium_driver = SeleniumDriver(config)
        driver = self._selenium_driver.setup()

        # Initialize helper components
        self._web_actions = WebActions(driver)
        self._mfa_handler = MFAHandler(driver)

        return driver

    def cleanup(self):
        """Clean up all resources (safe to call multiple times)"""
        logger.info("Starting cleanup process...")

        if self._selenium_driver:
            self._selenium_driver.cleanup()
            self._selenium_driver = None
            self._web_actions = None
            self._mfa_handler = None

        self.email_retriever.disconnect()
        logger.info("Cleanup completed")

    def __enter__(self):
        """Context manager entry"""
        self.setup_driver()
        return self

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        """Context manager exit"""
        self.cleanup()

    # =========================================================================
    # Login Flow: ID + Email MFA Selection (Migdal pattern)
    # Flow: Enter ID → Select email MFA option → Click continue → Enter MFA code
    # =========================================================================

    def login_with_id_and_mfa_flow(
        self,
        site_url: str,
        id_number: str,
        id_selector: str,
        login_button_selector: str,
        email_label_selector: str,
        continue_button_selector: str,
        otp_selectors: List[str],
        submit_button_selector: Optional[str] = None,
        fallback_selectors: Optional[Dict[str, List[str]]] = None
    ) -> bool:
        """
        Complete login flow with ID and email MFA selection (Migdal pattern)

        Flow:
        1. Navigate to login page
        2. Enter ID number
        3. Select email MFA option
        4. Click login button
        5. Wait for loader, click continue button
        6. Wait for MFA prompt
        7. Retrieve MFA code from email
        8. Enter MFA code into individual fields
        9. (Optionally) click submit button

        Args:
            site_url: URL to login page
            id_number: ID number to enter
            id_selector: CSS selector for ID input field
            login_button_selector: CSS selector for login button
            email_label_selector: CSS selector for email MFA option
            continue_button_selector: CSS selector for continue button
            otp_selectors: List of selectors for OTP fields (6 for individual fields)
            submit_button_selector: Optional selector for MFA submit button
            fallback_selectors: Dict of fallback selectors for elements

        Returns:
            True if login successful, False otherwise
        """
        fallback_selectors = fallback_selectors or {}

        try:
            # Ensure driver is set up
            if not self.driver:
                self.setup_driver()

            # Navigate to login page
            logger.info(f"Step 1/6: Navigating to login page: {site_url}")
            self.driver.get(site_url)

            # Enter ID number
            logger.info("Step 2/6: Entering ID number...")
            if not self._web_actions.enter_text_human_like(id_selector, id_number):
                logger.error("Failed to enter ID number")
                return False

            # Small delay to allow page to update
            time.sleep(2)

            # Select email MFA option
            logger.info("Step 3/6: Selecting email MFA option...")
            email_fallbacks = fallback_selectors.get('email_label', [])
            if not self._web_actions.select_option(email_label_selector, email_fallbacks):
                logger.warning("Could not select email MFA option, proceeding anyway...")

            time.sleep(1)

            # Click initial login button
            login_time = datetime.now()
            login_fallbacks = fallback_selectors.get('login_button', [])
            if not self._web_actions.click_button(login_button_selector, login_fallbacks):
                logger.error("Failed to click login button")
                return False

            # Wait for loader to disappear
            logger.info(f"Waiting {self.post_login_delay}s for page to process...")
            time.sleep(self.post_login_delay)

            # Click continue button
            continue_fallbacks = fallback_selectors.get('continue_button', [])
            if not self._web_actions.click_button(continue_button_selector, continue_fallbacks):
                logger.error("Failed to click continue button")
                return False

            # Wait for MFA prompt
            if not self._wait_for_mfa_prompt(otp_selectors[0]):
                logger.error("Failed to find MFA prompt")
                return False

            # Wait for MFA code in email
            logger.info("Waiting for MFA code in email...")
            mfa_code = self.email_retriever.wait_for_mfa_code(
                since_time=login_time,
                initial_delay=self.email_retriever.mfa_config.email_delay
            )

            if not mfa_code:
                logger.error("Failed to retrieve MFA code")
                return False

            logger.info(f"Retrieved MFA code: {mfa_code}")

            # Enter MFA code
            if len(otp_selectors) == 6:
                # Individual digit fields (Migdal pattern)
                if not self._mfa_handler.enter_code_individual_fields(mfa_code, otp_selectors):
                    logger.error("Failed to enter MFA code into individual fields")
                    return False
            else:
                # Single field pattern
                if not self._mfa_handler.enter_code_single_field(mfa_code, otp_selectors[0]):
                    logger.error("Failed to enter MFA code")
                    return False

            # Wait after entering MFA
            logger.info(f"Waiting {self.mfa_submission_delay}s for MFA processing...")
            time.sleep(self.mfa_submission_delay)

            # Click submit button if provided
            if submit_button_selector:
                submit_fallbacks = fallback_selectors.get('submit_button', [])
                self._mfa_handler.submit_mfa(submit_button_selector, submit_fallbacks)

            # Wait for page to process login
            logger.info(f"Waiting {self.login_processing_delay}s for login to complete...")
            time.sleep(self.login_processing_delay)

            current_url = self.driver.current_url
            logger.info(f"Current URL after MFA: {current_url}")
            logger.info("Login successful!")
            return True

        except MFAEntryError as e:
            logger.error(f"MFA entry failed: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Error during login flow: {e}", exc_info=True)
            return False

    # =========================================================================
    # Login Flow: ID + Email Fields (Phoenix pattern)
    # Flow: Enter ID + Email → Click login → Enter MFA code → Submit
    # =========================================================================

    def login_with_id_email_and_mfa_flow(
        self,
        site_url: str,
        id_number: str,
        email_address: str,
        id_selector: str,
        email_selector: str,
        login_button_selector: str,
        otp_selector: str,
        submit_button_selector: str,
        fallback_selectors: Optional[Dict[str, List[str]]] = None
    ) -> bool:
        """
        Complete login flow with ID, email, and MFA (Phoenix pattern)

        Flow:
        1. Navigate to login page
        2. Enter ID number
        3. Enter email address
        4. Click login button
        5. Wait for MFA prompt
        6. Retrieve MFA code from email
        7. Enter MFA code into single field
        8. Click submit button

        Args:
            site_url: URL to login page
            id_number: ID number to enter
            email_address: Email address to enter
            id_selector: CSS selector for ID input field
            email_selector: CSS selector for email input field
            login_button_selector: CSS selector for login button
            otp_selector: CSS selector for OTP input field
            submit_button_selector: CSS selector for MFA submit button
            fallback_selectors: Dict of fallback selectors for elements

        Returns:
            True if login successful, False otherwise
        """
        fallback_selectors = fallback_selectors or {}

        try:
            # Ensure driver is set up
            if not self.driver:
                self.setup_driver()

            # Navigate to login page
            logger.info(f"Step 1/5: Navigating to login page: {site_url}")
            self.driver.get(site_url)

            # Enter ID number
            logger.info("Step 2/5: Entering credentials...")
            if not self._web_actions.enter_text_human_like(id_selector, id_number):
                logger.error("Failed to enter ID number")
                return False

            # Enter email address
            if not self._web_actions.enter_text_human_like(email_selector, email_address):
                logger.error("Failed to enter email address")
                return False

            # Click login button
            logger.info("Step 3/5: Clicking login button...")
            login_time = datetime.now()
            login_fallbacks = fallback_selectors.get('login_button', [])
            if not self._web_actions.click_button(login_button_selector, login_fallbacks):
                logger.error("Failed to click login button")
                return False

            # Check for immediate MFA field or wait for it
            otp_fallbacks = fallback_selectors.get('otp_field', [])
            all_otp_selectors = [otp_selector] + otp_fallbacks

            mfa_field_found = self._web_actions.check_element_exists(all_otp_selectors)
            if not mfa_field_found:
                if not self._wait_for_mfa_prompt(otp_selector):
                    logger.error("Failed to find MFA prompt")
                    return False

            # Wait for MFA code in email
            logger.info("Waiting for MFA code in email...")
            mfa_code = self.email_retriever.wait_for_mfa_code(
                since_time=login_time,
                initial_delay=self.email_retriever.mfa_config.email_delay
            )

            if not mfa_code:
                logger.error("Failed to retrieve MFA code")
                return False

            logger.info(f"Retrieved MFA code: {mfa_code}")

            # Enter MFA code into single field
            if not self._mfa_handler.enter_code_single_field(mfa_code, otp_selector, otp_fallbacks):
                logger.error("Failed to enter MFA code")
                return False

            # Wait before submitting
            time.sleep(self.mfa_submission_delay)

            # Click submit button
            submit_fallbacks = fallback_selectors.get('submit_button', [])
            try:
                self._mfa_handler.submit_mfa(submit_button_selector, submit_fallbacks)
            except MFAEntryError as e:
                logger.warning(f"Could not click submit button: {e}")
                # Some sites auto-submit, so continue

            # Wait for page to process login
            logger.info(f"Waiting {self.login_processing_delay}s for login to complete...")
            time.sleep(self.login_processing_delay)

            current_url = self.driver.current_url
            logger.info(f"Current URL after MFA: {current_url}")
            logger.info("Login successful!")
            return True

        except MFAEntryError as e:
            logger.error(f"MFA entry failed: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Error during login flow: {e}", exc_info=True)
            return False

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _wait_for_mfa_prompt(self, otp_selector: str, timeout: int = 15) -> bool:
        """Wait for MFA prompt to appear on the page"""
        try:
            logger.info("Waiting for MFA prompt...")
            element = self._web_actions.wait_for_element(otp_selector, "present", timeout=timeout)
            if element:
                logger.info("MFA prompt found")
                return True
            logger.error(f"MFA prompt not found after {timeout}s")
            return False
        except Exception as e:
            logger.error(f"Error waiting for MFA prompt: {e}", exc_info=True)
            return False

    def wait_for_page_processing(self) -> str:
        """Wait for page to process and return current URL"""
        logger.info(f"Waiting {self.login_processing_delay}s for page to process...")
        time.sleep(self.login_processing_delay)
        current_url = self.driver.current_url
        logger.info(f"Current URL: {current_url}")
        return current_url

    # =========================================================================
    # Abstract Methods (must be implemented by subclasses)
    # =========================================================================

    @abstractmethod
    def login(self, site_url: str, credentials: Dict[str, str], selectors: Dict[str, str]) -> bool:
        """
        Perform login with the given credentials and selectors

        Args:
            site_url: URL of the login page
            credentials: Dictionary containing login credentials
            selectors: Dictionary containing CSS selectors for form elements

        Returns:
            True if login successful, False otherwise
        """
        pass

    @abstractmethod
    def extract_financial_data(self) -> Dict[str, Any]:
        """
        Extract financial data from the site after successful login

        Returns:
            Dictionary containing extracted financial data
        """
        pass

    def execute(self, site_url: str, credentials: Dict[str, str], selectors: Dict[str, str]) -> Dict[str, Any]:
        """
        Execute the complete automation flow (login + data extraction)

        Args:
            site_url: URL of the login page
            credentials: Dictionary containing login credentials
            selectors: Dictionary containing CSS selectors for form elements

        Returns:
            Dictionary containing extracted financial data, or empty dict if failed
        """
        try:
            logger.info(f"=== Starting {self.__class__.__name__} Automation ===")
            logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Perform login
            logger.info("1. Attempting login...")
            login_success = self.login(site_url, credentials, selectors)

            if not login_success:
                logger.error("Login failed, cannot extract data")
                return {}

            logger.info("2. Login successful! Extracting financial data...")

            # Extract financial data
            financial_data = self.extract_financial_data()

            logger.info("3. Data extraction completed")
            logger.info(f"=== {self.__class__.__name__} Automation Completed Successfully ===")

            return financial_data

        except Exception as e:
            logger.error(f"Error during automation execution: {e}", exc_info=True)
            return {}