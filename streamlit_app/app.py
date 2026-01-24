"""
Financial Data Aggregator - Hub Landing Page
Actionable dashboard answering: "What needs my attention right now?"

Phase 3: Visual Overhaul with card-based design, hero balance, and category icons.
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
from streamlit_app.utils.rtl import clean_merchant_name
from streamlit_app.components.cards import render_transaction_card, render_summary_card
from streamlit_app.components.sidebar import render_minimal_sidebar

# Page configuration
st.set_page_config(
    page_title="Financial Data Aggregator",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_custom_css():
    """Load Phase 3 custom CSS styling with cards, gradients, and modern design."""
    css = """
    <style>
    /* ===== GLOBAL BREATHING ROOM ===== */
    .main .block-container {
        padding: 1.5rem 2rem 2rem 2rem;
        max-width: 1200px;
    }

    /* ===== HERO BALANCE CARD ===== */
    .hero-balance {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem 2rem;
        border-radius: 20px;
        color: white;
        margin-bottom: 1rem;
    }
    .hero-balance .label {
        font-size: 0.9rem;
        opacity: 0.9;
        margin-bottom: 0.25rem;
        font-weight: 500;
    }
    .hero-balance .amount {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        line-height: 1.2;
    }
    .hero-balance .sublabel {
        font-size: 0.85rem;
        opacity: 0.8;
        margin-top: 0.5rem;
    }

    /* ===== METRIC CARDS ===== */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        text-align: center;
        border: 1px solid #f0f0f0;
        height: 100%;
    }
    .metric-card .value {
        font-size: 1.4rem;
        font-weight: 600;
        color: #1f2937;
        margin-bottom: 0.25rem;
    }
    .metric-card .label {
        font-size: 0.8rem;
        color: #6b7280;
        font-weight: 500;
    }
    .metric-card .sublabel {
        font-size: 0.7rem;
        color: #9ca3af;
        margin-top: 0.25rem;
    }

    /* ===== INSIGHT BANNER ===== */
    .insight-banner {
        padding: 0.75rem 1rem;
        border-radius: 10px;
        margin-bottom: 1.25rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .insight-banner.positive {
        background: #D1FAE5;
        color: #065F46;
    }
    .insight-banner.neutral {
        background: #F3F4F6;
        color: #374151;
    }
    .insight-banner.warning {
        background: #FEF3C7;
        color: #92400E;
    }
    .insight-banner .icon {
        font-size: 1.1rem;
    }
    .insight-banner .message {
        font-size: 0.9rem;
        font-weight: 500;
    }

    /* ===== ALERT CARDS ===== */
    .alert-card {
        padding: 0.75rem 1rem;
        border-radius: 10px;
        margin-bottom: 0.5rem;
    }
    .alert-card.sync {
        background: #FEF3C7;
        border-left: 3px solid #F59E0B;
    }
    .alert-card.category {
        background: #DBEAFE;
        border-left: 3px solid #3B82F6;
    }
    .alert-card.uncategorized {
        background: #E0E7FF;
        border-left: 3px solid #6366F1;
    }

    /* ===== BUTTONS ===== */
    .stButton>button {
        border-radius: 8px;
        font-weight: 500;
    }

    div[data-testid="stButton"] button[kind="secondary"] {
        border-color: #e5e7eb;
        color: #6b7280;
    }
    div[data-testid="stButton"] button[kind="secondary"]:hover {
        background: #f9fafb;
        color: #374151;
        border-color: #d1d5db;
    }

    /* ===== SIDEBAR STYLING ===== */
    [data-testid="stSidebarNav"] a[data-testid="stSidebarNavLink"]:hover {
        background-color: #e1e4e8 !important;
    }
    [data-testid="stSidebarNav"] a[data-testid="stSidebarNavLink"][aria-current="page"] {
        background-color: #667eea !important;
    }
    [data-testid="stSidebarNav"] a[data-testid="stSidebarNavLink"][aria-current="page"] span {
        color: white !important;
    }
    [data-testid="stSidebarNav"] li {
        border-radius: 6px;
        margin: 4px 0;
    }

    /* ===== STREAMLIT OVERRIDES ===== */
    [data-testid="stMetricValue"] {
        font-size: 24px;
    }
    [data-testid="stMetricDelta"] svg {
        display: none;
    }

    /* Remove iframe borders from components.html */
    iframe {
        border: none !important;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


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

        if st.button("Go to Sync Page", use_container_width=True, type="primary"):
            st.switch_page("pages/2_🔄_Sync.py")

        st.markdown("---")
        st.caption("Supports: CAL, Max, Isracard, Excellence, Migdal, Phoenix")


def render_header():
    """Render header with greeting and sync button."""
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title(f"{get_time_greeting()}")
    with col2:
        if st.button("Sync Now", use_container_width=True, type="secondary"):
            st.switch_page("pages/2_🔄_Sync.py")


def render_hero_and_metrics(stats: dict):
    """Render hero balance card with supporting metric cards."""
    # Layout: Hero (left) + 3 metrics (right)
    col_hero, col_metrics = st.columns([1.2, 1])

    with col_hero:
        # Hero balance card
        balance = format_amount_private(stats.get('total_balance', 0))
        last_sync = stats.get('last_sync')
        sync_text = format_relative_time(last_sync) if last_sync else "Never"

        st.markdown(
            f'<div class="hero-balance">'
            f'<div class="label">Net Worth</div>'
            f'<div class="amount">{balance}</div>'
            f'<div class="sublabel">Last synced {sync_text}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    with col_metrics:
        # Three metric cards in a row
        m1, m2, m3 = st.columns(3)

        with m1:
            monthly = format_amount_private(stats.get('monthly_spending', 0))
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="value">{monthly}</div>'
                f'<div class="label">This Month</div>'
                f'<div class="sublabel">spent</div>'
                f'</div>',
                unsafe_allow_html=True
            )

        with m2:
            pending_count = stats.get('pending_count', 0)
            pending_amount = stats.get('pending_amount', 0)
            pending_text = format_amount_private(pending_amount) if pending_amount else "—"
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="value">{pending_count}</div>'
                f'<div class="label">Pending</div>'
                f'<div class="sublabel">{pending_text}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

        with m3:
            account_count = stats.get('account_count', 0)
            txn_count = stats.get('transaction_count', 0)
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="value">{account_count}</div>'
                f'<div class="label">Accounts</div>'
                f'<div class="sublabel">{txn_count:,} txns</div>'
                f'</div>',
                unsafe_allow_html=True
            )


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
            f'<span class="icon">{icon}</span>'
            f'<span class="message">{message}</span>'
            f'</div>',
            unsafe_allow_html=True
        )


def render_alerts():
    """Render alerts section with color-coded cards."""
    alerts = get_hub_alerts()

    if not alerts:
        return

    st.markdown("#### Needs Attention")

    for alert in alerts:
        # Determine alert type for styling
        if 'sync' in alert['key']:
            alert_type = 'sync'
        elif 'unmapped' in alert['key']:
            alert_type = 'category'
        else:
            alert_type = 'uncategorized'

        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(
                f'<div class="alert-card {alert_type}">'
                f'<div class="alert-content">'
                f'<span class="alert-icon">{alert["icon"]}</span>'
                f'<span class="alert-message">{alert["message"]}</span>'
                f'</div></div>',
                unsafe_allow_html=True
            )
        with col2:
            if st.button(alert['action_label'], key=alert['key'], use_container_width=True):
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
        st.switch_page("pages/3_💳_Transactions.py")

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
        st.switch_page("pages/7_💰_Accounts.py")

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
    # Initialize session state
    init_session_state()

    # Load custom CSS
    load_custom_css()

    # Render sidebar
    render_minimal_sidebar()

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
