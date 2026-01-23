"""
Reusable filter components for Streamlit pages
Provides consistent filtering UI across the application
"""

import streamlit as st
from datetime import datetime, date, timedelta
from typing import Optional, Tuple, List
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def date_range_filter(
    key_prefix: str,
    default_months_back: int = 3
) -> Tuple[date, date]:
    """
    Create date range filter with start and end date

    Args:
        key_prefix: Unique prefix for widget keys
        default_months_back: Default months to go back from today

    Returns:
        Tuple of (start_date, end_date)
    """
    col1, col2 = st.columns(2)

    # Default date range
    end_date = date.today()
    start_date = end_date - timedelta(days=30 * default_months_back)

    with col1:
        start = st.date_input(
            "Start Date",
            value=start_date,
            key=f"{key_prefix}_start_date"
        )

    with col2:
        end = st.date_input(
            "End Date",
            value=end_date,
            key=f"{key_prefix}_end_date"
        )

    return start, end


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


def quick_date_buttons(key_prefix: str) -> Optional[Tuple[date, date]]:
    """
    Create quick date range selection buttons

    Args:
        key_prefix: Unique prefix for widget keys

    Returns:
        Tuple of (start_date, end_date) if button clicked, None otherwise
    """
    st.caption("Quick Select:")

    col1, col2, col3, col4 = st.columns(4)

    today = date.today()

    with col1:
        if st.button("This Month", key=f"{key_prefix}_this_month"):
            start = today.replace(day=1)
            return start, today

    with col2:
        if st.button("Last Month", key=f"{key_prefix}_last_month"):
            first_of_this_month = today.replace(day=1)
            end = first_of_this_month - timedelta(days=1)
            start = end.replace(day=1)
            return start, end

    with col3:
        if st.button("Last 3 Months", key=f"{key_prefix}_last_3_months"):
            start = today - timedelta(days=90)
            return start, today

    with col4:
        if st.button("This Year", key=f"{key_prefix}_this_year"):
            start = today.replace(month=1, day=1)
            return start, today

    return None


def date_range_filter_with_presets(
    key_prefix: str = "",
    default_months_back: int = 3,
    data_start: Optional[date] = None,
    data_end: Optional[date] = None
) -> Tuple[date, date]:
    """
    Date range filter with quick preset buttons and data coverage info.

    Args:
        key_prefix: Unique prefix for widget keys
        default_months_back: Default months to go back from today
        data_start: Earliest date with data (for showing coverage info)
        data_end: Latest date with data (for showing coverage info)

    Returns:
        Tuple of (start_date, end_date)
    """
    today = date.today()

    # Show data coverage info if available
    if data_start and data_end:
        st.caption(f"📊 Data available: {data_start.strftime('%b %d, %Y')} to {data_end.strftime('%b %d, %Y')}")

    st.markdown("**Quick Ranges:**")

    # Quick preset buttons in a single row
    col1, col2, col3, col4, col5 = st.columns(5)

    # Initialize session state for dates if not set
    if f"{key_prefix}_start" not in st.session_state:
        st.session_state[f"{key_prefix}_start"] = today - timedelta(days=30 * default_months_back)
    if f"{key_prefix}_end" not in st.session_state:
        st.session_state[f"{key_prefix}_end"] = today

    with col1:
        if st.button("📅 This Month", key=f"{key_prefix}_btn_this_month", use_container_width=True):
            st.session_state[f"{key_prefix}_start"] = today.replace(day=1)
            st.session_state[f"{key_prefix}_end"] = today
            st.rerun()

    with col2:
        if st.button("📅 Last Month", key=f"{key_prefix}_btn_last_month", use_container_width=True):
            last_month = today.replace(day=1) - timedelta(days=1)
            st.session_state[f"{key_prefix}_start"] = last_month.replace(day=1)
            st.session_state[f"{key_prefix}_end"] = last_month
            st.rerun()

    with col3:
        if st.button("📅 Last 3 Months", key=f"{key_prefix}_btn_3months", use_container_width=True):
            st.session_state[f"{key_prefix}_start"] = today - timedelta(days=90)
            st.session_state[f"{key_prefix}_end"] = today
            st.rerun()

    with col4:
        if st.button("📅 This Year", key=f"{key_prefix}_btn_this_year", use_container_width=True):
            st.session_state[f"{key_prefix}_start"] = today.replace(month=1, day=1)
            st.session_state[f"{key_prefix}_end"] = today
            st.rerun()

    with col5:
        if st.button("📅 Last Year", key=f"{key_prefix}_btn_last_year", use_container_width=True):
            last_year = today.year - 1
            st.session_state[f"{key_prefix}_start"] = date(last_year, 1, 1)
            st.session_state[f"{key_prefix}_end"] = date(last_year, 12, 31)
            st.rerun()

    # Manual date pickers
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "From",
            value=st.session_state.get(f"{key_prefix}_start", today - timedelta(days=90)),
            max_value=today,
            key=f"{key_prefix}_date_start_input"
        )
        # Update session state
        st.session_state[f"{key_prefix}_start"] = start_date

    with col2:
        end_date = st.date_input(
            "To",
            value=st.session_state.get(f"{key_prefix}_end", today),
            max_value=today,
            min_value=start_date,
            key=f"{key_prefix}_date_end_input"
        )
        # Update session state
        st.session_state[f"{key_prefix}_end"] = end_date

    return start_date, end_date
