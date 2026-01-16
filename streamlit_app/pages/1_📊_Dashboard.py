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

from streamlit_app.utils.session import init_session_state, get_db_session
from streamlit_app.utils.formatters import (
    format_currency, format_number, format_datetime,
    format_transaction_amount, color_for_amount, AMOUNT_STYLE_CSS
)
from streamlit_app.utils.cache import get_dashboard_stats, get_transactions_cached, get_accounts_cached
from streamlit_app.utils.errors import safe_call_with_spinner, ErrorBoundary
from streamlit_app.components.sidebar import render_full_sidebar
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

# Render sidebar
render_full_sidebar()

# Page header
st.title("📊 Dashboard")
st.markdown("High-level overview of your financial status")

# Inject amount styling CSS
st.markdown(AMOUNT_STYLE_CSS, unsafe_allow_html=True)

st.markdown("---")

# Load dashboard data with caching and error handling
with ErrorBoundary("Failed to load dashboard data"):
    # Get dashboard statistics (cached for 1 minute, default 3 months for performance)
    stats = safe_call_with_spinner(
        get_dashboard_stats,
        spinner_text="Loading dashboard statistics...",
        error_message="Failed to load dashboard stats",
        default_return=None,
        months_back=3
    )

    if not stats or stats['account_count'] == 0:
        empty_dashboard_state()
        st.stop()

    # Summary Cards Row
    st.subheader("📈 Summary")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Portfolio Value",
            value=format_currency(stats['total_balance']),
            help="Sum of all account balances"
        )

    with col2:
        st.metric(
            label="Monthly Spending",
            value=format_currency(stats['monthly_spending']),
            help="Total spending this month"
        )

    with col3:
        st.metric(
            label="Pending Transactions",
            value=format_number(stats['pending_count']),
            delta=format_currency(stats['pending_amount']) if stats['pending_amount'] else None,
            help="Transactions awaiting completion"
        )

    with col4:
        st.metric(
            label="Total Transactions",
            value=format_number(stats['transaction_count']),
            help=f"Total transactions ({stats['period_start']} to {stats['period_end']})"
        )

    st.markdown("---")

    # Quick Charts Section
    st.subheader("📊 Quick Insights")

    # Fetch transaction data for charts (cached for 5 minutes)
    six_months_ago = stats['period_start']
    end_date = stats['period_end']

    transactions_data = safe_call_with_spinner(
        get_transactions_cached,
        spinner_text="Loading transaction data for charts...",
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

    # Row 1: Spending by Category and Monthly Trend
    if not df_transactions.empty:
        col1, col2 = st.columns(2)

        with col1:
            # Spending by Category (Donut)
            fig_donut = spending_donut(
                df_transactions,
                title="Spending by Category (Top 10)",
                value_col="amount",
                label_col="category",
                top_n=10
            )
            st.plotly_chart(fig_donut, use_container_width=True)

        with col2:
            # Monthly Spending Trend
            fig_monthly = monthly_trend(
                df_transactions,
                title="Monthly Spending Trend (Last 6 Months)",
                date_col="date",
                amount_col="amount",
                months=6
            )
            st.plotly_chart(fig_monthly, use_container_width=True)

        # Row 2: Balance Distribution and Recent Spending
        col1, col2 = st.columns(2)

        with col1:
            # Balance Distribution by Account Type (cached)
            accounts_data = safe_call_with_spinner(
                get_accounts_cached,
                spinner_text="Loading account balances...",
                error_message="Failed to load account data",
                default_return=[]
            )

            # Filter accounts with positive balance
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
                st.info("No account balance data available")

        with col2:
            # Recent Spending by Day (Last 14 days)
            fig_daily = spending_by_day(
                df_transactions,
                title="Daily Spending (Last 14 Days)",
                date_col="date",
                amount_col="amount",
                days=14
            )
            st.plotly_chart(fig_daily, use_container_width=True)

    else:
        st.info("No transaction data available for charts. Sync your accounts to see insights.")

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
                # Format amount with proper sign
                if amount < 0:
                    amount_str = f"−₪{abs(amount):,.2f}"
                elif amount > 0:
                    amount_str = f"+₪{amount:,.2f}"
                else:
                    amount_str = f"₪{amount:,.2f}"

                txn_data.append({
                    'Date': format_datetime(txn['transaction_date'], '%Y-%m-%d'),
                    'Description': desc[:40] + '...' if len(desc) > 40 else desc,
                    'Amount': amount_str,
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
                    )
                }
            )
        else:
            st.info("No recent transactions")

    with col2:
        st.markdown("#### Account Summary")

        # Use cached accounts data (already loaded)
        if accounts_data:
            acc_data = []
            for acc in accounts_data:
                balance = acc['latest_balance']
                acc_data.append({
                    'Institution': acc['institution'],
                    'Type': acc['account_type'] or '-',
                    'Balance': format_currency(balance) if balance else 'N/A',
                    'Status': '✅' if balance and balance > 0 else '⭕'
                })

            df_accounts_summary = pd.DataFrame(acc_data)
            st.dataframe(df_accounts_summary, use_container_width=True, hide_index=True)
        else:
            st.info("No accounts available")

    st.markdown("---")

    # Quick Actions
    st.subheader("⚡ Quick Actions")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔄 Sync All Data", type="primary", use_container_width=True):
            st.switch_page("pages/2_🔄_Sync.py")

    with col2:
        if st.button("💳 View Transactions", use_container_width=True):
            st.switch_page("pages/3_💳_Transactions.py")

    with col3:
        if st.button("📈 View Analytics", use_container_width=True):
            st.switch_page("pages/4_📈_Analytics.py")
