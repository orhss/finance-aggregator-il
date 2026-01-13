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
from streamlit_app.utils.formatters import format_currency, format_number, format_datetime
from streamlit_app.components.sidebar import render_full_sidebar
from streamlit_app.components.charts import (
    spending_donut,
    monthly_trend,
    balance_distribution,
    spending_by_day
)

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
st.markdown("---")

# Get database session
try:
    from db.database import get_session
    from db.models import Account, Transaction, Balance
    from sqlalchemy import func, and_, desc

    session = get_session()

    # Check if database has data
    account_count = session.query(func.count(Account.id)).scalar()
    transaction_count = session.query(func.count(Transaction.id)).scalar()

    if not account_count or account_count == 0:
        st.warning("⚠️ No data available. Please sync your financial data first.")
        st.info("Go to the **Sync** page to synchronize your accounts.")

        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🔄 Go to Sync Page", type="primary"):
                st.switch_page("pages/2_🔄_Sync.py")

        st.stop()

    # Summary Cards Row
    st.subheader("📈 Summary")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Total Portfolio Value - get latest balance for each account
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
        ).scalar() or 0

        st.metric(
            label="Total Portfolio Value",
            value=format_currency(total_balance),
            help="Sum of all account balances"
        )

    with col2:
        # Monthly Spending (current month)
        first_of_month = date.today().replace(day=1)
        monthly_spending = session.query(func.sum(Transaction.original_amount)).filter(
            and_(
                Transaction.transaction_date >= first_of_month,
                Transaction.original_amount < 0
            )
        ).scalar() or 0
        st.metric(
            label="Monthly Spending",
            value=format_currency(abs(monthly_spending)),
            help="Total spending this month"
        )

    with col3:
        # Pending Transactions
        pending_count = session.query(func.count(Transaction.id)).filter(
            Transaction.status == 'pending'
        ).scalar() or 0

        pending_amount = session.query(func.sum(Transaction.original_amount)).filter(
            Transaction.status == 'pending'
        ).scalar() or 0

        st.metric(
            label="Pending Transactions",
            value=format_number(pending_count),
            delta=format_currency(pending_amount) if pending_amount else None,
            help="Transactions awaiting completion"
        )

    with col4:
        # Last Sync Status
        # For now, show transaction count as proxy
        st.metric(
            label="Total Transactions",
            value=format_number(transaction_count),
            help="Total number of synced transactions"
        )

    st.markdown("---")

    # Quick Charts Section
    st.subheader("📊 Quick Insights")

    # Fetch transaction data for charts
    # Get last 6 months of data
    six_months_ago = date.today() - timedelta(days=180)

    transactions_query = session.query(Transaction).filter(
        and_(
            Transaction.transaction_date >= six_months_ago,
            Transaction.original_amount < 0  # Only expenses
        )
    )

    # Convert to DataFrame
    transactions_data = []
    for txn in transactions_query.all():
        transactions_data.append({
            'date': txn.transaction_date,
            'amount': txn.original_amount,
            'category': txn.effective_category or 'Uncategorized',
            'description': txn.description,
            'status': txn.status
        })

    df_transactions = pd.DataFrame(transactions_data)

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
            # Balance Distribution by Account Type
            # Get latest balance for each account
            accounts_with_balance = session.query(
                Account.account_type,
                Account.institution,
                Balance.total_amount
            ).join(
                Balance,
                Balance.account_id == Account.id
            ).join(
                latest_balances,
                and_(
                    Balance.account_id == latest_balances.c.account_id,
                    Balance.balance_date == latest_balances.c.max_date
                )
            ).filter(Balance.total_amount > 0).all()

            accounts_data = []
            for acc_type, institution, balance in accounts_with_balance:
                accounts_data.append({
                    'balance': balance,
                    'account_type': acc_type or 'Other',
                    'institution': institution
                })

            df_accounts = pd.DataFrame(accounts_data)

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

        # Get last 10 transactions
        recent_txns = session.query(Transaction).order_by(
            Transaction.transaction_date.desc()
        ).limit(10).all()

        if recent_txns:
            txn_data = []
            for txn in recent_txns:
                txn_data.append({
                    'Date': format_datetime(txn.transaction_date, '%Y-%m-%d'),
                    'Description': txn.description[:40] + '...' if len(txn.description) > 40 else txn.description,
                    'Amount': format_currency(txn.original_amount),
                    'Category': txn.effective_category or '-'
                })

            df_recent = pd.DataFrame(txn_data)
            st.dataframe(df_recent, use_container_width=True, hide_index=True)
        else:
            st.info("No recent transactions")

    with col2:
        st.markdown("#### Account Summary")

        # Get all accounts with their latest balance
        accounts_with_balances = session.query(
            Account.institution,
            Account.account_type,
            Balance.total_amount
        ).outerjoin(
            Balance,
            Balance.account_id == Account.id
        ).outerjoin(
            latest_balances,
            and_(
                Balance.account_id == latest_balances.c.account_id,
                Balance.balance_date == latest_balances.c.max_date
            )
        ).all()

        if accounts_with_balances:
            acc_data = []
            for institution, acc_type, balance in accounts_with_balances:
                acc_data.append({
                    'Institution': institution,
                    'Type': acc_type or '-',
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

except Exception as e:
    st.error(f"Error loading dashboard: {str(e)}")
    st.exception(e)
    st.info("💡 Make sure the database is initialized with `fin-cli init`")
