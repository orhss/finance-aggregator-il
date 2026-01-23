"""
Session state management for Streamlit application
Handles service instances and shared state across pages
"""

import streamlit as st
from typing import Optional
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from streamlit_app.utils.formatters import format_balance


# =============================================================================
# PRIVACY-AWARE FORMATTING
# =============================================================================
# Use these instead of format_currency/format_balance directly to ensure
# the mask_balances privacy setting is always respected.

def format_amount_private(amount: float, currency: str = "₪") -> str:
    """
    Format an amount respecting the privacy setting.
    Use this for any financial amount display (balances, totals, transactions).

    Returns "••••••" if mask_balances is enabled, otherwise formatted amount.
    """
    if amount is None:
        return "N/A"
    masked = st.session_state.get('mask_balances', False)
    return format_balance(amount, masked=masked, currency=currency)


# =============================================================================
# DISPLAY-READY DATA WRAPPERS
# =============================================================================
# These functions wrap cached data and add pre-formatted display fields.
# Use these when you need data for display (respects privacy settings).
# Use the raw cached functions when you need data for calculations.

def get_accounts_display() -> list[dict]:
    """
    Get accounts with pre-formatted balance for display.
    Wraps get_accounts_cached() and adds 'balance_display' field.

    Returns list of account dicts with:
        - All fields from get_accounts_cached()
        - balance_display: formatted balance string (respects mask_balances)
    """
    from streamlit_app.utils.cache import get_accounts_cached
    accounts = get_accounts_cached()
    for acc in accounts:
        acc['balance_display'] = format_amount_private(acc['latest_balance'])
    return accounts


def get_dashboard_stats_display() -> dict:
    """
    Get dashboard stats with pre-formatted amounts for display.
    Wraps get_dashboard_stats() and adds '_display' fields.

    Returns dict with:
        - All fields from get_dashboard_stats()
        - total_balance_display: formatted total balance
        - monthly_spending_display: formatted monthly spending
        - pending_amount_display: formatted pending amount
    """
    from streamlit_app.utils.cache import get_dashboard_stats
    stats = get_dashboard_stats()
    if stats:
        stats['total_balance_display'] = format_amount_private(stats.get('total_balance', 0))
        stats['monthly_spending_display'] = format_amount_private(stats.get('monthly_spending', 0))
        stats['pending_amount_display'] = format_amount_private(stats.get('pending_amount', 0))
    return stats


def get_transactions_display(
    start_date,
    end_date,
    account_ids=None,
    status=None,
    category=None,
    institution=None
) -> list[dict]:
    """
    Get transactions with pre-formatted amounts for display.
    Wraps get_transactions_cached() and adds '_display' fields.

    Returns list of transaction dicts with:
        - All fields from get_transactions_cached()
        - amount_display: formatted original_amount (respects mask_balances)
        - charged_display: formatted charged_amount
    """
    from streamlit_app.utils.cache import get_transactions_cached
    transactions = get_transactions_cached(
        start_date=start_date,
        end_date=end_date,
        account_ids=account_ids,
        status=status,
        category=category,
        institution=institution
    )
    for txn in transactions:
        txn['amount_display'] = format_amount_private(txn.get('original_amount', 0))
        txn['charged_display'] = format_amount_private(txn.get('charged_amount', 0))
    return transactions


def get_tags_display() -> list[dict]:
    """
    Get tags with pre-formatted amounts for display.
    Wraps get_tags_cached() and adds 'amount_display' field.

    Returns list of tag dicts with:
        - All fields from get_tags_cached()
        - amount_display: formatted total_amount (respects mask_balances)
    """
    from streamlit_app.utils.cache import get_tags_cached
    tags = get_tags_cached()
    for tag in tags:
        tag['amount_display'] = format_amount_private(tag.get('total_amount', 0))
    return tags


def init_session_state():
    """Initialize all session state variables with defaults"""
    defaults = {
        # Service instances (lazy loaded)
        'analytics_service': None,
        'tag_service': None,
        'rules_service': None,
        'category_service': None,
        'credit_card_service': None,
        'broker_service': None,
        'pension_service': None,

        # Database session
        'db_session': None,

        # Current filters and selections
        'current_filters': {},
        'selected_transactions': [],
        'selected_date_range': None,

        # Sync state
        'sync_in_progress': False,
        'sync_output': [],
        'last_sync_time': None,

        # UI state
        'current_page': 'Home',
        'show_welcome': True,

        # Privacy settings
        'mask_account_numbers': True,  # Mask account/card numbers by default
        'mask_balances': False,  # Don't mask balances by default (users can toggle)
    }

    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def get_analytics_service():
    """Get or create AnalyticsService instance"""
    if st.session_state.analytics_service is None:
        try:
            from services.analytics_service import AnalyticsService
            st.session_state.analytics_service = AnalyticsService()
        except Exception as e:
            st.error(f"Failed to initialize Analytics Service: {e}")
            return None
    return st.session_state.analytics_service


def get_tag_service():
    """Get or create TagService instance"""
    if st.session_state.tag_service is None:
        try:
            from services.tag_service import TagService
            from db.database import get_session

            session = get_session()
            st.session_state.tag_service = TagService(session)
        except Exception as e:
            st.error(f"Failed to initialize Tag Service: {e}")
            return None
    return st.session_state.tag_service


def get_rules_service():
    """Get or create RulesService instance"""
    if st.session_state.rules_service is None:
        try:
            from services.rules_service import RulesService
            from db.database import get_session

            session = get_session()
            st.session_state.rules_service = RulesService(session)
        except Exception as e:
            st.error(f"Failed to initialize Rules Service: {e}")
            return None
    return st.session_state.rules_service


def get_category_service():
    """Get or create CategoryService instance"""
    if st.session_state.category_service is None:
        try:
            from services.category_service import CategoryService
            from db.database import get_session

            session = get_session()
            st.session_state.category_service = CategoryService(session)
        except Exception as e:
            st.error(f"Failed to initialize Category Service: {e}")
            return None
    return st.session_state.category_service


def get_credit_card_service():
    """Get or create CreditCardService instance"""
    if st.session_state.credit_card_service is None:
        try:
            from services.credit_card_service import CreditCardService
            from db.database import get_session

            session = get_session()
            st.session_state.credit_card_service = CreditCardService(session)
        except Exception as e:
            st.error(f"Failed to initialize Credit Card Service: {e}")
            return None
    return st.session_state.credit_card_service


def get_broker_service():
    """Get or create BrokerService instance"""
    if st.session_state.broker_service is None:
        try:
            from services.broker_service import BrokerService
            from db.database import get_session

            session = get_session()
            st.session_state.broker_service = BrokerService(session)
        except Exception as e:
            st.error(f"Failed to initialize Broker Service: {e}")
            return None
    return st.session_state.broker_service


def get_pension_service():
    """Get or create PensionService instance"""
    if st.session_state.pension_service is None:
        try:
            from services.pension_service import PensionService
            from db.database import get_session

            session = get_session()
            st.session_state.pension_service = PensionService(session)
        except Exception as e:
            st.error(f"Failed to initialize Pension Service: {e}")
            return None
    return st.session_state.pension_service


def get_db_session():
    """Get or create database session"""
    if st.session_state.db_session is None:
        try:
            from db.database import get_session
            st.session_state.db_session = get_session()
        except Exception as e:
            st.error(f"Failed to initialize database session: {e}")
            return None
    return st.session_state.db_session


def clear_cache():
    """Clear all cached data (call after sync)"""
    # Reset service instances to force reload
    st.session_state.analytics_service = None
    st.session_state.tag_service = None
    st.session_state.rules_service = None
    st.session_state.category_service = None
    st.session_state.credit_card_service = None
    st.session_state.broker_service = None
    st.session_state.pension_service = None

    # Clear Streamlit's cache
    if hasattr(st, 'cache_data'):
        st.cache_data.clear()


def safe_service_call(func, *args, **kwargs):
    """Wrapper for service calls with error handling"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        st.error(f"Service error: {str(e)}")
        return None


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_all_categories() -> list[str]:
    """
    Get all unique categories from transactions (user_category, normalized category, raw_category).
    Returns a sorted list of category names.
    """
    try:
        from db.database import get_session
        from db.models import Transaction

        session = get_session()
        categories = set()

        # Get user-assigned categories
        user_cats = session.query(Transaction.user_category).filter(
            Transaction.user_category.isnot(None)
        ).distinct().all()
        categories.update([c[0] for c in user_cats if c[0]])

        # Get normalized categories
        source_cats = session.query(Transaction.category).filter(
            Transaction.category.isnot(None)
        ).distinct().all()
        categories.update([c[0] for c in source_cats if c[0]])

        # Get raw categories (for unmapped)
        raw_cats = session.query(Transaction.raw_category).filter(
            Transaction.raw_category.isnot(None)
        ).distinct().all()
        categories.update([c[0] for c in raw_cats if c[0]])

        return sorted(list(categories))
    except Exception as e:
        st.error(f"Failed to fetch categories: {e}")
        return []


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_unified_categories() -> list[str]:
    """
    Get all unified category names from mappings.
    Returns a sorted list of unified category names.
    """
    try:
        from db.database import get_session
        from db.models import CategoryMapping
        from sqlalchemy import distinct

        session = get_session()
        cats = session.query(distinct(CategoryMapping.unified_category)).order_by(
            CategoryMapping.unified_category
        ).all()
        return [c[0] for c in cats if c[0]]
    except Exception as e:
        st.error(f"Failed to fetch unified categories: {e}")
        return []


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_all_tags() -> list[str]:
    """
    Get all tag names from the database.
    Returns a sorted list of tag names.
    """
    try:
        from db.database import get_session
        from db.models import Tag

        session = get_session()
        tags = session.query(Tag.name).order_by(Tag.name).all()
        return [tag[0] for tag in tags]
    except Exception as e:
        st.error(f"Failed to fetch tags: {e}")
        return []