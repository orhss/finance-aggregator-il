"""
Settings Page - Application configuration and management
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path
import shutil

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from streamlit_app.utils.session import init_session_state
from streamlit_app.auth import check_authentication
from streamlit_app.utils.formatters import format_number
from streamlit_app.components.sidebar import render_minimal_sidebar
from streamlit_app.components.theme import apply_theme, render_page_header
from streamlit_app.components.cards import render_metric_row
from streamlit_app.utils.mobile import detect_mobile, is_mobile
from streamlit_app.components.mobile_ui import apply_mobile_css, bottom_navigation

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

# Mobile detection
detect_mobile()

# Apply theme
theme = apply_theme()


def render_theme_settings():
    """Render theme settings section."""
    from streamlit_app.config.theme import set_theme_mode

    def on_theme_change():
        """Callback when user clicks the toggle - only fires on actual clicks."""
        new_mode = 'dark' if st.session_state.setting_dark_mode else 'light'
        st.session_state.theme_mode = new_mode
        set_theme_mode(new_mode)

    current_mode = st.session_state.get('theme_mode', 'light')
    is_dark = current_mode == 'dark'

    # Sync toggle key with theme_mode to handle external changes (e.g., sidebar button)
    # Must happen before toggle renders so widget shows correct state
    if 'setting_dark_mode' not in st.session_state:
        st.session_state.setting_dark_mode = is_dark
    elif st.session_state.setting_dark_mode != is_dark:
        # External change detected (sidebar button) - sync the toggle
        st.session_state.setting_dark_mode = is_dark

    st.toggle(
        "Dark Mode",
        key="setting_dark_mode",
        help="Switch between light and dark theme",
        on_change=on_theme_change
    )

    st.caption("🌙 Easier on the eyes in low light")


def render_privacy_settings():
    """Render privacy settings section."""
    mask_balances = st.toggle(
        "Hide All Balances",
        value=st.session_state.get('mask_balances', False),
        key="setting_mask_balances",
        help="Hide all financial amounts (shows ••••••)"
    )
    st.session_state.mask_balances = mask_balances
    st.caption("🔒 Useful when sharing screen")

    mask_accounts = st.toggle(
        "Mask Account Numbers",
        value=st.session_state.get('mask_account_numbers', True),
        key="setting_mask_account_numbers",
        help="Show account numbers as ••••1234"
    )
    st.session_state.mask_account_numbers = mask_accounts
    st.caption("📋 Account numbers show as ••••1234")


def render_budget_settings(session):
    """Render budget settings section."""
    try:
        from services.budget_service import BudgetService
        from datetime import date

        budget_service = BudgetService(session)
        progress = budget_service.get_current_progress()
        today = date.today()
        month_name = today.strftime("%B %Y")

        current_budget = progress['budget'] if progress['budget'] else 5000

        new_budget = st.number_input(
            f"Monthly Budget for {month_name} (₪)",
            min_value=0.0,
            value=float(current_budget),
            step=500.0,
            key="budget_input"
        )

        if st.button("💾 Save Budget", use_container_width=True):
            budget_service.set_current_budget(new_budget)
            st.success(f"Budget set to ₪{new_budget:,.0f}")
            st.rerun()

        if progress['budget']:
            spent = progress['spent']
            percent = progress['percent_actual']
            remaining = progress['remaining']

            st.progress(min(percent / 100, 1.0))

            if progress['is_over_budget']:
                st.error(f"₪{spent:,.0f} spent — ₪{abs(remaining):,.0f} over budget")
            else:
                st.success(f"₪{spent:,.0f} spent — ₪{remaining:,.0f} remaining")

    except Exception as e:
        st.warning(f"Could not load budget: {str(e)}")


def render_mobile_settings():
    """Render mobile-optimized settings view."""
    apply_mobile_css()

    render_page_header("⚙️ Settings")

    # Get database session
    try:
        from db.database import get_session
        session = get_session()
    except:
        session = None

    # Theme Section
    st.markdown("---")
    st.markdown("**🌓 Theme**")
    render_theme_settings()

    # Privacy Section
    st.markdown("---")
    st.markdown("**🔒 Privacy**")
    render_privacy_settings()

    # Budget Section
    if session:
        st.markdown("---")
        st.markdown("**💰 Budget**")
        render_budget_settings(session)

    # Link to full settings on desktop
    st.markdown("---")
    st.caption("For advanced settings (credentials, database, authentication), use the desktop version.")

    # Bottom navigation
    bottom_navigation(current="settings")


def render_desktop_settings():
    """Render full desktop settings view."""
    # Render sidebar
    render_minimal_sidebar()

    # Page header
    render_page_header("⚙️ Settings")

    try:
        from db.database import get_session
        from db.models import Account, Transaction, Balance, Tag
        from config.settings import CONFIG_DIR, CREDENTIALS_FILE
        from sqlalchemy import func

        session = get_session()

        # Use tabs for organization
        tab_appearance, tab_data, tab_security, tab_about = st.tabs([
            "🎨 Appearance",
            "💾 Data & Budget",
            "🔑 Security",
            "ℹ️ About"
        ])

        # =====================================================================
        # APPEARANCE TAB
        # =====================================================================
        with tab_appearance:
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("🌓 Theme")
                render_theme_settings()

                st.markdown("")
                st.subheader("🎨 Display")

                rows_per_page = st.selectbox(
                    "Default Rows Per Page",
                    [25, 50, 100, 200],
                    index=1,
                    key="rows_per_page"
                )

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

                st.caption("💡 Display settings are for preview only")

            with col2:
                st.subheader("🔒 Privacy")
                render_privacy_settings()

        # =====================================================================
        # DATA & BUDGET TAB
        # =====================================================================
        with tab_data:
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("💰 Monthly Budget")
                render_budget_settings(session)

                st.markdown("")
                st.subheader("📤 Export Defaults")

                export_format = st.selectbox(
                    "Format",
                    ["CSV", "JSON"],
                    key="export_format"
                )

                default_range = st.selectbox(
                    "Date Range",
                    ["Last Month", "Last 3 Months", "Last 6 Months", "This Year", "All Time"],
                    index=1,
                    key="default_range"
                )

            with col2:
                st.subheader("🔐 Credentials")

                creds_path = CREDENTIALS_FILE
                if creds_path.exists():
                    st.success("✅ Credentials configured")

                    institutions = session.query(Account.institution).distinct().all()
                    if institutions:
                        st.markdown("**Institutions:**")
                        for inst in institutions:
                            count = session.query(func.count(Account.id)).filter(
                                Account.institution == inst[0]
                            ).scalar()
                            st.markdown(f"- {inst[0]}: {count} account(s)")
                else:
                    st.warning("⚠️ No credentials configured")

                st.code("fin-cli config setup", language="bash")
                st.caption("Run this command to configure credentials")

                st.markdown("")
                st.subheader("💾 Database")

                db_path = CONFIG_DIR / "financial_data.db"
                if db_path.exists():
                    db_size = db_path.stat().st_size / (1024 * 1024)
                    st.success(f"✅ Database: {db_size:.2f} MB")

                    account_count = session.query(func.count(Account.id)).scalar()
                    txn_count = session.query(func.count(Transaction.id)).scalar()
                    st.markdown(f"- {account_count} accounts, {txn_count:,} transactions")

                    if st.button("📥 Create Backup", use_container_width=True):
                        backup_name = f"financial_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                        backup_path = CONFIG_DIR / backup_name
                        shutil.copy(db_path, backup_path)
                        st.success(f"✅ Backup: `{backup_name}`")
                else:
                    st.warning("⚠️ Database not found")
                    st.code("fin-cli init", language="bash")

        # =====================================================================
        # SECURITY TAB
        # =====================================================================
        with tab_security:
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

                col1, col2 = st.columns([2, 1])

                with col1:
                    if auth_enabled:
                        st.success(f"✅ Authentication **enabled** ({user_count} user{'s' if user_count != 1 else ''})")
                    else:
                        st.warning("⚠️ Authentication **disabled** — anyone with network access can view your data")

                with col2:
                    if user_count > 0:
                        new_auth_state = st.toggle(
                            "Require login",
                            value=auth_enabled,
                            key="auth_toggle"
                        )
                        if new_auth_state != auth_enabled:
                            set_auth_enabled(new_auth_state)
                            st.rerun()

                col_users, col_add = st.columns(2)

                with col_users:
                    st.markdown("**Users**")
                    if users:
                        for user in users:
                            ucol1, ucol2 = st.columns([3, 1])
                            with ucol1:
                                st.markdown(f"👤 **{user['username']}** ({user['name']})")
                            with ucol2:
                                if st.button("🗑️", key=f"del_{user['username']}"):
                                    remove_auth_user(user['username'])
                                    if len(list_auth_users()) == 0:
                                        set_auth_enabled(False)
                                    st.rerun()
                    else:
                        st.info("No users configured")

                with col_add:
                    st.markdown("**Add User**")
                    with st.form("add_user_form", clear_on_submit=True):
                        new_username = st.text_input("Username", placeholder="admin")
                        new_name = st.text_input("Display Name", placeholder="Administrator")
                        new_password = st.text_input("Password", type="password")
                        confirm_password = st.text_input("Confirm Password", type="password")

                        if st.form_submit_button("Add User", use_container_width=True):
                            if not new_username:
                                st.error("Username required")
                            elif not new_password:
                                st.error("Password required")
                            elif new_password != confirm_password:
                                st.error("Passwords don't match")
                            else:
                                hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
                                if add_auth_user(new_username, new_name or new_username, hashed):
                                    st.success(f"User '{new_username}' created")
                                    st.rerun()

            except ImportError:
                st.warning("bcrypt package required. Install with: `pip install bcrypt`")
            except Exception as e:
                st.warning(f"Could not load auth settings: {str(e)}")

        # =====================================================================
        # ABOUT TAB
        # =====================================================================
        with tab_about:
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("📱 Application")
                st.markdown("**Financial Data Aggregator**")
                st.markdown("Version: 1.0.0")
                st.markdown("License: MIT")

                st.markdown("**Components:**")
                st.markdown("- CLI: `fin-cli`")
                st.markdown("- Web UI: Streamlit")
                st.markdown("- Database: SQLite")

            with col2:
                st.subheader("📁 Configuration")
                st.code(str(CONFIG_DIR), language="bash")

                config_files = ["financial_data.db", "credentials.enc", "config.json"]
                for file in config_files:
                    file_path = CONFIG_DIR / file
                    if file_path.exists():
                        st.markdown(f"✅ `{file}`")
                    else:
                        st.markdown(f"❌ `{file}`")

            with st.expander("🖥️ System Information"):
                st.code(f"Python: {sys.version}", language="text")
                st.code(f"Platform: {sys.platform}", language="text")

                try:
                    import streamlit as st_pkg
                    import sqlalchemy
                    st.markdown(f"- Streamlit: {st_pkg.__version__}")
                    st.markdown(f"- SQLAlchemy: {sqlalchemy.__version__}")
                except:
                    pass

    except Exception as e:
        st.error(f"Error loading settings: {str(e)}")
        st.exception(e)


# Main routing
if is_mobile():
    render_mobile_settings()
else:
    render_desktop_settings()
