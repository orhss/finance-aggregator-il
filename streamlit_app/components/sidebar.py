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

from streamlit_app.utils.formatters import format_currency, format_datetime


def render_quick_stats():
    """
    Render quick statistics in the sidebar
    Shows total balance, pending transactions, last sync time
    """
    st.sidebar.markdown("### 📊 Quick Stats")

    try:
        from streamlit_app.utils.session import get_db_session
        from db.models import Account, Transaction, Balance
        from sqlalchemy import func, and_

        session = get_db_session()

        if session:
            # Get total balance from latest Balance records
            latest_balances = session.query(
                Balance.account_id,
                func.max(Balance.balance_date).label('max_date')
            ).group_by(Balance.account_id).subquery()

            total_balance = session.query(
                func.sum(Balance.total_amount)
            ).join(
                latest_balances,
                and_(
                    Balance.account_id == latest_balances.c.account_id,
                    Balance.balance_date == latest_balances.c.max_date
                )
            ).scalar()

            if total_balance:
                st.sidebar.metric(
                    "Total Balance",
                    format_currency(total_balance),
                    help="Sum of all account balances"
                )
            else:
                st.sidebar.metric("Total Balance", "Not synced")

            # Get pending transactions count
            pending_count = session.query(func.count(Transaction.id)).filter(
                Transaction.status == 'pending'
            ).scalar()

            pending_amount = session.query(func.sum(Transaction.original_amount)).filter(
                Transaction.status == 'pending'
            ).scalar()

            if pending_count and pending_count > 0:
                st.sidebar.metric(
                    "Pending Transactions",
                    f"{pending_count}",
                    format_currency(pending_amount or 0) if pending_amount else None,
                    help="Transactions awaiting completion"
                )
            else:
                st.sidebar.metric("Pending Transactions", "0")

            # Last sync time from session state
            if st.session_state.get('last_sync_time'):
                last_sync = st.session_state.last_sync_time
                st.sidebar.caption(f"Last sync: {format_datetime(last_sync, '%m/%d %H:%M')}")
            else:
                st.sidebar.info("💡 No sync data available")

        else:
            st.sidebar.info("💡 Initialize database to see stats")

    except Exception as e:
        st.sidebar.warning("Stats unavailable")
        st.sidebar.caption(f"Error: {str(e)}")


def render_navigation_info():
    """
    Render navigation information and tips
    """
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🧭 Navigation")
    st.sidebar.caption("""
    Use the menu above to navigate:
    - **Dashboard** - Overview
    - **Sync** - Update data
    - **Transactions** - Browse
    - **Analytics** - Insights
    - **Tags** - Organize
    - **Rules** - Automate
    - **Accounts** - Manage
    - **Settings** - Configure
    """)


def render_about():
    """
    Render about section in sidebar
    """
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ℹ️ About")
    st.sidebar.caption("Financial Data Aggregator v1.0")
    st.sidebar.caption("[Documentation](https://github.com) · [Issues](https://github.com)")


def render_full_sidebar():
    """
    Render complete sidebar with all components
    Can be called from any page
    """
    render_quick_stats()
    render_navigation_info()
    render_about()


def render_minimal_sidebar():
    """
    Render minimal sidebar (just stats)
    For pages that need more sidebar space
    """
    render_quick_stats()
    render_about()
