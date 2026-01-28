"""
Authentication wrapper for Streamlit UI

Optional password protection for secure remote access.
Enabled via CLI: fin-cli auth enable

Copyright (C) 2024-2026 Or Hasson
SPDX-License-Identifier: AGPL-3.0-or-later
"""

import streamlit as st
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import (
    is_auth_enabled,
    get_auth_users_file,
    load_auth_users,
)


def check_authentication() -> bool:
    """
    Check if user is authenticated. If auth is disabled, always returns True.

    If auth is enabled and user is not authenticated, shows login form.

    Returns:
        True if user is authenticated (or auth is disabled), False otherwise
    """
    # If auth is disabled, allow access
    if not is_auth_enabled():
        return True

    # Check if users are configured
    users = load_auth_users()
    if not users:
        st.error("Authentication is enabled but no users are configured.")
        st.info("Add a user with: `fin-cli auth add-user <username>`")
        return False

    # Initialize authentication state
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.username = None

    # If already authenticated, allow access
    if st.session_state.authenticated:
        return True

    # Show login form
    return _show_login_form(users)


def _show_login_form(users: dict) -> bool:
    """
    Display login form and handle authentication.

    Args:
        users: Dictionary of configured users

    Returns:
        True if authentication successful, False otherwise
    """
    import streamlit_authenticator as stauth
    import yaml

    # Load the full config file for streamlit-authenticator
    users_file = get_auth_users_file()

    if not users_file.exists():
        st.error("Users file not found. Run `fin-cli auth add-user` first.")
        return False

    with open(users_file, 'r') as f:
        config = yaml.safe_load(f)

    # Create authenticator
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days'],
    )

    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("## Financial Data Aggregator")
        st.markdown("---")

        # Show login form
        name, authentication_status, username = authenticator.login(
            location='main',
            fields={
                'Form name': 'Login',
                'Username': 'Username',
                'Password': 'Password',
                'Login': 'Login'
            }
        )

        if authentication_status:
            st.session_state.authenticated = True
            st.session_state.username = username
            st.session_state.name = name
            st.rerun()
        elif authentication_status is False:
            st.error("Invalid username or password")

    return False


def get_logout_button():
    """
    Get a logout button if auth is enabled and user is logged in.
    Call this in the sidebar to show logout option.
    """
    if not is_auth_enabled():
        return

    if not st.session_state.get("authenticated"):
        return

    name = st.session_state.get("name", "User")
    st.sidebar.markdown(f"Logged in as **{name}**")

    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.name = None
        st.rerun()


def require_auth(func):
    """
    Decorator to require authentication for a page.

    Usage:
        @require_auth
        def main():
            # Page content here
            pass
    """
    def wrapper(*args, **kwargs):
        if not check_authentication():
            st.stop()
        return func(*args, **kwargs)
    return wrapper
