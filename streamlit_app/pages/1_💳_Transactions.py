"""
Transactions Browser Page - View, filter, search, and manage transactions
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import sys
from pathlib import Path
from typing import List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from streamlit_app.utils.session import init_session_state, get_db_session, get_tag_service, get_all_categories, get_all_tags, format_amount_private
from streamlit_app.utils.formatters import (
    format_number, format_datetime,
    format_transaction_amount, color_for_amount, AMOUNT_STYLE_CSS
)
from streamlit_app.utils.rtl import fix_rtl, has_hebrew
from streamlit_app.utils.cache import get_transactions_cached, invalidate_transaction_cache, invalidate_tag_cache
from streamlit_app.utils.errors import safe_call_with_spinner, ErrorBoundary, show_success, show_warning
from streamlit_app.components.sidebar import render_minimal_sidebar
from streamlit_app.components.empty_states import empty_transactions_state
# Filters are now inline for better coherence
from streamlit_app.components.theme import apply_theme, render_page_header
from streamlit_app.utils.mobile import detect_mobile, is_mobile
from streamlit_app.auth import check_authentication
from streamlit_app.components.mobile_ui import (
    apply_mobile_css,
    transaction_list,
    bottom_navigation,
    filter_chips,
)
from streamlit_app.utils.formatters import get_category_icon

# Page config
st.set_page_config(
    page_title="Transactions - Financial Aggregator",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="collapsed" if 'mobile' in st.query_params else "expanded"
)

# Initialize session state
init_session_state()

# Check authentication (if enabled)
if not check_authentication():
    st.stop()

# Mobile detection
detect_mobile()


def render_mobile_transactions():
    """Render mobile-optimized transactions view."""
    from db.database import get_session
    from db.models import Account, Transaction
    from sqlalchemy import func, and_, desc

    # Apply theme (for dark mode support)
    apply_theme()

    # Apply mobile CSS
    apply_mobile_css()

    session = get_session()

    # Check for data
    transaction_count = session.query(func.count(Transaction.id)).scalar()
    if not transaction_count:
        st.info("No transactions yet. Sync your accounts to see transactions.")
        bottom_navigation(current="transactions")
        return

    # Header
    render_page_header("💳 Transactions")

    # Search bar
    search = st.text_input(
        "Search",
        placeholder="Search transactions...",
        key="mobile_search",
        label_visibility="collapsed"
    )

    # Date filter presets
    today = date.today()
    date_presets = {
        "This Month": (today.replace(day=1), today),
        "Last Month": ((today.replace(day=1) - timedelta(days=1)).replace(day=1), today.replace(day=1) - timedelta(days=1)),
        "Last 3 Months": (today - timedelta(days=90), today),
        "All Time": (today - timedelta(days=365*5), today),
    }

    selected_preset = st.selectbox(
        "Date Range",
        options=list(date_presets.keys()),
        index=0,
        key="mobile_date_preset",
        label_visibility="collapsed"
    )

    start_date, end_date = date_presets[selected_preset]

    # Quick filter chips for transaction type
    st.markdown("**Quick Filters**")
    filter_cols = st.columns(4)

    type_filter = st.session_state.get('mobile_type_filter', 'All')
    with filter_cols[0]:
        if st.button("All", type="primary" if type_filter == "All" else "secondary", use_container_width=True):
            st.session_state.mobile_type_filter = "All"
            st.rerun()
    with filter_cols[1]:
        if st.button("Expenses", type="primary" if type_filter == "Expenses" else "secondary", use_container_width=True):
            st.session_state.mobile_type_filter = "Expenses"
            st.rerun()
    with filter_cols[2]:
        if st.button("Income", type="primary" if type_filter == "Income" else "secondary", use_container_width=True):
            st.session_state.mobile_type_filter = "Income"
            st.rerun()
    with filter_cols[3]:
        if st.button("Pending", type="primary" if type_filter == "Pending" else "secondary", use_container_width=True):
            st.session_state.mobile_type_filter = "Pending"
            st.rerun()

    type_filter = st.session_state.get('mobile_type_filter', 'All')

    # Build query
    query = session.query(Transaction).filter(
        and_(
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date
        )
    )

    # Apply type filter
    if type_filter == "Expenses":
        query = query.filter(Transaction.original_amount < 0)
    elif type_filter == "Income":
        query = query.filter(Transaction.original_amount > 0)
    elif type_filter == "Pending":
        query = query.filter(Transaction.status == "pending")

    # Apply search
    if search:
        query = query.filter(Transaction.description.ilike(f"%{search}%"))

    # Order and limit
    query = query.order_by(desc(Transaction.transaction_date)).limit(50)
    transactions = query.all()

    # Display count
    st.caption(f"Showing {len(transactions)} transactions")

    # Convert to mobile transaction list format
    mobile_txns = []
    for txn in transactions:
        merchant = txn.description
        if len(merchant) > 30:
            merchant = merchant[:27] + "..."

        category = txn.effective_category
        amount = txn.original_amount

        mobile_txns.append({
            'date': txn.transaction_date,
            'icon': get_category_icon(category),
            'merchant': merchant,
            'category': category,
            'amount': format_amount_private(amount),
            'is_positive': amount > 0,
        })

    # Render transaction cards
    transaction_list(mobile_txns)

    session.close()

    # Bottom navigation
    bottom_navigation(current="transactions")


# Check if mobile and render mobile view
if is_mobile():
    render_mobile_transactions()
    st.stop()

# Apply theme (must be called before any content)
theme = apply_theme()

# Render sidebar
render_minimal_sidebar()

# Inject amount styling CSS
st.markdown(AMOUNT_STYLE_CSS, unsafe_allow_html=True)

# Table styling is now in styles/main.css (loaded via apply_theme())

# Page header
render_page_header("💳 Transactions")

# Get database session
try:
    from db.database import get_session
    from db.models import Account, Transaction, Tag, TransactionTag
    from sqlalchemy import func, and_, or_, desc

    session = get_session()

    # Check if database has data
    transaction_count = session.query(func.count(Transaction.id)).scalar()

    if not transaction_count or transaction_count == 0:
        empty_transactions_state()
        st.stop()

    # Get earliest and latest transaction dates for data coverage info
    earliest_date = session.query(func.min(Transaction.transaction_date)).scalar()
    latest_date = session.query(func.max(Transaction.transaction_date)).scalar()

    # Hero card with transaction summary
    date_range_str = f"{earliest_date.strftime('%b %Y')} - {latest_date.strftime('%b %Y')}" if earliest_date and latest_date else "No data"
    st.markdown(f'''<div class="hero-card" style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);">
        <div class="hero-label">Total Transactions</div>
        <div class="hero-amount">{transaction_count:,}</div>
        <div class="hero-sync">{date_range_str}</div>
    </div>''', unsafe_allow_html=True)

    # ============================================================================
    # FILTER PANEL - Compact, coherent layout
    # ============================================================================

    # Date range presets
    today = date.today()
    DATE_PRESETS = {
        "Last 3 Months": (today - timedelta(days=90), today),
        "This Month": (today.replace(day=1), today),
        "Last Month": ((today.replace(day=1) - timedelta(days=1)).replace(day=1), today.replace(day=1) - timedelta(days=1)),
        "This Year": (today.replace(month=1, day=1), today),
        "Last Year": (date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)),
        "All Time": (earliest_date or today - timedelta(days=365), latest_date or today),
        "Custom": None,
    }

    # Main filter row - 4 equal columns
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        search_query = st.text_input(
            "🔍 Search",
            placeholder="merchant, description, amount",
            key="filter_search",
            help="Search by merchant name, description, or amount"
        )

    with col2:
        date_preset = st.selectbox(
            "📅 Date Range",
            options=list(DATE_PRESETS.keys()),
            index=0,
            key="filter_date_preset"
        )

    with col3:
        # Get unique categories
        user_categories = session.query(Transaction.user_category).filter(
            Transaction.user_category.isnot(None)
        ).distinct().all()
        source_categories = session.query(Transaction.category).filter(
            Transaction.category.isnot(None)
        ).distinct().all()
        raw_categories = session.query(Transaction.raw_category).filter(
            Transaction.raw_category.isnot(None)
        ).distinct().all()

        category_set = set()
        category_set.update([cat[0] for cat in user_categories if cat[0]])
        category_set.update([cat[0] for cat in source_categories if cat[0]])
        category_set.update([cat[0] for cat in raw_categories if cat[0]])
        category_list = sorted(list(category_set))

        selected_categories = st.multiselect(
            "📂 Category",
            options=category_list,
            key="filter_categories",
            placeholder="All categories"
        )

    with col4:
        # Account filter in main row
        accounts = session.query(Account).all()
        account_options = {f"{acc.institution} - {acc.account_type or 'Account'}": acc.id for acc in accounts}
        selected_accounts = st.multiselect(
            "🏦 Account",
            options=list(account_options.keys()),
            key="filter_accounts",
            placeholder="All accounts"
        )

    # Handle date preset selection
    if date_preset == "Custom":
        custom_col1, custom_col2, _, _ = st.columns(4)
        with custom_col1:
            start_date = st.date_input(
                "From",
                value=st.session_state.get("txn_filter_custom_start", today - timedelta(days=90)),
                max_value=today,
                key="txn_filter_custom_start"
            )
        with custom_col2:
            end_date = st.date_input(
                "To",
                value=st.session_state.get("txn_filter_custom_end", today),
                max_value=today,
                min_value=start_date,
                key="txn_filter_custom_end"
            )
    else:
        start_date, end_date = DATE_PRESETS[date_preset]

    # More Filters (collapsed by default)
    with st.expander("More Filters", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            # Amount Range
            amount_col1, amount_col2 = st.columns(2)
            with amount_col1:
                amount_min = st.number_input(
                    "Min Amount (₪)",
                    value=None,
                    step=10.0,
                    key="filter_amount_min"
                )
            with amount_col2:
                amount_max = st.number_input(
                    "Max Amount (₪)",
                    value=None,
                    step=10.0,
                    key="filter_amount_max"
                )

        with col2:
            # Transaction Type
            transaction_type = st.radio(
                "Type",
                options=["All", "Expenses", "Income"],
                key="filter_type",
                horizontal=True
            )

            # Status Filter
            status_filter = st.radio(
                "Status",
                options=["All", "Completed", "Pending"],
                key="filter_status",
                horizontal=True
            )

        with col3:
            # Tags Filter
            tags = session.query(Tag).all()
            tag_list = [tag.name for tag in tags]

            selected_tags = st.multiselect(
                "Tags",
                options=tag_list,
                key="filter_tags",
                placeholder="All tags"
            )

            # Checkbox filters in a row
            check_col1, check_col2 = st.columns(2)
            with check_col1:
                untagged_only = st.checkbox("Untagged", key="filter_untagged")
            with check_col2:
                unmapped_only = st.checkbox(
                    "Unmapped",
                    key="filter_unmapped_categories",
                    help="Unmapped raw categories only"
                )

    # Clear filters button (only show if filters are active)
    active_filters = []
    if search_query: active_filters.append("search")
    if selected_categories: active_filters.append("categories")
    if 'filter_accounts' in st.session_state and st.session_state.filter_accounts: active_filters.append("accounts")
    if 'filter_institutions' in st.session_state and st.session_state.filter_institutions: active_filters.append("institutions")
    if 'filter_tags' in st.session_state and st.session_state.filter_tags: active_filters.append("tags")
    if 'filter_amount_min' in st.session_state and st.session_state.filter_amount_min is not None: active_filters.append("amount")
    if 'filter_amount_max' in st.session_state and st.session_state.filter_amount_max is not None: active_filters.append("amount")
    if 'filter_status' in st.session_state and st.session_state.filter_status != "All": active_filters.append("status")
    if 'filter_type' in st.session_state and st.session_state.filter_type != "All": active_filters.append("type")
    if 'filter_untagged' in st.session_state and st.session_state.filter_untagged: active_filters.append("untagged")
    if 'filter_unmapped_categories' in st.session_state and st.session_state.filter_unmapped_categories: active_filters.append("unmapped")

    if active_filters:
        if st.button(f"🔄 Clear {len(set(active_filters))} filter(s)", type="secondary"):
            for key in list(st.session_state.keys()):
                if key.startswith("filter_"):
                    del st.session_state[key]
            st.rerun()

    # ============================================================================
    # BUILD QUERY WITH FILTERS
    # ============================================================================
    with st.spinner("Loading transactions..."):
        query = session.query(Transaction).filter(
            and_(
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date
            )
        )

    # Apply account filter
    if selected_accounts:
        account_ids = [account_options[acc_name] for acc_name in selected_accounts]
        query = query.filter(Transaction.account_id.in_(account_ids))

    # Apply status filter
    if status_filter == "Completed":
        query = query.filter(Transaction.status == "completed")
    elif status_filter == "Pending":
        query = query.filter(Transaction.status == "pending")

    # Apply category filter (check user_category, normalized category, and raw_category)
    if selected_categories:
        query = query.filter(
            or_(
                Transaction.user_category.in_(selected_categories),
                and_(
                    Transaction.user_category.is_(None),
                    or_(
                        Transaction.category.in_(selected_categories),
                        and_(
                            Transaction.category.is_(None),
                            Transaction.raw_category.in_(selected_categories)
                        )
                    )
                )
            )
        )

    # Apply unmapped categories filter (transactions with raw_category but no normalized category)
    if unmapped_only:
        query = query.filter(
            and_(
                Transaction.raw_category.isnot(None),
                Transaction.category.is_(None),
                Transaction.user_category.is_(None)
            )
        )

    # Apply tags filter
    if selected_tags:
        # Get transaction IDs that have all selected tags (AND logic)
        for tag_name in selected_tags:
            tag = session.query(Tag).filter(Tag.name == tag_name).first()
            if tag:
                tagged_txn_ids = session.query(TransactionTag.transaction_id).filter(
                    TransactionTag.tag_id == tag.id
                ).all()
                tagged_txn_ids = [txn_id[0] for txn_id in tagged_txn_ids]
                query = query.filter(Transaction.id.in_(tagged_txn_ids))

    # Apply untagged filter
    if untagged_only:
        tagged_ids = session.query(TransactionTag.transaction_id).distinct().all()
        tagged_ids = [txn_id[0] for txn_id in tagged_ids]
        query = query.filter(~Transaction.id.in_(tagged_ids))

    # Apply amount range filter
    if amount_min is not None:
        query = query.filter(Transaction.original_amount >= amount_min)
    if amount_max is not None:
        query = query.filter(Transaction.original_amount <= amount_max)

    # Apply transaction type filter
    if transaction_type == "Expenses":
        query = query.filter(Transaction.original_amount < 0)
    elif transaction_type == "Income":
        query = query.filter(Transaction.original_amount > 0)

    # Apply search filter (supports both description and amount search)
    if search_query:
        # Try to parse as number for amount search
        try:
            search_amount = float(search_query.replace(',', '').replace('₪', '').strip())
            # Search in both description and amount
            query = query.filter(
                or_(
                    Transaction.description.ilike(f"%{search_query}%"),
                    func.abs(Transaction.original_amount).between(search_amount - 0.01, search_amount + 0.01)
                )
            )
        except ValueError:
            # Not a number, search only in description
            query = query.filter(Transaction.description.ilike(f"%{search_query}%"))

    # Order by date (newest first)
    query = query.order_by(desc(Transaction.transaction_date))

    # Get total count
    total_transactions = query.count()

    # ============================================================================
    # PAGINATION
    # ============================================================================
    st.markdown(f'<div class="section-title">📋 Transactions <span class="results-count">({format_number(total_transactions)} found)</span></div>', unsafe_allow_html=True)

    # Search statistics and feedback
    if search_query:
        if total_transactions > 0:
            st.caption(f"🔍 Found {format_number(total_transactions)} transactions matching '{search_query}'")
        else:
            # No results - show helpful message
            st.warning(f"""
            🔍 No transactions found for "{search_query}"

            **Try:**
            - Checking spelling
            - Using fewer or different keywords
            - Searching by amount (e.g., "100" for ₪100 transactions)
            - Adjusting your date range or other filters
            """)

            # Add clear search button
            if st.button("🔄 Clear Search", key="clear_search_no_results"):
                st.session_state.filter_search = ""
                st.rerun()

    col1, col2 = st.columns([3, 1])

    with col1:
        # Rows per page selector
        rows_per_page = st.selectbox(
            "Rows per page",
            options=[25, 50, 100, 200],
            index=0,
            key="rows_per_page"
        )

    with col2:
        # Current page
        total_pages = max(1, (total_transactions + rows_per_page - 1) // rows_per_page)

        # Initialize page number in session state if not exists
        if 'txn_page_number' not in st.session_state:
            st.session_state.txn_page_number = 1

        current_page = st.number_input(
            "Page",
            min_value=1,
            max_value=total_pages,
            value=min(st.session_state.txn_page_number, total_pages),
            step=1,
            key="txn_page_input"
        )

        # Update session state
        st.session_state.txn_page_number = int(current_page)

    # Fetch paginated data
    offset = (current_page - 1) * rows_per_page
    transactions = query.limit(rows_per_page).offset(offset).all()

    # ============================================================================
    # BULK ACTIONS
    # ============================================================================
    if total_transactions > 0:
        st.markdown('<div class="section-title" style="font-size: 0.9rem; margin-top: 1rem;">Export Options</div>', unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("📥 Export Current Page to CSV", use_container_width=True):
                # Export current page
                export_data = []
                for txn in transactions:
                    export_data.append({
                        'Date': txn.transaction_date.strftime('%Y-%m-%d') if txn.transaction_date else '',
                        'Description': txn.description,
                        'Amount': txn.original_amount,
                        'Category': txn.effective_category or '',
                        'Status': txn.status,
                        'Account': f"{txn.account.institution if txn.account else ''}"
                    })

                df_export = pd.DataFrame(export_data)
                csv = df_export.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"transactions_{start_date}_{end_date}_page{current_page}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

        with col2:
            if st.button("📥 Export All to CSV", use_container_width=True):
                # Export all filtered transactions
                all_transactions = query.all()
                export_data = []
                for txn in all_transactions:
                    export_data.append({
                        'Date': txn.transaction_date.strftime('%Y-%m-%d') if txn.transaction_date else '',
                        'Description': txn.description,
                        'Amount': txn.original_amount,
                        'Category': txn.effective_category or '',
                        'Status': txn.status,
                        'Account': f"{txn.account.institution if txn.account else ''}"
                    })

                df_export = pd.DataFrame(export_data)
                csv = df_export.to_csv(index=False)
                st.download_button(
                    label="Download All CSV",
                    data=csv,
                    file_name=f"transactions_{start_date}_{end_date}_all.csv",
                    mime="text/csv",
                    use_container_width=True
                )

    # ============================================================================
    # TRANSACTION TABLE
    # ============================================================================
    if not transactions:
        # Count active filters for better feedback
        active_filters = 0
        if selected_accounts: active_filters += 1
        if status_filter != "All": active_filters += 1
        if selected_categories: active_filters += 1
        if unmapped_only: active_filters += 1
        if selected_tags: active_filters += 1
        if untagged_only: active_filters += 1
        if amount_min is not None: active_filters += 1
        if amount_max is not None: active_filters += 1
        if search_query: active_filters += 1
        if transaction_type != "All": active_filters += 1

        # Show helpful no results message
        if active_filters > 0:
            st.info(f"""
            🔍 No transactions match your {active_filters} active filter(s).

            **Try:**
            - Expanding your date range
            - Removing some filters using "Clear Filters" button above
            - Checking for typos in search terms
            """)
        else:
            st.info("No transactions found in the selected date range.")
    else:
        # Column customization
        with st.expander("⚙️ Customize Table View", expanded=False):
            all_columns = ["Date", "Description", "Amount", "Category", "Tags", "Status", "Account"]
            default_columns = st.session_state.get('table_columns', ["Date", "Description", "Amount", "Category", "Status"])

            # Ensure default columns are valid
            default_columns = [col for col in default_columns if col in all_columns]
            if not default_columns:
                default_columns = ["Date", "Description", "Amount", "Category", "Status"]

            selected_columns = st.multiselect(
                "Select columns to display",
                options=all_columns,
                default=default_columns,
                key="visible_columns_select"
            )

            # Save to session state
            st.session_state.table_columns = selected_columns

            col1, col2 = st.columns(2)
            with col1:
                compact_view = st.checkbox("Compact view", value=False, key="compact_view",
                                          help="Show more rows with smaller text")
            with col2:
                show_row_numbers = st.checkbox("Show row numbers", value=False, key="show_row_numbers")

        # Create DataFrame for display
        table_data = []
        for idx, txn in enumerate(transactions, start=1):
            # Get tags for this transaction
            txn_tags = session.query(Tag.name).join(
                TransactionTag,
                TransactionTag.tag_id == Tag.id
            ).filter(
                TransactionTag.transaction_id == txn.id
            ).all()
            tags_str = ", ".join([tag[0] for tag in txn_tags]) if txn_tags else "-"

            # Format description with RTL support
            description = fix_rtl(txn.description) if has_hebrew(txn.description) else txn.description

            # Get account info
            account_name = f"{txn.account.institution}" if txn.account else "Unknown"

            # Build amount display with original currency in parentheses if different
            amount_display = {
                'charged_amount': txn.charged_amount if txn.charged_amount is not None else txn.original_amount,
                'charged_currency': txn.charged_currency or txn.original_currency,
                'original_amount': txn.original_amount,
                'original_currency': txn.original_currency
            }

            row_data = {
                'ID': txn.id,
                '#': idx + ((current_page - 1) * rows_per_page),  # Row number with pagination
                'Date': txn.transaction_date.strftime('%Y-%m-%d') if txn.transaction_date else '',
                'Description': description[:50] + '...' if len(description) > 50 else description,
                'Amount': amount_display,  # Keep structured data for formatting
                'Category': txn.effective_category or 'Uncategorized',
                'Tags': tags_str,
                'Status': '✅' if txn.status == 'completed' else '⏳',
                'Account': account_name
            }
            table_data.append(row_data)

        df_display = pd.DataFrame(table_data)

        def format_amount_display(val):
            """
            Format amount with proper sign and show original currency in parentheses if different.

            Expected input: dict with keys:
                - charged_amount: float (primary amount to display)
                - charged_currency: str (primary currency, e.g., 'ILS', '₪')
                - original_amount: float (original transaction amount)
                - original_currency: str (original currency, e.g., '$', 'USD')

            Returns: Formatted string like "−₪18.50 ($5.00)" or just "−₪18.50" if same currency
            """
            # Handle legacy format (just a float)
            if isinstance(val, (int, float)):
                if val < 0:
                    return f"−₪{abs(val):,.2f}"
                elif val > 0:
                    return f"+₪{val:,.2f}"
                else:
                    return f"₪{val:,.2f}"

            # Handle new dict format
            if not isinstance(val, dict):
                return "N/A"

            charged_amount = val.get('charged_amount', 0)
            charged_currency = val.get('charged_currency', '₪')
            original_amount = val.get('original_amount', charged_amount)
            original_currency = val.get('original_currency', charged_currency)

            # Normalize currency symbols for comparison
            def normalize_currency(curr):
                """Convert currency codes to symbols for display"""
                curr_map = {
                    'ILS': '₪',
                    'USD': '$',
                    'EUR': '€',
                    'GBP': '£',
                }
                return curr_map.get(curr, curr)

            charged_curr_symbol = normalize_currency(charged_currency)
            original_curr_symbol = normalize_currency(original_currency)

            # Format the primary (charged) amount
            if charged_amount < 0:
                primary = f"−{charged_curr_symbol}{abs(charged_amount):,.2f}"
            elif charged_amount > 0:
                primary = f"+{charged_curr_symbol}{charged_amount:,.2f}"
            else:
                primary = f"{charged_curr_symbol}{charged_amount:,.2f}"

            # Check if we need to show original currency in parentheses
            # Show only if currencies differ OR amounts differ significantly (>0.01 tolerance)
            currencies_differ = charged_curr_symbol != original_curr_symbol
            amounts_differ = abs(abs(charged_amount) - abs(original_amount)) > 0.01

            if currencies_differ or amounts_differ:
                # Format original amount (without sign, just the value)
                original_formatted = f"{original_curr_symbol}{abs(original_amount):,.2f}"
                return f"{primary} ({original_formatted})"
            else:
                # Same currency and amount, just show primary
                return primary

        # Create a copy for display with formatted amounts
        df_styled = df_display.copy()
        df_styled['Amount'] = df_styled['Amount'].apply(format_amount_display)

        # Build display columns based on selection
        display_cols = []
        if show_row_numbers:
            display_cols.append('#')
        display_cols.extend([col for col in selected_columns if col in df_styled.columns])

        # If no columns selected, use defaults
        if not display_cols or display_cols == ['#']:
            display_cols = ['#', 'Date', 'Description', 'Amount', 'Category', 'Status'] if show_row_numbers else ['Date', 'Description', 'Amount', 'Category', 'Status']

        # Determine table height
        table_height = 400 if compact_view else 600

        # Display table with styling
        st.dataframe(
            df_styled[display_cols],
            use_container_width=True,
            hide_index=True,
            height=table_height,
            column_config={
                '#': st.column_config.NumberColumn(
                    '#',
                    help='Row number',
                    width='small'
                ),
                'Date': st.column_config.TextColumn(
                    'Date',
                    width='small'
                ),
                'Description': st.column_config.TextColumn(
                    'Description',
                    width='large'
                ),
                'Amount': st.column_config.TextColumn(
                    'Amount',
                    help='Transaction amount (−=expense, +=income)',
                    width='medium'
                ),
                'Category': st.column_config.TextColumn(
                    'Category',
                    width='medium'
                ),
                'Tags': st.column_config.TextColumn(
                    'Tags',
                    width='medium'
                ),
                'Status': st.column_config.TextColumn(
                    'Status',
                    width='small'
                ),
                'Account': st.column_config.TextColumn(
                    'Account',
                    width='small'
                )
            }
        )

        # ============================================================================
        # TRANSACTION EDIT PANEL
        # ============================================================================
        st.markdown('<div class="section-title">✏️ Edit Transaction</div>', unsafe_allow_html=True)

        # Select a transaction to edit
        selected_txn_id = st.selectbox(
            "Select a transaction to edit",
            options=[txn.id for txn in transactions],
            format_func=lambda x: f"ID {x}: {next((t.description[:40] for t in transactions if t.id == x), 'Unknown')}",
            key="selected_transaction"
        )

        if selected_txn_id:
            txn = session.query(Transaction).filter(Transaction.id == selected_txn_id).first()

            if txn:
                # Get current tags for this transaction
                current_tag_names = [tag[0] for tag in session.query(Tag.name).join(
                    TransactionTag,
                    TransactionTag.tag_id == Tag.id
                ).filter(
                    TransactionTag.transaction_id == txn.id
                ).all()]

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown('<div class="edit-section-header">📋 Original Transaction Info <span class="edit-section-hint">(read-only)</span></div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="edit-info-text">ID: {txn.id}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="edit-info-text">Date: {format_datetime(txn.transaction_date, "%Y-%m-%d")}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="edit-info-text">Description: {txn.description}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="edit-info-text">Amount: {format_amount_private(txn.original_amount)} {txn.original_currency}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="edit-info-text">Status: {"✅ Completed" if txn.status == "completed" else "⏳ Pending"}</div>', unsafe_allow_html=True)
                    if txn.account:
                        st.markdown(f'<div class="edit-info-text">Account: {txn.account.institution} ({txn.account.account_type or "N/A"})</div>', unsafe_allow_html=True)
                    if txn.raw_category:
                        st.markdown(f'<div class="edit-info-text">Raw Category: {txn.raw_category}</div>', unsafe_allow_html=True)
                    if txn.category:
                        st.markdown(f'<div class="edit-info-text">Normalized Category: {txn.category}</div>', unsafe_allow_html=True)

                with col2:
                    st.markdown('<div class="edit-section-header">✏️ Editable Fields</div>', unsafe_allow_html=True)

                    # --- Memo/Notes Field ---
                    new_memo = st.text_area(
                        "Notes / Description Override",
                        value=txn.memo or "",
                        placeholder="Add your own notes or description for this transaction...",
                        key=f"edit_memo_{txn.id}",
                        help="Your personal notes. The original description is preserved above."
                    )

                    # --- Category Editor ---
                    # Get all unique categories for autocomplete
                    all_categories = get_all_categories()
                    category_options = ["(No category)", "(Enter new...)"] + all_categories

                    # Determine current selection
                    current_category = txn.user_category or txn.category or ""
                    if current_category in category_options:
                        default_idx = category_options.index(current_category)
                    elif current_category:
                        category_options.append(current_category)
                        default_idx = len(category_options) - 1
                    else:
                        default_idx = 0

                    selected_category = st.selectbox(
                        "Category",
                        options=category_options,
                        index=default_idx,
                        key=f"edit_category_{txn.id}"
                    )

                    # Show text input if "Enter new..." selected
                    new_category_input = ""
                    if selected_category == "(Enter new...)":
                        new_category_input = st.text_input(
                            "New category name",
                            key=f"new_category_{txn.id}",
                            placeholder="Enter a new category..."
                        )

                    # --- Tags Editor ---
                    st.markdown('<div class="edit-field-label">Tags</div>', unsafe_allow_html=True)

                    # Get all existing tags for multiselect
                    all_tags = get_all_tags()

                    # Multiselect for existing tags
                    selected_tags = st.multiselect(
                        "Select tags",
                        options=all_tags,
                        default=current_tag_names,
                        key=f"edit_tags_{txn.id}",
                        help="Select existing tags or add new ones below"
                    )

                    # Text input for adding new tags
                    new_tags_input = st.text_input(
                        "Add new tags (comma-separated)",
                        key=f"new_tags_{txn.id}",
                        placeholder="e.g., groceries, monthly, shared"
                    )

                # --- Save/Reset Buttons ---
                btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 3])

                with btn_col1:
                    save_clicked = st.button("💾 Save Changes", type="primary", use_container_width=True)

                with btn_col2:
                    reset_clicked = st.button("↩️ Reset", use_container_width=True)

                if reset_clicked:
                    # Clear the edit form by removing session state keys
                    for key in list(st.session_state.keys()):
                        if key.startswith(f"edit_") or key.startswith(f"new_"):
                            if str(txn.id) in key:
                                del st.session_state[key]
                    st.rerun()

                if save_clicked:
                    tag_service = get_tag_service()
                    changes_made = []

                    # Determine final category value
                    if selected_category == "(No category)":
                        final_category = ""
                    elif selected_category == "(Enter new...)":
                        final_category = new_category_input.strip()
                    else:
                        final_category = selected_category

                    # Update memo and category
                    memo_changed = (new_memo.strip() or None) != (txn.memo or None)
                    category_changed = (final_category or None) != (txn.user_category or None)

                    if memo_changed or category_changed:
                        tag_service.update_transaction(
                            txn.id,
                            user_category=final_category if category_changed else None,
                            memo=new_memo.strip() if memo_changed else None
                        )
                        if memo_changed:
                            changes_made.append("notes")
                        if category_changed:
                            changes_made.append("category")

                    # Process tags
                    # Combine selected tags with any new tags from text input
                    final_tags = set(selected_tags)
                    if new_tags_input.strip():
                        new_tag_names = [t.strip() for t in new_tags_input.split(",") if t.strip()]
                        final_tags.update(new_tag_names)

                    current_tags_set = set(current_tag_names)

                    tags_to_add = final_tags - current_tags_set
                    tags_to_remove = current_tags_set - final_tags

                    if tags_to_add:
                        tag_service.tag_transaction(txn.id, list(tags_to_add))
                        changes_made.append(f"added {len(tags_to_add)} tag(s)")

                    if tags_to_remove:
                        tag_service.untag_transaction(txn.id, list(tags_to_remove))
                        changes_made.append(f"removed {len(tags_to_remove)} tag(s)")

                    if changes_made:
                        invalidate_transaction_cache()
                        if tags_to_add or tags_to_remove:
                            invalidate_tag_cache()
                        st.success(f"✅ Transaction updated: {', '.join(changes_made)}")
                        st.rerun()
                    else:
                        st.info("No changes to save.")


    # ============================================================================
    # SUMMARY FOOTER
    # ============================================================================
    if total_transactions > 0:
        # Calculate summary statistics
        all_filtered_transactions = query.all()

        total_amount = sum([txn.original_amount for txn in all_filtered_transactions])
        income = sum([txn.original_amount for txn in all_filtered_transactions if txn.original_amount > 0])
        expenses = abs(sum([txn.original_amount for txn in all_filtered_transactions if txn.original_amount < 0]))

        # Summary section with new design
        st.markdown('<div class="section-title">📊 Summary</div>', unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">Total Transactions</div>
                <div class="stat-value">{format_number(total_transactions)}</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">Total Income</div>
                <div class="stat-value positive">{format_amount_private(income)}</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">Total Expenses</div>
                <div class="stat-value negative">{format_amount_private(expenses)}</div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            net_class = "positive" if total_amount >= 0 else "negative"
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">Net Amount</div>
                <div class="stat-value {net_class}">{format_amount_private(total_amount)}</div>
            </div>
            """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error loading transactions: {str(e)}")
    st.exception(e)
    st.info("💡 Make sure the database is initialized with `fin-cli init`")
