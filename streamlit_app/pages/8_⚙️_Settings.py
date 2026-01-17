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
from streamlit_app.utils.formatters import format_number
from streamlit_app.components.sidebar import render_minimal_sidebar
from streamlit_app.components.theme import apply_theme, render_theme_switcher

# Page config
st.set_page_config(
    page_title="Settings - Financial Aggregator",
    page_icon="⚙️",
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
st.title("⚙️ Settings")
st.markdown("Application configuration and management")
st.markdown("---")

try:
    from db.database import get_session
    from db.models import Account, Transaction, Balance, Tag
    from config.settings import CONFIG_DIR, CREDENTIALS_FILE
    from sqlalchemy import func
    import json

    session = get_session()

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

    st.markdown("---")

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
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            account_count = session.query(func.count(Account.id)).scalar()
            st.metric("Accounts", format_number(account_count))

        with col2:
            txn_count = session.query(func.count(Transaction.id)).scalar()
            st.metric("Transactions", format_number(txn_count))

        with col3:
            balance_count = session.query(func.count(Balance.id)).scalar()
            st.metric("Balance Records", format_number(balance_count))

        with col4:
            tag_count = session.query(func.count(Tag.id)).scalar()
            st.metric("Tags", format_number(tag_count))
    else:
        st.warning(f"⚠️ Database not found at `{db_path}`")
        st.markdown("Run the following command to initialize:")
        st.code("fin-cli init", language="bash")

    st.markdown("---")

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

    st.markdown("---")

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

    st.markdown("---")

    # ============================================================================
    # PRIVACY SETTINGS
    # ============================================================================
    st.subheader("🔒 Privacy & Security Settings")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Sensitive Data Masking**")

        mask_accounts = st.toggle(
            "Mask Account Numbers",
            value=st.session_state.get('mask_account_numbers', True),
            key="mask_account_numbers_toggle",
            help="Show account/card numbers as ••••1234"
        )

        if mask_accounts != st.session_state.get('mask_account_numbers', True):
            st.session_state.mask_account_numbers = mask_accounts
            st.success("✅ Account masking preference updated")
            st.info("💡 Changes will apply on next page load")

        st.caption("📋 Account numbers show as ••••1234")

    with col2:
        st.markdown("**Balance Visibility**")

        mask_balances = st.toggle(
            "Hide All Balances",
            value=st.session_state.get('mask_balances', False),
            key="mask_balances_toggle",
            help="Hide all financial amounts for privacy (shows ••••••)"
        )

        if mask_balances != st.session_state.get('mask_balances', False):
            st.session_state.mask_balances = mask_balances
            st.success("✅ Balance visibility preference updated")
            st.info("💡 Changes will apply on next page load")

        st.caption("🔒 Useful when sharing screen or in public")

    # Security reminder
    st.info("""
    🛡️ **Security Best Practices:**
    - Use account number masking when presenting or sharing screenshots
    - Enable balance hiding in public spaces or during video calls
    - Your credentials are always encrypted - these settings only affect display
    - All data stays local on your device
    """)

    st.markdown("---")

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

    st.markdown("---")

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

    st.markdown("---")

    # ============================================================================
    # LINKS & RESOURCES
    # ============================================================================
    st.subheader("🔗 Links & Resources")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Documentation**")
        st.markdown("- [README](../README.md)")
        st.markdown("- [CLI Plan](../plans/CLI_PLAN.md)")
        st.markdown("- [UI Plan](../plans/STREAMLIT_UI_PLAN.md)")

    with col2:
        st.markdown("**Plans**")
        st.markdown("- [Multi-Account](../plans/MULTI_ACCOUNT_PLAN.md)")
        st.markdown("- [Tagging Design](../plans/TAGGING_DESIGN.md)")
        st.markdown("- [Service Refactoring](../plans/SERVICE_REFACTORING_PLAN.md)")

    with col3:
        st.markdown("**Development**")
        st.markdown("- [CLAUDE.md](../CLAUDE.md)")
        st.markdown("- GitHub: [Report Issues](#)")
        st.markdown("- Contribute: [Pull Requests](#)")

    st.markdown("---")

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
