"""
Financial Data Aggregator - Hub Landing Page
Actionable dashboard answering: "What needs my attention right now?"

Copyright (C) 2024-2026 Or Hasson
SPDX-License-Identifier: AGPL-3.0-or-later

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import streamlit as st
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from streamlit_app.utils.session import (
    init_session_state,
    format_amount_private,
    get_accounts_display,
    get_dashboard_stats_display,
)
from streamlit_app.utils.cache import (
    get_dashboard_stats,
    get_recent_transactions,
    get_hub_alerts,
    get_monthly_trend_cached,
)
from streamlit_app.utils.formatters import (
    format_relative_time,
    format_date_relative,
    get_category_icon,
)
from streamlit_app.utils.insights import get_time_greeting, generate_hub_insight
from services.budget_service import BudgetService
from streamlit_app.utils.rtl import clean_merchant_name
from streamlit_app.components.cards import render_transaction_card, render_summary_card
from streamlit_app.components.sidebar import render_minimal_sidebar
from streamlit_app.components.theme import apply_theme, render_theme_switcher
from streamlit_app.utils.mobile import detect_mobile, is_mobile
from streamlit_app.auth import check_authentication, get_logout_button

# Page configuration - collapse sidebar if mobile detected via query param
st.set_page_config(
    page_title="💰 Home",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed" if st.query_params.get("mobile") == "true" else "expanded",
)

# Mobile detection (automatic via viewport JS + User-Agent fallback)
detect_mobile()

if is_mobile():
    from streamlit_app.mobile_dashboard import render_mobile_dashboard
    render_mobile_dashboard()
    st.stop()


def render_empty_state():
    """Render welcome screen for new users (no data)."""
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## Welcome!")
        st.markdown("""
        Get started by syncing your financial accounts:

        1. **Configure credentials** (one-time setup)
        ```bash
        fin-cli config setup
        ```

        2. **Sync your data**
        """)

        if st.button("Go to Accounts", use_container_width=True, type="primary"):
            st.switch_page("pages/3_🏦_Accounts.py")

        st.markdown("---")
        st.caption("Supports: CAL, Max, Isracard, Excellence, Migdal, Phoenix")


def render_header():
    """Render header with greeting and sync button."""
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title(f"{get_time_greeting()}")
    with col2:
        if st.button("Sync Now", use_container_width=True, type="secondary"):
            st.switch_page("pages/3_🏦_Accounts.py")


def render_hero_and_metrics(stats: dict):
    """Render hero balance card (full width) with metrics row below."""
    # Hero balance card - full width
    balance = format_amount_private(stats.get('total_balance', 0))
    last_sync = stats.get('last_sync')
    sync_text = format_relative_time(last_sync) if last_sync else "Never"

    st.markdown(
        f'<div class="hero-card">'
        f'<div class="hero-label">Net Worth</div>'
        f'<div class="hero-amount">{balance}</div>'
        f'<div class="hero-sync">Last synced {sync_text}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Three metric cards in a row below
    m1, m2, m3 = st.columns(3)

    with m1:
        monthly = format_amount_private(stats.get('monthly_spending', 0))
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-value">{monthly}</div>'
            f'<div class="metric-label">This Month</div>'
            f'<div class="metric-sublabel">spent</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    with m2:
        pending_count = stats.get('pending_count', 0)
        pending_amount = stats.get('pending_amount', 0)
        pending_text = format_amount_private(pending_amount) if pending_amount else "—"
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-value">{pending_count}</div>'
            f'<div class="metric-label">Pending</div>'
            f'<div class="metric-sublabel">{pending_text}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    with m3:
        account_count = stats.get('account_count', 0)
        txn_count = stats.get('transaction_count', 0)
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-value">{account_count}</div>'
            f'<div class="metric-label">Accounts</div>'
            f'<div class="metric-sublabel">{txn_count:,} txns</div>'
            f'</div>',
            unsafe_allow_html=True
        )


def render_budget_progress():
    """Render budget progress bar below hero metrics if budget is set."""
    try:
        budget_service = BudgetService()
        progress = budget_service.get_current_progress()
        budget_service.close()

        if progress['budget'] is None:
            return  # No budget set, don't show anything

        spent = progress['spent']
        budget = progress['budget']
        percent = progress['percent_actual']
        remaining = progress['remaining']

        # Determine status class for both text and bar
        if progress['is_over_budget']:
            status_text = f"{abs(remaining):,.0f} over budget"
            status_class = "over"
        elif percent >= 80:
            status_text = f"{remaining:,.0f} remaining"
            status_class = "warning"
        else:
            status_text = f"{remaining:,.0f} remaining"
            status_class = "good"

        # Cap display percent at 100 for the bar
        display_percent = min(percent, 100)

        st.markdown(
            f'<div class="budget-card">'
            f'<div class="budget-header">'
            f'<span class="budget-title">Monthly Budget</span>'
            f'<span class="budget-remaining {status_class}">{status_text}</span>'
            f'</div>'
            f'<div class="budget-bar-bg">'
            f'<div class="budget-bar {status_class}" style="width: {display_percent}%;"></div>'
            f'</div>'
            f'<div class="budget-details">'
            f'<span>{spent:,.0f} of {budget:,.0f}</span>'
            f'<span>{percent:.0f}%</span>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    except Exception:
        pass  # Silently fail if budget table doesn't exist yet


def render_insight_banner(stats: dict):
    """Render contextual insight banner if there's a meaningful insight."""
    # Get monthly trend for insight calculation
    try:
        monthly_df = get_monthly_trend_cached(months_back=6)
        monthly_trend = monthly_df.to_dict('records') if not monthly_df.empty else None
    except Exception:
        monthly_trend = None

    insight = generate_hub_insight(stats, monthly_trend)

    if insight:
        insight_type = insight.get('type', 'neutral')
        icon = insight.get('icon', '💡')
        message = insight.get('message', '')

        st.markdown(
            f'<div class="insight-banner {insight_type}">'
            f'<span class="insight-icon">{icon}</span>'
            f'<span class="insight-message">{message}</span>'
            f'</div>',
            unsafe_allow_html=True
        )


def render_alerts():
    """Render alerts section with color-coded cards."""
    alerts = get_hub_alerts()

    if not alerts:
        return

    st.markdown('<div class="section-title">Needs Attention</div>', unsafe_allow_html=True)

    for alert in alerts:
        # Determine alert type for styling
        if 'sync' in alert['key']:
            alert_type = 'sync'
        elif 'unmapped' in alert['key']:
            alert_type = 'category'
        else:
            alert_type = 'uncategorized'

        # Alert card with button inside using columns for layout
        col1, col2 = st.columns([6, 1], gap="small")
        with col1:
            st.markdown(
                f'<div class="alert-card {alert_type}">'
                f'<span>{alert["icon"]}</span>'
                f'<span class="alert-message">{alert["message"]}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
        with col2:
            if st.button(alert['action_label'], key=alert['key'], use_container_width=True, type="secondary"):
                st.switch_page(alert['page'])


def render_recent_activity(min_height: int = None) -> int:
    """
    Render recent transactions section with icons and badges.

    Args:
        min_height: Optional minimum height for card alignment

    Returns:
        The actual height used
    """
    recent = get_recent_transactions(limit=7)

    if not recent:
        st.markdown("#### 📋 Recent Activity")
        st.info("No recent transactions. Sync to see activity.")
        return 0

    # Transform raw data into card component format
    transactions = []
    for txn in recent:
        merchant = clean_merchant_name(txn['description'])
        if len(merchant) > 28:
            merchant = merchant[:25] + "..."

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

    # Use reusable card component
    height = render_transaction_card(
        title="📋 Recent Activity",
        transactions=transactions,
        date_formatter=format_date_relative,
        min_height=min_height
    )

    if st.button("View all transactions", use_container_width=True, type="secondary"):
        st.switch_page("pages/1_💳_Transactions.py")

    return height


def render_accounts_overview(min_height: int = None) -> int:
    """
    Render accounts overview with card design.

    Args:
        min_height: Optional minimum height for card alignment

    Returns:
        The actual height used
    """
    accounts = get_accounts_display()

    if not accounts:
        st.markdown("#### 🏦 Accounts")
        st.info("No accounts yet. Sync to add accounts.")
        return 0

    # Group by institution
    by_institution = {}
    for acc in accounts:
        inst = acc['institution']
        if inst not in by_institution:
            by_institution[inst] = {'accounts': [], 'total': 0}
        by_institution[inst]['accounts'].append(acc)
        by_institution[inst]['total'] += acc['latest_balance'] or 0

    # Transform into card component format
    items = []
    for inst, data in by_institution.items():
        account_count = len(data['accounts'])
        is_card = 'card' in data['accounts'][0].get('account_type', '').lower() or inst.lower() in ['cal', 'max', 'isracard']
        count_text = f"{account_count} card{'s' if account_count > 1 else ''}" if is_card else f"{account_count} account{'s' if account_count > 1 else ''}"

        items.append({
            'name': inst.upper(),
            'subtitle': count_text,
            'value': format_amount_private(data['total']),
        })

    # Use reusable card component
    height = render_summary_card(title="🏦 Accounts", items=items, min_height=min_height)

    if st.button("View all accounts", use_container_width=True, type="secondary"):
        st.switch_page("pages/3_🏦_Accounts.py")

    return height


def calculate_card_heights():
    """
    Pre-calculate the heights needed for activity and accounts cards.
    Used to align both cards to the same height.

    Returns:
        Tuple of (transactions_height, accounts_height, max_height)
    """
    # Calculate transactions height
    recent = get_recent_transactions(limit=7)
    if recent:
        num_dates = len(set(t['transaction_date'] for t in recent))
        num_with_cat = sum(1 for t in recent if t.get('effective_category'))
        num_without_cat = len(recent) - num_with_cat
        txn_height = 80 + num_with_cat * 58 + num_without_cat * 48 + num_dates * 32
    else:
        txn_height = 0

    # Calculate accounts height
    accounts = get_accounts_display()
    if accounts:
        institutions = set(a['institution'] for a in accounts)
        acc_height = 80 + len(institutions) * 72
    else:
        acc_height = 0

    max_height = max(txn_height, acc_height)
    return txn_height, acc_height, max_height


def main():
    """Main hub page entry point."""
    # Check authentication (if enabled)
    if not check_authentication():
        st.stop()

    # Initialize session state
    init_session_state()

    # Apply theme (loads CSS + theme-specific styles)
    apply_theme()

    # Render sidebar
    render_minimal_sidebar()

    # Add logout button if auth is enabled
    get_logout_button()

    # Get stats to check if we have data
    stats = get_dashboard_stats()

    # Empty state - no accounts yet
    if not stats or stats.get('account_count', 0) == 0:
        st.title("Financial Data Aggregator")
        render_empty_state()
        return

    # Normal hub layout
    render_header()

    # Hero balance + metrics row
    render_hero_and_metrics(stats)

    # Budget progress bar (if budget is set)
    render_budget_progress()

    # Contextual insight banner
    render_insight_banner(stats)

    # Alerts section
    render_alerts()

    # Calculate aligned heights for both cards
    _, _, aligned_height = calculate_card_heights()

    # Two-column layout for activity and accounts
    col_left, col_right = st.columns([3, 2])

    with col_left:
        render_recent_activity(min_height=aligned_height)

    with col_right:
        render_accounts_overview(min_height=aligned_height)


if __name__ == "__main__":
    main()
