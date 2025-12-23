"""
Selenium WebDriver setup and management

Provides a clean interface for browser automation with:
- Context manager for guaranteed cleanup
- Configurable Chrome options
- Proper logging
"""

import logging
from typing import Optional
from dataclasses import dataclass, field
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webdriver import WebDriver

logger = logging.getLogger(__name__)


@dataclass
class DriverConfig:
    """Configuration for Chrome WebDriver"""
    headless: bool = True
    window_size: str = "1920,1080"
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    implicit_wait: int = 10
    disable_gpu: bool = True
    no_sandbox: bool = True
    disable_dev_shm: bool = True
    # Performance logging for capturing network requests (useful for API token extraction)
    enable_performance_logging: bool = False
    # Additional Chrome arguments
    extra_arguments: list = field(default_factory=list)


class SeleniumDriver:
    """
    Manages Chrome WebDriver lifecycle with context manager support

    Usage:
        config = DriverConfig(headless=True)
        with SeleniumDriver(config) as driver:
            driver.get("https://example.com")
            # ... automation code ...
        # Driver automatically cleaned up

    Or manually:
        selenium_driver = SeleniumDriver(config)
        driver = selenium_driver.setup()
        try:
            driver.get("https://example.com")
        finally:
            selenium_driver.cleanup()
    """

    def __init__(self, config: Optional[DriverConfig] = None):
        """
        Initialize SeleniumDriver

        Args:
            config: Driver configuration. Uses defaults if not provided.
        """
        self.config = config or DriverConfig()
        self.driver: Optional[WebDriver] = None

    def __enter__(self) -> WebDriver:
        """Context manager entry - setup and return driver"""
        return self.setup()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup driver"""
        self.cleanup()

    def setup(self) -> WebDriver:
        """
        Setup and return Chrome WebDriver

        Returns:
            Configured WebDriver instance

        Raises:
            Exception: If driver setup fails
        """
        logger.info("Setting up Chrome WebDriver...")

        options = self._build_options()

        try:
            logger.debug("Initializing Chrome driver...")
            self.driver = webdriver.Chrome(options=options)
            self.driver.implicitly_wait(self.config.implicit_wait)
            logger.info("Chrome driver initialized successfully")
            return self.driver

        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}", exc_info=True)
            raise

    def cleanup(self):
        """
        Clean up WebDriver resources (safe to call multiple times)
        """
        if self.driver:
            try:
                logger.debug("Closing Chrome driver...")
                self.driver.quit()
                logger.info("Chrome driver closed successfully")
            except Exception as e:
                logger.warning(f"Error during driver cleanup: {e}")
            finally:
                self.driver = None
        else:
            logger.debug("No Chrome driver to close")

    def _build_options(self) -> Options:
        """Build Chrome options from config"""
        options = Options()

        if self.config.headless:
            logger.debug("Running in headless mode")
            options.add_argument('--headless')
        else:
            logger.debug("Running in visible mode")

        if self.config.no_sandbox:
            options.add_argument('--no-sandbox')

        if self.config.disable_dev_shm:
            options.add_argument('--disable-dev-shm-usage')

        if self.config.disable_gpu:
            options.add_argument('--disable-gpu')

        options.add_argument(f'--window-size={self.config.window_size}')
        options.add_argument(f'--user-agent={self.config.user_agent}')

        # Add performance logging if enabled (for capturing network requests)
        if self.config.enable_performance_logging:
            options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
            logger.debug("Performance logging enabled")

        # Add any extra arguments
        for arg in self.config.extra_arguments:
            options.add_argument(arg)

        return options

    def get_driver(self) -> Optional[WebDriver]:
        """
        Get the current driver instance

        Returns:
            WebDriver if setup, None otherwise
        """
        return self.driver

    def is_active(self) -> bool:
        """
        Check if driver is active and usable

        Returns:
            True if driver is active
        """
        if not self.driver:
            return False
        try:
            # Try to get current URL to check if driver is responsive
            _ = self.driver.current_url
            return True
        except Exception:
            return False