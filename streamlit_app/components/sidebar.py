"""
Shared sidebar components used across pages
"""

import streamlit as st
from datetime import datetime
from typing import Optional
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from streamlit_app.utils.formatters import format_datetime
from streamlit_app.utils.session import format_amount_private
from streamlit_app.utils.cache import get_dashboard_stats


def render_privacy_toggle():
    """
    Render a quick privacy mode toggle in the sidebar.
    Toggles balance masking with a single click.
    """
    # Current state
    is_private = st.session_state.get('mask_balances', False)

    # Use columns to align the toggle nicely
    col1, col2 = st.sidebar.columns([3, 1])

    with col1:
        st.markdown("**Privacy Mode**")

    with col2:
        # Toggle with eye icon
        icon = "🙈" if is_private else "👁️"
        if st.button(icon, key="privacy_toggle", help="Toggle balance visibility"):
            st.session_state.mask_balances = not is_private
            st.rerun()


def render_quick_stats():
    """
    Render quick statistics in the sidebar.
    Uses the same cached data source as the Dashboard for consistency.
    """
    st.sidebar.markdown("### 📊 Quick Stats")

    try:
        # Use the same cached stats as Dashboard - single source of truth
        stats = get_dashboard_stats()

        if stats and stats['account_count'] > 0:
            # Total Balance
            if stats['total_balance']:
                st.sidebar.metric(
                    "Total Balance",
                    format_amount_private(stats['total_balance']),
                    help="Sum of all account balances"
                )
            else:
                st.sidebar.metric("Total Balance", "Not synced")

            # Pending transactions
            if stats['pending_count'] and stats['pending_count'] > 0:
                st.sidebar.metric(
                    "Pending Transactions",
                    f"{stats['pending_count']}",
                    format_amount_private(stats['pending_amount']) if stats['pending_amount'] else None,
                    help="Transactions awaiting completion"
                )
            else:
                st.sidebar.metric("Pending Transactions", "0")

            # Last sync time
            if stats['last_sync']:
                st.sidebar.caption(f"Last sync: {format_datetime(stats['last_sync'], '%m/%d %H:%M')}")
        else:
            st.sidebar.info("💡 Initialize database to see stats")

    except Exception as e:
        st.sidebar.warning("Stats unavailable")
        st.sidebar.caption(f"Error: {str(e)}")


def render_about():
    """
    Render about section in sidebar
    """
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ℹ️ About")
    st.sidebar.caption("Financial Data Aggregator v1.0")
    st.sidebar.caption("[Documentation](https://github.com) · [Issues](https://github.com)")


def render_minimal_sidebar():
    """
    Render minimal sidebar (just stats)
    For pages that need more sidebar space
    """
    render_privacy_toggle()
    render_quick_stats()
    render_about()
