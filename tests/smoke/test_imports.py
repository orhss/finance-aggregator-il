"""
Smoke tests - verify modules import without errors.

These catch missing dependencies, circular imports, and syntax errors.
Run these tests first to ensure basic module loading works.
"""

import pytest


# ==================== CLI Imports ====================

def test_cli_main_imports():
    """CLI main module imports successfully."""
    from cli.main import app
    assert app is not None


def test_cli_commands_import():
    """CLI command modules import successfully."""
    from cli.commands import (
        sync,
        accounts,
        transactions,
        categories,
        config,
        export,
        maintenance,
        tags,
        rules,
        reports,
        budget,
        auth,
    )
    assert sync.app is not None
    assert accounts.app is not None
    assert transactions.app is not None
    assert categories.app is not None


def test_cli_tui_imports():
    """CLI TUI browser imports successfully."""
    from cli.tui.browser import TransactionBrowser
    assert TransactionBrowser is not None


# ==================== Service Imports ====================

def test_services_import():
    """Service modules import successfully."""
    from services.analytics_service import AnalyticsService
    from services.category_service import CategoryService
    from services.credit_card_service import CreditCardService
    from services.rules_service import RulesService
    from services.tag_service import TagService
    from services.base_service import BaseSyncService
    from services.broker_service import BrokerService
    from services.pension_service import PensionService
    from services.budget_service import BudgetService

    assert AnalyticsService is not None
    assert CategoryService is not None
    assert CreditCardService is not None
    assert RulesService is not None


# ==================== Model Imports ====================

def test_models_import():
    """Database models import successfully."""
    from db.models import (
        Account,
        Transaction,
        Balance,
        Tag,
        TransactionTag,
        CategoryMapping,
        MerchantMapping,
        SyncHistory,
    )
    assert Account is not None
    assert Transaction is not None
    assert CategoryMapping is not None


def test_database_import():
    """Database module imports successfully."""
    from db.database import (
        SessionLocal,
        create_database_engine,
        init_db,
        get_database_url,
    )
    assert SessionLocal is not None


# ==================== Config Imports ====================

def test_config_imports():
    """Config modules import successfully."""
    from config.settings import (
        Credentials,
        load_credentials,
        save_credentials,
    )
    from config.constants import (
        AccountType,
        Institution,
        SyncType,
        SyncStatus,
        UnifiedCategory,
    )
    assert Credentials is not None
    assert AccountType is not None


# ==================== Scraper Imports ====================

def test_scraper_base_imports():
    """Scraper base classes import successfully."""
    from scrapers.base.broker_base import (
        BrokerAPIClient,
        LoginCredentials,
        AccountInfo,
        BalanceInfo,
    )
    from scrapers.base.email_retriever import (
        EmailMFARetriever,
        EmailConfig,
        MFAConfig,
    )
    from scrapers.base.selenium_driver import SeleniumDriver, DriverConfig
    from scrapers.base.web_actions import WebActions
    from scrapers.base.mfa_handler import MFAHandler

    assert BrokerAPIClient is not None
    assert SeleniumDriver is not None


def test_credit_card_scraper_imports():
    """Credit card scraper modules import successfully."""
    from scrapers.credit_cards.cal_credit_card_client import (
        CALCreditCardScraper,
        CALCredentials,
        Transaction,
        CardAccount,
    )
    from scrapers.credit_cards.max_credit_card_client import (
        MaxCreditCardScraper,
        MaxCredentials,
    )
    from scrapers.credit_cards.isracard_credit_card_client import (
        IsracardCreditCardScraper,
        IsracardCredentials,
    )

    assert CALCreditCardScraper is not None
    assert MaxCreditCardScraper is not None
    assert IsracardCreditCardScraper is not None


def test_broker_scraper_imports():
    """Broker scraper modules import successfully."""
    from scrapers.brokers.excellence_broker_client import ExtraDeProAPIClient
    from scrapers.brokers.meitav_broker_client import MeitavScraperError

    assert ExtraDeProAPIClient is not None


def test_scraper_utils_import():
    """Scraper utility modules import successfully."""
    from scrapers.utils.retry import (
        retry_with_backoff,
        retry_selenium_action,
        retry_api_call,
    )
    from scrapers.utils.wait_conditions import SmartWait
    from scrapers.exceptions import (
        ScraperError,
        AuthenticationError,
        LoginFailedError,
    )

    assert retry_with_backoff is not None
    assert SmartWait is not None


# ==================== Streamlit Imports ====================

def test_streamlit_app_imports():
    """
    Streamlit app modules import successfully.

    Note: These may require display/environment setup on some systems.
    """
    try:
        import streamlit_app.main
        import streamlit_app.app
        assert True
    except ImportError as e:
        # Skip if Streamlit has display issues
        if "display" in str(e).lower() or "DISPLAY" in str(e):
            pytest.skip(f"Streamlit import requires display: {e}")
        raise


def test_streamlit_components_import():
    """Streamlit component modules import successfully."""
    try:
        from streamlit_app.components.theme import apply_theme
        from streamlit_app.components.sidebar import render_minimal_sidebar
        from streamlit_app.components.cards import render_card
        from streamlit_app.components.filters import date_range_filter
        from streamlit_app.components.charts import spending_donut

        assert apply_theme is not None
    except ImportError as e:
        if "display" in str(e).lower() or "DISPLAY" in str(e):
            pytest.skip(f"Streamlit import requires display: {e}")
        raise


def test_streamlit_utils_import():
    """Streamlit utility modules import successfully."""
    try:
        from streamlit_app.utils.formatters import format_currency, format_date
        from streamlit_app.utils.cache import get_transactions_cached
        from streamlit_app.utils.session import format_amount_private
        from streamlit_app.utils.mobile import detect_mobile

        assert format_currency is not None
    except ImportError as e:
        if "display" in str(e).lower() or "DISPLAY" in str(e):
            pytest.skip(f"Streamlit import requires display: {e}")
        raise


# ==================== Query Utils ====================

def test_query_utils_import():
    """Database query utilities import successfully."""
    from db.query_utils import (
        effective_amount_expr,
        effective_category_expr,
        get_effective_amount,
    )
    assert effective_amount_expr is not None
    assert effective_category_expr is not None
