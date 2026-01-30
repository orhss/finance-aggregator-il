"""
Mobile Dashboard - Touch-friendly mobile-first experience.

This module provides the mobile dashboard that can be rendered from app.py
when mobile device is detected.
"""

import streamlit as st
from datetime import date

from streamlit_app.utils.session import format_amount_private
from streamlit_app.utils.cache import (
    get_dashboard_stats,
    get_recent_transactions,
    get_hub_alerts,
)
from streamlit_app.utils.formatters import format_relative_time, format_date_relative, get_category_icon
from streamlit_app.utils.rtl import clean_merchant_name
from streamlit_app.utils.insights import get_time_greeting
from streamlit_app.components.mobile_ui import (
    apply_mobile_css,
    hero_balance_card,
    summary_card,
    transaction_list,
    bottom_navigation,
)
from streamlit_app.components.theme import apply_theme, render_page_header


def render_budget_progress():
    """Render budget progress card if budget is set."""
    try:
        from services.budget_service import BudgetService

        budget_service = BudgetService()
        progress = budget_service.get_current_progress()
        budget_service.close()

        if progress['budget'] is None:
            return  # No budget set

        spent = progress['spent']
        budget = progress['budget']
        percent = progress['percent_actual']
        remaining = progress['remaining']

        # Determine color
        if progress['is_over_budget']:
            color = "#EF4444"
            status = f"₪{abs(remaining):,.0f} over"
        elif percent >= 80:
            color = "#F59E0B"
            status = f"₪{remaining:,.0f} left"
        else:
            color = "#10B981"
            status = f"₪{remaining:,.0f} left"

        summary_card(
            title="Monthly Budget",
            value=f"₪{spent:,.0f} / ₪{budget:,.0f}",
            secondary=status,
            progress=percent,
            progress_color=color,
        )

    except Exception:
        pass  # Silently fail if budget not available


def render_alerts():
    """Render expandable alerts section."""
    alerts = get_hub_alerts()

    if not alerts:
        return

    with st.expander(f"⚠️ {len(alerts)} items need attention", expanded=False):
        for alert in alerts:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"{alert['icon']} {alert['message']}")
            with col2:
                if st.button(alert['action_label'], key=alert['key'], use_container_width=True):
                    st.switch_page(alert['page'])


def render_recent_transactions():
    """Render recent transactions as mobile cards."""
    recent = get_recent_transactions(limit=5)

    if not recent:
        st.info("No recent transactions. Sync to see activity.")
        return

    st.markdown("### Recent Activity")

    # Transform data for mobile transaction list
    transactions = []
    for txn in recent:
        merchant = clean_merchant_name(txn['description'])
        if len(merchant) > 25:
            merchant = merchant[:22] + "..."

        category = txn['effective_category']
        amount = txn['original_amount']

        transactions.append({
            'date': txn['transaction_date'],
            'icon': get_category_icon(category),
            'merchant': merchant,
            'category': category,
            'amount': format_amount_private(amount),
            'is_positive': amount > 0,
        })

    transaction_list(transactions, date_formatter=format_date_relative)

    if st.button("View All Transactions", use_container_width=True, type="secondary"):
        st.switch_page("views/transactions.py")


def render_mobile_dashboard():
    """
    Main mobile dashboard render function.
    Call this from app.py when mobile is detected.
    """
    # Apply theme (for dark mode support)
    apply_theme()

    # Apply mobile CSS
    apply_mobile_css()

    # Get stats
    stats = get_dashboard_stats()

    # Empty state
    if not stats or stats.get('account_count', 0) == 0:
        render_page_header("💰 Welcome")
        st.markdown("---")
        st.info("No accounts configured yet. Set up your accounts to get started.")

        if st.button("Go to Accounts", use_container_width=True, type="primary"):
            st.switch_page("views/accounts.py")
        return

    # Page header with greeting
    greeting = get_time_greeting()
    render_page_header(f"💰 {greeting}")

    # Hero balance card
    balance = format_amount_private(stats.get('total_balance', 0))
    last_sync = stats.get('last_sync')
    sync_text = f"Updated {format_relative_time(last_sync)}" if last_sync else "Not synced yet"

    hero_balance_card(
        balance=balance,
        label="Total Balance",
        change=sync_text,
        change_positive=True,
    )

    # Main content area (with bottom nav padding)
    st.markdown('<div class="mobile-content">', unsafe_allow_html=True)

    # Summary cards row
    col1, col2 = st.columns(2)

    with col1:
        monthly = format_amount_private(stats.get('monthly_spending', 0))
        summary_card(
            title="Spent This Month",
            value=monthly,
        )

    with col2:
        pending_count = stats.get('pending_count', 0)
        pending_amount = format_amount_private(stats.get('pending_amount', 0))
        summary_card(
            title="Pending",
            value=str(pending_count),
            secondary=pending_amount if pending_count > 0 else None,
        )

    # Budget progress (if set)
    render_budget_progress()

    # Alerts
    render_alerts()

    # Recent transactions
    render_recent_transactions()

    st.markdown('</div>', unsafe_allow_html=True)

    # Bottom navigation
    bottom_navigation(current="home")