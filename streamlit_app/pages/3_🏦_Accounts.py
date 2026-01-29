"""
Accounts Management Page - View accounts and sync status

Combines account overview with sync functionality:
- Tab 1: Accounts overview with balances and details
- Tab 2: Sync status and trigger sync operations
"""

import streamlit as st
import pandas as pd
from datetime import timedelta, date, datetime
import sys
import os
from pathlib import Path
import subprocess
import threading
import queue
import time

# Page config MUST be first
st.set_page_config(
    page_title="Accounts - Financial Aggregator",
    page_icon="🏦",
    layout="wide"
)

# Third-party imports
from sqlalchemy import func, and_, desc

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Session imports
from streamlit_app.utils.session import init_session_state, format_amount_private
from streamlit_app.auth import check_authentication

# Initialize session state
init_session_state()

# Check authentication (if enabled)
if not check_authentication():
    st.stop()

from db.database import get_session
from db.models import Account, Transaction, Balance
from services.analytics_service import AnalyticsService

from streamlit_app.utils.formatters import format_number, format_datetime, format_account_number
from streamlit_app.components.sidebar import render_minimal_sidebar
from streamlit_app.components.charts import balance_history
from streamlit_app.components.theme import apply_theme
from streamlit_app.components.cards import render_metric_row
from streamlit_app.components.mobile_ui import mobile_quick_settings

# Apply theme
theme = apply_theme()

# Mobile quick settings (for pages without dedicated mobile views)
mobile_quick_settings()

# Render sidebar
render_minimal_sidebar()

# Page header with new design
st.markdown("""
<div class="page-header">
    <h1>🏦 Accounts & Sync</h1>
    <p class="subtitle">Manage accounts and synchronize financial data</p>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# SYNC HELPER FUNCTIONS (moved from Sync page)
# ============================================================================

INSTITUTION_MAP = {
    'excellence': 'excellence', 'Excellence': 'excellence',
    'meitav': 'meitav', 'Meitav': 'meitav',
    'migdal': 'migdal', 'Migdal': 'migdal',
    'phoenix': 'phoenix', 'Phoenix': 'phoenix',
    'cal': 'cal', 'CAL': 'cal',
    'max': 'max', 'Max': 'max',
    'isracard': 'isracard', 'Isracard': 'isracard',
}


def get_status_indicator(last_sync_date: date) -> tuple:
    """Determine sync status based on last sync date."""
    if not last_sync_date:
        return "❓", "Never synced"
    days_since_sync = (date.today() - last_sync_date).days
    if days_since_sync <= 7:
        return "✅", "Up to date"
    elif days_since_sync <= 14:
        return "⚠️", "May need sync"
    else:
        return "❌", "Needs sync"


def run_sync_in_thread(institution: str, headless: bool, months_back: int, months_forward: int, output_queue: queue.Queue):
    """Run sync command in subprocess and capture output."""
    cmd = [sys.executable, "-m", "cli.main", "sync", institution]
    if headless:
        cmd.append("--headless")

    credit_card_institutions = ['cal', 'max', 'isracard']
    if institution in credit_card_institutions or institution == 'all':
        if months_back:
            cmd.extend(["--months-back", str(months_back)])
        if months_forward:
            cmd.extend(["--months-forward", str(months_forward)])

    output_lines = []
    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, universal_newlines=True,
            cwd=str(project_root), env=os.environ.copy()
        )

        for line in process.stdout:
            output_lines.append(line)
            if output_queue:
                output_queue.put(('output', line))

        return_code = process.wait()
        if output_queue:
            output_queue.put(('status', 'success' if return_code == 0 else 'failed'))

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        output_lines.append(error_msg)
        if output_queue:
            output_queue.put(('output', error_msg))
            output_queue.put(('status', 'error'))
    finally:
        if output_queue:
            output_queue.put(('done', output_lines))


def start_sync(institution: str, headless: bool = True, months_back: int = 3, months_forward: int = 1):
    """Start sync in background thread."""
    st.session_state.sync_running = True
    st.session_state.sync_output = []
    st.session_state.sync_status = "running"
    st.session_state.sync_institution = institution
    st.session_state.sync_start_time = time.time()
    st.session_state.sync_queue = queue.Queue()

    thread = threading.Thread(
        target=run_sync_in_thread,
        args=(institution, headless, months_back, months_forward, st.session_state.sync_queue),
        daemon=True
    )
    thread.start()
    st.session_state.sync_thread = thread


# Initialize sync state
for key, default in [
    ('sync_running', False), ('sync_output', []), ('sync_status', None),
    ('sync_thread', None), ('sync_institution', None),
    ('sync_queue', queue.Queue()), ('sync_start_time', None)
]:
    if key not in st.session_state:
        st.session_state[key] = default

# Get database session
try:
    session = get_session()
    account_count = session.query(func.count(Account.id)).scalar()

    if not account_count or account_count == 0:
        st.warning("No account data available. Please sync your financial data first.")

        # Show sync options for new users
        st.info("""
        🔒 **Your Data is Secure**
        - Encrypted credentials stored locally
        - Read-only access to financial data
        - All data stays on your device
        """)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Sync All Accounts", type="primary", use_container_width=True):
                start_sync("all")
                st.rerun()
        with col2:
            st.caption("Or use CLI: `fin-cli sync all`")

        st.stop()

    # ========================================================================
    # MAIN TABS
    # ========================================================================
    tab_accounts, tab_sync = st.tabs(["💰 Accounts", "🔄 Sync"])

    # ========================================================================
    # TAB 1: ACCOUNTS
    # ========================================================================
    with tab_accounts:
        analytics = AnalyticsService(session)
        latest_balances_data = analytics.get_latest_balances()

        # Get accounts without balances
        accounts_with_balances_ids = [acc.id for acc, _ in latest_balances_data]
        accounts_without_balances = session.query(Account).filter(
            ~Account.id.in_(accounts_with_balances_ids) if accounts_with_balances_ids else True
        ).all()

        # Combine into unified format
        accounts_with_balance = []
        for account, balance in latest_balances_data:
            accounts_with_balance.append((account, balance.total_amount, balance.balance_date))
        for account in accounts_without_balances:
            accounts_with_balance.append((account, None, None))

        # Build enriched account data
        enriched_accounts = []
        for account, balance, balance_date in accounts_with_balance:
            txn_count = session.query(func.count(Transaction.id)).filter(
                Transaction.account_id == account.id
            ).scalar() or 0

            last_txn = session.query(func.max(Transaction.transaction_date)).filter(
                Transaction.account_id == account.id
            ).scalar()

            is_credit_card = account.account_type == "credit_card"
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
        active = sum([1 for items in account_types.values() for item in items if item['balance'] and item['balance'] > 0])

        # Hero card showing total portfolio value
        st.markdown(f'''<div class="hero-card" style="background: linear-gradient(135deg, #10b981 0%, #34d399 100%);">
            <div class="hero-label">Total Portfolio Value</div>
            <div class="hero-amount">{format_amount_private(total_balance)}</div>
            <div class="hero-sync">{total_accounts} accounts · {active} active</div>
        </div>''', unsafe_allow_html=True)

        st.markdown("")  # Spacing

        # Account Details View
        if 'selected_account_id' in st.session_state and st.session_state.selected_account_id:
            account_id = st.session_state.selected_account_id
            account = session.query(Account).filter(Account.id == account_id).first()

            if account:
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.markdown(f"### {account.institution}")
                    st.markdown(f"**Type:** {account.account_type or 'N/A'}")
                    if account.account_number:
                        masked = st.session_state.get('mask_account_numbers', True)
                        st.markdown(f"**Account:** {format_account_number(account.account_number, masked=masked)}")

                with col2:
                    if st.button("❌ Close Details", use_container_width=True):
                        del st.session_state.selected_account_id
                        st.rerun()

                latest_balance = account.latest_balance
                if latest_balance:
                    st.markdown("")  # Spacing
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Amount", format_amount_private(latest_balance.total_amount))
                    with col2:
                        if latest_balance.available:
                            st.metric("Available", format_amount_private(latest_balance.available))
                    with col3:
                        st.metric("As of", format_datetime(latest_balance.balance_date, '%Y-%m-%d'))

                # Balance History Chart
                st.markdown("")  # Spacing
                st.markdown("**Balance History (Last 3 Months)**")

                three_months_ago = date.today() - timedelta(days=90)
                balance_history_query = session.query(
                    Balance.balance_date, Balance.total_amount
                ).filter(
                    and_(Balance.account_id == account_id, Balance.balance_date >= three_months_ago)
                ).order_by(Balance.balance_date).all()

                if balance_history_query:
                    df_balance_history = pd.DataFrame([
                        {'date': bd, 'balance': ta} for bd, ta in balance_history_query
                    ])
                    fig = balance_history(df_balance_history, title=f"Balance History - {account.institution}")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No balance history available")

                st.markdown("")  # Spacing

        # Accounts by Type (Card View)
        for acc_type, accounts_list in sorted(account_types.items()):
            st.subheader(f"📁 {acc_type}")

            cols = st.columns(3)
            for idx, item in enumerate(accounts_list):
                account = item['account']
                balance = item['balance']
                is_credit_card = item['is_credit_card']
                status_icon = item['status_icon']
                txn_count = item['txn_count']

                with cols[idx % 3]:
                    # Account number formatting
                    account_info = ""
                    if account.account_number:
                        masked = st.session_state.get('mask_account_numbers', True)
                        account_info = format_account_number(account.account_number, masked=masked)

                    # Balance display (hide for credit cards)
                    balance_display = format_amount_private(balance) if not is_credit_card and balance is not None else ""

                    # Subtitle with transaction count and account number
                    subtitle_parts = [f"{txn_count} transactions"]
                    if account_info:
                        subtitle_parts.append(account_info)
                    subtitle = " · ".join(subtitle_parts)

                    # Render account card using CSS from main.css
                    st.markdown(
                        f'<div class="account-card">'
                        f'<div class="icon">🏦</div>'
                        f'<div class="info">'
                        f'<div class="name">{status_icon} {account.institution}</div>'
                        f'<div class="subtitle">{subtitle}</div>'
                        f'</div>'
                        f'<div class="balance">{balance_display}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

                    if st.button("View Details", key=f"view_{account.id}", use_container_width=True):
                        st.session_state.selected_account_id = account.id
                        st.rerun()

    # ========================================================================
    # TAB 2: SYNC
    # ========================================================================
    with tab_sync:
        # Security Notice
        st.markdown('''
        <div class="insight-banner neutral">
            <span class="insight-icon">🔒</span>
            <span class="insight-message">
                <strong>Your Data is Secure</strong> · Encrypted credentials stored locally · Read-only access · All data stays on your device
            </span>
        </div>
        ''', unsafe_allow_html=True)

        # Process queue messages
        if st.session_state.sync_running and st.session_state.sync_queue:
            try:
                while not st.session_state.sync_queue.empty():
                    msg_type, msg_data = st.session_state.sync_queue.get_nowait()
                    if msg_type == 'output':
                        st.session_state.sync_output.append(msg_data)
                    elif msg_type == 'status':
                        st.session_state.sync_status = msg_data
                    elif msg_type == 'done':
                        st.session_state.sync_running = False
                        st.session_state.sync_thread = None
            except queue.Empty:
                pass

        # Display sync status
        if st.session_state.sync_status in ["success", "failed", "error"]:
            if st.session_state.sync_status == "success":
                st.success("✅ Sync completed successfully!")
            else:
                st.error("❌ Sync failed. Check the output below.")

            if st.session_state.sync_output:
                with st.expander("Sync Log", expanded=st.session_state.sync_status != "success"):
                    for line in st.session_state.sync_output:
                        if line.strip():
                            st.text(line.strip())

            if st.button("Clear Status", key="clear_sync_status"):
                st.session_state.sync_status = None
                st.session_state.sync_output = []
                st.rerun()

        # Sync progress indicator
        if st.session_state.sync_running:
            institution_name = st.session_state.sync_institution.upper() if st.session_state.sync_institution else "ALL"
            elapsed = int(time.time() - st.session_state.sync_start_time) if st.session_state.sync_start_time else 0

            col1, col2 = st.columns([3, 1])
            with col1:
                st.info(f"🔄 **Syncing {institution_name}** - Please wait...")
            with col2:
                st.metric("Elapsed", f"{elapsed // 60:02d}:{elapsed % 60:02d}")

            st.progress(0.5)

            if st.session_state.sync_output:
                recent = st.session_state.sync_output[-3:]
                for line in recent:
                    if line.strip():
                        st.caption(f"› {line.strip()}")

            time.sleep(3)
            st.rerun()

        st.markdown("")  # Spacing

        # Sync Status by Institution
        st.subheader("📊 Sync Status")

        accounts = session.query(Account).all()

        # Group by institution and type
        brokers_pensions = {}
        credit_cards = {}

        for account in accounts:
            institution = account.institution
            if account.account_type == 'credit_card':
                if institution not in credit_cards:
                    credit_cards[institution] = []
                credit_cards[institution].append(account)
            else:
                if institution not in brokers_pensions:
                    brokers_pensions[institution] = []
                brokers_pensions[institution].append(account)

        # Render institution cards
        def render_sync_card(institution, accounts_list, is_credit_card):
            icon = "💳" if is_credit_card else "🏦"
            st.markdown(f"**{icon} {institution}**")

            account_ids = [acc.id for acc in accounts_list]

            if is_credit_card:
                last_sync_dt = session.query(func.max(Transaction.created_at)).filter(
                    Transaction.account_id.in_(account_ids)
                ).scalar()
                last_sync = last_sync_dt.date() if last_sync_dt else None
                txn_count = session.query(func.count(Transaction.id)).filter(
                    Transaction.account_id.in_(account_ids)
                ).scalar() or 0
            else:
                balances = [acc.latest_balance for acc in accounts_list if acc.latest_balance]
                if balances:
                    latest = max(balances, key=lambda b: b.balance_date)
                    last_sync = latest.balance_date
                else:
                    last_sync = None

            emoji, status_text = get_status_indicator(last_sync)
            st.markdown(f"**Status:** {emoji} {status_text}")
            st.caption(f"Accounts: {len(accounts_list)}")

            if is_credit_card:
                st.caption(f"Transactions: {format_number(txn_count)}")
            elif balances:
                total = sum(b.total_amount for b in balances)
                st.caption(f"Balance: {format_amount_private(total)}")

            if last_sync:
                st.caption(f"Last sync: {format_datetime(last_sync, '%Y-%m-%d')}")

            if st.button(
                f"🔄 Sync",
                key=f"sync_{institution}",
                disabled=st.session_state.sync_running,
                use_container_width=True
            ):
                sync_target = INSTITUTION_MAP.get(institution, institution.lower())
                st.toast(f"Starting sync for {institution}...", icon="🔄")
                start_sync(sync_target)
                st.rerun()

            st.markdown("")  # Spacing

        # Brokers & Pensions
        if brokers_pensions:
            st.markdown("### 📈 Brokers & Pension Funds")
            cols = st.columns(3)
            for i, (institution, accs) in enumerate(brokers_pensions.items()):
                with cols[i % 3]:
                    render_sync_card(institution, accs, is_credit_card=False)

        # Credit Cards
        if credit_cards:
            st.markdown("### 💳 Credit Cards")
            cols = st.columns(3)
            for i, (institution, accs) in enumerate(credit_cards.items()):
                with cols[i % 3]:
                    render_sync_card(institution, accs, is_credit_card=True)

        st.markdown("")  # Spacing

        # Sync Options
        st.subheader("⚙️ Sync Options")

        col1, col2 = st.columns(2)

        with col1:
            headless_mode = st.checkbox("Headless Mode", value=True, disabled=st.session_state.sync_running)

        with col2:
            st.caption("Date Range (Credit Cards only)")
            months_back = st.slider("Months Back", 1, 24, 3, disabled=st.session_state.sync_running)
            months_forward = st.slider("Months Forward", 0, 6, 1, disabled=st.session_state.sync_running)

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔄 Sync All", type="primary", disabled=st.session_state.sync_running, use_container_width=True):
                st.toast("Starting sync for all institutions...", icon="🔄")
                start_sync("all", headless_mode, months_back, months_forward)
                st.rerun()

        with col2:
            st.caption("CLI: `fin-cli sync all`")

except Exception as e:
    st.error(f"Error loading accounts: {str(e)}")
    st.exception(e)
    st.info("Make sure the database is initialized with `fin-cli init`")
