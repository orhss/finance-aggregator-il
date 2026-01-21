"""
Sync Management Page - Trigger sync and view sync status
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import sys
from pathlib import Path
import subprocess
import threading
import queue
import time

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from streamlit_app.utils.session import init_session_state
from streamlit_app.utils.formatters import format_currency, format_number, format_datetime
from streamlit_app.components.sidebar import render_minimal_sidebar
from streamlit_app.components.theme import apply_theme, render_theme_switcher

# Page config
st.set_page_config(
    page_title="Sync - Financial Aggregator",
    page_icon="🔄",
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
st.title("🔄 Sync Management")
st.markdown("View sync status and synchronization history")

# Security Notice - Build Trust
st.info("""
🔒 **Your Data is Secure**
- **Encrypted Credentials**: All credentials are encrypted and never stored in plain text
- **Read-Only Access**: We only read your financial data, never perform transactions
- **Local Storage**: All data stays on your device - no cloud uploads or external sharing
- **Secure Connections**: All connections use HTTPS/TLS encryption
""")

st.markdown("---")

# Get database session
try:
    from db.database import get_session
    from db.models import Account, Transaction, Balance
    from sqlalchemy import func, and_, desc

    session = get_session()

    # Initialize sync state
    if 'sync_running' not in st.session_state:
        st.session_state.sync_running = False
    if 'sync_output' not in st.session_state:
        st.session_state.sync_output = []
    if 'sync_status' not in st.session_state:
        st.session_state.sync_status = None
    if 'sync_thread' not in st.session_state:
        st.session_state.sync_thread = None
    if 'sync_institution' not in st.session_state:
        st.session_state.sync_institution = None
    if 'sync_queue' not in st.session_state:
        st.session_state.sync_queue = queue.Queue()
    if 'sync_start_time' not in st.session_state:
        st.session_state.sync_start_time = None

    # ============================================================================
    # HELPER FUNCTIONS
    # ============================================================================

    # Institution name mapping (used throughout the page)
    INSTITUTION_MAP = {
        'excellence': 'excellence',
        'Excellence': 'excellence',
        'meitav': 'meitav',
        'Meitav': 'meitav',
        'migdal': 'migdal',
        'Migdal': 'migdal',
        'phoenix': 'phoenix',
        'Phoenix': 'phoenix',
        'cal': 'cal',
        'CAL': 'cal',
        'max': 'max',
        'Max': 'max',
        'isracard': 'isracard',
        'Isracard': 'isracard',
    }

    def get_status_indicator(last_sync_date: date) -> tuple[str, str]:
        """
        Determine sync status based on last sync date.
        Returns (emoji, text) tuple.

        Credit cards: 1 day = good, 7 days = warning
        Others: 7 days = good, 14 days = warning
        """
        if not last_sync_date:
            return "❓", "Never synced"

        days_since_sync = (date.today() - last_sync_date).days
        if days_since_sync <= 7:
            return "✅", "Up to date"
        elif days_since_sync <= 14:
            return "⚠️", "May need sync"
        else:
            return "❌", "Needs sync"

    def render_sync_status_message(status: str, output_lines: list[str], clear_key: str):
        """Render sync status messages with consistent format."""
        status_config = {
            'success': {
                'message': "✅ Sync completed successfully!",
                'type': 'success',
                'expander_title': "📋 View Sync Log",
                'expander_expanded': False
            },
            'failed': {
                'message': "❌ Sync failed. Please check the output below for details.",
                'type': 'error',
                'expander_title': "Sync Output:",
                'expander_expanded': True
            },
            'error': {
                'message': "❌ Sync error occurred. Please see details below.",
                'type': 'error',
                'expander_title': "Error Details:",
                'expander_expanded': True
            }
        }

        config = status_config.get(status)
        if not config:
            return

        # Display status message
        if config['type'] == 'success':
            st.success(config['message'])
        else:
            st.error(config['message'])

        # Display output
        if output_lines:
            if config['expander_expanded']:
                st.markdown(f"**{config['expander_title']}**")
                with st.container():
                    for line in output_lines:
                        if line.strip():
                            st.text(line.strip())
            else:
                with st.expander(config['expander_title'], expanded=False):
                    for line in output_lines:
                        st.text(line.strip())
        elif status != 'success':
            st.warning("No output captured. The sync process may have failed to start.")

        # Clear button
        if st.button("Clear Status", key=clear_key):
            st.session_state.sync_status = None
            st.session_state.sync_output = []
            st.rerun()

    def render_institution_card(
        institution: str,
        accounts_list: list,
        is_credit_card: bool,
        session
    ):
        """Render a status card for an institution."""
        with st.container():
            # Institution header
            icon = "💳" if is_credit_card else "🏦"
            st.markdown(f"**{icon} {institution}**")

            # Get stats for this institution
            account_ids = [acc.id for acc in accounts_list]

            # Calculate last sync date based on account type
            if is_credit_card:
                # For credit cards, use latest transaction's created_at
                last_sync_datetime = session.query(func.max(Transaction.created_at)).filter(
                    Transaction.account_id.in_(account_ids)
                ).scalar()
                last_sync = last_sync_datetime.date() if last_sync_datetime else None

                # Transaction count
                txn_count = session.query(func.count(Transaction.id)).filter(
                    Transaction.account_id.in_(account_ids)
                ).scalar() or 0

                # Latest transaction date
                latest_txn_date = session.query(func.max(Transaction.transaction_date)).filter(
                    Transaction.account_id.in_(account_ids)
                ).scalar()
            else:
                # For brokers/pensions, use balance date
                last_sync = session.query(func.max(Balance.balance_date)).filter(
                    Balance.account_id.in_(account_ids)
                ).scalar()

                # Get latest balance amount
                latest_balance = session.query(Balance).filter(
                    Balance.account_id.in_(account_ids)
                ).order_by(desc(Balance.balance_date)).first()

            # Status indicator
            emoji, status_text = get_status_indicator(last_sync)
            st.markdown(f"**Status:** {emoji} {status_text}")

            # Metrics
            st.caption(f"Accounts: {len(accounts_list)}")

            if is_credit_card:
                st.caption(f"Transactions: {format_number(txn_count)}")
                if last_sync:
                    st.caption(f"Last sync: {format_datetime(last_sync, '%Y-%m-%d')}")
                else:
                    st.caption("Last sync: Never")
                if latest_txn_date:
                    st.caption(f"Latest txn: {format_datetime(latest_txn_date, '%Y-%m-%d')}")
                else:
                    st.caption("Latest txn: N/A")
            else:
                if latest_balance:
                    st.caption(f"Balance: {format_currency(latest_balance.total_amount)}")
                else:
                    st.caption("Balance: N/A")
                if last_sync:
                    st.caption(f"Last sync: {format_datetime(last_sync, '%Y-%m-%d')}")
                else:
                    st.caption("Last sync: Never")

            # Sync button
            if st.button(
                f"🔄 Sync {institution}",
                key=f"sync_{institution}",
                disabled=st.session_state.sync_running,
                use_container_width=True,
                help="Click to sync this institution"
            ):
                sync_target = INSTITUTION_MAP.get(institution, institution.lower())
                st.toast(f"🔄 Starting sync for {institution}...", icon="🔄")
                start_sync(sync_target)
                st.rerun()

            st.markdown("---")

    # Helper function to run sync command in background thread
    def run_sync_in_thread(institution: str = "all", headless: bool = True, months_back: int = 3, months_forward: int = 1, output_queue: queue.Queue = None):
        """Run sync command in subprocess and capture output"""
        # Build command
        cmd = ["fin-cli", "sync", institution]
        if headless:
            cmd.append("--headless")

        # Date range options are only supported by credit card scrapers
        credit_card_institutions = ['cal', 'max', 'isracard']
        if institution in credit_card_institutions or institution == 'all':
            if months_back:
                cmd.extend(["--months-back", str(months_back)])
            if months_forward:
                cmd.extend(["--months-forward", str(months_forward)])

        output_lines = []
        try:
            # Run command and capture output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Read output line by line
            for line in process.stdout:
                output_lines.append(line)
                if output_queue:
                    output_queue.put(('output', line))

            # Wait for completion
            return_code = process.wait()

            # Send final status through queue
            if return_code == 0:
                if output_queue:
                    output_queue.put(('status', 'success'))
            else:
                if output_queue:
                    output_queue.put(('status', 'failed'))

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            output_lines.append(error_msg)
            if output_queue:
                output_queue.put(('output', error_msg))
                output_queue.put(('status', 'error'))
        finally:
            if output_queue:
                output_queue.put(('done', output_lines))

    def start_sync(institution: str = "all", headless: bool = True, months_back: int = 3, months_forward: int = 1):
        """Start sync in background thread"""
        st.session_state.sync_running = True
        st.session_state.sync_output = []
        st.session_state.sync_status = "running"
        st.session_state.sync_institution = institution
        st.session_state.sync_start_time = time.time()

        # Create new queue for this sync
        st.session_state.sync_queue = queue.Queue()

        # Start background thread
        thread = threading.Thread(
            target=run_sync_in_thread,
            args=(institution, headless, months_back, months_forward, st.session_state.sync_queue),
            daemon=True
        )
        thread.start()
        st.session_state.sync_thread = thread

    # Process queue messages if sync is running
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

    # ============================================================================
    # SYNC EXECUTION SECTION
    # ============================================================================

    # Display sync status messages using helper function
    if st.session_state.sync_status in ["success", "failed", "error"]:
        render_sync_status_message(
            st.session_state.sync_status,
            st.session_state.sync_output,
            f"clear_{st.session_state.sync_status}"
        )

    if st.session_state.sync_running:
        # Show prominent progress indicator with institution info
        institution_name = st.session_state.sync_institution.upper() if st.session_state.sync_institution else "ALL"

        # Calculate elapsed time
        elapsed_time = int(time.time() - st.session_state.sync_start_time) if st.session_state.sync_start_time else 0
        elapsed_minutes = elapsed_time // 60
        elapsed_seconds = elapsed_time % 60

        # Progress indicator
        progress_col1, progress_col2 = st.columns([3, 1])
        with progress_col1:
            st.info(f"🔄 **Syncing {institution_name}** - Please wait while we fetch your latest financial data...")
        with progress_col2:
            st.metric("Elapsed Time", f"{elapsed_minutes:02d}:{elapsed_seconds:02d}")

        # Show progress bar (indeterminate)
        st.progress(0.5)

        # Display simplified status or detailed output
        if st.session_state.sync_output and len(st.session_state.sync_output) > 0:
            # Show last few lines as preview
            recent_output = st.session_state.sync_output[-3:]
            for line in recent_output:
                if line.strip():
                    st.caption(f"› {line.strip()}")

            # Show full output in collapsible section
            with st.expander("📋 View Detailed Sync Log", expanded=False):
                for line in st.session_state.sync_output:
                    st.text(line.strip())

        # Show manual refresh button and auto-refresh timer
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🔄 Refresh Now", use_container_width=True):
                st.rerun()
        with col2:
            st.caption("ℹ️ Auto-refreshing every 3 seconds...")

        # Auto-refresh every 3 seconds while sync is running
        time.sleep(3)
        st.rerun()

    # ============================================================================
    # SYNC STATUS OVERVIEW
    # ============================================================================
    st.subheader("📊 Sync Status Overview")

    # Get all accounts and their last sync info
    accounts = session.query(Account).all()

    if not accounts or len(accounts) == 0:
        st.warning("⚠️ No accounts configured. Please sync your financial data using the CLI first.")
        st.code("fin-cli sync all", language="bash")
        st.stop()

    # Group accounts by institution and type
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

    # Display status cards by institution - separated by type
    cols_per_row = 3

    # Brokers & Pensions Section
    if brokers_pensions:
        st.markdown("### 📈 Brokers & Pension Funds")

        institutions_list = list(brokers_pensions.items())

        for i in range(0, len(institutions_list), cols_per_row):
            cols = st.columns(cols_per_row)

            for j, (institution, accounts_list) in enumerate(institutions_list[i:i+cols_per_row]):
                with cols[j]:
                    render_institution_card(institution, accounts_list, is_credit_card=False, session=session)

        st.markdown("")  # Add spacing between sections

    # Credit Cards Section
    if credit_cards:
        st.markdown("### 💳 Credit Cards")

        institutions_list = list(credit_cards.items())

        for i in range(0, len(institutions_list), cols_per_row):
            cols = st.columns(cols_per_row)

            for j, (institution, accounts_list) in enumerate(institutions_list[i:i+cols_per_row]):
                with cols[j]:
                    render_institution_card(institution, accounts_list, is_credit_card=True, session=session)

    st.markdown("---")

    # ============================================================================
    # ACCOUNT-LEVEL STATUS
    # ============================================================================
    st.subheader("📋 Detailed Account Status")

    account_status_data = []
    for account in accounts:
        # Determine last sync date based on account type
        if account.account_type == 'credit_card':
            # For credit cards, use latest transaction's created_at
            last_txn_created = session.query(func.max(Transaction.created_at)).filter(
                Transaction.account_id == account.id
            ).scalar()
            last_sync = last_txn_created.date() if last_txn_created else None
            balance_amount = None  # Credit cards don't have balance
        else:
            # For brokers/pensions, use balance date
            last_balance = session.query(Balance).filter(
                Balance.account_id == account.id
            ).order_by(desc(Balance.balance_date)).first()
            last_sync = last_balance.balance_date if last_balance else None
            balance_amount = last_balance.total_amount if last_balance else None

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
        if last_sync:
            days_since_sync = (date.today() - last_sync).days
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
            'Last Sync': format_datetime(last_sync, '%Y-%m-%d') if last_sync else 'Never',
            'Transactions': format_number(txn_count),
            'Latest Transaction': format_datetime(latest_txn.transaction_date, '%Y-%m-%d') if latest_txn else 'N/A',
            'Pending': pending_count,
            'Balance': format_currency(balance_amount) if balance_amount else 'N/A'
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
    # SYNC OPTIONS
    # ============================================================================
    st.markdown("---")
    st.subheader("⚙️ Sync Options")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**General Options**")
        headless_mode = st.checkbox(
            "Headless Mode",
            value=True,
            disabled=st.session_state.sync_running,
            help="Run browser in background without UI"
        )

    with col2:
        st.markdown("**Date Range**")
        st.caption("ℹ️ Only applies to credit card syncs")
        months_back = st.slider(
            "Months Back",
            min_value=1,
            max_value=24,
            value=3,
            disabled=st.session_state.sync_running,
            help="Number of months of historical data to fetch (credit cards only)"
        )
        months_forward = st.slider(
            "Months Forward",
            min_value=0,
            max_value=6,
            value=1,
            disabled=st.session_state.sync_running,
            help="Number of future months to fetch (credit cards only)"
        )

    st.markdown("**Select Institutions to Sync**")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Brokers**")
        sync_excellence = st.checkbox("Excellence", disabled=st.session_state.sync_running, key="sync_opt_excellence")
        sync_meitav = st.checkbox("Meitav", disabled=st.session_state.sync_running, key="sync_opt_meitav")

    with col2:
        st.markdown("**Pensions**")
        sync_migdal = st.checkbox("Migdal", disabled=st.session_state.sync_running, key="sync_opt_migdal")
        sync_phoenix = st.checkbox("Phoenix", disabled=st.session_state.sync_running, key="sync_opt_phoenix")

    with col3:
        st.markdown("**Credit Cards**")
        sync_cal = st.checkbox("CAL", disabled=st.session_state.sync_running, key="sync_opt_cal")
        sync_max = st.checkbox("Max", disabled=st.session_state.sync_running, key="sync_opt_max")
        sync_isracard = st.checkbox("Isracard", disabled=st.session_state.sync_running, key="sync_opt_isracard")

    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button(
            "🔄 Sync Selected",
            type="primary",
            disabled=st.session_state.sync_running,
            use_container_width=True,
            help="Sync only selected institutions"
        ):
            # Collect selected institutions using a clean mapping
            institution_selections = {
                'excellence': sync_excellence,
                'meitav': sync_meitav,
                'migdal': sync_migdal,
                'phoenix': sync_phoenix,
                'cal': sync_cal,
                'max': sync_max,
                'isracard': sync_isracard
            }
            selected = [inst for inst, is_selected in institution_selections.items() if is_selected]

            if selected:
                st.toast(f"🔄 Starting sync for {len(selected)} institutions...", icon="🔄")
                # Note: Currently syncs first institution only
                # TODO: Implement sequential sync for multiple institutions
                start_sync(selected[0], headless_mode, months_back, months_forward)
                st.rerun()
            else:
                st.toast("Please select at least one institution", icon="⚠️")

    with col2:
        if st.button(
            "🔄 Sync All",
            disabled=st.session_state.sync_running,
            use_container_width=True,
            help="Sync all configured institutions"
        ):
            st.toast("🔄 Starting sync for all institutions...", icon="🔄")
            start_sync("all", headless_mode, months_back, months_forward)
            st.rerun()

    # ============================================================================
    # CLI INSTRUCTIONS
    # ============================================================================
    st.markdown("---")
    st.subheader("💻 CLI Sync Instructions")

    st.info("💡 You can now sync from the UI above, or use the CLI directly:")

    st.markdown("""

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
