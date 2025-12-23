"""
Web automation actions for Selenium

Provides reusable utilities for:
- Form filling with human-like typing
- Button clicking with fallback selectors
- Element waiting and detection
- Common web interaction patterns
"""

import time
import logging
from typing import List, Optional, Union
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    StaleElementReferenceException
)

logger = logging.getLogger(__name__)


class WebActionError(Exception):
    """Base exception for web action errors"""
    pass


class ElementNotFoundError(WebActionError):
    """Raised when element cannot be found"""
    def __init__(self, selector: str, message: str = None):
        self.selector = selector
        super().__init__(message or f"Element not found: {selector}")


class WebActions:
    """
    Utility class for common web automation actions

    Provides human-like interactions and robust element handling
    with fallback selectors and proper error handling.
    """

    def __init__(self, driver: WebDriver, default_timeout: int = 30):
        """
        Initialize WebActions

        Args:
            driver: Selenium WebDriver instance
            default_timeout: Default timeout for waits in seconds
        """
        self.driver = driver
        self.default_timeout = default_timeout

    def enter_text_human_like(
        self,
        selector: str,
        text: str,
        delay_between_chars: float = 0.1,
        clear_first: bool = True,
        trigger_blur: bool = True,
        by: By = By.CSS_SELECTOR,
        timeout: Optional[int] = None
    ) -> bool:
        """
        Enter text into a field with human-like typing behavior

        Args:
            selector: CSS selector or XPath for the input field
            text: Text to enter
            delay_between_chars: Delay between each character in seconds
            clear_first: Whether to clear the field before typing
            trigger_blur: Whether to trigger blur event after typing
            by: Selector type (CSS_SELECTOR or XPATH)
            timeout: Timeout for finding element

        Returns:
            True if successful, False otherwise
        """
        timeout = timeout or self.default_timeout

        try:
            logger.debug(f"Looking for input field: {selector}")
            field = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            logger.debug("Found input field")

            if clear_first:
                field.clear()

            # Type character by character
            logger.debug(f"Typing text: {text[:3]}..." if len(text) > 3 else f"Typing text: {text}")
            for char in text:
                field.send_keys(char)
                time.sleep(delay_between_chars)

            if trigger_blur:
                self.driver.execute_script("arguments[0].blur();", field)
                time.sleep(0.5)

            # Verify the text was entered correctly
            entered_value = field.get_attribute("value")
            if entered_value != text:
                logger.warning(f"Text mismatch. Expected: {text}, Got: {entered_value}")
                # Retry once
                field.clear()
                for char in text:
                    field.send_keys(char)
                    time.sleep(delay_between_chars)
                if trigger_blur:
                    self.driver.execute_script("arguments[0].blur();", field)
                    time.sleep(0.5)

            logger.info(f"Successfully entered text in field: {selector}")
            return True

        except TimeoutException:
            logger.error(f"Timeout waiting for field: {selector}")
            return False
        except Exception as e:
            logger.error(f"Error entering text in field {selector}: {e}", exc_info=True)
            return False

    def click_button(
        self,
        primary_selector: str,
        fallback_selectors: Optional[List[str]] = None,
        wait_for_enabled: bool = True,
        enabled_timeout: int = 5,
        by: By = By.CSS_SELECTOR,
        timeout: Optional[int] = None,
        fallback_timeout: int = 2
    ) -> bool:
        """
        Click a button with fallback selectors

        Args:
            primary_selector: Primary selector for the button
            fallback_selectors: List of fallback selectors to try
            wait_for_enabled: Whether to wait for button to be enabled
            enabled_timeout: Timeout for waiting for button to be enabled
            by: Selector type for primary selector
            timeout: Timeout for finding primary element
            fallback_timeout: Short timeout for fallback selectors (default 2s)

        Returns:
            True if button clicked successfully, False otherwise
        """
        timeout = timeout or self.default_timeout

        logger.debug(f"Looking for button: {primary_selector}")

        # Try primary selector first with full timeout
        if primary_selector:
            if self._try_click_button(primary_selector, by, timeout, wait_for_enabled, enabled_timeout):
                return True

        # Try fallback selectors with short timeout (don't wait long for each)
        if fallback_selectors:
            for selector in fallback_selectors:
                if self._try_click_button(selector, by, fallback_timeout, wait_for_enabled, enabled_timeout):
                    return True

        logger.error(f"Could not find or click button with any selector")
        return False

    def _try_click_button(
        self,
        selector: str,
        by: By,
        timeout: int,
        wait_for_enabled: bool,
        enabled_timeout: int
    ) -> bool:
        """Try to click a button with given selector"""
        try:
            # Determine selector type
            selector_by = By.XPATH if selector.startswith("//") else by

            button = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((selector_by, selector))
            )

            # Wait for button to be enabled if required
            if wait_for_enabled:
                logger.debug("Waiting for button to be enabled...")
                try:
                    WebDriverWait(self.driver, enabled_timeout).until(
                        lambda d: not button.get_attribute("disabled")
                    )
                except TimeoutException:
                    logger.debug(f"Button still disabled: {selector}")
                    return False

            if button.is_enabled():
                button.click()
                logger.info(f"Clicked button: {selector}")
                return True
            else:
                logger.debug(f"Button found but disabled: {selector}")
                return False

        except TimeoutException:
            logger.debug(f"Button not found: {selector}")
        except ElementClickInterceptedException:
            logger.debug(f"Button click intercepted: {selector}")
        except StaleElementReferenceException:
            logger.debug(f"Stale element: {selector}")
        except Exception as e:
            logger.debug(f"Error with button {selector}: {e}")

        return False

    def wait_for_element(
        self,
        selector: str,
        condition: str = "present",
        by: By = By.CSS_SELECTOR,
        timeout: Optional[int] = None
    ) -> Optional[WebElement]:
        """
        Wait for element with specified condition

        Args:
            selector: Element selector
            condition: Wait condition - "present", "visible", "clickable", "invisible"
            by: Selector type
            timeout: Timeout in seconds

        Returns:
            WebElement if found, None otherwise
        """
        timeout = timeout or self.default_timeout

        conditions = {
            "present": EC.presence_of_element_located,
            "visible": EC.visibility_of_element_located,
            "clickable": EC.element_to_be_clickable,
            "invisible": EC.invisibility_of_element_located
        }

        if condition not in conditions:
            raise ValueError(f"Unknown condition: {condition}. Use: {list(conditions.keys())}")

        try:
            logger.debug(f"Waiting for element ({condition}): {selector}")
            element = WebDriverWait(self.driver, timeout).until(
                conditions[condition]((by, selector))
            )
            logger.debug(f"Element found: {selector}")
            return element

        except TimeoutException:
            logger.debug(f"Timeout waiting for element ({condition}): {selector}")
            return None

    def check_element_exists(
        self,
        selectors: List[str],
        by: By = By.CSS_SELECTOR
    ) -> Optional[str]:
        """
        Check if any of the given elements exist on the page

        Args:
            selectors: List of selectors to check
            by: Selector type

        Returns:
            First matching selector if found, None otherwise
        """
        for selector in selectors:
            try:
                selector_by = By.XPATH if selector.startswith("//") else by
                element = self.driver.find_element(selector_by, selector)
                if element and element.is_displayed():
                    logger.debug(f"Element found: {selector}")
                    return selector
            except (NoSuchElementException, StaleElementReferenceException):
                continue

        return None

    def wait_for_url_contains(
        self,
        url_fragment: str,
        timeout: Optional[int] = None
    ) -> bool:
        """
        Wait until URL contains specific text

        Args:
            url_fragment: Text that URL should contain
            timeout: Timeout in seconds

        Returns:
            True if URL contains fragment, False on timeout
        """
        timeout = timeout or self.default_timeout

        try:
            logger.debug(f"Waiting for URL to contain: {url_fragment}")
            WebDriverWait(self.driver, timeout).until(
                EC.url_contains(url_fragment)
            )
            logger.info(f"URL now contains: {url_fragment}")
            return True
        except TimeoutException:
            logger.error(f"URL did not contain '{url_fragment}' after {timeout}s")
            return False

    def wait_for_page_load(self, timeout: Optional[int] = None) -> bool:
        """
        Wait for page to fully load

        Args:
            timeout: Timeout in seconds

        Returns:
            True if page loaded, False on timeout
        """
        timeout = timeout or self.default_timeout

        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            logger.debug("Page fully loaded")
            return True
        except TimeoutException:
            logger.warning("Page load timeout")
            return False

    def scroll_to_element(self, element: WebElement) -> bool:
        """
        Scroll element into view

        Args:
            element: WebElement to scroll to

        Returns:
            True if successful
        """
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                element
            )
            time.sleep(0.5)  # Allow scroll animation
            return True
        except Exception as e:
            logger.warning(f"Error scrolling to element: {e}")
            return False

    def get_element_text(
        self,
        selector: str,
        by: By = By.CSS_SELECTOR,
        timeout: Optional[int] = None
    ) -> Optional[str]:
        """
        Get text content of an element

        Args:
            selector: Element selector
            by: Selector type
            timeout: Timeout in seconds

        Returns:
            Element text if found, None otherwise
        """
        element = self.wait_for_element(selector, "visible", by, timeout)
        if element:
            return element.text
        return None

    def select_option(
        self,
        primary_selector: str,
        fallback_selectors: Optional[List[str]] = None,
        by: By = By.CSS_SELECTOR,
        timeout: Optional[int] = None,
        fallback_timeout: int = 2
    ) -> bool:
        """
        Click to select an option (like radio button or checkbox label)

        Args:
            primary_selector: Primary selector for the option
            fallback_selectors: Fallback selectors to try
            by: Selector type
            timeout: Timeout in seconds for primary selector
            fallback_timeout: Short timeout for fallback selectors (default 2s)

        Returns:
            True if option selected, False otherwise
        """
        timeout = timeout or self.default_timeout

        logger.debug(f"Looking for option: {primary_selector}")

        # Try primary selector first with full timeout
        if primary_selector:
            if self._try_select_option(primary_selector, by, timeout):
                return True

        # Try fallback selectors with short timeout
        if fallback_selectors:
            for selector in fallback_selectors:
                if self._try_select_option(selector, by, fallback_timeout):
                    return True

        logger.error("Could not find or select option with any selector")
        return False

    def _try_select_option(self, selector: str, by: By, timeout: int) -> bool:
        """Try to select an option with given selector"""
        try:
            selector_by = By.XPATH if selector.startswith("//") else by

            option = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((selector_by, selector))
            )
            option.click()
            logger.info(f"Selected option: {selector}")
            return True

        except TimeoutException:
            logger.debug(f"Option not found or not clickable: {selector}")
        except Exception as e:
            logger.debug(f"Error selecting option {selector}: {e}")

        return False

    def switch_to_iframe(
        self,
        selector: str,
        by: By = By.CSS_SELECTOR,
        timeout: Optional[int] = None
    ) -> bool:
        """
        Switch to an iframe

        Args:
            selector: Iframe selector
            by: Selector type
            timeout: Timeout in seconds

        Returns:
            True if switched successfully
        """
        timeout = timeout or self.default_timeout

        try:
            iframe = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            self.driver.switch_to.frame(iframe)
            logger.debug(f"Switched to iframe: {selector}")
            return True
        except Exception as e:
            logger.error(f"Error switching to iframe {selector}: {e}")
            return False

    def switch_to_default_content(self):
        """Switch back to main document from iframe"""
        self.driver.switch_to.default_content()
        logger.debug("Switched to default content")