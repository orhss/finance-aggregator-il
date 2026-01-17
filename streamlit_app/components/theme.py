"""
Theme Components - Theme switcher and theme utilities

This module provides components for theme switching and theme application.
"""

import streamlit as st
from streamlit_app.config.theme import get_theme, set_theme_mode, Theme


def init_theme() -> Theme:
    """
    Initialize theme from session state

    Returns:
        Current theme instance
    """
    # Initialize theme mode in session state if not present
    if 'theme_mode' not in st.session_state:
        st.session_state.theme_mode = 'light'

    # Get or create theme with current mode
    theme = get_theme(st.session_state.theme_mode)

    return theme


def render_theme_switcher(location: str = "sidebar") -> None:
    """
    Render theme switcher toggle

    Args:
        location: Where to render ("sidebar", "main", "header")

    Example:
        # In sidebar
        render_theme_switcher("sidebar")

        # In main content
        render_theme_switcher("main")
    """
    current_mode = st.session_state.get('theme_mode', 'light')
    is_dark = current_mode == 'dark'

    # Create toggle based on location
    if location == "sidebar":
        with st.sidebar:
            st.markdown("---")
            st.markdown("**⚙️ Settings**")

            # Theme toggle
            new_mode_is_dark = st.toggle(
                "🌙 Dark Mode",
                value=is_dark,
                key="theme_toggle_sidebar"
            )

            # Update theme if changed
            new_mode = 'dark' if new_mode_is_dark else 'light'
            if new_mode != current_mode:
                st.session_state.theme_mode = new_mode
                set_theme_mode(new_mode)
                st.rerun()

    elif location == "header":
        col1, col2, col3 = st.columns([6, 1, 1])
        with col3:
            new_mode_is_dark = st.toggle(
                "🌙",
                value=is_dark,
                key="theme_toggle_header",
                help="Toggle dark mode"
            )

            new_mode = 'dark' if new_mode_is_dark else 'light'
            if new_mode != current_mode:
                st.session_state.theme_mode = new_mode
                set_theme_mode(new_mode)
                st.rerun()

    else:  # main
        new_mode_is_dark = st.toggle(
            "🌙 Dark Mode",
            value=is_dark,
            key="theme_toggle_main"
        )

        new_mode = 'dark' if new_mode_is_dark else 'light'
        if new_mode != current_mode:
            st.session_state.theme_mode = new_mode
            set_theme_mode(new_mode)
            st.rerun()


def apply_theme() -> Theme:
    """
    Apply theme to the current page

    This function should be called at the top of each page to:
    1. Initialize theme from session state
    2. Apply global CSS
    3. Return theme instance for use in page

    Returns:
        Current theme instance

    Example:
        theme = apply_theme()
        # Now use theme for colors
        st.markdown(f"<span style='color: {theme.get_color('primary')}'>Text</span>")
    """
    # Initialize theme
    theme = init_theme()

    # Apply global CSS
    st.markdown(theme.generate_global_css(), unsafe_allow_html=True)

    return theme


def format_category_badge_themed(category: str, theme: Theme) -> str:
    """
    Format category badge using theme colors

    Args:
        category: Category name
        theme: Theme instance

    Returns:
        HTML string with themed badge
    """
    if not category:
        return f"<span style='color:{theme.get_color('text_muted')}; font-size:0.85rem'>Uncategorized</span>"

    color = theme.get_category_color(category)
    style = theme.get_badge_style(color)

    return f"<span style='{style}'>{category}</span>"


def format_tags_themed(tags: list, theme: Theme) -> str:
    """
    Format tags using theme colors

    Args:
        tags: List of tag names
        theme: Theme instance

    Returns:
        HTML string with themed badges
    """
    if not tags:
        return ""

    badges = []
    tag_color = theme.get_color('primary')

    for tag in tags:
        style = theme.get_badge_style(
            tag_color,
            text_color=tag_color,
            border_color=f"{tag_color}40"
        )
        badges.append(f"<span style='{style}'>🏷️ {tag}</span>")

    return " ".join(badges)


def format_status_themed(status: str, theme: Theme, as_badge: bool = True) -> str:
    """
    Format status with theme colors

    Args:
        status: Status string
        theme: Theme instance
        as_badge: If True, return HTML badge

    Returns:
        Formatted status
    """
    status_config = {
        'completed': {'icon': '✅', 'label': 'Completed'},
        'pending': {'icon': '⏳', 'label': 'Pending'},
        'failed': {'icon': '❌', 'label': 'Failed'},
        'success': {'icon': '✅', 'label': 'Success'},
        'error': {'icon': '❌', 'label': 'Error'},
        'running': {'icon': '🔄', 'label': 'Running'},
        'active': {'icon': '✅', 'label': 'Active'},
        'inactive': {'icon': '⭕', 'label': 'Inactive'},
    }

    config = status_config.get(status.lower(), {'icon': '❓', 'label': status})

    if not as_badge:
        return f"{config['icon']} {config['label']}"

    color = theme.get_status_color(status)
    style = theme.get_badge_style(color)

    return f"<span style='{style}'>{config['icon']} {config['label']}</span>"


def get_themed_chart_colors(theme: Theme, count: int = 4) -> list:
    """
    Get chart colors from theme

    Args:
        theme: Theme instance
        count: Number of colors needed

    Returns:
        List of color hex codes
    """
    return theme.get_chart_colors(count)


def themed_metric(
    label: str,
    value: str,
    delta: str = None,
    theme: Theme = None,
    delta_color: str = "normal"
) -> None:
    """
    Display metric with theme-aware styling

    Args:
        label: Metric label
        value: Metric value
        delta: Delta value (optional)
        theme: Theme instance (optional, will use current if not provided)
        delta_color: Delta color mode ("normal", "inverse", "off")
    """
    if theme is None:
        theme = get_theme()

    st.metric(
        label=label,
        value=value,
        delta=delta,
        delta_color=delta_color
    )


def themed_card(
    content_func,
    theme: Theme = None,
    elevated: bool = True
) -> None:
    """
    Display content in a themed card

    Args:
        content_func: Function that renders card content
        theme: Theme instance (optional)
        elevated: Whether to add elevation
    """
    if theme is None:
        theme = get_theme()

    card_style = theme.get_card_style(elevated=elevated)

    st.markdown(f"<div style='{card_style}'>", unsafe_allow_html=True)
    content_func()
    st.markdown("</div>", unsafe_allow_html=True)


def themed_hero_metric(
    label: str,
    value: str,
    icon: str,
    theme: Theme,
    gradient: bool = True
) -> None:
    """
    Display hero metric with themed gradient card

    Args:
        label: Metric label
        value: Metric value
        icon: Icon emoji
        theme: Theme instance
        gradient: Whether to use gradient background
    """
    if gradient:
        if theme.mode == "light":
            gradient_colors = f"linear-gradient(135deg, {theme.get_color('primary')}15, {theme.get_color('secondary')}15)"
        else:
            gradient_colors = f"linear-gradient(135deg, {theme.get_color('primary')}25, {theme.get_color('secondary')}25)"
    else:
        gradient_colors = theme.get_color('bg_secondary')

    card_css = f"""
        background: {gradient_colors};
        border: 1px solid {theme.get_color('border_light')};
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    """

    st.markdown(f"""
        <div style='{card_css}'>
            <div style='font-size: 2rem; margin-bottom: 0.5rem'>{icon}</div>
            <div style='color: {theme.get_color('text_secondary')}; font-size: 0.9rem; margin-bottom: 0.5rem'>{label}</div>
            <div style='color: {theme.get_color('text_primary')}; font-size: 2rem; font-weight: 600'>{value}</div>
        </div>
    """, unsafe_allow_html=True)


# Helper function to get current theme anywhere in the app
def current_theme() -> Theme:
    """
    Get current theme instance

    Returns:
        Current theme
    """
    mode = st.session_state.get('theme_mode', 'light')
    return get_theme(mode)
