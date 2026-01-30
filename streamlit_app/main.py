"""
Financial Data Aggregator - Central Entrypoint

This is the main entry point for the Streamlit app using st.navigation.
All common setup (authentication, theme, sidebar) is handled here once.
"""

import streamlit as st
from pathlib import Path
import sys

# Add project root to path (must be before any local imports)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from streamlit_app.utils.session import init_session_state
from streamlit_app.utils.mobile import detect_mobile, is_mobile
from streamlit_app.auth import check_authentication, get_logout_button
from streamlit_app.components.theme import apply_theme
from streamlit_app.components.sidebar import render_minimal_sidebar

# Page config (MUST be first Streamlit call)
st.set_page_config(
    page_title="Financial Aggregator",
    page_icon=":material/account_balance_wallet:",
    layout="wide",
    initial_sidebar_state="collapsed" if st.query_params.get("mobile") == "true" else "expanded",
)

# Initialize session state
init_session_state()

# Check authentication (if enabled)
if not check_authentication():
    st.stop()

# Mobile detection (automatic via viewport JS + User-Agent fallback)
detect_mobile()

# Apply theme (loads CSS + theme-specific styles)
apply_theme()

# Define pages with Material Icons and explicit URL paths
home = st.Page("app.py", title="Home", icon=":material/home:", url_path="home", default=True)
transactions = st.Page("views/transactions.py", title="Transactions", icon=":material/receipt_long:", url_path="transactions")
analytics = st.Page("views/analytics.py", title="Analytics", icon=":material/insights:", url_path="analytics")
accounts = st.Page("views/accounts.py", title="Accounts", icon=":material/account_balance:", url_path="accounts")
organize = st.Page("views/organize.py", title="Organize", icon=":material/label:", url_path="organize")
settings = st.Page("views/settings.py", title="Settings", icon=":material/settings:", url_path="settings")

# Page groups for navigation
pages = {
    "Main": [home, transactions, analytics],
    "Manage": [accounts, organize, settings],
}

# Navigation
if is_mobile():
    # Mobile uses bottom navigation, hide sidebar nav
    pg = st.navigation(pages, position="hidden")
else:
    pg = st.navigation(pages)

# Sidebar content AFTER navigation (so nav appears first in sidebar)
if not is_mobile():
    render_minimal_sidebar()
    get_logout_button()

pg.run()
