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


def init_session_state():
    """Initialize all session state variables with defaults"""
    defaults = {
        # Service instances (lazy loaded)
        'analytics_service': None,
        'tag_service': None,
        'rules_service': None,
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