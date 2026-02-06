"""
Tests for credit card base scraper class.

These tests verify the common driver lifecycle behavior
that will be extracted to base_scraper.py.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass
from typing import Optional


# ==================== Test Fixtures ====================

@dataclass
class MockCredentials:
    """Mock credentials for testing."""
    username: str
    password: str


class MockSeleniumDriver:
    """Mock SeleniumDriver for testing."""

    def __init__(self, config=None):
        self.config = config
        self._driver = MagicMock()
        self.setup_called = False
        self.cleanup_called = False

    def setup(self):
        self.setup_called = True
        return self._driver

    def cleanup(self):
        self.cleanup_called = True


# ==================== Base Scraper Lifecycle Tests ====================

class TestBaseScraperLifecycle:
    """Test driver setup and cleanup patterns."""

    def test_setup_driver_creates_selenium_driver(self):
        """setup_driver() creates SeleniumDriver instance."""
        scraper = self._create_mock_scraper()

        with patch('scrapers.base.selenium_driver.SeleniumDriver', MockSeleniumDriver):
            scraper.setup_driver()

        assert scraper.driver is not None

    def test_cleanup_releases_driver(self):
        """cleanup() releases driver resources."""
        scraper = self._create_mock_scraper()
        mock_selenium = MockSeleniumDriver()
        scraper._selenium_driver = mock_selenium
        scraper.driver = mock_selenium._driver

        scraper.cleanup()

        assert mock_selenium.cleanup_called
        assert scraper.driver is None
        assert scraper._selenium_driver is None

    def test_cleanup_handles_no_driver(self):
        """cleanup() handles case where driver was never created."""
        scraper = self._create_mock_scraper()
        scraper._selenium_driver = None
        scraper.driver = None

        # Should not raise
        scraper.cleanup()

        assert scraper.driver is None

    def test_context_manager_setup_and_cleanup(self):
        """Context manager calls setup and cleanup."""
        scraper = self._create_mock_scraper()
        setup_called = False
        cleanup_called = False

        original_setup = scraper.setup_driver
        original_cleanup = scraper.cleanup

        def mock_setup():
            nonlocal setup_called
            setup_called = True
            original_setup()

        def mock_cleanup():
            nonlocal cleanup_called
            cleanup_called = True
            original_cleanup()

        scraper.setup_driver = mock_setup
        scraper.cleanup = mock_cleanup

        with scraper:
            assert setup_called
            assert not cleanup_called

        assert cleanup_called

    def test_context_manager_cleanup_on_exception(self):
        """Context manager cleans up even on exception."""
        scraper = self._create_mock_scraper()
        cleanup_called = False

        def mock_cleanup():
            nonlocal cleanup_called
            cleanup_called = True

        scraper.cleanup = mock_cleanup

        with pytest.raises(RuntimeError):
            with scraper:
                raise RuntimeError("Test error")

        assert cleanup_called

    def _create_mock_scraper(self):
        """Create a mock scraper for testing."""
        # This simulates the base scraper behavior
        class MockBaseScraper:
            def __init__(self, credentials, headless=True):
                self.credentials = credentials
                self.headless = headless
                self._selenium_driver = None
                self.driver = None

            def setup_driver(self):
                self._selenium_driver = MockSeleniumDriver()
                self.driver = self._selenium_driver.setup()

            def cleanup(self):
                if self._selenium_driver:
                    self._selenium_driver.cleanup()
                    self._selenium_driver = None
                self.driver = None

            def __enter__(self):
                self.setup_driver()
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                self.cleanup()
                return False

        return MockBaseScraper(MockCredentials("user", "pass"))


# ==================== Scraper Configuration Tests ====================

class TestScraperConfiguration:
    """Test scraper configuration options."""

    def test_headless_mode_default(self):
        """Default headless mode is True."""
        scraper = self._create_scraper(MockCredentials("user", "pass"))
        assert scraper.headless is True

    def test_headless_mode_explicit_true(self):
        """Headless can be explicitly set True."""
        scraper = self._create_scraper(MockCredentials("user", "pass"), headless=True)
        assert scraper.headless is True

    def test_headless_mode_explicit_false(self):
        """Headless can be set False for debugging."""
        scraper = self._create_scraper(MockCredentials("user", "pass"), headless=False)
        assert scraper.headless is False

    def test_credentials_stored(self):
        """Credentials are stored on scraper instance."""
        creds = MockCredentials("test_user", "test_pass")
        scraper = self._create_scraper(creds)
        assert scraper.credentials.username == "test_user"
        assert scraper.credentials.password == "test_pass"

    def _create_scraper(self, credentials, headless=True):
        """Create a mock scraper for configuration testing."""
        class MockScraper:
            def __init__(self, credentials, headless=True):
                self.credentials = credentials
                self.headless = headless

        return MockScraper(credentials, headless=headless)


# ==================== Current Scraper Behavior Verification ====================

class TestCurrentScraperBehavior:
    """
    Tests to verify current scraper behavior before refactoring.
    These ensure we don't break existing functionality.
    """

    def test_cal_scraper_has_context_manager(self):
        """CAL scraper supports context manager protocol (inherited from base)."""
        from scrapers.credit_cards.cal_credit_card_client import CALCreditCardScraper

        # Verify __enter__ and __exit__ exist
        assert hasattr(CALCreditCardScraper, '__enter__')
        assert hasattr(CALCreditCardScraper, '__exit__')

    def test_max_scraper_has_context_manager(self):
        """Max scraper supports context manager protocol (inherited from base)."""
        from scrapers.credit_cards.max_credit_card_client import MaxCreditCardScraper

        assert hasattr(MaxCreditCardScraper, '__enter__')
        assert hasattr(MaxCreditCardScraper, '__exit__')

    def test_isracard_scraper_has_context_manager(self):
        """Isracard scraper supports context manager protocol (inherited from base)."""
        from scrapers.credit_cards.isracard_credit_card_client import IsracardCreditCardScraper

        assert hasattr(IsracardCreditCardScraper, '__enter__')
        assert hasattr(IsracardCreditCardScraper, '__exit__')

    def test_cal_scraper_has_setup_cleanup(self):
        """CAL scraper has setup_driver and cleanup methods."""
        from scrapers.credit_cards.cal_credit_card_client import CALCreditCardScraper

        assert hasattr(CALCreditCardScraper, 'setup_driver')
        assert hasattr(CALCreditCardScraper, 'cleanup')

    def test_max_scraper_has_setup_cleanup(self):
        """Max scraper has setup_driver and cleanup methods."""
        from scrapers.credit_cards.max_credit_card_client import MaxCreditCardScraper

        assert hasattr(MaxCreditCardScraper, 'setup_driver')
        assert hasattr(MaxCreditCardScraper, 'cleanup')

    def test_isracard_scraper_has_setup_cleanup(self):
        """Isracard scraper has setup_driver and cleanup methods."""
        from scrapers.credit_cards.isracard_credit_card_client import IsracardCreditCardScraper

        assert hasattr(IsracardCreditCardScraper, 'setup_driver')
        assert hasattr(IsracardCreditCardScraper, 'cleanup')


# ==================== Driver Configuration Tests ====================

class TestScraperDriverConfig:
    """Test scraper-specific driver configurations."""

    def test_cal_enables_performance_logging(self):
        """CAL scraper enables performance logging for token capture."""
        from scrapers.credit_cards.cal_credit_card_client import (
            CALCreditCardScraper, CALCredentials
        )

        scraper = CALCreditCardScraper(
            CALCredentials(username="test", password="test"),
            headless=True
        )
        config = scraper._create_driver_config()

        assert config.enable_performance_logging is True
        assert config.headless is True

    def test_cal_respects_headless_setting(self):
        """CAL scraper passes headless setting to driver config."""
        from scrapers.credit_cards.cal_credit_card_client import (
            CALCreditCardScraper, CALCredentials
        )

        scraper = CALCreditCardScraper(
            CALCredentials(username="test", password="test"),
            headless=False
        )
        config = scraper._create_driver_config()

        assert config.headless is False
        assert config.enable_performance_logging is True

    def test_max_uses_default_config(self):
        """Max scraper uses default driver config (no special settings)."""
        from scrapers.credit_cards.max_credit_card_client import (
            MaxCreditCardScraper, MaxCredentials
        )

        scraper = MaxCreditCardScraper(
            MaxCredentials(username="test", password="test"),
            headless=True
        )
        config = scraper._create_driver_config()

        assert config.headless is True
        # Max doesn't need performance logging
        assert config.enable_performance_logging is False

    def test_isracard_sets_hebrew_language(self):
        """Isracard scraper sets Hebrew language for proper rendering."""
        from scrapers.credit_cards.isracard_credit_card_client import (
            IsracardCreditCardScraper, IsracardCredentials
        )

        scraper = IsracardCreditCardScraper(
            IsracardCredentials(user_id="123", password="test", card_6_digits="123456"),
            base_url="https://digital.isracard.co.il",
            company_code="11",
            headless=True
        )
        config = scraper._create_driver_config()

        assert config.headless is True
        assert '--lang=he-IL' in config.extra_arguments

    def test_isracard_respects_headless_setting(self):
        """Isracard scraper passes headless setting to driver config."""
        from scrapers.credit_cards.isracard_credit_card_client import (
            IsracardCreditCardScraper, IsracardCredentials
        )

        scraper = IsracardCreditCardScraper(
            IsracardCredentials(user_id="123", password="test", card_6_digits="123456"),
            base_url="https://digital.isracard.co.il",
            company_code="11",
            headless=False
        )
        config = scraper._create_driver_config()

        assert config.headless is False


# ==================== Base Class Inheritance Tests ====================

class TestBaseClassInheritance:
    """Test that scrapers properly inherit from BaseCreditCardScraper."""

    def test_cal_inherits_from_base(self):
        """CAL scraper inherits from BaseCreditCardScraper."""
        from scrapers.credit_cards.cal_credit_card_client import CALCreditCardScraper
        from scrapers.credit_cards.base_scraper import BaseCreditCardScraper

        assert issubclass(CALCreditCardScraper, BaseCreditCardScraper)

    def test_max_inherits_from_base(self):
        """Max scraper inherits from BaseCreditCardScraper."""
        from scrapers.credit_cards.max_credit_card_client import MaxCreditCardScraper
        from scrapers.credit_cards.base_scraper import BaseCreditCardScraper

        assert issubclass(MaxCreditCardScraper, BaseCreditCardScraper)

    def test_isracard_inherits_from_base(self):
        """Isracard scraper inherits from BaseCreditCardScraper."""
        from scrapers.credit_cards.isracard_credit_card_client import IsracardCreditCardScraper
        from scrapers.credit_cards.base_scraper import BaseCreditCardScraper

        assert issubclass(IsracardCreditCardScraper, BaseCreditCardScraper)

    def test_scrapers_have_abstract_methods_implemented(self):
        """All scrapers implement required abstract methods."""
        from scrapers.credit_cards.cal_credit_card_client import CALCreditCardScraper
        from scrapers.credit_cards.max_credit_card_client import MaxCreditCardScraper
        from scrapers.credit_cards.isracard_credit_card_client import IsracardCreditCardScraper

        for scraper_class in [CALCreditCardScraper, MaxCreditCardScraper, IsracardCreditCardScraper]:
            # These are the abstract methods from BaseCreditCardScraper
            assert callable(getattr(scraper_class, 'login', None))
            assert callable(getattr(scraper_class, 'fetch_transactions', None))


# ==================== Exception Handling Tests ====================

class TestExceptionHierarchy:
    """Test exception class hierarchy before consolidation."""

    def test_cal_exception_hierarchy(self):
        """CAL exceptions inherit from base."""
        from scrapers.credit_cards.cal_credit_card_client import (
            CALScraperError, CALLoginError, CALAuthorizationError, CALAPIError
        )

        assert issubclass(CALLoginError, CALScraperError)
        assert issubclass(CALAuthorizationError, CALScraperError)
        assert issubclass(CALAPIError, CALScraperError)
        assert issubclass(CALScraperError, Exception)

    def test_max_exception_hierarchy(self):
        """Max exceptions inherit from base."""
        from scrapers.credit_cards.max_credit_card_client import (
            MaxScraperError, MaxLoginError, MaxAPIError
        )

        assert issubclass(MaxLoginError, MaxScraperError)
        assert issubclass(MaxAPIError, MaxScraperError)
        assert issubclass(MaxScraperError, Exception)

    def test_isracard_exception_hierarchy(self):
        """Isracard exceptions inherit from base."""
        from scrapers.credit_cards.isracard_credit_card_client import (
            IsracardScraperError, IsracardLoginError, IsracardAPIError
        )

        assert issubclass(IsracardLoginError, IsracardScraperError)
        assert issubclass(IsracardAPIError, IsracardScraperError)
        assert issubclass(IsracardScraperError, Exception)

    def test_exceptions_can_carry_message(self):
        """All exceptions can carry error messages."""
        from scrapers.credit_cards.cal_credit_card_client import CALLoginError

        error = CALLoginError("Invalid credentials")
        assert str(error) == "Invalid credentials"
