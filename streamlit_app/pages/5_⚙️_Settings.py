"""
Settings Page - Application configuration and management
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path
import shutil
import os

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from streamlit_app.utils.session import init_session_state
from streamlit_app.auth import check_authentication
from streamlit_app.utils.formatters import format_number
from streamlit_app.components.sidebar import render_minimal_sidebar
from streamlit_app.components.theme import apply_theme
from streamlit_app.components.cards import render_metric_row

# Page config
st.set_page_config(
    page_title="Settings - Financial Aggregator",
    page_icon="⚙️",
    layout="wide"
)

# Initialize session state
init_session_state()

# Check authentication (if enabled)
if not check_authentication():
    st.stop()

# Apply theme (must be called before any content)
theme = apply_theme()

# Render sidebar
render_minimal_sidebar()

# Page header with new design
st.markdown("""
<div class="page-header">
    <h1>⚙️ Settings</h1>
    <p class="subtitle">Application configuration and management</p>
</div>
""", unsafe_allow_html=True)

try:
    from db.database import get_session
    from db.models import Account, Transaction, Balance, Tag
    from config.settings import CONFIG_DIR, CREDENTIALS_FILE
    from sqlalchemy import func
    import json

    session = get_session()

    # ============================================================================
    # THEME SETTINGS (most frequently used)
    # ============================================================================
    st.subheader("🌓 Theme")

    from streamlit_app.config.theme import set_theme_mode

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Appearance**")

        current_mode = st.session_state.get('theme_mode', 'light')
        is_dark = current_mode == 'dark'

        dark_mode = st.toggle(
            "Dark Mode",
            value=is_dark,
            key="setting_dark_mode",
            help="Switch between light and dark theme"
        )

        if dark_mode != is_dark:
            new_mode = 'dark' if dark_mode else 'light'
            st.session_state.theme_mode = new_mode
            set_theme_mode(new_mode)
            st.rerun()

        st.caption("🌙 Easier on the eyes in low light")

    with col2:
        st.markdown("**Tips**")
        st.caption("On desktop, you can also toggle dark mode from the sidebar.")

    st.markdown("")  # Spacing

    # ============================================================================
    # PRIVACY SETTINGS
    # ============================================================================
    st.subheader("🔒 Privacy & Security")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Balance Visibility**")

        # Use the session state value directly - toggle writes back to session state via key
        mask_balances = st.toggle(
            "Hide All Balances",
            value=st.session_state.get('mask_balances', False),
            key="setting_mask_balances",
            help="Hide all financial amounts for privacy (shows ••••••)"
        )
        # Sync back to the main session state key used by other components
        st.session_state.mask_balances = mask_balances

        st.caption("🔒 Useful when sharing screen or in public")

    with col2:
        st.markdown("**Sensitive Data Masking**")

        # Use the session state value directly - toggle writes back to session state via key
        mask_accounts = st.toggle(
            "Mask Account Numbers",
            value=st.session_state.get('mask_account_numbers', True),
            key="setting_mask_account_numbers",
            help="Show account/card numbers as ••••1234"
        )
        # Sync back to the main session state key used by other components
        st.session_state.mask_account_numbers = mask_accounts

        st.caption("📋 Account numbers show as ••••1234")

    st.markdown("")  # Spacing

    # ============================================================================
    # DISPLAY SETTINGS
    # ============================================================================
    st.subheader("🎨 Display Settings")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Table Settings**")

        rows_per_page = st.selectbox(
            "Default Rows Per Page",
            [25, 50, 100, 200],
            index=1,
            key="rows_per_page"
        )

        st.caption("Default number of rows in tables")

    with col2:
        st.markdown("**Format Settings**")

        currency_format = st.selectbox(
            "Currency Display",
            ["₪1,234.56", "1,234.56 ₪", "1234.56"],
            key="currency_format"
        )

        date_format = st.selectbox(
            "Date Format",
            ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d %b %Y"],
            key="date_format"
        )

    st.info("💡 **Note**: Display settings are currently for preview only. Settings persistence will be added in a future update.")

    st.markdown("")  # Spacing

    # ============================================================================
    # BUDGET SETTINGS
    # ============================================================================
    st.subheader("💰 Monthly Budget")

    try:
        from services.budget_service import BudgetService
        from datetime import date

        budget_service = BudgetService(session)
        progress = budget_service.get_current_progress()
        today = date.today()
        month_name = today.strftime("%B %Y")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**Set Budget for {month_name}**")

            # Current budget value for default
            current_budget = progress['budget'] if progress['budget'] else 5000

            new_budget = st.number_input(
                "Monthly Budget (₪)",
                min_value=0.0,
                value=float(current_budget),
                step=500.0,
                key="budget_input"
            )

            if st.button("💾 Save Budget", use_container_width=True):
                budget_service.set_current_budget(new_budget)
                st.success(f"Budget set to ₪{new_budget:,.0f}")
                st.rerun()

        with col2:
            st.markdown("**Current Progress**")

            if progress['budget']:
                spent = progress['spent']
                budget = progress['budget']
                percent = progress['percent_actual']
                remaining = progress['remaining']

                # Color: green if under 80%, neutral 80-100%, red if over
                delta_color = "normal" if percent < 80 else ("inverse" if percent >= 100 else "off")
                st.metric("Spent this month", f"₪{spent:,.0f}", delta=f"{percent:.1f}% of budget", delta_color=delta_color)

                # Progress bar
                st.progress(min(percent / 100, 1.0))

                if progress['is_over_budget']:
                    st.error(f"₪{abs(remaining):,.0f} over budget")
                else:
                    st.success(f"₪{remaining:,.0f} remaining")
            else:
                st.info("No budget set. Set a monthly budget to track your spending.")

    except Exception as e:
        st.warning(f"Could not load budget settings: {str(e)}")

    st.markdown("")  # Spacing

    # ============================================================================
    # CREDENTIALS MANAGEMENT
    # ============================================================================
    st.subheader("🔐 Credentials Management")

    st.info("💡 **Security Note**: Credentials are encrypted and stored in `~/.fin/credentials.enc`. Use the CLI to manage credentials: `fin-cli config setup`")

    # Check if credentials file exists
    creds_path = CREDENTIALS_FILE
    creds_exist = creds_path.exists()

    if creds_exist:
        st.success(f"✅ Credentials file found: `{creds_path}`")

        # Get configured institutions from accounts in database
        institutions = session.query(Account.institution).distinct().all()
        institution_list = [inst[0] for inst in institutions]

        if institution_list:
            st.markdown("**Configured Institutions:**")

            inst_data = []
            for inst in institution_list:
                # Count accounts for this institution
                account_count = session.query(func.count(Account.id)).filter(
                    Account.institution == inst
                ).scalar()

                inst_data.append({
                    'Institution': inst,
                    'Accounts': account_count,
                    'Status': '✅ Configured'
                })

            df_institutions = pd.DataFrame(inst_data)
            st.dataframe(df_institutions, use_container_width=True, hide_index=True)
        else:
            st.info("No institutions configured yet. Run `fin-cli sync all` to set up your accounts.")
    else:
        st.warning(f"⚠️ No credentials file found at `{creds_path}`")
        st.markdown("Run the following command to set up credentials:")
        st.code("fin-cli config setup", language="bash")

    # Credential management buttons
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Manage Credentials (CLI)**")
        st.code("fin-cli config setup", language="bash")
        st.caption("Interactive credential setup")

    with col2:
        st.markdown("**View Configuration**")
        st.code("fin-cli config show", language="bash")
        st.caption("Show current configuration (masked)")

    st.markdown("")  # Spacing

    # ============================================================================
    # DATABASE MANAGEMENT
    # ============================================================================
    st.subheader("💾 Database Management")

    # Database info
    db_path = CONFIG_DIR / "financial_data.db"
    db_exists = db_path.exists()

    if db_exists:
        db_size = db_path.stat().st_size / (1024 * 1024)  # MB
        st.success(f"✅ Database: `{db_path}` ({db_size:.2f} MB)")

        # Database statistics
        account_count = session.query(func.count(Account.id)).scalar()
        txn_count = session.query(func.count(Transaction.id)).scalar()
        balance_count = session.query(func.count(Balance.id)).scalar()
        tag_count = session.query(func.count(Tag.id)).scalar()

        render_metric_row([
            {"value": format_number(account_count), "label": "Accounts"},
            {"value": format_number(txn_count), "label": "Transactions"},
            {"value": format_number(balance_count), "label": "Balance Records"},
            {"value": format_number(tag_count), "label": "Tags"},
        ])
    else:
        st.warning(f"⚠️ Database not found at `{db_path}`")
        st.markdown("Run the following command to initialize:")
        st.code("fin-cli init", language="bash")

    st.markdown("")  # Spacing

    # Database actions
    st.markdown("**Database Actions**")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Backup Database**")

        if st.button("📥 Create Backup", use_container_width=True):
            if db_exists:
                try:
                    backup_name = f"financial_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                    backup_path = CONFIG_DIR / backup_name

                    shutil.copy(db_path, backup_path)
                    st.success(f"✅ Backup created: `{backup_name}`")
                except Exception as e:
                    st.error(f"Error creating backup: {str(e)}")
            else:
                st.warning("No database to backup")

    with col2:
        st.markdown("**Initialize Database**")

        if st.button("🔧 Initialize DB", use_container_width=True):
            st.info("Use CLI to initialize database:")
            st.code("fin-cli init", language="bash")

    with col3:
        st.markdown("**Reset Database**")

        if st.button("⚠️ Reset DB", type="secondary", use_container_width=True):
            if st.session_state.get('confirm_reset_db'):
                st.warning("⚠️ This will delete ALL data! Use CLI to reset:")
                st.code("fin-cli init --reset", language="bash")
                st.session_state.confirm_reset_db = False
            else:
                st.session_state.confirm_reset_db = True
                st.warning("⚠️ Click again to confirm reset")

    st.markdown("")  # Spacing

    # ============================================================================
    # AUTHENTICATION SETTINGS
    # ============================================================================
    st.subheader("🔑 Authentication")

    try:
        from config.settings import (
            is_auth_enabled, set_auth_enabled, list_auth_users,
            add_auth_user, remove_auth_user
        )
        import bcrypt

        auth_enabled = is_auth_enabled()
        users = list_auth_users()
        user_count = len(users)

        # Status and toggle
        col1, col2 = st.columns([2, 1])

        with col1:
            if auth_enabled:
                st.success(f"✅ Authentication is **enabled** ({user_count} user{'s' if user_count != 1 else ''})")
            else:
                st.warning("⚠️ Authentication is **disabled** — anyone with network access can view your data")

        with col2:
            if user_count > 0:
                new_auth_state = st.toggle(
                    "Require login",
                    value=auth_enabled,
                    key="auth_toggle",
                    help="When enabled, users must log in to access the app"
                )

                if new_auth_state != auth_enabled:
                    set_auth_enabled(new_auth_state)
                    st.rerun()

        # Two columns: User list and Add user form
        col_users, col_add = st.columns(2)

        with col_users:
            st.markdown("**Configured Users**")

            if users:
                for user in users:
                    user_col1, user_col2 = st.columns([3, 1])
                    with user_col1:
                        st.markdown(f"👤 **{user['username']}** ({user['name']})")
                    with user_col2:
                        if st.button("🗑️", key=f"del_{user['username']}", help=f"Remove {user['username']}"):
                            st.session_state[f"confirm_delete_{user['username']}"] = True

                        # Confirmation dialog
                        if st.session_state.get(f"confirm_delete_{user['username']}"):
                            st.warning(f"Remove **{user['username']}**?")
                            c1, c2 = st.columns(2)
                            with c1:
                                if st.button("Yes", key=f"yes_{user['username']}", type="primary"):
                                    remove_auth_user(user['username'])
                                    # Disable auth if no users left
                                    if len(list_auth_users()) == 0:
                                        set_auth_enabled(False)
                                    st.session_state[f"confirm_delete_{user['username']}"] = False
                                    st.rerun()
                            with c2:
                                if st.button("No", key=f"no_{user['username']}"):
                                    st.session_state[f"confirm_delete_{user['username']}"] = False
                                    st.rerun()
            else:
                st.info("No users configured. Add a user to enable authentication.")

        with col_add:
            st.markdown("**Add User**")

            with st.form("add_user_form", clear_on_submit=True):
                new_username = st.text_input(
                    "Username",
                    placeholder="admin",
                    help="Used for login"
                )
                new_name = st.text_input(
                    "Display Name",
                    placeholder="Administrator",
                    help="Shown after login (optional, defaults to username)"
                )
                new_password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Enter password"
                )
                confirm_password = st.text_input(
                    "Confirm Password",
                    type="password",
                    placeholder="Confirm password"
                )

                submitted = st.form_submit_button("Add User", use_container_width=True)

                if submitted:
                    # Validation
                    if not new_username:
                        st.error("Username is required")
                    elif not new_username.isalnum():
                        st.error("Username must be alphanumeric")
                    elif any(u['username'] == new_username for u in users):
                        st.error(f"User '{new_username}' already exists")
                    elif not new_password:
                        st.error("Password is required")
                    elif len(new_password) < 4:
                        st.error("Password must be at least 4 characters")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match")
                    else:
                        # Hash password and add user
                        hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
                        display_name = new_name if new_name else new_username

                        if add_auth_user(new_username, display_name, hashed):
                            st.success(f"User '{new_username}' created")
                            st.rerun()
                        else:
                            st.error("Failed to create user")

        # Help text for new users
        if not auth_enabled and user_count == 0:
            st.info("""
            💡 **Recommended for network access**: If you access this app from other devices
            (phone, tablet, other computers), add a user and enable authentication to protect your financial data.
            """)

    except ImportError:
        st.warning("bcrypt package required for authentication. Install with: `pip install bcrypt`")
    except Exception as e:
        st.warning(f"Could not load authentication settings: {str(e)}")

    st.markdown("")  # Spacing

    # ============================================================================
    # EXPORT SETTINGS
    # ============================================================================
    st.subheader("📤 Export Settings")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Default Export Format**")
        export_format = st.selectbox(
            "Format",
            ["CSV", "JSON"],
            key="export_format"
        )
        st.caption("Default format for exporting data")

    with col2:
        st.markdown("**Default Date Range**")
        default_range = st.selectbox(
            "Range",
            ["Last Month", "Last 3 Months", "Last 6 Months", "This Year", "All Time"],
            index=1,
            key="default_range"
        )
        st.caption("Default time range for reports")

    st.markdown("")  # Spacing

    # ============================================================================
    # APPLICATION INFO
    # ============================================================================
    st.subheader("ℹ️ About")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Financial Data Aggregator**")
        st.markdown("Version: 1.0.0")
        st.markdown("License: MIT")

        st.markdown("**Components:**")
        st.markdown("- CLI: `fin-cli`")
        st.markdown("- Web UI: Streamlit")
        st.markdown("- Database: SQLite")
        st.markdown("- Scrapers: Selenium + API")

    with col2:
        st.markdown("**Configuration Directory**")
        st.code(str(CONFIG_DIR), language="bash")

        st.markdown("**Files:**")
        config_files = [
            "financial_data.db",
            "credentials.enc",
            ".key",
            "config.json",
            "category_rules.yaml"
        ]

        for file in config_files:
            file_path = CONFIG_DIR / file
            if file_path.exists():
                size = file_path.stat().st_size
                st.markdown(f"- ✅ `{file}` ({size:,} bytes)")
            else:
                st.markdown(f"- ❌ `{file}` (not found)")

    st.markdown("")  # Spacing

    # ============================================================================
    # SYSTEM INFORMATION
    # ============================================================================
    with st.expander("🖥️ System Information", expanded=False):
        st.markdown("**Python Environment**")
        st.code(f"Python: {sys.version}", language="text")
        st.code(f"Platform: {sys.platform}", language="text")

        st.markdown("**Installed Packages (Key)**")
        try:
            import streamlit as st_pkg
            import sqlalchemy
            import pandas as pd_pkg
            import plotly

            st.markdown(f"- Streamlit: {st_pkg.__version__}")
            st.markdown(f"- SQLAlchemy: {sqlalchemy.__version__}")
            st.markdown(f"- Pandas: {pd_pkg.__version__}")
            st.markdown(f"- Plotly: {plotly.__version__}")
        except Exception as e:
            st.warning(f"Could not retrieve package versions: {str(e)}")

        st.markdown("**Environment Variables**")
        st.code(f"CONFIG_DIR: {CONFIG_DIR}", language="text")
        st.code(f"HOME: {Path.home()}", language="text")


except Exception as e:
    st.error(f"Error loading settings: {str(e)}")
    st.exception(e)
    st.info("💡 Make sure the database is initialized with `fin-cli init`")
