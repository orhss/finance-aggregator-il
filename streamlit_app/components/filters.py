"""
Reusable filter components for Streamlit pages
Provides consistent filtering UI across the application
"""

import streamlit as st
from datetime import datetime, date, timedelta
from typing import Optional, Tuple, List, Literal
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from streamlit_app.utils.analytics_helpers import get_period_options


def date_range_picker(
    key_prefix: str = "date",
    mode: Literal["dropdown", "buttons"] = "dropdown",
    show_custom: bool = True,
    include_options: Optional[List[str]] = None,
    default_option: str = "Last 3 Months",
) -> Tuple[date, date]:
    """
    Unified date range picker with presets.

    Uses get_period_options() for consistent date calculations across the app.

    Args:
        key_prefix: Unique prefix for widget keys
        mode: "dropdown" for selectbox, "buttons" for button row
        show_custom: Whether to allow custom date selection
        include_options: List of period names to include (default: all)
        default_option: Which option to select by default

    Returns:
        Tuple of (start_date, end_date)
    """
    today = date.today()
    period_options = get_period_options(today)

    # Filter to requested options
    if include_options:
        period_options = {k: v for k, v in period_options.items() if k in include_options}

    option_names = list(period_options.keys())
    if show_custom:
        option_names.append("Custom")

    # Determine default index
    default_idx = 0
    if default_option in option_names:
        default_idx = option_names.index(default_option)

    if mode == "dropdown":
        selected = st.selectbox(
            "Date Range",
            options=option_names,
            index=default_idx,
            key=f"{key_prefix}_range_select"
        )

        if selected == "Custom":
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "From",
                    value=today - timedelta(days=90),
                    max_value=today,
                    key=f"{key_prefix}_custom_start"
                )
            with col2:
                end_date = st.date_input(
                    "To",
                    value=today,
                    max_value=today,
                    min_value=start_date,
                    key=f"{key_prefix}_custom_end"
                )
            return start_date, end_date
        else:
            return period_options[selected]

    else:  # buttons mode
        # Store selection in session state
        state_key = f"{key_prefix}_selected_period"
        if state_key not in st.session_state:
            st.session_state[state_key] = default_option

        cols = st.columns(len(option_names))
        for i, option in enumerate(option_names):
            with cols[i]:
                is_selected = st.session_state[state_key] == option
                if st.button(
                    option,
                    key=f"{key_prefix}_btn_{option.replace(' ', '_').lower()}",
                    type="primary" if is_selected else "secondary",
                    width="stretch"
                ):
                    st.session_state[state_key] = option
                    st.rerun()

        selected = st.session_state[state_key]

        if selected == "Custom":
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "From",
                    value=today - timedelta(days=90),
                    max_value=today,
                    key=f"{key_prefix}_custom_start"
                )
            with col2:
                end_date = st.date_input(
                    "To",
                    value=today,
                    max_value=today,
                    min_value=start_date,
                    key=f"{key_prefix}_custom_end"
                )
            return start_date, end_date
        else:
            return period_options[selected]


def account_filter(
    key_prefix: str,
    accounts: Optional[List[dict]] = None
) -> List[int]:
    """
    Create account multi-select filter

    Args:
        key_prefix: Unique prefix for widget keys
        accounts: List of account dicts with 'id' and 'name' keys

    Returns:
        List of selected account IDs
    """
    if not accounts:
        st.info("No accounts available. Sync data first.")
        return []

    # Group accounts by type for better organization
    account_options = {
        f"{acc.get('institution', 'Unknown')} - {acc.get('name', acc.get('account_number', 'Unknown'))}": acc['id']
        for acc in accounts
    }

    selected_names = st.multiselect(
        "Select Accounts",
        options=list(account_options.keys()),
        default=[],
        key=f"{key_prefix}_accounts"
    )

    # Convert names back to IDs
    return [account_options[name] for name in selected_names]


def institution_filter(
    key_prefix: str,
    institutions: Optional[List[str]] = None
) -> List[str]:
    """
    Create institution multi-select filter

    Args:
        key_prefix: Unique prefix for widget keys
        institutions: List of institution names (if None, use default list)

    Returns:
        List of selected institution names
    """
    if institutions is None:
        # Default institutions
        institutions = [
            "CAL", "Max", "Isracard",  # Credit cards
            "Excellence", "Meitav",     # Brokers
            "Migdal", "Phoenix"         # Pensions
        ]

    selected = st.multiselect(
        "Select Institutions",
        options=institutions,
        default=[],
        key=f"{key_prefix}_institutions"
    )

    return selected


def status_filter(key_prefix: str) -> str:
    """
    Create status radio filter

    Args:
        key_prefix: Unique prefix for widget keys

    Returns:
        Selected status ('all', 'pending', 'completed')
    """
    status = st.radio(
        "Transaction Status",
        options=["All", "Pending", "Completed"],
        index=0,
        horizontal=True,
        key=f"{key_prefix}_status"
    )

    return status.lower()


def category_filter(
    key_prefix: str,
    categories: Optional[List[str]] = None
) -> List[str]:
    """
    Create category multi-select filter

    Args:
        key_prefix: Unique prefix for widget keys
        categories: List of available categories

    Returns:
        List of selected categories
    """
    if not categories:
        categories = []

    selected = st.multiselect(
        "Select Categories",
        options=categories,
        default=[],
        key=f"{key_prefix}_categories"
    )

    return selected


def unified_category_filter(
    key_prefix: str,
    include_unmapped: bool = True
) -> Tuple[List[str], bool]:
    """
    Create unified category filter with optional unmapped toggle.

    Fetches unified categories from CategoryMapping table.

    Args:
        key_prefix: Unique prefix for widget keys
        include_unmapped: If True, show checkbox for filtering unmapped transactions

    Returns:
        Tuple of (selected unified categories, unmapped_only flag)
    """
    try:
        from db.database import get_session
        from db.models import CategoryMapping
        from sqlalchemy import distinct

        session = get_session()
        unified_cats = session.query(distinct(CategoryMapping.unified_category)).order_by(
            CategoryMapping.unified_category
        ).all()
        categories = [c[0] for c in unified_cats if c[0]]
    except Exception:
        categories = []

    selected = st.multiselect(
        "Unified Categories",
        options=categories,
        default=[],
        key=f"{key_prefix}_unified_categories",
        help="Filter by normalized category names"
    )

    unmapped_only = False
    if include_unmapped:
        unmapped_only = st.checkbox(
            "Unmapped only",
            key=f"{key_prefix}_unmapped_only",
            help="Show only transactions without a category mapping"
        )

    return selected, unmapped_only


def tag_filter(
    key_prefix: str,
    tags: Optional[List[str]] = None,
    use_and_logic: bool = True
) -> List[str]:
    """
    Create tag multi-select filter

    Args:
        key_prefix: Unique prefix for widget keys
        tags: List of available tags
        use_and_logic: If True, use AND logic (all tags must match)

    Returns:
        List of selected tags
    """
    if not tags:
        tags = []

    st.caption(f"Filter by tags ({'AND' if use_and_logic else 'OR'} logic)")

    selected = st.multiselect(
        "Select Tags",
        options=tags,
        default=[],
        key=f"{key_prefix}_tags",
        label_visibility="collapsed"
    )

    return selected


def search_filter(key_prefix: str) -> str:
    """
    Create search text input filter

    Args:
        key_prefix: Unique prefix for widget keys

    Returns:
        Search query string
    """
    query = st.text_input(
        "Search descriptions",
        placeholder="Enter search term...",
        key=f"{key_prefix}_search"
    )

    return query.strip()


def amount_range_filter(
    key_prefix: str,
    min_amount: float = -10000,
    max_amount: float = 10000
) -> Tuple[float, float]:
    """
    Create amount range slider filter

    Args:
        key_prefix: Unique prefix for widget keys
        min_amount: Minimum possible amount
        max_amount: Maximum possible amount

    Returns:
        Tuple of (min_selected, max_selected)
    """
    amount_range = st.slider(
        "Amount Range",
        min_value=float(min_amount),
        max_value=float(max_amount),
        value=(float(min_amount), float(max_amount)),
        key=f"{key_prefix}_amount_range"
    )

    return amount_range


def clear_filters_button(key_prefix: str, callback=None) -> bool:
    """
    Create a button to clear all filters

    Args:
        key_prefix: Prefix to identify related filter keys
        callback: Optional callback function to run after clearing

    Returns:
        True if button was clicked
    """
    if st.button("🔄 Clear All Filters", key=f"{key_prefix}_clear"):
        # Clear session state keys related to this filter set
        keys_to_clear = [k for k in st.session_state.keys() if k.startswith(key_prefix)]
        for key in keys_to_clear:
            del st.session_state[key]

        if callback:
            callback()

        st.rerun()
        return True

    return False


