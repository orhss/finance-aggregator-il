"""
Base class for credit card scrapers.

Provides common driver lifecycle management and defines the scraping interface.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List, Any, TypeVar, Generic

from scrapers.base.selenium_driver import SeleniumDriver, DriverConfig

logger = logging.getLogger(__name__)

# Type variable for credentials (different per scraper)
CredentialsT = TypeVar('CredentialsT')
# Type variable for card account (different per scraper)
CardAccountT = TypeVar('CardAccountT')


class BaseCreditCardScraper(ABC, Generic[CredentialsT, CardAccountT]):
    """
    Abstract base class for credit card scrapers.

    Provides:
    - Selenium WebDriver lifecycle management (setup, cleanup, context manager)
    - Common attributes (headless, driver)
    - Template method pattern for scraping flow

    Subclasses must implement:
    - _create_driver_config(): Return DriverConfig for this scraper
    - login(): Perform login and return True on success
    - fetch_transactions(): Fetch and return card accounts with transactions
    """

    def __init__(self, credentials: CredentialsT, headless: bool = True):
        """
        Initialize the scraper.

        Args:
            credentials: Institution-specific credentials dataclass
            headless: Run browser in headless mode (default True)
        """
        self.credentials = credentials
        self.headless = headless
        self._selenium_driver: Optional[SeleniumDriver] = None
        self.driver: Optional[Any] = None  # WebDriver instance

    def _create_driver_config(self) -> DriverConfig:
        """
        Create driver configuration for this scraper.

        Override to customize driver settings (e.g., enable performance logging).

        Returns:
            DriverConfig instance
        """
        return DriverConfig(headless=self.headless)

    def setup_driver(self) -> None:
        """Setup Chrome WebDriver using centralized SeleniumDriver."""
        config = self._create_driver_config()
        self._selenium_driver = SeleniumDriver(config)
        self.driver = self._selenium_driver.setup()
        logger.debug("WebDriver initialized")

    def cleanup(self) -> None:
        """Clean up WebDriver resources."""
        logger.debug("Starting cleanup process...")
        if self._selenium_driver:
            self._selenium_driver.cleanup()
            self._selenium_driver = None
        self.driver = None
        logger.debug("Cleanup completed")

    def __enter__(self) -> 'BaseCreditCardScraper[CredentialsT, CardAccountT]':
        """Context manager entry - sets up driver."""
        self.setup_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - cleans up driver."""
        self.cleanup()

    @abstractmethod
    def login(self) -> bool:
        """
        Perform login to the credit card website.

        Returns:
            True if login successful

        Raises:
            Institution-specific login error on failure
        """
        pass

    @abstractmethod
    def fetch_transactions(
        self,
        start_date: Optional[datetime] = None,
        months_back: int = 12,
        months_forward: int = 1
    ) -> List[CardAccountT]:
        """
        Fetch transactions for all cards.

        Args:
            start_date: Start date for fetching transactions
            months_back: Number of months to fetch backwards
            months_forward: Number of months to fetch forward

        Returns:
            List of CardAccount objects with transactions
        """
        pass

    def scrape(
        self,
        start_date: Optional[datetime] = None,
        months_back: int = 12,
        months_forward: int = 1
    ) -> List[CardAccountT]:
        """
        Complete scraping flow: login and fetch transactions.

        This is a template method that ensures proper cleanup.

        Args:
            start_date: Start date for fetching transactions
            months_back: Number of months to fetch backwards
            months_forward: Number of months to fetch forward

        Returns:
            List of CardAccount objects with transactions
        """
        try:
            logger.info(f"Starting {self.__class__.__name__}...")

            # Login
            self.login()

            # Fetch transactions
            accounts = self.fetch_transactions(start_date, months_back, months_forward)

            return accounts

        finally:
            self.cleanup()
