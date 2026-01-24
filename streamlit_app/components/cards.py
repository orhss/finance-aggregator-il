"""
Reusable card components for Streamlit UI.

Uses streamlit.components.v1.html() to render custom HTML cards that bypass
Streamlit's markdown sanitizer. Each component is self-contained with embedded styles.

Usage:
    from streamlit_app.components.cards import render_card, render_metric_row

    # Simple card with custom content
    render_card("My Title", "<p>Content here</p>", height=100)

    # Metric cards row (uses CSS from main.css)
    render_metric_row([
        {"value": "₪50,000", "label": "Total Balance"},
        {"value": "12", "label": "Accounts"},
    ])

    # List card with items
    items = [
        {"icon": "🛒", "title": "Item 1", "subtitle": "Details", "value": "$10"},
        {"icon": "⛽", "title": "Item 2", "subtitle": "More details", "value": "$20"},
    ]
    render_list_card("My List", items, height=200)
"""

import streamlit as st
import streamlit.components.v1 as components
from typing import List, Dict, Any, Optional


# ============================================================================
# SHARED STYLES
# ============================================================================

# Design tokens - single source of truth for colors, fonts, spacing
TOKENS = {
    # Colors
    "color_text_primary": "#1f2937",
    "color_text_secondary": "#6b7280",
    "color_text_muted": "#9ca3af",
    "color_background": "white",
    "color_background_subtle": "#fafafa",
    "color_border": "#f0f0f0",
    "color_border_light": "#f3f4f6",
    "color_expense": "#dc2626",
    "color_income": "#16a34a",
    # Typography
    "font_family": '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    "font_mono": "'SF Mono', 'Roboto Mono', monospace",
    # Spacing & Sizing
    "border_radius_card": "16px",
    "border_radius_item": "10px",
    "shadow_card": "0 2px 8px rgba(0,0,0,0.06)",
    "padding_card": "1.25rem 1.5rem",
}

# Base card styles (shared across all card types)
BASE_CARD_CSS = f"""
.card {{
    background: {TOKENS['color_background']};
    border-radius: {TOKENS['border_radius_card']};
    padding: {TOKENS['padding_card']};
    box-shadow: {TOKENS['shadow_card']};
    border: 1px solid {TOKENS['color_border']};
    font-family: {TOKENS['font_family']};
}}
.card-header {{
    font-size: 1rem;
    font-weight: 600;
    color: {TOKENS['color_text_primary']};
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid {TOKENS['color_border_light']};
}}
"""


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
    html = f"""
    <style>
    {BASE_CARD_CSS}
    {extra_css}
    </style>
    <div class="card">
        <div class="card-header">{title}</div>
        <div class="card-content">{content_html}</div>
    </div>
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
            {"value": "₪50,000", "label": "Total Balance"},
            {"value": "12", "label": "Accounts", "sublabel": "3 active"},
        ])
    """
    cols = st.columns(len(metrics))
    for col, metric in zip(cols, metrics):
        with col:
            sublabel = metric.get('sublabel', '')
            sublabel_html = f'<div class="sublabel">{sublabel}</div>' if sublabel else ''
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="value">{metric["value"]}</div>'
                f'<div class="label">{metric["label"]}</div>'
                f'{sublabel_html}'
                f'</div>',
                unsafe_allow_html=True
            )


def render_account_card(
    institution: str,
    balance: str,
    subtitle: str,
    status_icon: str = "✅",
    on_click_key: str = None
) -> bool:
    """
    Render an account card using shared CSS from main.css.

    Args:
        institution: Institution name (e.g., "CAL", "Excellence")
        balance: Formatted balance string
        subtitle: Subtitle text (e.g., "2 cards", "15 transactions")
        status_icon: Status emoji (default "✅")
        on_click_key: Optional key for a "View Details" button

    Returns:
        True if the button was clicked, False otherwise
    """
    st.markdown(
        f'<div class="account-card">'
        f'<div class="icon">🏦</div>'
        f'<div class="info">'
        f'<div class="name">{status_icon} {institution}</div>'
        f'<div class="subtitle">{subtitle}</div>'
        f'</div>'
        f'<div class="balance">{balance}</div>'
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

    extra_css = f"""
    .date-header {{
        font-size: 0.7rem;
        font-weight: 600;
        color: {TOKENS['color_text_muted']};
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
        border-bottom: 1px solid {TOKENS['color_border_light']};
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
        color: {TOKENS['color_text_primary']};
        font-size: 0.9rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .txn-category {{
        display: inline-block;
        font-size: 0.7rem;
        padding: 0.1rem 0.5rem;
        border-radius: 9999px;
        background: {TOKENS['color_border_light']};
        color: {TOKENS['color_text_secondary']};
        margin-top: 0.2rem;
    }}
    .txn-amount {{
        font-family: {TOKENS['font_mono']};
        font-weight: 500;
        font-size: 0.9rem;
        color: {TOKENS['color_expense']};
        text-align: right;
        min-width: 80px;
    }}
    .txn-amount.positive {{
        color: {TOKENS['color_income']};
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
        items_html.append(
            f'<div class="summary-item">'
            f'<div>'
            f'<div class="summary-name">{item["name"]}</div>'
            f'<div class="summary-subtitle">{item["subtitle"]}</div>'
            f'</div>'
            f'<div class="summary-value">{item["value"]}</div>'
            f'</div>'
        )

    extra_css = f"""
    .summary-item {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem;
        background: {TOKENS['color_background_subtle']};
        border-radius: {TOKENS['border_radius_item']};
        margin-bottom: 0.5rem;
    }}
    .summary-item:last-child {{
        margin-bottom: 0;
    }}
    .summary-name {{
        font-weight: 600;
        color: {TOKENS['color_text_primary']};
        font-size: 0.95rem;
    }}
    .summary-subtitle {{
        font-size: 0.8rem;
        color: {TOKENS['color_text_secondary']};
    }}
    .summary-value {{
        font-family: {TOKENS['font_mono']};
        font-weight: 500;
        color: {TOKENS['color_text_primary']};
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