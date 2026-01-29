"""
Shared sidebar components used across pages.

Styled HTML components following the Hybrid Material + Glassmorphism design system.
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from streamlit_app.utils.formatters import format_datetime
from streamlit_app.utils.session import format_amount_private
from streamlit_app.utils.cache import get_dashboard_stats


def render_privacy_toggle():
    """
    Render a styled privacy mode toggle in the sidebar.
    Toggles balance masking with a single click.
    """
    is_private = st.session_state.get('mask_balances', False)
    icon = "🙈" if is_private else "👁️"
    label = "Privacy Mode"

    # Use columns for layout
    col1, col2 = st.sidebar.columns([3, 1])
    with col1:
        st.markdown(
            f'<span class="sidebar-toggle-label">{label}</span>',
            unsafe_allow_html=True
        )
    with col2:
        if st.button(icon, key="privacy_toggle", help="Toggle balance visibility"):
            st.session_state.mask_balances = not is_private
            st.rerun()


def render_quick_stats():
    """
    Render styled quick statistics cards in the sidebar.
    Uses the same cached data source as the Dashboard for consistency.
    Uses the same metric-card styling as the main content area for consistency.
    """
    st.sidebar.markdown(
        '<div class="sidebar-section-header">📊 Quick Stats</div>',
        unsafe_allow_html=True
    )

    try:
        # Use the same cached stats as Dashboard - single source of truth
        stats = get_dashboard_stats()

        if stats and stats['account_count'] > 0:
            # Total Balance card - using metric-card class for consistent dark/light mode styling
            if stats['total_balance']:
                balance_value = format_amount_private(stats['total_balance'])
            else:
                balance_value = "Not synced"

            st.sidebar.markdown(
                f'''<div class="metric-card" style="padding: 0.875rem 1rem; margin-bottom: 0.5rem;">
                    <div class="metric-label">Total Balance</div>
                    <div class="metric-value" style="font-size: 1.25rem;">{balance_value}</div>
                </div>''',
                unsafe_allow_html=True
            )

            # Pending transactions card
            pending_count = stats.get('pending_count', 0) or 0
            pending_amount = stats.get('pending_amount')
            sublabel = format_amount_private(pending_amount) if pending_amount else ""

            sublabel_html = f'<div class="metric-sublabel">{sublabel}</div>' if sublabel else ''

            st.sidebar.markdown(
                f'''<div class="metric-card" style="padding: 0.875rem 1rem; margin-bottom: 0.5rem;">
                    <div class="metric-label">Pending</div>
                    <div class="metric-value" style="font-size: 1.25rem;">{pending_count}</div>
                    {sublabel_html}
                </div>''',
                unsafe_allow_html=True
            )

            # Last sync time
            if stats['last_sync']:
                sync_time = format_datetime(stats['last_sync'], '%m/%d %H:%M')
                st.sidebar.markdown(
                    f'<div class="metric-sublabel" style="text-align: center; margin-top: 0.5rem;">Last sync: {sync_time}</div>',
                    unsafe_allow_html=True
                )
        else:
            st.sidebar.info("💡 Initialize database to see stats")

    except Exception:
        st.sidebar.warning("Stats unavailable")


def render_theme_toggle():
    """
    Render a styled dark mode toggle in the sidebar.
    """
    from streamlit_app.config.theme import set_theme_mode

    current_mode = st.session_state.get('theme_mode', 'light')
    is_dark = current_mode == 'dark'
    icon = "🌙" if is_dark else "☀️"
    label = "Dark Mode" if is_dark else "Light Mode"

    # Section header
    st.sidebar.markdown(
        '<div class="sidebar-section-header">⚙️ Settings</div>',
        unsafe_allow_html=True
    )

    # Use columns for layout
    col1, col2 = st.sidebar.columns([3, 1])
    with col1:
        st.markdown(
            f'<span class="sidebar-toggle-label">{label}</span>',
            unsafe_allow_html=True
        )
    with col2:
        if st.button(icon, key="theme_toggle_sidebar", help="Toggle dark mode"):
            new_mode = 'light' if is_dark else 'dark'
            st.session_state.theme_mode = new_mode
            set_theme_mode(new_mode)
            st.rerun()


def render_about():
    """
    Render styled about card in sidebar.
    """
    st.sidebar.markdown(
        '''<div class="sidebar-about-card">
            <div class="about-title">Financial Aggregator</div>
            <div class="about-version">v1.0</div>
            <div class="about-links">
                <a href="https://github.com" target="_blank">Docs</a> ·
                <a href="https://github.com" target="_blank">Issues</a>
            </div>
        </div>''',
        unsafe_allow_html=True
    )


def render_minimal_sidebar():
    """
    Render styled sidebar with all components.

    Order:
    1. Privacy Mode toggle
    2. Quick Stats section
    3. Dark Mode toggle (in Settings section)
    4. About card
    """
    render_privacy_toggle()
    render_quick_stats()
    render_theme_toggle()
    render_about()
