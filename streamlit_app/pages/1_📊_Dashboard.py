"""
Dashboard Page - High-level overview of financial status
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from streamlit_app.utils.session import (
    init_session_state, get_db_session, format_amount_private,
    get_accounts_display, get_dashboard_stats_display, get_transactions_display
)
from streamlit_app.utils.formatters import (
    format_number, format_datetime, color_for_amount, AMOUNT_STYLE_CSS,
    format_status
)
from streamlit_app.utils.cache import get_transactions_cached
from streamlit_app.utils.errors import safe_call_with_spinner, ErrorBoundary
from streamlit_app.utils.insights import generate_spending_insight, generate_pending_insight
from streamlit_app.components.sidebar import render_minimal_sidebar
from streamlit_app.components.loading import contextual_spinner
from streamlit_app.components.theme import apply_theme, render_theme_switcher
from streamlit_app.components.charts import (
    spending_donut,
    monthly_trend,
    balance_distribution,
    spending_by_day
)
from streamlit_app.components.empty_states import empty_dashboard_state

# Page config
st.set_page_config(
    page_title="Dashboard - Financial Aggregator",
    page_icon="📊",
    layout="wide"
)

# Initialize session state
init_session_state()

# Apply theme (must be called before any content)
theme = apply_theme()

# Render sidebar
render_minimal_sidebar()

# Render theme switcher in sidebar
render_theme_switcher("sidebar")

# Page header
st.title("📊 Dashboard")
st.markdown("High-level overview of your financial status")

# Inject amount styling CSS
st.markdown(AMOUNT_STYLE_CSS, unsafe_allow_html=True)

st.markdown("---")

# Load dashboard data with caching and error handling
with ErrorBoundary("Failed to load dashboard data"):
    # Get dashboard statistics with pre-formatted display values
    stats = safe_call_with_spinner(
        get_dashboard_stats_display,
        spinner_text=contextual_spinner("calculating", "financial statistics"),
        error_message="Failed to load dashboard stats",
        default_return=None
    )

    if not stats or stats['account_count'] == 0:
        empty_dashboard_state()
        st.stop()

    # ========================================================================
    # HERO METRICS (Most Important - 2 key numbers)
    # ========================================================================
    st.markdown("## 💰 Your Financial Snapshot")

    col1, col2 = st.columns(2)

    with col1:
        # Net Worth / Total Balance (Primary Hero)
        balance_color = "#00897b" if stats['total_balance'] >= 0 else "#c62828"
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); padding: 1.5rem; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            <p style="margin: 0; font-size: 0.9rem; color: #666; font-weight: 500;">Net Worth</p>
            <p style="margin: 0.5rem 0 0 0; font-size: 2.5rem; font-weight: 700; color: {balance_color};">
                {stats['total_balance_display']}
            </p>
            <p style="margin: 0.25rem 0 0 0; font-size: 0.75rem; color: #888;">
                Across {stats['account_count']} account{'s' if stats['account_count'] > 1 else ''}
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        # Monthly Spending (Secondary Hero)
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #fff5f5 0%, #fecaca 100%); padding: 1.5rem; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            <p style="margin: 0; font-size: 0.9rem; color: #666; font-weight: 500;">This Month's Spending</p>
            <p style="margin: 0.5rem 0 0 0; font-size: 2.5rem; font-weight: 700; color: #c62828;">
                {stats['monthly_spending_display']}
            </p>
            <p style="margin: 0.25rem 0 0 0; font-size: 0.75rem; color: #888;">
                {format_number(stats['transaction_count'])} transactions total
            </p>
        </div>
        """, unsafe_allow_html=True)

    # ========================================================================
    # CONTEXTUAL INSIGHT
    # ========================================================================
    # Build insight data
    insight_data = {
        'monthly_spending': abs(stats['monthly_spending']) if stats['monthly_spending'] else 0,
        'monthly_avg_spending': stats.get('monthly_avg_spending'),
        'transaction_count': stats['transaction_count'],
        'pending_count': stats['pending_count'],
        'pending_amount': stats['pending_amount']
    }

    spending_insight = generate_spending_insight(insight_data)
    pending_insight = generate_pending_insight(insight_data)

    if spending_insight:
        st.info(f"💡 **Insight:** {spending_insight}")

    if pending_insight:
        st.warning(f"⏳ {pending_insight}")

    # Check for unmapped categories
    try:
        from services.category_service import CategoryService
        category_service = CategoryService(session=get_db_session())
        unmapped_count = category_service.get_unmapped_count()
        unmapped_categories = len(category_service.get_unmapped_categories())

        if unmapped_count > 0:
            st.warning(
                f"📂 **{unmapped_categories} categories** ({unmapped_count:,} transactions) need mapping. "
                f"[Manage Categories →](./10_📂_Categories)"
            )
    except Exception:
        pass  # Silently skip if category service unavailable

    st.markdown("---")

    # ========================================================================
    # PROGRESSIVE DISCLOSURE WITH TABS
    # ========================================================================
    # Fetch transaction data for charts (cached for 5 minutes)
    six_months_ago = stats['period_start']
    end_date = stats['period_end']

    transactions_data = safe_call_with_spinner(
        get_transactions_cached,
        spinner_text=contextual_spinner("loading", "transaction history"),
        error_message="Failed to load transaction data",
        default_return=[],
        start_date=six_months_ago,
        end_date=end_date
    )

    # Filter expenses only and convert to DataFrame
    df_transactions = pd.DataFrame([
        {
            'date': txn['transaction_date'],
            'amount': txn['original_amount'],
            'category': txn['effective_category'] or 'Uncategorized',
            'description': txn['description'],
            'status': txn['status']
        }
        for txn in transactions_data
        if txn['original_amount'] < 0  # Only expenses
    ])

    # Load accounts data with pre-formatted display values
    accounts_data = safe_call_with_spinner(
        get_accounts_display,
        spinner_text=contextual_spinner("fetching", "account balances"),
        error_message="Failed to load account data",
        default_return=[]
    )

    # Organize content into tabs for progressive disclosure
    tab_overview, tab_trends, tab_categories = st.tabs(["📊 Overview", "📈 Trends", "🎯 Categories"])

    with tab_overview:
        # Quick overview - 2 charts max
        if not df_transactions.empty:
            col1, col2 = st.columns(2)

            with col1:
                # Spending by Category (Donut) - Most useful at a glance
                fig_donut = spending_donut(
                    df_transactions,
                    title="Where Your Money Goes",
                    value_col="amount",
                    label_col="category",
                    top_n=8
                )
                st.plotly_chart(fig_donut, use_container_width=True)

            with col2:
                # Recent Spending by Day (Last 14 days)
                fig_daily = spending_by_day(
                    df_transactions,
                    title="Recent Daily Spending",
                    date_col="date",
                    amount_col="amount",
                    days=14
                )
                st.plotly_chart(fig_daily, use_container_width=True)
        else:
            st.info("No transaction data available for charts. Sync your accounts to see insights.")

    with tab_trends:
        # Detailed trends
        if not df_transactions.empty:
            # Monthly Spending Trend
            fig_monthly = monthly_trend(
                df_transactions,
                title="Monthly Spending Trend",
                date_col="date",
                amount_col="amount",
                months=6
            )
            st.plotly_chart(fig_monthly, use_container_width=True)

            # Balance Distribution by Account Type
            df_accounts = pd.DataFrame([
                {
                    'balance': acc['latest_balance'],
                    'account_type': acc['account_type'] or 'Other',
                    'institution': acc['institution']
                }
                for acc in accounts_data
                if acc['latest_balance'] > 0
            ])

            if not df_accounts.empty:
                fig_balance = balance_distribution(
                    df_accounts,
                    title="Balance Distribution by Account Type",
                    value_col="balance",
                    label_col="account_type"
                )
                st.plotly_chart(fig_balance, use_container_width=True)
        else:
            st.info("No trend data available. Sync your accounts to see trends.")

    with tab_categories:
        # Category breakdown
        if not df_transactions.empty:
            # Aggregate by category
            category_totals = df_transactions.groupby('category')['amount'].sum().abs().sort_values(ascending=False)

            st.markdown("#### Spending by Category")

            # Show top categories as a table with progress bars
            total_spending = category_totals.sum()

            for category, amount in category_totals.head(10).items():
                pct = (amount / total_spending) * 100 if total_spending > 0 else 0
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.progress(pct / 100, text=category)
                with col2:
                    st.markdown(f"**{format_amount_private(amount)}**")
                with col3:
                    st.markdown(f"*{pct:.1f}%*")
        else:
            st.info("No category data available. Sync your accounts to see category breakdown.")

    st.markdown("---")

    # Recent Activity Section
    st.subheader("🕒 Recent Activity")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Last 10 Transactions")

        # Get recent transactions from cached data (already loaded)
        if transactions_data:
            # Sort by date and take last 10
            sorted_txns = sorted(transactions_data, key=lambda x: x['transaction_date'], reverse=True)[:10]

            txn_data = []
            for txn in sorted_txns:
                desc = txn['description']
                amount = txn['original_amount']

                txn_data.append({
                    'Date': format_datetime(txn['transaction_date'], '%Y-%m-%d'),
                    'Description': desc[:35] + '...' if len(desc) > 35 else desc,
                    'Amount': format_amount_private(amount),
                    'Status': format_status(txn['status'], as_badge=False),
                    'Category': txn['effective_category'] or '-'
                })

            df_recent = pd.DataFrame(txn_data)
            st.dataframe(
                df_recent,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'Amount': st.column_config.TextColumn(
                        'Amount',
                        help='Transaction amount',
                        width='small'
                    ),
                    'Status': st.column_config.TextColumn(
                        'Status',
                        help='Transaction status',
                        width='small'
                    )
                }
            )
        else:
            st.info("No recent transactions")

    with col2:
        st.markdown("#### Account Summary")

        # Use accounts data with pre-formatted display values
        if accounts_data:
            acc_data = []
            for acc in accounts_data:
                acc_data.append({
                    'Institution': acc['institution'],
                    'Type': acc['account_type'] or '-',
                    'Balance': acc['balance_display'],
                    'Status': '✅' if acc['latest_balance'] and acc['latest_balance'] > 0 else '⭕'
                })

            df_accounts_summary = pd.DataFrame(acc_data)
            st.dataframe(df_accounts_summary, use_container_width=True, hide_index=True)
        else:
            st.info("No accounts available")
