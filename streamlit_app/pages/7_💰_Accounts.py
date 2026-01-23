"""
Accounts Management Page - View and manage financial accounts
"""

import streamlit as st
import pandas as pd
from datetime import timedelta, date
import sys
from pathlib import Path

# Page config MUST be first (before any other Streamlit commands)
st.set_page_config(
    page_title="Accounts - Financial Aggregator",
    page_icon="💰",
    layout="wide"
)

# Third-party imports that don't use Streamlit
from sqlalchemy import func, and_, desc

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Now import things that might use st.session_state
from streamlit_app.utils.session import init_session_state, format_amount_private

# Initialize session state
init_session_state()

from db.database import get_session
from db.models import Account, Transaction, Balance
from services.analytics_service import AnalyticsService

from streamlit_app.utils.formatters import (
    format_number, format_datetime,
    format_account_number
)
from streamlit_app.components.sidebar import render_minimal_sidebar
from streamlit_app.components.charts import balance_history
from streamlit_app.components.theme import apply_theme, render_theme_switcher

# Apply theme (must be called before any content)
theme = apply_theme()

# Render sidebar
render_minimal_sidebar()

# Render theme switcher in sidebar
render_theme_switcher("sidebar")

# Page header
st.title("💰 Accounts Management")
st.markdown("View and manage your financial accounts")
st.markdown("---")

# Get database session
try:
    session = get_session()

    # Check if database has data
    account_count = session.query(func.count(Account.id)).scalar()

    if not account_count or account_count == 0:
        st.warning("⚠️ No account data available. Please sync your financial data first.")
        st.info("Go to the **Sync** page to synchronize your accounts.")
        if st.button("🔄 Go to Sync Page", type="primary"):
            st.switch_page("pages/2_🔄_Sync.py")
        st.stop()

    # ============================================================================
    # ACCOUNTS OVERVIEW
    # ============================================================================
    st.subheader("📊 Accounts Overview")

    # Get latest balance for each account using analytics service
    analytics = AnalyticsService(session)

    # Get accounts with their latest balances
    latest_balances_data = analytics.get_latest_balances()

    # Also get accounts without balances (not returned by get_latest_balances)
    accounts_with_balances_ids = [acc.id for acc, _ in latest_balances_data]
    accounts_without_balances = session.query(Account).filter(
        ~Account.id.in_(accounts_with_balances_ids) if accounts_with_balances_ids else True
    ).all()

    # Combine into format expected by rest of page: (Account, balance_amount, balance_date)
    accounts_with_balance = []
    for account, balance in latest_balances_data:
        accounts_with_balance.append((account, balance.total_amount, balance.balance_date))

    # Add accounts without balances
    for account in accounts_without_balances:
        accounts_with_balance.append((account, None, None))

    # Build enriched account data once - calculate all needed info in single pass
    enriched_accounts = []
    for account, balance, balance_date in accounts_with_balance:
        # Get transaction count
        txn_count = session.query(func.count(Transaction.id)).filter(
            Transaction.account_id == account.id
        ).scalar() or 0

        # Get last transaction date
        last_txn = session.query(func.max(Transaction.transaction_date)).filter(
            Transaction.account_id == account.id
        ).scalar()

        # Determine if credit card
        is_credit_card = account.account_type == "credit_card"

        # Determine status
        if is_credit_card or (balance and balance > 0):
            status_icon = "✅"
        elif balance == 0:
            status_icon = "⭕"
        else:
            status_icon = "❌"

        enriched_accounts.append({
            'account': account,
            'balance': balance,
            'balance_date': balance_date,
            'txn_count': txn_count,
            'last_txn': last_txn,
            'is_credit_card': is_credit_card,
            'status_icon': status_icon
        })

    # Group by account type
    account_types = {}
    for item in enriched_accounts:
        acc_type = item['account'].account_type or "Other"
        if acc_type not in account_types:
            account_types[acc_type] = []
        account_types[acc_type].append(item)

    # Summary metrics
    total_balance = sum([item['balance'] for items in account_types.values() for item in items if item['balance']])
    total_accounts = len(accounts_with_balance)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Accounts", format_number(total_accounts))

    with col2:
        st.metric("Total Balance", format_amount_private(total_balance))

    with col3:
        active_accounts = sum(
            [1 for items in account_types.values() for item in items if item['balance'] and item['balance'] > 0])
        st.metric("Active Accounts", format_number(active_accounts))

    st.markdown("---")

    # ============================================================================
    # ACCOUNT DETAILS VIEW (Show at top when selected)
    # ============================================================================
    if 'selected_account_id' in st.session_state and st.session_state.selected_account_id:
        account_id = st.session_state.selected_account_id
        account = session.query(Account).filter(Account.id == account_id).first()

        if account:
            st.subheader("🔍 Account Details")

            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"### {account.institution}")
                st.markdown(f"**Type:** {account.account_type or 'N/A'}")
                if account.account_number:
                    masked = st.session_state.get('mask_account_numbers', True)
                    account_display = format_account_number(account.account_number, masked=masked)
                    st.markdown(f"**Account Number:** {account_display}")

            with col2:
                if st.button("❌ Close Details", use_container_width=True):
                    del st.session_state.selected_account_id
                    st.rerun()

            # Get latest balance (single source of truth)
            latest_balance = account.latest_balance

            if latest_balance:
                st.markdown("---")
                st.markdown("**Current Balance**")

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Total Amount", format_amount_private(latest_balance.total_amount))

                with col2:
                    if latest_balance.available:
                        st.metric("Available", format_amount_private(latest_balance.available))

                with col3:
                    st.metric("As of", format_datetime(latest_balance.balance_date, '%Y-%m-%d'))

            # Balance History Chart
            st.markdown("---")
            st.markdown("**Balance History (Last 3 Months)**")

            three_months_ago = date.today() - timedelta(days=90)

            balance_history_query = session.query(
                Balance.balance_date,
                Balance.total_amount
            ).filter(
                and_(
                    Balance.account_id == account_id,
                    Balance.balance_date >= three_months_ago
                )
            ).order_by(Balance.balance_date).all()

            if balance_history_query:
                balance_data = []
                for balance_date, total_amount in balance_history_query:
                    balance_data.append({
                        'date': balance_date,
                        'balance': total_amount
                    })

                df_balance_history = pd.DataFrame(balance_data)

                fig_balance_hist = balance_history(
                    df_balance_history,
                    title=f"Balance History - {account.institution}",
                    x_col="date",
                    y_col="balance"
                )
                st.plotly_chart(fig_balance_hist, use_container_width=True)
            else:
                st.info("No balance history available")

            # Recent Transactions
            st.markdown("---")
            st.markdown("**Recent Transactions (Last 20)**")

            recent_txns = session.query(Transaction).filter(
                Transaction.account_id == account_id
            ).order_by(desc(Transaction.transaction_date)).limit(20).all()

            if recent_txns:
                txn_data = []
                for txn in recent_txns:
                    txn_data.append({
                        'Date': format_datetime(txn.transaction_date, '%Y-%m-%d'),
                        'Description': txn.description[:50] + '...' if len(txn.description) > 50 else txn.description,
                        'Amount': format_amount_private(txn.original_amount),
                        'Category': txn.effective_category or 'Uncategorized',
                        'Status': '✅' if txn.status == 'completed' else '⏳'
                    })

                df_recent_txns = pd.DataFrame(txn_data)
                st.dataframe(df_recent_txns, use_container_width=True, hide_index=True)

                # Link to full transactions page
                if st.button("📋 View All Transactions", use_container_width=True):
                    st.switch_page("pages/3_💳_Transactions.py")
            else:
                st.info("No transactions found for this account")

            # Account Statistics
            st.markdown("---")
            st.markdown("**Account Statistics**")

            # Last 90 days stats
            ninety_days_ago = date.today() - timedelta(days=90)

            income_90d = session.query(func.sum(Transaction.original_amount)).filter(
                and_(
                    Transaction.account_id == account_id,
                    Transaction.transaction_date >= ninety_days_ago,
                    Transaction.original_amount > 0
                )
            ).scalar() or 0

            expenses_90d = session.query(func.sum(Transaction.original_amount)).filter(
                and_(
                    Transaction.account_id == account_id,
                    Transaction.transaction_date >= ninety_days_ago,
                    Transaction.original_amount < 0
                )
            ).scalar() or 0

            txn_count_90d = session.query(func.count(Transaction.id)).filter(
                and_(
                    Transaction.account_id == account_id,
                    Transaction.transaction_date >= ninety_days_ago
                )
            ).scalar() or 0

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Income (90 days)", format_amount_private(income_90d))

            with col2:
                st.metric("Expenses (90 days)", format_amount_private(abs(expenses_90d)))

            with col3:
                st.metric("Transactions (90 days)", format_number(txn_count_90d))

            st.markdown("---")
            st.markdown("---")  # Extra separator before account list

    # ============================================================================
    # ACCOUNTS BY TYPE (Card View)
    # ============================================================================
    for acc_type, accounts_list in sorted(account_types.items()):
        st.subheader(f"📁 {acc_type}")

        # Create columns for cards (3 per row)
        cols = st.columns(3)

        for idx, item in enumerate(accounts_list):
            account = item['account']
            balance = item['balance']
            balance_date = item['balance_date']
            is_credit_card = item['is_credit_card']
            status_icon = item['status_icon']
            txn_count = item['txn_count']

            with cols[idx % 3]:
                # Card container
                with st.container():
                    st.markdown(f"**{status_icon} {account.institution}**")

                    # Balance info
                    if not is_credit_card:
                        if balance is not None:
                            st.metric("Balance", format_amount_private(balance))
                            if balance_date:
                                st.caption(f"As of: {format_datetime(balance_date, '%Y-%m-%d')}")
                        else:
                            st.info("No balance data")

                    # Account details (masked by default for privacy)
                    if account.account_number:
                        masked = st.session_state.get('mask_account_numbers', True)
                        account_display = format_account_number(account.account_number, masked=masked)
                        st.caption(f"Account: {account_display}")

                    # Transaction count (from enriched data)
                    st.caption(f"Transactions: {txn_count}")

                    # View details button
                    if st.button(f"View Details", key=f"view_{account.id}", use_container_width=True):
                        st.session_state.selected_account_id = account.id
                        st.rerun()

                    st.markdown("---")

    # ============================================================================
    # ACCOUNT TABLE VIEW
    # ============================================================================
    st.subheader("📋 Account List")

    # Get masking preference
    masked = st.session_state.get('mask_account_numbers', True)

    # Build table data from enriched accounts (no additional queries needed)
    table_data = []
    for item in enriched_accounts:
        account = item['account']
        balance = item['balance']
        balance_date = item['balance_date']
        txn_count = item['txn_count']
        last_txn = item['last_txn']
        status_icon = item['status_icon']

        table_data.append({
            'ID': account.id,
            'Type': account.account_type or 'Other',
            'Institution': account.institution,
            'Account Number': format_account_number(account.account_number,
                                                    masked=masked) if account.account_number else 'N/A',
            'Balance': format_amount_private(balance) if balance else 'N/A',
            'Last Updated': format_datetime(balance_date, '%Y-%m-%d') if balance_date else 'Never',
            'Transactions': txn_count,
            'Last Transaction': format_datetime(last_txn, '%Y-%m-%d') if last_txn else 'N/A',
            'Status': status_icon
        })

    df_accounts = pd.DataFrame(table_data)

    st.dataframe(
        df_accounts[['Type', 'Institution', 'Account Number', 'Balance', 'Last Updated', 'Transactions', 'Status']],
        use_container_width=True,
        hide_index=True
    )

except Exception as e:
    st.error(f"Error loading accounts: {str(e)}")
    st.exception(e)
    st.info("💡 Make sure the database is initialized with `fin-cli init`")
