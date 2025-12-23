"""
MFA code entry and submission handling
Supports both single-field and individual-field patterns
"""

import time
from typing import List, Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import logging

logger = logging.getLogger(__name__)


class MFAEntryError(Exception):
    """Raised when MFA code entry fails"""
    pass


class MFAHandler:
    """
    Handles MFA code entry with various input patterns

    Supports:
    - Single field (Phoenix pattern)
    - Individual digit fields (Migdal pattern)
    - Human-like typing with delays
    - Fallback selectors
    """

    def __init__(self, driver: WebDriver, timeout: int = 30):
        self.driver = driver
        self.timeout = timeout

    def enter_code_single_field(
        self,
        code: str,
        selector: str,
        fallback_selectors: Optional[List[str]] = None,
        typing_delay: float = 0.2
    ) -> bool:
        """
        Enter MFA code into single input field

        Args:
            code: MFA code to enter (e.g., "123456")
            selector: CSS selector for input field
            fallback_selectors: Alternative selectors to try
            typing_delay: Delay between characters (human-like)

        Returns:
            True if successful, False otherwise

        Raises:
            MFAEntryError: If code entry fails
        """
        if not self._validate_code(code):
            raise MFAEntryError(f"Invalid MFA code: {code}")

        # Try primary selector
        if self._try_enter_field(code, selector, typing_delay):
            return True

        # Try fallback selectors
        if fallback_selectors:
            for fallback in fallback_selectors:
                logger.debug(f"Trying fallback selector: {fallback}")
                if self._try_enter_field(code, fallback, typing_delay):
                    return True

        raise MFAEntryError(f"Could not find MFA input field with any selector")

    def enter_code_individual_fields(
        self,
        code: str,
        selectors: List[str],
        typing_delay: float = 0.2
    ) -> bool:
        """
        Enter MFA code into individual digit fields (Migdal pattern)

        Args:
            code: MFA code (must be 6 digits)
            selectors: List of selectors for each digit field (must be 6)
            typing_delay: Delay between characters

        Returns:
            True if successful

        Raises:
            MFAEntryError: If code entry fails
        """
        if not self._validate_code(code):
            raise MFAEntryError(f"Invalid MFA code: {code}")

        if len(selectors) != 6:
            raise MFAEntryError(f"Expected 6 selectors, got {len(selectors)}")

        logger.info("Entering MFA code into individual fields")

        for i, (digit, selector) in enumerate(zip(code, selectors)):
            try:
                field = WebDriverWait(self.driver, self.timeout).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                field.clear()
                field.send_keys(digit)
                logger.debug(f"Entered digit {i+1}/6")
                time.sleep(typing_delay)

            except TimeoutException:
                raise MFAEntryError(f"Timeout waiting for field {i+1} ({selector})")
            except Exception as e:
                raise MFAEntryError(f"Error entering digit {i+1}: {e}")

        logger.info("All digits entered successfully")
        return True

    def submit_mfa(
        self,
        button_selector: str,
        fallback_selectors: Optional[List[str]] = None,
        wait_before_submit: float = 1.0
    ) -> bool:
        """
        Click MFA submission button

        Args:
            button_selector: CSS selector or XPath for submit button
            fallback_selectors: Alternative selectors
            wait_before_submit: Delay before clicking (allow UI to update)

        Returns:
            True if successful

        Raises:
            MFAEntryError: If button not found or not clickable
        """
        if wait_before_submit > 0:
            logger.debug(f"Waiting {wait_before_submit}s before submitting")
            time.sleep(wait_before_submit)

        all_selectors = [button_selector] + (fallback_selectors or [])

        for selector in all_selectors:
            try:
                logger.debug(f"Looking for submit button: {selector}")

                if selector.startswith("//"):
                    button = self.driver.find_element(By.XPATH, selector)
                else:
                    button = self.driver.find_element(By.CSS_SELECTOR, selector)

                if button.is_enabled():
                    button.click()
                    logger.info("MFA submitted successfully")
                    return True
                else:
                    logger.debug(f"Button found but disabled: {selector}")

            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue

        raise MFAEntryError("Could not find or click MFA submit button")

    def _validate_code(self, code: str) -> bool:
        """Validate MFA code format"""
        return len(code) == 6 and code.isdigit()

    def _try_enter_field(
        self,
        code: str,
        selector: str,
        typing_delay: float
    ) -> bool:
        """Try to enter code in a specific field"""
        try:
            logger.debug(f"Looking for MFA field: {selector}")

            field = WebDriverWait(self.driver, self.timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )

            field.clear()

            # Type character by character
            for digit in code:
                field.send_keys(digit)
                time.sleep(typing_delay)

            # Trigger blur event
            self.driver.execute_script("arguments[0].blur();", field)
            time.sleep(0.5)

            logger.info(f"MFA code entered in field: {selector}")
            return True

        except TimeoutException:
            logger.debug(f"Field not found: {selector}")
            return False
        except Exception as e:
            logger.debug(f"Error with field {selector}: {e}")
            return False