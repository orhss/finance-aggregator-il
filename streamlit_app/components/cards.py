"""
Reusable card components for Streamlit UI.

Uses streamlit.components.v1.html() to render custom HTML cards that bypass
Streamlit's markdown sanitizer. Each component is self-contained with embedded styles.

Design System: Hybrid Material + Glassmorphism
- Solid cards with subtle shadows for main content (high readability)
- Gradient hero with glass overlay for visual focus
- Glass effects reserved for floating elements

Usage:
    from streamlit_app.components.cards import render_card, render_metric_row

    # Simple card with custom content
    render_card("My Title", "<p>Content here</p>", height=100)

    # Metric cards row (uses CSS from main.css)
    render_metric_row([
        {"value": "50,000", "label": "Total Balance"},
        {"value": "12", "label": "Accounts"},
    ])

    # List card with items
    items = [
        {"icon": "cart", "title": "Item 1", "subtitle": "Details", "value": "$10"},
        {"icon": "fuel", "title": "Item 2", "subtitle": "More details", "value": "$20"},
    ]
    render_list_card("My List", items, height=200)
"""

import streamlit as st
import streamlit.components.v1 as components
from typing import List, Dict, Any, Optional


# ============================================================================
# DESIGN TOKENS - Single source of truth for card component styling
# Aligned with streamlit_app/styles/design_tokens.py and main.css
# ============================================================================

# Light mode tokens
TOKENS_LIGHT = {
    # Colors - Light mode
    "color_primary": "#6366f1",
    "color_primary_light": "#818cf8",
    "color_text_primary": "#1f2937",
    "color_text_secondary": "#6b7280",
    "color_text_muted": "#9ca3af",
    "color_background": "#ffffff",
    "color_surface": "#ffffff",
    "color_surface_subtle": "#fafafa",
    "color_surface_hover": "#f9fafb",
    "color_border": "rgba(0,0,0,0.08)",
    "color_border_light": "rgba(0,0,0,0.05)",
    "color_border_divider": "#f3f4f6",  # For card header borders
    "color_border_subtle": "#f9fafb",    # For transaction item borders
    "color_expense": "#dc2626",
    "color_income": "#16a34a",
    "color_category_bg": "#eef2ff",

    # Typography
    "font_family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    "font_mono": "'SF Mono', 'Roboto Mono', Consolas, monospace",

    # Spacing & Sizing
    "radius_sm": "6px",
    "radius_md": "12px",
    "radius_lg": "16px",
    "radius_full": "9999px",

    # Shadows
    "shadow_sm": "0 1px 2px rgba(0,0,0,0.05)",
    "shadow_md": "0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -1px rgba(0,0,0,0.04)",

    # Transitions
    "transition_fast": "150ms ease",
    "transition_normal": "200ms ease",
}

# Dark mode tokens
TOKENS_DARK = {
    # Colors - Dark mode
    "color_primary": "#818cf8",
    "color_primary_light": "#a5b4fc",
    "color_text_primary": "#f1f5f9",
    "color_text_secondary": "#94a3b8",
    "color_text_muted": "#64748b",
    "color_background": "#0f172a",
    "color_surface": "#1e293b",
    "color_surface_subtle": "#0f172a",
    "color_surface_hover": "#334155",
    "color_border": "rgba(255,255,255,0.1)",
    "color_border_light": "rgba(255,255,255,0.05)",
    "color_border_divider": "#334155",  # For card header borders
    "color_border_subtle": "#1e293b",    # For transaction item borders
    "color_expense": "#f87171",
    "color_income": "#34d399",
    "color_category_bg": "rgba(129, 140, 248, 0.15)",

    # Typography (same as light)
    "font_family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    "font_mono": "'SF Mono', 'Roboto Mono', Consolas, monospace",

    # Spacing & Sizing (same as light)
    "radius_sm": "6px",
    "radius_md": "12px",
    "radius_lg": "16px",
    "radius_full": "9999px",

    # Shadows (darker for dark mode)
    "shadow_sm": "0 1px 2px rgba(0,0,0,0.2)",
    "shadow_md": "0 4px 6px -1px rgba(0,0,0,0.3), 0 2px 4px -1px rgba(0,0,0,0.2)",

    # Transitions (same as light)
    "transition_fast": "150ms ease",
    "transition_normal": "200ms ease",
}


def get_tokens() -> dict:
    """Get the appropriate tokens based on current theme mode."""
    theme_mode = st.session_state.get('theme_mode', 'light')
    return TOKENS_DARK if theme_mode == 'dark' else TOKENS_LIGHT


# Backwards compatibility - TOKENS defaults to light mode
TOKENS = TOKENS_LIGHT


# ============================================================================
# BASE CARD STYLES
# ============================================================================

def get_base_card_css() -> str:
    """Generate base card CSS with current theme tokens."""
    tokens = get_tokens()
    return f"""
* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}
body {{
    font-family: {tokens['font_family']};
    background: transparent;
    line-height: 1.5;
}}
.card {{
    background: {tokens['color_surface']};
    border-radius: {tokens['radius_lg']};
    padding: 1.25rem 1.5rem;
    box-shadow: {tokens['shadow_md']};
    border: 1px solid {tokens['color_border_light']};
}}
.card-header {{
    font-size: 1rem;
    font-weight: 600;
    color: {tokens['color_text_primary']};
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid {tokens['color_border_divider']};
}}
"""


# Keep BASE_CARD_CSS for backwards compatibility (uses light mode)
BASE_CARD_CSS = get_base_card_css.__doc__  # Placeholder, actual CSS generated dynamically


# ============================================================================
# CARD COMPONENTS
# ============================================================================

def render_card(
    title: str,
    content_html: str,
    height: int = 200,
    extra_css: str = ""
) -> None:
    """
    Render a basic card with title and custom HTML content.

    Args:
        title: Card header text (can include emoji)
        content_html: HTML string for card body
        height: Iframe height in pixels
        extra_css: Additional CSS rules to inject
    """
    base_css = get_base_card_css()
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
        {base_css}
        {extra_css}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="card-header">{title}</div>
            <div class="card-content">{content_html}</div>
        </div>
    </body>
    </html>
    """
    components.html(html, height=height, scrolling=False)


def render_metric_row(metrics: List[Dict[str, str]]) -> None:
    """
    Render a row of metric cards using shared CSS from main.css.

    This function uses st.markdown with the .metric-card class from main.css,
    ensuring consistent styling across all pages.

    Args:
        metrics: List of dicts with keys:
            - value: The metric value (string)
            - label: The metric label
            - sublabel: Optional sublabel text (e.g., delta or description)

    Example:
        render_metric_row([
            {"value": "50,000", "label": "Total Balance"},
            {"value": "12", "label": "Accounts", "sublabel": "3 active"},
        ])
    """
    cols = st.columns(len(metrics))
    for col, metric in zip(cols, metrics):
        with col:
            sublabel = metric.get('sublabel', '')
            # Always render sublabel div for consistent card height
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-value">{metric["value"]}</div>'
                f'<div class="metric-label">{metric["label"]}</div>'
                f'<div class="metric-sublabel">{sublabel}</div>'
                f'</div>',
                unsafe_allow_html=True
            )


def render_account_card(
    institution: str,
    balance: str,
    subtitle: str,
    status_icon: str = "",
    on_click_key: str = None
) -> bool:
    """
    Render an account card using shared CSS from main.css.

    Args:
        institution: Institution name (e.g., "CAL", "Excellence")
        balance: Formatted balance string
        subtitle: Subtitle text (e.g., "2 cards", "15 transactions")
        status_icon: Status emoji (default "")
        on_click_key: Optional key for a "View Details" button

    Returns:
        True if the button was clicked, False otherwise
    """
    # Determine if balance is negative for styling
    balance_class = "balance negative" if balance.startswith("-") or balance.startswith("-") else "balance"

    st.markdown(
        f'<div class="account-card">'
        f'<div class="icon">🏦</div>'
        f'<div class="info">'
        f'<div class="name">{status_icon} {institution}</div>'
        f'<div class="subtitle">{subtitle}</div>'
        f'</div>'
        f'<div class="{balance_class}">{balance}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    if on_click_key:
        return st.button("View Details", key=on_click_key, use_container_width=True)
    return False


def render_transaction_card(
    title: str,
    transactions: List[Dict[str, Any]],
    date_formatter: callable,
    height: Optional[int] = None,
    min_height: Optional[int] = None
) -> int:
    """
    Render a card with grouped transaction items.

    Args:
        title: Card header text
        transactions: List of transaction dicts with keys:
            - date: Date object for grouping
            - icon: Emoji icon
            - merchant: Merchant/description text
            - category: Optional category name
            - amount: Formatted amount string
            - is_positive: Boolean for color coding
        date_formatter: Function to format date for display (e.g., "Today", "Jan 20")
        height: Optional fixed height, auto-calculated if None
        min_height: Optional minimum height (for alignment with other cards)

    Returns:
        The actual height used (for alignment purposes)
    """
    # Group by date and build HTML
    items_html = []
    current_date = None

    for txn in transactions:
        # Date header
        if txn['date'] != current_date:
            current_date = txn['date']
            date_str = date_formatter(current_date)
            items_html.append(f'<div class="date-header">{date_str}</div>')

        # Category badge
        category_html = ""
        if txn.get('category'):
            category_html = f'<div class="txn-category">{txn["category"]}</div>'

        # Amount styling
        amount_class = "txn-amount positive" if txn.get('is_positive') else "txn-amount"

        items_html.append(
            f'<div class="txn-item">'
            f'<span class="txn-icon">{txn["icon"]}</span>'
            f'<div class="txn-details">'
            f'<div class="txn-merchant">{txn["merchant"]}</div>'
            f'{category_html}'
            f'</div>'
            f'<span class="{amount_class}">{txn["amount"]}</span>'
            f'</div>'
        )

    # Get theme-aware tokens
    tokens = get_tokens()

    extra_css = f"""
    .date-header {{
        font-size: 0.7rem;
        font-weight: 600;
        color: {tokens['color_text_muted']};
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin: 0.75rem 0 0.25rem 0;
        padding-top: 0.5rem;
    }}
    .date-header:first-child {{
        margin-top: 0;
        padding-top: 0;
    }}
    .txn-item {{
        display: flex;
        align-items: center;
        padding: 0.6rem 0;
        border-bottom: 1px solid {tokens['color_border_subtle']};
        transition: background-color {tokens['transition_fast']};
    }}
    .txn-item:hover {{
        background-color: {tokens['color_surface_hover']};
    }}
    .txn-item:last-child {{
        border-bottom: none;
    }}
    .txn-icon {{
        font-size: 1.2rem;
        margin-right: 0.75rem;
        width: 28px;
        text-align: center;
    }}
    .txn-details {{
        flex: 1;
        min-width: 0;
    }}
    .txn-merchant {{
        font-weight: 500;
        color: {tokens['color_text_primary']};
        font-size: 0.9rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .txn-category {{
        display: inline-block;
        font-size: 0.65rem;
        padding: 0.1rem 0.5rem;
        border-radius: {tokens['radius_full']};
        background: {tokens['color_category_bg']};
        color: {tokens['color_primary']};
        margin-top: 0.2rem;
        font-weight: 500;
    }}
    .txn-amount {{
        font-family: {tokens['font_mono']};
        font-weight: 500;
        font-size: 0.9rem;
        color: {tokens['color_expense']};
        text-align: right;
        min-width: 80px;
    }}
    .txn-amount.positive {{
        color: {tokens['color_income']};
    }}
    """

    # Auto-calculate height if not provided
    # Heights: header ~50px, date header ~30px, txn with category ~55px, txn without ~45px, padding ~30px
    if height is None:
        num_dates = len(set(t['date'] for t in transactions))
        num_with_category = sum(1 for t in transactions if t.get('category'))
        num_without_category = len(transactions) - num_with_category
        height = 80 + num_with_category * 58 + num_without_category * 48 + num_dates * 32

    # Apply minimum height if specified (for alignment)
    if min_height and height < min_height:
        height = min_height

    render_card(title, ''.join(items_html), height=height, extra_css=extra_css)
    return height


def render_summary_card(
    title: str,
    items: List[Dict[str, Any]],
    height: Optional[int] = None,
    min_height: Optional[int] = None
) -> int:
    """
    Render a card with summary items (e.g., accounts grouped by institution).

    Args:
        title: Card header text
        items: List of item dicts with keys:
            - name: Primary text (e.g., institution name)
            - subtitle: Secondary text (e.g., "2 cards")
            - value: Right-aligned value (e.g., formatted balance)
        height: Optional fixed height, auto-calculated if None
        min_height: Optional minimum height (for alignment with other cards)

    Returns:
        The actual height used (for alignment purposes)
    """
    items_html = []
    for item in items:
        # Check if value is negative for styling
        value = item.get("value", "")
        value_class = "summary-value negative" if "-" in str(value) and "" in str(value) else "summary-value"

        items_html.append(
            f'<div class="summary-item">'
            f'<div>'
            f'<div class="summary-name">{item["name"]}</div>'
            f'<div class="summary-subtitle">{item["subtitle"]}</div>'
            f'</div>'
            f'<div class="{value_class}">{value}</div>'
            f'</div>'
        )

    # Get theme-aware tokens
    tokens = get_tokens()

    extra_css = f"""
    .summary-item {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem 1rem;
        background: {tokens['color_surface_subtle']};
        border-radius: {tokens['radius_md']};
        margin-bottom: 0.5rem;
        transition: background-color {tokens['transition_fast']};
    }}
    .summary-item:hover {{
        background: {tokens['color_surface_hover']};
    }}
    .summary-item:last-child {{
        margin-bottom: 0;
    }}
    .summary-name {{
        font-weight: 600;
        color: {tokens['color_text_primary']};
        font-size: 0.95rem;
    }}
    .summary-subtitle {{
        font-size: 0.8rem;
        color: {tokens['color_text_secondary']};
    }}
    .summary-value {{
        font-family: {tokens['font_mono']};
        font-weight: 500;
        color: {tokens['color_text_primary']};
    }}
    .summary-value.negative {{
        color: {tokens['color_expense']};
    }}
    """

    # Auto-calculate height: header ~50px, each item ~70px, padding ~30px
    if height is None:
        height = 80 + len(items) * 72

    # Apply minimum height if specified (for alignment)
    if min_height and height < min_height:
        height = min_height

    render_card(title, ''.join(items_html), height=height, extra_css=extra_css)
    return height


def render_alert_card(
    icon: str,
    message: str,
    alert_type: str = "info",
    action_label: Optional[str] = None,
    action_key: Optional[str] = None
) -> bool:
    """
    Render an alert card with optional action button.

    Args:
        icon: Emoji icon for the alert
        message: Alert message text
        alert_type: Type of alert ('sync', 'category', 'uncategorized', 'info')
        action_label: Optional button label
        action_key: Optional key for button

    Returns:
        True if action button was clicked, False otherwise
    """
    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown(
            f'<div class="alert-card {alert_type}">'
            f'<span>{icon}</span>'
            f'<span class="alert-message">{message}</span>'
            f'</div>',
            unsafe_allow_html=True
        )
    with col2:
        if action_label and action_key:
            return st.button(action_label, key=action_key, use_container_width=True)
    return False


def render_insight_banner(
    icon: str,
    message: str,
    insight_type: str = "neutral"
) -> None:
    """
    Render an insight banner.

    Args:
        icon: Emoji icon for the insight
        message: Insight message text
        insight_type: Type of insight ('positive', 'neutral', 'warning')
    """
    st.markdown(
        f'<div class="insight-banner {insight_type}">'
        f'<span class="insight-icon">{icon}</span>'
        f'<span class="insight-message">{message}</span>'
        f'</div>',
        unsafe_allow_html=True
    )
