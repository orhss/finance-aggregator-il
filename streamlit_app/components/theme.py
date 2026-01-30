"""
Theme Components - Theme switcher and theme utilities

This module provides components for theme switching and theme application.
"""

import streamlit as st
from pathlib import Path
from streamlit_app.config.theme import get_theme, set_theme_mode, Theme


def load_shared_css():
    """
    Load shared CSS styles from styles/main.css

    Call this function once per page to apply consistent styling.

    Example:
        from streamlit_app.components.theme import load_shared_css
        load_shared_css()
    """
    css_path = Path(__file__).resolve().parent.parent / "styles" / "main.css"

    if css_path.exists():
        with open(css_path, 'r') as f:
            css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    else:
        # Fallback: basic styles inline if file doesn't exist
        pass


def _save_settings_to_localstorage(theme_mode: str, privacy_mode: bool):
    """Inject JavaScript to save settings to localStorage."""
    privacy_value = '1' if privacy_mode else '0'
    st.markdown(f"""
    <script>
    localStorage.setItem('fin_theme_mode', '{theme_mode}');
    localStorage.setItem('fin_privacy_mode', '{privacy_value}');
    </script>
    """, unsafe_allow_html=True)


def _save_theme_to_localstorage(mode: str):
    """Inject JavaScript to save theme to localStorage."""
    st.markdown(f"""
    <script>
    localStorage.setItem('fin_theme_mode', '{mode}');
    </script>
    """, unsafe_allow_html=True)


def _save_privacy_to_localstorage(enabled: bool):
    """Inject JavaScript to save privacy mode to localStorage."""
    value = '1' if enabled else '0'
    st.markdown(f"""
    <script>
    localStorage.setItem('fin_privacy_mode', '{value}');
    </script>
    """, unsafe_allow_html=True)


def init_theme() -> Theme:
    """
    Initialize theme and privacy settings from session state, query params, or localStorage.

    Priority:
    1. Session state (if already set)
    2. Query params (set by JS from localStorage on page load)
    3. Defaults: theme='light', privacy=False, mask_account_numbers=True

    Note: Does NOT inject any HTML/scripts - that's done in apply_theme() to minimize container divs.

    Returns:
        Current theme instance
    """
    # Check query params first (set by JS from localStorage)
    query_params = st.query_params
    url_theme = query_params.get('theme', None)
    url_privacy = query_params.get('privacy', None)

    # Initialize theme mode in session state if not present
    # Only use URL params on first init, not on reruns (to respect user's toggle choice)
    if 'theme_mode' not in st.session_state:
        if url_theme in ('light', 'dark'):
            st.session_state.theme_mode = url_theme
        else:
            st.session_state.theme_mode = 'light'

    # Initialize privacy mode (mask_balances)
    # Only use URL params on first init, not on reruns
    if 'mask_balances' not in st.session_state:
        if url_privacy == '1':
            st.session_state.mask_balances = True
        else:
            st.session_state.mask_balances = False

    # Initialize mask_account_numbers (default True)
    if 'mask_account_numbers' not in st.session_state:
        st.session_state.mask_account_numbers = True

    # Get or create theme with current mode
    theme = get_theme(st.session_state.theme_mode)

    return theme


def _get_localstorage_script(theme_mode: str, privacy_mode: bool) -> str:
    """Generate JavaScript to save settings to localStorage (no injection)."""
    privacy_value = '1' if privacy_mode else '0'
    return f"""
    <script>
    localStorage.setItem('fin_theme_mode', '{theme_mode}');
    localStorage.setItem('fin_privacy_mode', '{privacy_value}');
    </script>
    """


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
                _save_theme_to_localstorage(new_mode)
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
                _save_theme_to_localstorage(new_mode)
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
            _save_theme_to_localstorage(new_mode)
            st.rerun()


def generate_css_variables(theme: Theme) -> str:
    """
    Generate CSS custom properties based on current theme.

    This injects the correct colors into :root so main.css can use them.
    """
    p = theme.palette
    is_dark = theme.mode == "dark"

    # Generate hero gradient based on theme
    if is_dark:
        hero_gradient = f"linear-gradient(135deg, {p.primary} 0%, {p.secondary} 100%)"
        hero_shadow = f"0 25px 50px -12px {p.primary}40"
    else:
        hero_gradient = f"linear-gradient(135deg, {p.primary} 0%, {p.secondary} 100%)"
        hero_shadow = f"0 25px 50px -12px {p.primary}40"

    return f"""
    <style>
    :root {{
        /* Primary brand colors */
        --color-primary: {p.primary};
        --color-primary-light: {p.secondary};
        --color-primary-dark: {p.primary};
        --color-secondary: {p.secondary};

        /* Semantic colors */
        --color-success: {p.success};
        --color-success-light: {p.success};
        --color-success-bg: {p.success}20;
        --color-success-text: {p.success};

        --color-warning: {p.warning};
        --color-warning-light: {p.warning};
        --color-warning-bg: {p.warning}20;
        --color-warning-text: {p.warning};

        --color-error: {p.error};
        --color-error-light: {p.error};
        --color-error-bg: {p.error}20;
        --color-error-text: {p.error};

        --color-info: {p.info};
        --color-info-bg: {p.info}20;
        --color-info-text: {p.info};

        /* Text colors */
        --color-text-primary: {p.text_primary};
        --color-text-secondary: {p.text_secondary};
        --color-text-muted: {p.text_muted};

        /* Surface colors */
        --color-background: {p.bg_primary};
        --color-surface: {p.bg_secondary};
        --color-surface-hover: {p.bg_tertiary};
        --color-surface-subtle: {p.bg_secondary};

        /* Border colors - using semi-transparent for polished look */
        --color-border: {'rgba(255,255,255,0.1)' if is_dark else 'rgba(0,0,0,0.08)'};
        --color-border-light: {'rgba(255,255,255,0.05)' if is_dark else 'rgba(0,0,0,0.05)'};
        --color-border-heavy: {p.border_heavy};

        /* Financial colors */
        --color-expense: {p.expense_color};
        --color-income: {p.income_color};

        /* Gradients */
        --gradient-hero: {hero_gradient};
        --gradient-hero-overlay: radial-gradient(circle at top right, rgba(255,255,255,0.15) 0%, transparent 70%);
        --gradient-success: linear-gradient(90deg, {p.success}, {p.success});

        /* Shadows */
        --shadow-sm: 0 1px 2px rgba(0,0,0,{'0.2' if is_dark else '0.05'});
        --shadow-md: 0 4px 6px -1px rgba(0,0,0,{'0.3' if is_dark else '0.07'}), 0 2px 4px -1px rgba(0,0,0,{'0.2' if is_dark else '0.04'});
        --shadow-lg: 0 10px 15px -3px rgba(0,0,0,{'0.3' if is_dark else '0.08'}), 0 4px 6px -2px rgba(0,0,0,{'0.2' if is_dark else '0.04'});
        --shadow-hero: {hero_shadow};

        /* Glass effect */
        --glass-background: rgba({'30, 41, 59' if is_dark else '255, 255, 255'}, 0.85);
        --glass-blur: 12px;
        --glass-border: rgba(255, 255, 255, {'0.1' if is_dark else '0.3'});
    }}

    /* Base styles for sidebar toggle labels */
    .sidebar-toggle-label {{
        font-size: 0.9rem;
        font-weight: 500;
        color: var(--color-text-primary);
    }}

    /* Base styles for edit panel elements */
    .edit-section-header {{
        color: var(--color-text-primary);
        font-weight: 600;
        font-size: 1rem;
        margin-bottom: 0.75rem;
    }}
    .edit-section-hint {{
        color: var(--color-text-muted);
        font-weight: 400;
        font-size: 0.85rem;
        font-style: italic;
    }}
    .edit-info-text {{
        color: var(--color-text-secondary);
        font-size: 0.9rem;
        margin-bottom: 0.25rem;
        font-family: monospace;
    }}
    .edit-field-label {{
        color: var(--color-text-primary);
        font-weight: 600;
        font-size: 0.9rem;
        margin-top: 0.5rem;
        margin-bottom: 0.25rem;
    }}

    /* Dark mode specific overrides */
    {f'''
    .stApp {{
        background-color: {p.bg_primary};
    }}

    /* Make Streamlit header transparent */
    [data-testid="stHeader"] {{
        background: transparent !important;
    }}
    [data-testid="stDecoration"] {{
        display: none !important;
    }}

    [data-testid="stSidebar"] {{
        background-color: {p.bg_secondary};
    }}

    /* Hero card - darker gradient for dark mode */
    .hero-card {{
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
        box-shadow: 0 25px 50px -12px rgba(79, 70, 229, 0.3) !important;
    }}
    .hero-card::before {{
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%) !important;
    }}

    /* Metric cards */
    .metric-card {{
        background: {p.bg_secondary} !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2) !important;
    }}
    .metric-value {{
        color: {p.text_primary} !important;
    }}
    .metric-label {{
        color: {p.text_secondary} !important;
    }}
    .metric-sublabel {{
        color: {p.text_muted} !important;
    }}

    /* Sidebar metric cards - use bg_tertiary for contrast against bg_secondary sidebar */
    [data-testid="stSidebar"] .metric-card {{
        background: #334155 !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
    }}

    /* Sidebar section headers - more visible separator */
    [data-testid="stSidebar"] .sidebar-section-header {{
        border-bottom-color: rgba(255,255,255,0.15) !important;
    }}

    /* Sidebar about card - same treatment */
    [data-testid="stSidebar"] .sidebar-about-card {{
        background: #334155 !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
    }}

    /* Sidebar toggle labels (Privacy Mode, Dark Mode) - ensure visibility */
    .sidebar-toggle-label {{
        color: {p.text_primary} !important;
        font-size: 0.9rem;
        font-weight: 500;
    }}

    /* Edit panel section headers and text - ensure visibility in dark mode */
    .edit-section-header {{
        color: {p.text_primary} !important;
        font-weight: 600;
        font-size: 1rem;
        margin-bottom: 0.75rem;
    }}
    .edit-section-hint {{
        color: {p.text_muted} !important;
        font-weight: 400;
        font-size: 0.85rem;
        font-style: italic;
    }}
    .edit-info-text {{
        color: {p.text_secondary} !important;
        font-size: 0.9rem;
        margin-bottom: 0.25rem;
        font-family: monospace;
    }}
    .edit-field-label {{
        color: {p.text_primary} !important;
        font-weight: 600;
        font-size: 0.9rem;
        margin-top: 0.5rem;
        margin-bottom: 0.25rem;
    }}

    /* Streamlit tabs - fix dark mode background and text */
    [data-testid="stTabs"] {{
        background: transparent !important;
    }}
    [data-baseweb="tab-list"] {{
        background: transparent !important;
        background-color: transparent !important;
    }}
    /* Tab buttons */
    [data-testid="stTab"] {{
        background: transparent !important;
        background-color: transparent !important;
    }}
    [data-testid="stTab"] p {{
        color: {p.text_secondary} !important;
    }}
    [data-testid="stTab"][aria-selected="true"] {{
        background: transparent !important;
        background-color: transparent !important;
    }}
    [data-testid="stTab"][aria-selected="true"] p {{
        color: {p.text_primary} !important;
    }}
    /* Tab panel content area */
    [data-baseweb="tab-panel"] {{
        background: transparent !important;
        background-color: transparent !important;
    }}
    [role="tabpanel"] {{
        background: transparent !important;
        background-color: transparent !important;
    }}
    /* Fix any white background containers inside tabs */
    [data-testid="stTabs"] > div {{
        background: transparent !important;
        background-color: transparent !important;
    }}
    [data-testid="stTabs"] [data-testid="stVerticalBlock"] {{
        background: transparent !important;
        background-color: transparent !important;
    }}
    /* Fix tab content text and headings */
    [data-testid="stTabs"] h1,
    [data-testid="stTabs"] h2,
    [data-testid="stTabs"] h3,
    [data-testid="stTabs"] h4,
    [data-testid="stTabs"] p,
    [data-testid="stTabs"] span,
    [data-testid="stTabs"] label {{
        color: {p.text_primary} !important;
    }}
    [data-testid="stMarkdownContainer"] p {{
        color: {p.text_primary} !important;
    }}
    /* Streamlit subheader inside tabs */
    [data-testid="stTabs"] [data-testid="stSubheader"] {{
        color: {p.text_primary} !important;
    }}
    /* Checkbox labels */
    [data-testid="stCheckbox"] label span {{
        color: {p.text_primary} !important;
    }}

    /* Budget card */
    .budget-card {{
        background: {p.bg_secondary} !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2) !important;
    }}
    .budget-title {{
        color: {p.text_primary} !important;
    }}
    .budget-bar-bg {{
        background: {p.bg_tertiary} !important;
    }}
    .budget-details {{
        color: #94a3b8 !important;
    }}
    .budget-details span {{
        color: #94a3b8 !important;
    }}

    /* Insight banner */
    .insight-banner.positive {{
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(52, 211, 153, 0.1) 100%) !important;
        border: 1px solid rgba(16, 185, 129, 0.2) !important;
    }}
    .insight-banner.positive .insight-message {{
        color: #6ee7b7 !important;
    }}
    .insight-banner.neutral {{
        background: {p.bg_secondary} !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
    }}
    .insight-banner.neutral .insight-message {{
        color: {p.text_primary} !important;
    }}
    .insight-banner.warning {{
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(251, 191, 36, 0.1) 100%) !important;
        border: 1px solid rgba(245, 158, 11, 0.2) !important;
    }}
    .insight-banner.warning .insight-message {{
        color: #fcd34d !important;
    }}

    /* Alert cards - preserve border-left accent */
    .alert-card {{
        background: {p.bg_secondary} !important;
        border-top: 1px solid rgba(255,255,255,0.05) !important;
        border-right: 1px solid rgba(255,255,255,0.05) !important;
        border-bottom: 1px solid rgba(255,255,255,0.05) !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2) !important;
    }}
    .alert-card.sync {{
        border-left: 4px solid #f59e0b !important;
    }}
    .alert-card.category {{
        border-left: 4px solid {p.primary} !important;
    }}
    .alert-card.uncategorized {{
        border-left: 4px solid {p.secondary} !important;
    }}
    .alert-message {{
        color: {p.text_primary} !important;
    }}

    /* Section headings (h4) and titles */
    h4, .section-title {{
        color: {p.text_primary} !important;
    }}

    /* Section cards */
    .section-card {{
        background: {p.bg_secondary} !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
    }}
    .section-card .header {{
        color: {p.text_primary} !important;
        border-bottom-color: {p.bg_tertiary} !important;
    }}

    /* Account cards */
    .account-card {{
        background: {p.bg_secondary} !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
    }}
    .account-card .name {{
        color: {p.text_primary} !important;
    }}
    .account-card .subtitle {{
        color: {p.text_muted} !important;
    }}
    .account-card .balance {{
        color: {p.text_primary} !important;
    }}

    /* Summary items */
    .summary-item {{
        background: {p.bg_primary} !important;
    }}
    .summary-item:hover {{
        background: {p.bg_tertiary} !important;
    }}
    .summary-item .name {{
        color: {p.text_primary} !important;
    }}
    .summary-item .subtitle {{
        color: {p.text_muted} !important;
    }}
    .summary-item .value {{
        color: {p.text_primary} !important;
    }}

    /* Transaction rows */
    .transaction-row {{
        border-bottom-color: {p.bg_tertiary} !important;
    }}
    .transaction-row:hover {{
        background-color: {p.bg_tertiary} !important;
    }}
    .transaction-row .merchant {{
        color: {p.text_primary} !important;
    }}
    .transaction-row .category {{
        color: {p.text_secondary} !important;
    }}

    /* Date headers */
    .date-header {{
        color: {p.text_muted} !important;
    }}

    /* Category badge */
    .category-badge {{
        background: rgba(129, 140, 248, 0.15) !important;
        color: #a5b4fc !important;
    }}

    /* Buttons - dark mode styling matching preview */
    .stButton > button,
    div[data-testid="stButton"] button {{
        background: #334155 !important;
        color: #94a3b8 !important;
        border: none !important;
        border-radius: 8px !important;
    }}
    .stButton > button:hover,
    div[data-testid="stButton"] button:hover {{
        background: #475569 !important;
        color: {p.text_primary} !important;
    }}
    .stButton > button p,
    .stButton > button span,
    div[data-testid="stButton"] button p,
    div[data-testid="stButton"] button span {{
        color: inherit !important;
    }}

    /* Primary buttons keep their color */
    .stButton > button[kind="primary"],
    div[data-testid="stButton"] button[kind="primary"] {{
        background: {p.primary} !important;
        color: white !important;
        border: none !important;
    }}
    .stButton > button[kind="primary"]:hover,
    div[data-testid="stButton"] button[kind="primary"]:hover {{
        opacity: 0.9;
    }}

    /* View all buttons after card iframes - dark mode */
    iframe + div .stButton > button,
    iframe + div div[data-testid="stButton"] button {{
        background: #334155 !important;
        color: #94a3b8 !important;
    }}
    iframe + div .stButton > button:hover,
    iframe + div div[data-testid="stButton"] button:hover {{
        background: #475569 !important;
        color: {p.text_primary} !important;
    }}

    /* Filter panel */
    .filter-panel {{
        background: {p.bg_secondary} !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
    }}
    .filter-panel .filter-title {{
        color: {p.text_secondary} !important;
    }}

    /* Content card */
    .content-card {{
        background: {p.bg_secondary} !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
    }}
    .content-card .card-header {{
        color: {p.text_primary} !important;
        border-bottom-color: {p.bg_tertiary} !important;
    }}

    /* Stat cards */
    .stat-card {{
        background: {p.bg_secondary} !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
    }}
    .stat-card .stat-label {{
        color: {p.text_secondary} !important;
    }}
    .stat-card .stat-value {{
        color: {p.text_primary} !important;
    }}
    .stat-card .stat-value.positive {{
        color: {p.income_color} !important;
    }}
    .stat-card .stat-value.negative {{
        color: {p.expense_color} !important;
    }}

    /* Edit panel */
    .edit-panel {{
        background: {p.bg_secondary} !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
        border-left: 4px solid {p.primary} !important;
    }}
    .edit-panel .panel-header {{
        color: {p.text_primary} !important;
    }}

    /* Info display */
    .info-display {{
        background: {p.bg_primary} !important;
    }}
    .info-display .info-row {{
        border-bottom-color: {p.bg_tertiary} !important;
    }}
    .info-display .info-label {{
        color: {p.text_secondary} !important;
    }}
    .info-display .info-value {{
        color: {p.text_primary} !important;
    }}

    /* Table container */
    .table-container {{
        background: {p.bg_secondary} !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
    }}
    .table-container .table-header {{
        border-bottom-color: {p.bg_tertiary} !important;
    }}
    .table-container .table-title {{
        color: {p.text_primary} !important;
    }}
    .table-container .table-count {{
        color: {p.text_secondary} !important;
    }}

    /* Empty state */
    .empty-state .empty-title {{
        color: {p.text_primary} !important;
    }}
    .empty-state .empty-message {{
        color: {p.text_secondary} !important;
    }}

    /* Results count */
    .results-count {{
        color: {p.text_secondary} !important;
    }}
    .results-count strong {{
        color: {p.text_primary} !important;
    }}
    ''' if is_dark else ''}
    </style>
    """


def apply_theme() -> Theme:
    """
    Apply theme to the current page

    This function should be called at the top of each page to:
    1. Initialize theme from session state
    2. Inject CSS variables for current theme
    3. Apply shared CSS styles
    4. Apply theme-specific overrides
    5. Return theme instance for use in page

    Returns:
        Current theme instance

    Example:
        theme = apply_theme()
        # Now use theme for colors
        st.markdown(f"<span style='color: {theme.get_color('primary')}'>Text</span>")
    """
    # Initialize theme
    theme = init_theme()

    # Save settings to localStorage
    _save_settings_to_localstorage(
        st.session_state.theme_mode,
        st.session_state.mask_balances
    )

    # Inject CSS variables FIRST (so main.css can use them)
    st.markdown(generate_css_variables(theme), unsafe_allow_html=True)

    # Load shared CSS styles (uses the CSS variables we just set)
    load_shared_css()

    # Apply additional theme-specific CSS overrides
    st.markdown(theme.generate_global_css(), unsafe_allow_html=True)

    return theme


def render_page_header(title: str, theme: Theme = None) -> None:
    """
    Render a styled page header with correct colors for light/dark mode.

    Args:
        title: Page title (can include emoji, e.g., "💳 Transactions")
        theme: Theme instance (if None, uses current theme from session)
    """
    if theme is None:
        theme = init_theme()

    # Use #FAFAFA for dark mode to match Streamlit's native heading color
    is_dark = theme.mode == "dark"
    heading_color = "#FAFAFA" if is_dark else theme.palette.text_primary

    # Use st.html for better control over styling (bypasses markdown sanitization)
    st.html(
        f'<div class="page-header" style="margin-bottom: 1.5rem;">'
        f'<h1 style="color: {heading_color} !important; font-size: 1.75rem; font-weight: 700; margin: 0;">{title}</h1>'
        f'</div>'
    )


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

    # UX Best Practice: Use outer glow instead of shadow for dark mode
    if theme.mode == "light":
        shadow = "box-shadow: 0 2px 8px rgba(0,0,0,0.1);"
    else:
        shadow = "box-shadow: 0 0 16px rgba(255,255,255,0.05);"

    card_css = f"""
        background: {gradient_colors};
        border: 1px solid {theme.get_color('border_light')};
        border-radius: 12px;
        padding: 1.5rem;
        {shadow}
    """

    # UX Best Practice: Use medium/bold fonts in dark mode (thin fonts appear faint)
    font_weight = "700" if theme.mode == "dark" else "600"

    st.markdown(f"""
        <div style='{card_css}'>
            <div style='font-size: 2rem; margin-bottom: 0.5rem'>{icon}</div>
            <div style='color: {theme.get_color('text_secondary')}; font-size: 0.9rem; margin-bottom: 0.5rem; font-weight: 500'>{label}</div>
            <div style='color: {theme.get_color('text_primary')}; font-size: 2rem; font-weight: {font_weight}'>{value}</div>
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
