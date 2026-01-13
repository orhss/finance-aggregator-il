"""
Sync Management Page - View sync status and history (read-only for Phase 2)
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from streamlit_app.utils.session import init_session_state
from streamlit_app.utils.formatters import format_currency, format_number, format_datetime
from streamlit_app.components.sidebar import render_minimal_sidebar

# Page config
st.set_page_config(
    page_title="Sync - Financial Aggregator",
    page_icon="🔄",
    layout="wide"
)

# Initialize session state
init_session_state()

# Render sidebar
render_minimal_sidebar()

# Page header
st.title("🔄 Sync Management")
st.markdown("View sync status and synchronization history")
st.markdown("---")

# Get database session
try:
    from db.database import get_session
    from db.models import Account, Transaction, Balance
    from sqlalchemy import func, and_, desc

    session = get_session()

    # ============================================================================
    # SYNC STATUS OVERVIEW
    # ============================================================================
    st.subheader("📊 Sync Status Overview")

    st.info("💡 **Note**: Sync execution from UI will be available in Phase 5. For now, use the CLI: `fin-cli sync all`")

    # Get all accounts and their last sync info
    accounts = session.query(Account).all()

    if not accounts or len(accounts) == 0:
        st.warning("⚠️ No accounts configured. Please sync your financial data using the CLI first.")
        st.code("fin-cli sync all", language="bash")
        st.stop()

    # Group accounts by institution
    institutions = {}
    for account in accounts:
        institution = account.institution
        if institution not in institutions:
            institutions[institution] = []
        institutions[institution].append(account)

    # Display status cards by institution
    st.markdown("### Status by Institution")

    cols_per_row = 3
    institutions_list = list(institutions.items())

    for i in range(0, len(institutions_list), cols_per_row):
        cols = st.columns(cols_per_row)

        for j, (institution, accounts_list) in enumerate(institutions_list[i:i+cols_per_row]):
            with cols[j]:
                with st.container():
                    # Institution header
                    st.markdown(f"**🏦 {institution}**")

                    # Get stats for this institution
                    account_ids = [acc.id for acc in accounts_list]

                    # Last sync date (approximate from latest balance date)
                    last_sync = session.query(func.max(Balance.balance_date)).filter(
                        Balance.account_id.in_(account_ids)
                    ).scalar()

                    # Transaction count
                    txn_count = session.query(func.count(Transaction.id)).filter(
                        Transaction.account_id.in_(account_ids)
                    ).scalar() or 0

                    # Latest transaction date
                    latest_txn_date = session.query(func.max(Transaction.transaction_date)).filter(
                        Transaction.account_id.in_(account_ids)
                    ).scalar()

                    # Status indicator
                    if last_sync:
                        days_since_sync = (date.today() - last_sync).days
                        if days_since_sync <= 1:
                            status = "✅ Up to date"
                            status_color = "green"
                        elif days_since_sync <= 7:
                            status = "⚠️ May need sync"
                            status_color = "orange"
                        else:
                            status = "❌ Needs sync"
                            status_color = "red"
                    else:
                        status = "❓ Never synced"
                        status_color = "gray"

                    st.markdown(f"**Status:** {status}")

                    # Metrics
                    st.caption(f"Accounts: {len(accounts_list)}")
                    st.caption(f"Transactions: {format_number(txn_count)}")

                    if last_sync:
                        st.caption(f"Last sync: {format_datetime(last_sync, '%Y-%m-%d')}")
                    else:
                        st.caption("Last sync: Never")

                    if latest_txn_date:
                        st.caption(f"Latest txn: {format_datetime(latest_txn_date, '%Y-%m-%d')}")

                    # Sync button (disabled for now)
                    st.button(
                        f"🔄 Sync {institution}",
                        key=f"sync_{institution}",
                        disabled=True,
                        use_container_width=True,
                        help="Sync execution will be available in Phase 5"
                    )

                    st.markdown("---")

    st.markdown("---")

    # ============================================================================
    # ACCOUNT-LEVEL STATUS
    # ============================================================================
    st.subheader("📋 Detailed Account Status")

    account_status_data = []
    for account in accounts:
        # Last balance date
        last_balance = session.query(Balance).filter(
            Balance.account_id == account.id
        ).order_by(desc(Balance.balance_date)).first()

        # Transaction count
        txn_count = session.query(func.count(Transaction.id)).filter(
            Transaction.account_id == account.id
        ).scalar() or 0

        # Latest transaction
        latest_txn = session.query(Transaction).filter(
            Transaction.account_id == account.id
        ).order_by(desc(Transaction.transaction_date)).first()

        # Pending transactions
        pending_count = session.query(func.count(Transaction.id)).filter(
            and_(
                Transaction.account_id == account.id,
                Transaction.status == 'pending'
            )
        ).scalar() or 0

        # Determine status
        if last_balance:
            days_since_sync = (date.today() - last_balance.balance_date).days
            if days_since_sync <= 1:
                status = "✅"
            elif days_since_sync <= 7:
                status = "⚠️"
            else:
                status = "❌"
        else:
            status = "❓"

        account_status_data.append({
            'Status': status,
            'Institution': account.institution,
            'Type': account.account_type or 'N/A',
            'Account Number': account.account_number or 'N/A',
            'Last Sync': format_datetime(last_balance.balance_date, '%Y-%m-%d') if last_balance else 'Never',
            'Transactions': format_number(txn_count),
            'Latest Transaction': format_datetime(latest_txn.transaction_date, '%Y-%m-%d') if latest_txn else 'N/A',
            'Pending': pending_count,
            'Balance': format_currency(last_balance.total_amount) if last_balance else 'N/A'
        })

    df_account_status = pd.DataFrame(account_status_data)

    st.dataframe(
        df_account_status,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    # ============================================================================
    # SYNC HISTORY (Simulated from transaction/balance updates)
    # ============================================================================
    st.subheader("📜 Recent Activity")

    st.info("💡 **Note**: Dedicated sync history tracking will be added in Phase 5. Showing recent data updates below.")

    # Get recent balance updates (proxy for sync events)
    recent_balances = session.query(
        Balance.balance_date,
        Account.institution,
        Account.account_type,
        Balance.total_amount
    ).join(
        Account,
        Account.id == Balance.account_id
    ).order_by(desc(Balance.balance_date)).limit(20).all()

    if recent_balances:
        st.markdown("**Recent Balance Updates**")

        balance_history_data = []
        for balance_date, institution, account_type, total_amount in recent_balances:
            balance_history_data.append({
                'Date': format_datetime(balance_date, '%Y-%m-%d'),
                'Institution': institution,
                'Account Type': account_type or 'N/A',
                'Balance': format_currency(total_amount),
                'Status': '✅ Updated'
            })

        df_balance_history = pd.DataFrame(balance_history_data)
        st.dataframe(df_balance_history, use_container_width=True, hide_index=True)
    else:
        st.info("No recent balance updates found")

    st.markdown("---")

    # Get recent transactions (last 24 hours)
    yesterday = datetime.now() - timedelta(days=1)
    recent_transactions = session.query(
        func.count(Transaction.id),
        Account.institution
    ).join(
        Account,
        Account.id == Transaction.account_id
    ).filter(
        Transaction.created_at >= yesterday
    ).group_by(Account.institution).all()

    if recent_transactions:
        st.markdown("**Recent Transaction Additions (Last 24 Hours)**")

        recent_txn_data = []
        for txn_count, institution in recent_transactions:
            recent_txn_data.append({
                'Institution': institution,
                'New Transactions': format_number(txn_count),
                'Status': '✅ Added'
            })

        df_recent_txn = pd.DataFrame(recent_txn_data)
        st.dataframe(df_recent_txn, use_container_width=True, hide_index=True)

    # ============================================================================
    # SYNC OPTIONS (Preview - will be functional in Phase 5)
    # ============================================================================
    st.markdown("---")
    st.subheader("⚙️ Sync Options (Preview)")

    st.info("These options will be functional in Phase 5 when sync execution is enabled")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**General Options**")
        headless_mode = st.checkbox("Headless Mode", value=True, disabled=True)
        st.caption("Run browser in background without UI")

    with col2:
        st.markdown("**Date Range**")
        months_back = st.slider("Months Back", min_value=1, max_value=24, value=3, disabled=True)
        months_forward = st.slider("Months Forward", min_value=0, max_value=6, value=1, disabled=True)

    st.markdown("**Select Institutions to Sync**")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Brokers**")
        st.checkbox("Excellence", disabled=True)
        st.checkbox("Meitav", disabled=True)

    with col2:
        st.markdown("**Pensions**")
        st.checkbox("Migdal", disabled=True)
        st.checkbox("Phoenix", disabled=True)

    with col3:
        st.markdown("**Credit Cards**")
        st.checkbox("CAL", disabled=True)
        st.checkbox("Max", disabled=True)
        st.checkbox("Isracard", disabled=True)

    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.button(
            "🔄 Sync Selected",
            type="primary",
            disabled=True,
            use_container_width=True,
            help="Will be enabled in Phase 5"
        )

    with col2:
        st.button(
            "🔄 Sync All",
            disabled=True,
            use_container_width=True,
            help="Will be enabled in Phase 5"
        )

    # ============================================================================
    # CLI INSTRUCTIONS
    # ============================================================================
    st.markdown("---")
    st.subheader("💻 CLI Sync Instructions")

    st.markdown("""
    For now, please use the CLI to sync your financial data:

    **Sync all institutions:**
    ```bash
    fin-cli sync all
    ```

    **Sync specific institution:**
    ```bash
    fin-cli sync cal
    fin-cli sync excellence
    fin-cli sync migdal
    ```

    **Sync with options:**
    ```bash
    fin-cli sync cal --headless --months-back 6 --months-forward 1
    ```

    **Sync specific account (for multi-account support):**
    ```bash
    fin-cli sync cal --account 0          # First account
    fin-cli sync cal --account personal   # Account labeled "personal"
    ```

    **View available sync commands:**
    ```bash
    fin-cli sync --help
    ```
    """)

    # ============================================================================
    # SUMMARY STATISTICS
    # ============================================================================
    st.markdown("---")
    st.subheader("📊 Summary")

    col1, col2, col3, col4 = st.columns(4)

    total_accounts = len(accounts)
    total_transactions = session.query(func.count(Transaction.id)).scalar() or 0

    # Accounts synced today
    today = date.today()
    synced_today = session.query(func.count(func.distinct(Balance.account_id))).filter(
        Balance.balance_date == today
    ).scalar() or 0

    # Pending transactions
    pending_transactions = session.query(func.count(Transaction.id)).filter(
        Transaction.status == 'pending'
    ).scalar() or 0

    with col1:
        st.metric("Total Accounts", format_number(total_accounts))

    with col2:
        st.metric("Total Transactions", format_number(total_transactions))

    with col3:
        st.metric("Synced Today", format_number(synced_today))

    with col4:
        st.metric("Pending Transactions", format_number(pending_transactions))

except Exception as e:
    st.error(f"Error loading sync status: {str(e)}")
    st.exception(e)
    st.info("💡 Make sure the database is initialized with `fin-cli init`")
