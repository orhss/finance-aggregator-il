"""
Custom wait conditions for Selenium
Replaces time.sleep with smart, condition-based waits
"""

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


class SmartWait:
    """
    Smart waiting utilities that replace time.sleep

    Uses explicit waits with specific conditions instead of blind delays.
    More reliable and faster than fixed sleep times.
    """

    def __init__(self, driver: WebDriver, default_timeout: int = 30):
        self.driver = driver
        self.default_timeout = default_timeout

    def until_element_present(
        self,
        selector: str,
        by: By = By.CSS_SELECTOR,
        timeout: Optional[int] = None
    ):
        """
        Wait until element is present in DOM

        Args:
            selector: Element selector
            by: Selenium By strategy (default: CSS_SELECTOR)
            timeout: Timeout in seconds (uses default if not specified)

        Returns:
            The WebElement

        Raises:
            TimeoutException: If element not found within timeout
        """
        timeout = timeout or self.default_timeout
        try:
            logger.debug(f"Waiting for element: {selector}")
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            logger.debug(f"Element found: {selector}")
            return element
        except TimeoutException:
            logger.error(f"Element not found after {timeout}s: {selector}")
            raise

    def until_element_clickable(
        self,
        selector: str,
        by: By = By.CSS_SELECTOR,
        timeout: Optional[int] = None
    ):
        """
        Wait until element is clickable (visible and enabled)

        Args:
            selector: Element selector
            by: Selenium By strategy (default: CSS_SELECTOR)
            timeout: Timeout in seconds (uses default if not specified)

        Returns:
            The WebElement

        Raises:
            TimeoutException: If element not clickable within timeout
        """
        timeout = timeout or self.default_timeout
        try:
            logger.debug(f"Waiting for clickable element: {selector}")
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, selector))
            )
            logger.debug(f"Element clickable: {selector}")
            return element
        except TimeoutException:
            logger.error(f"Element not clickable after {timeout}s: {selector}")
            raise

    def until_element_invisible(
        self,
        selector: str,
        by: By = By.CSS_SELECTOR,
        timeout: Optional[int] = None
    ) -> bool:
        """
        Wait until element becomes invisible or removed from DOM

        Args:
            selector: Element selector
            by: Selenium By strategy (default: CSS_SELECTOR)
            timeout: Timeout in seconds (uses default if not specified)

        Returns:
            True if element became invisible

        Raises:
            TimeoutException: If element still visible after timeout
        """
        timeout = timeout or self.default_timeout
        try:
            logger.debug(f"Waiting for element to become invisible: {selector}")
            WebDriverWait(self.driver, timeout).until(
                EC.invisibility_of_element_located((by, selector))
            )
            logger.debug(f"Element invisible: {selector}")
            return True
        except TimeoutException:
            logger.error(f"Element still visible after {timeout}s: {selector}")
            raise

    def until_text_present(
        self,
        text: str,
        timeout: Optional[int] = None
    ) -> bool:
        """
        Wait until text appears anywhere on page

        Args:
            text: Text to wait for
            timeout: Timeout in seconds (uses default if not specified)

        Returns:
            True if text found

        Raises:
            TimeoutException: If text not found within timeout
        """
        timeout = timeout or self.default_timeout

        def text_in_page(driver):
            return text in driver.page_source

        try:
            logger.debug(f"Waiting for text: {text}")
            WebDriverWait(self.driver, timeout).until(text_in_page)
            logger.debug(f"Text found: {text}")
            return True
        except TimeoutException:
            logger.error(f"Text not found after {timeout}s: {text}")
            raise

    def until_url_contains(
        self,
        url_fragment: str,
        timeout: Optional[int] = None
    ) -> bool:
        """
        Wait until URL contains specific text

        Args:
            url_fragment: Text that should be in URL
            timeout: Timeout in seconds (uses default if not specified)

        Returns:
            True if URL contains fragment

        Raises:
            TimeoutException: If URL doesn't contain fragment after timeout
        """
        timeout = timeout or self.default_timeout
        try:
            logger.debug(f"Waiting for URL to contain: {url_fragment}")
            WebDriverWait(self.driver, timeout).until(
                EC.url_contains(url_fragment)
            )
            logger.debug(f"URL contains: {url_fragment}")
            return True
        except TimeoutException:
            current_url = self.driver.current_url
            logger.error(f"URL did not contain '{url_fragment}' after {timeout}s. Current URL: {current_url}")
            raise

    def until_custom_condition(
        self,
        condition: Callable,
        timeout: Optional[int] = None,
        error_message: str = "Custom condition not met"
    ) -> bool:
        """
        Wait for custom condition

        Args:
            condition: Callable that takes driver and returns True when condition met
            timeout: Timeout in seconds (uses default if not specified)
            error_message: Error message for timeout

        Returns:
            True if condition met

        Raises:
            TimeoutException: If condition not met within timeout
        """
        timeout = timeout or self.default_timeout
        try:
            logger.debug(f"Waiting for custom condition: {error_message}")
            WebDriverWait(self.driver, timeout).until(condition)
            logger.debug(f"Custom condition met: {error_message}")
            return True
        except TimeoutException:
            logger.error(f"{error_message} after {timeout}s")
            raise

    def until_element_has_text(
        self,
        selector: str,
        text: str,
        by: By = By.CSS_SELECTOR,
        timeout: Optional[int] = None
    ) -> bool:
        """
        Wait until element contains specific text

        Args:
            selector: Element selector
            text: Text that element should contain
            by: Selenium By strategy (default: CSS_SELECTOR)
            timeout: Timeout in seconds (uses default if not specified)

        Returns:
            True if element has text

        Raises:
            TimeoutException: If element doesn't have text after timeout
        """
        timeout = timeout or self.default_timeout
        try:
            logger.debug(f"Waiting for element '{selector}' to have text: {text}")
            WebDriverWait(self.driver, timeout).until(
                EC.text_to_be_present_in_element((by, selector), text)
            )
            logger.debug(f"Element has text: {text}")
            return True
        except TimeoutException:
            logger.error(f"Element '{selector}' did not have text '{text}' after {timeout}s")
            raise