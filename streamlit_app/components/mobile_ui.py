"""
Mobile UI Components for Streamlit.

Touch-friendly, mobile-optimized components following fintech UX best practices.
"""

import streamlit as st
import streamlit.components.v1 as components
from typing import List, Dict, Any, Optional, Callable
from datetime import date
from streamlit_app.utils.mobile import is_mobile

# ===== MOBILE CSS =====

MOBILE_CSS = """
<style>
/* Mobile base styles */
.mobile-container {
    padding: 0;
    max-width: 100%;
    overflow-x: hidden;
}

/* Hero balance card - mobile optimized */
.mobile-hero {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 2rem 1.5rem;
    border-radius: 0 0 24px 24px;
    color: white;
    text-align: center;
    margin: -1rem -1rem 1rem -1rem;
}
.mobile-hero .label {
    font-size: 0.9rem;
    opacity: 0.9;
    margin-bottom: 0.5rem;
}
.mobile-hero .amount {
    font-size: 2.8rem;
    font-weight: 700;
    margin: 0;
    line-height: 1.1;
}
.mobile-hero .change {
    font-size: 0.85rem;
    opacity: 0.85;
    margin-top: 0.75rem;
}
.mobile-hero .change.positive { color: #86EFAC; }
.mobile-hero .change.negative { color: #FCA5A5; }

/* Summary card */
.mobile-summary-card {
    background: white;
    border-radius: 16px;
    padding: 1rem 1.25rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    margin-bottom: 0.75rem;
}
.mobile-summary-card .title {
    font-size: 0.8rem;
    color: #6b7280;
    margin-bottom: 0.25rem;
}
.mobile-summary-card .value {
    font-size: 1.5rem;
    font-weight: 600;
    color: #1f2937;
}
.mobile-summary-card .secondary {
    font-size: 0.75rem;
    color: #9ca3af;
    margin-top: 0.25rem;
}
.mobile-summary-card .progress-bar {
    height: 6px;
    background: #E5E7EB;
    border-radius: 999px;
    margin-top: 0.75rem;
    overflow: hidden;
}
.mobile-summary-card .progress-fill {
    height: 100%;
    border-radius: 999px;
    transition: width 0.3s ease;
}

/* Transaction card - touch friendly */
.mobile-transaction {
    background: white;
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 0.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    display: flex;
    align-items: center;
    min-height: 64px;
    cursor: pointer;
    transition: background 0.15s ease;
}
.mobile-transaction:active {
    background: #F3F4F6;
}
.mobile-transaction .icon {
    font-size: 1.75rem;
    margin-right: 0.75rem;
    width: 40px;
    text-align: center;
}
.mobile-transaction .details {
    flex: 1;
    min-width: 0;
}
.mobile-transaction .merchant {
    font-weight: 500;
    color: #1f2937;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.mobile-transaction .category {
    font-size: 0.75rem;
    color: #6b7280;
    margin-top: 0.125rem;
}
.mobile-transaction .amount {
    font-weight: 600;
    font-size: 1rem;
    text-align: right;
    min-width: 80px;
}
.mobile-transaction .amount.positive { color: #10B981; }
.mobile-transaction .amount.negative { color: #1f2937; }

/* Date separator */
.mobile-date-separator {
    font-size: 0.75rem;
    color: #6b7280;
    font-weight: 500;
    padding: 0.75rem 0 0.5rem 0;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Bottom navigation */
.mobile-bottom-nav {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: white;
    border-top: 1px solid #E5E7EB;
    display: flex;
    justify-content: space-around;
    padding: 0.5rem 0 calc(0.5rem + env(safe-area-inset-bottom, 0));
    z-index: 1000;
}
.mobile-nav-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 0.5rem 1rem;
    color: #6b7280;
    text-decoration: none;
    font-size: 0.7rem;
    transition: color 0.15s ease;
}
.mobile-nav-item.active {
    color: #667eea;
}
.mobile-nav-item .icon {
    font-size: 1.5rem;
    margin-bottom: 0.25rem;
}

/* Alert banner */
.mobile-alert {
    background: #FEF3C7;
    border-left: 4px solid #F59E0B;
    padding: 0.75rem 1rem;
    border-radius: 8px;
    margin-bottom: 0.75rem;
    font-size: 0.85rem;
    color: #92400E;
}
.mobile-alert.info {
    background: #DBEAFE;
    border-left-color: #3B82F6;
    color: #1E40AF;
}

/* Quick categorize */
.mobile-category-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.5rem;
    margin: 1rem 0;
}
.mobile-category-btn {
    background: white;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    padding: 1rem;
    text-align: center;
    cursor: pointer;
    transition: all 0.15s ease;
}
.mobile-category-btn:active {
    background: #667eea;
    color: white;
    border-color: #667eea;
}
.mobile-category-btn .icon {
    font-size: 1.5rem;
    margin-bottom: 0.25rem;
}
.mobile-category-btn .label {
    font-size: 0.8rem;
    font-weight: 500;
}

/* Search bar */
.mobile-search {
    position: relative;
    margin-bottom: 1rem;
}
.mobile-search input {
    width: 100%;
    padding: 0.75rem 1rem 0.75rem 2.5rem;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    font-size: 1rem;
    outline: none;
}
.mobile-search input:focus {
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

/* Filter chips */
.mobile-filter-chips {
    display: flex;
    gap: 0.5rem;
    overflow-x: auto;
    padding-bottom: 0.5rem;
    margin-bottom: 0.75rem;
    -webkit-overflow-scrolling: touch;
}
.mobile-filter-chip {
    flex-shrink: 0;
    padding: 0.5rem 1rem;
    background: #F3F4F6;
    border-radius: 999px;
    font-size: 0.85rem;
    color: #374151;
    cursor: pointer;
    transition: all 0.15s ease;
}
.mobile-filter-chip.active {
    background: #667eea;
    color: white;
}

/* Spacing for bottom nav */
.mobile-content {
    padding-bottom: 80px;
}
</style>
"""


def apply_mobile_css():
    """Inject mobile CSS styles into the page."""
    st.markdown(MOBILE_CSS, unsafe_allow_html=True)


# ===== COMPONENTS =====

def hero_balance_card(balance: str, label: str = "Total Balance", change: Optional[str] = None, change_positive: bool = True):
    """
    Render hero balance card at the top of mobile pages.

    Args:
        balance: Formatted balance string (e.g., "₪12,345")
        label: Label above balance
        change: Optional change indicator (e.g., "+₪500 this week")
        change_positive: Whether change is positive (affects color)
    """
    change_html = ""
    if change:
        change_class = "positive" if change_positive else "negative"
        change_html = f'<div class="change {change_class}">{change}</div>'

    st.markdown(
        f'<div class="mobile-hero">'
        f'<div class="label">{label}</div>'
        f'<div class="amount">{balance}</div>'
        f'{change_html}'
        f'</div>',
        unsafe_allow_html=True
    )


def summary_card(title: str, value: str, secondary: Optional[str] = None, progress: Optional[float] = None, progress_color: str = "#667eea"):
    """
    Render a summary card with optional progress bar.

    Args:
        title: Card title
        value: Main value to display
        secondary: Optional secondary text
        progress: Optional progress percentage (0-100)
        progress_color: Color for progress bar
    """
    progress_html = ""
    if progress is not None:
        progress_html = f'''
        <div class="progress-bar">
            <div class="progress-fill" style="width: {min(progress, 100)}%; background: {progress_color};"></div>
        </div>
        '''

    secondary_html = f'<div class="secondary">{secondary}</div>' if secondary else ""

    st.markdown(
        f'<div class="mobile-summary-card">'
        f'<div class="title">{title}</div>'
        f'<div class="value">{value}</div>'
        f'{secondary_html}'
        f'{progress_html}'
        f'</div>',
        unsafe_allow_html=True
    )


def transaction_list(transactions: List[Dict[str, Any]], date_formatter: Optional[Callable] = None):
    """
    Render a touch-friendly transaction list with date separators.

    Args:
        transactions: List of transaction dicts with keys:
            - date: Transaction date
            - icon: Category icon emoji
            - merchant: Merchant name
            - category: Category name (optional)
            - amount: Formatted amount string
            - is_positive: Whether amount is positive
        date_formatter: Optional function to format dates (date -> str)
    """
    if not transactions:
        st.info("No transactions to display")
        return

    if date_formatter is None:
        date_formatter = lambda d: d.strftime("%a, %b %d") if isinstance(d, date) else str(d)

    current_date = None
    html_parts = []

    for txn in transactions:
        txn_date = txn.get('date')
        if txn_date != current_date:
            current_date = txn_date
            date_str = date_formatter(txn_date)
            html_parts.append(f'<div class="mobile-date-separator">{date_str}</div>')

        icon = txn.get('icon', '💳')
        merchant = txn.get('merchant', 'Unknown')
        category = txn.get('category', '')
        amount = txn.get('amount', '₪0')
        amount_class = 'positive' if txn.get('is_positive', False) else 'negative'

        category_html = f'<div class="category">{category}</div>' if category else ""

        html_parts.append(
            f'<div class="mobile-transaction">'
            f'<div class="icon">{icon}</div>'
            f'<div class="details">'
            f'<div class="merchant">{merchant}</div>'
            f'{category_html}'
            f'</div>'
            f'<div class="amount {amount_class}">{amount}</div>'
            f'</div>'
        )

    st.markdown(''.join(html_parts), unsafe_allow_html=True)


def bottom_navigation(current: str = "home"):
    """
    Render bottom navigation bar.

    Note: Due to Streamlit constraints, this uses buttons rather than fixed HTML.
    Call this at the end of mobile pages.

    Args:
        current: Current active page ("home", "transactions", "analytics", "settings")
    """
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)  # Spacer

    cols = st.columns(4)

    nav_items = [
        ("home", "🏠", "Home", "app.py"),
        ("transactions", "💳", "Transactions", "pages/1_💳_Transactions.py"),
        ("analytics", "📈", "Analytics", "pages/2_📈_Analytics.py"),
        ("settings", "⚙️", "Settings", "pages/5_⚙️_Settings.py"),
    ]

    for idx, (key, icon, label, page) in enumerate(nav_items):
        with cols[idx]:
            btn_type = "primary" if current == key else "secondary"
            if st.button(f"{icon}\n{label}", key=f"nav_{key}", use_container_width=True, type=btn_type):
                st.switch_page(page)


def alert_banner(message: str, alert_type: str = "warning"):
    """
    Render an alert banner.

    Args:
        message: Alert message
        alert_type: "warning" or "info"
    """
    st.markdown(
        f'<div class="mobile-alert {alert_type}">{message}</div>',
        unsafe_allow_html=True
    )


def filter_chips(options: List[str], selected: str, key: str = "filter") -> str:
    """
    Render horizontal scrolling filter chips.

    Args:
        options: List of filter option labels
        selected: Currently selected option
        key: Unique key for the component

    Returns:
        Selected option label
    """
    cols = st.columns(len(options))
    for idx, option in enumerate(options):
        with cols[idx]:
            btn_type = "primary" if option == selected else "secondary"
            if st.button(option, key=f"{key}_{idx}", use_container_width=True, type=btn_type):
                return option
    return selected


def quick_categorize_card(
    transaction: Dict[str, Any],
    categories: List[Dict[str, str]],
    on_categorize: Callable[[str], None],
    on_skip: Callable[[], None],
    progress: Optional[tuple] = None,
):
    """
    Render quick categorization card for a transaction.

    Args:
        transaction: Transaction dict with merchant, amount, date
        categories: List of category dicts with 'name' and 'icon'
        on_categorize: Callback when category is selected (receives category name)
        on_skip: Callback when skip is pressed
        progress: Optional (current, total) tuple for progress indicator
    """
    # Progress indicator
    if progress:
        current, total = progress
        st.markdown(f"**Categorizing {current} of {total}**")
        st.progress(current / total)

    # Transaction info
    st.markdown(f"### {transaction.get('merchant', 'Unknown')}")
    st.markdown(f"**{transaction.get('amount', '₪0')}** • {transaction.get('date', '')}")

    st.markdown("---")

    # Category grid (4x2 for top 8)
    grid_categories = categories[:8]
    cols_per_row = 4
    rows = (len(grid_categories) + cols_per_row - 1) // cols_per_row

    for row in range(rows):
        cols = st.columns(cols_per_row)
        for col_idx in range(cols_per_row):
            cat_idx = row * cols_per_row + col_idx
            if cat_idx < len(grid_categories):
                cat = grid_categories[cat_idx]
                with cols[col_idx]:
                    if st.button(f"{cat['icon']}\n{cat['name']}", key=f"cat_{cat_idx}", use_container_width=True):
                        on_categorize(cat['name'])

    # More and Skip buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("More...", use_container_width=True, type="secondary"):
            # Could expand to show all categories
            pass
    with col2:
        if st.button("Skip", use_container_width=True, type="secondary"):
            on_skip()


def mobile_quick_settings():
    """
    Render quick settings bar for mobile - Privacy & Dark Mode.

    Shows compact toggle buttons at the top of mobile pages since the sidebar
    is collapsed by default on mobile devices.

    Only renders when on mobile. Call at the top of page content after theme application.
    """
    if not is_mobile():
        return

    from streamlit_app.config.theme import set_theme_mode

    is_private = st.session_state.get('mask_balances', False)
    current_mode = st.session_state.get('theme_mode', 'light')
    is_dark = current_mode == 'dark'

    # Create right-aligned compact buttons
    _, col_privacy, col_theme = st.columns([4, 1, 1])

    with col_privacy:
        privacy_icon = "🙈" if is_private else "👁️"
        if st.button(privacy_icon, key="mobile_privacy_toggle", help="Toggle privacy mode"):
            st.session_state.mask_balances = not is_private
            st.rerun()

    with col_theme:
        theme_icon = "🌙" if is_dark else "☀️"
        if st.button(theme_icon, key="mobile_theme_toggle", help="Toggle dark mode"):
            new_mode = 'light' if is_dark else 'dark'
            st.session_state.theme_mode = new_mode
            set_theme_mode(new_mode)
            st.rerun()
