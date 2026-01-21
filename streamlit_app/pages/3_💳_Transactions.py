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

from streamlit_app.utils.session import init_session_state, get_db_session, get_tag_service, get_all_categories, get_all_tags
from streamlit_app.utils.formatters import (
    format_currency, format_number, format_datetime,
    format_transaction_amount, color_for_amount, AMOUNT_STYLE_CSS
)
from streamlit_app.utils.rtl import fix_rtl, has_hebrew
from streamlit_app.utils.cache import get_transactions_cached, invalidate_transaction_cache
from streamlit_app.utils.errors import safe_call_with_spinner, ErrorBoundary, show_success, show_warning
from streamlit_app.components.sidebar import render_minimal_sidebar
from streamlit_app.components.empty_states import empty_transactions_state
from streamlit_app.components.filters import date_range_filter_with_presets
from streamlit_app.components.theme import apply_theme, render_theme_switcher

# Page config
st.set_page_config(
    page_title="Transactions - Financial Aggregator",
    page_icon="💳",
    layout="wide"
)

# Initialize session state
init_session_state()

# Apply theme (must be called before any content)
theme = apply_theme()

# Render sidebar
render_minimal_sidebar()

# Render theme switcher in sidebar
render_theme_switcher("sidebar")

# Page header
st.title("💳 Transactions Browser")
st.markdown("Browse, filter, and manage your financial transactions")

# Inject amount styling CSS
st.markdown(AMOUNT_STYLE_CSS, unsafe_allow_html=True)

# Table styling CSS for better readability
TABLE_STYLE_CSS = """
<style>
/* Zebra striping for better readability */
[data-testid="stDataFrame"] tbody tr:nth-child(even) {
    background-color: #f8f9fa !important;
}

/* Hover effect */
[data-testid="stDataFrame"] tbody tr:hover {
    background-color: #e3f2fd !important;
    cursor: pointer;
    transition: background-color 0.15s ease;
}

/* Column headers */
[data-testid="stDataFrame"] thead th {
    background-color: #1976d2 !important;
    color: white !important;
    font-weight: 600 !important;
    text-align: left !important;
}

/* Compact and readable table */
[data-testid="stDataFrame"] {
    font-size: 14px !important;
    line-height: 1.4 !important;
}

/* Amount column styling */
[data-testid="stDataFrame"] td:nth-child(3) {
    font-family: 'SF Mono', 'Roboto Mono', Consolas, monospace !important;
    font-weight: 500 !important;
}
</style>
"""
st.markdown(TABLE_STYLE_CSS, unsafe_allow_html=True)

st.markdown("---")

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

    # ============================================================================
    # FILTER PANEL
    # ============================================================================
    with st.expander("🔍 Filters", expanded=True):
        # Date Range with Quick Presets (full width)
        st.markdown("**Date Range**")
        start_date, end_date = date_range_filter_with_presets(
            key_prefix="txn_filter",
            default_months_back=3,
            data_start=earliest_date,
            data_end=latest_date
        )

        st.markdown("---")

        col1, col2, col3 = st.columns(3)

        with col1:
            # Account and Institution Filter
            st.markdown("**Account / Institution**")

            # Get all accounts
            accounts = session.query(Account).all()
            account_options = {f"{acc.institution} - {acc.account_type or 'Account'}": acc.id for acc in accounts}

            selected_accounts = st.multiselect(
                "Select Accounts",
                options=list(account_options.keys()),
                key="filter_accounts"
            )

            # Get unique institutions
            institutions = session.query(Account.institution).distinct().all()
            institution_list = [inst[0] for inst in institutions if inst[0]]

            selected_institutions = st.multiselect(
                "Select Institutions",
                options=institution_list,
                key="filter_institutions"
            )

        with col2:
            # Status and Category Filter
            st.markdown("**Status / Category**")

            status_filter = st.radio(
                "Transaction Status",
                options=["All", "Completed", "Pending"],
                key="filter_status",
                horizontal=True
            )

            # Get unique categories (both user_category and category columns)
            user_categories = session.query(Transaction.user_category).filter(
                Transaction.user_category.isnot(None)
            ).distinct().all()
            source_categories = session.query(Transaction.category).filter(
                Transaction.category.isnot(None)
            ).distinct().all()

            # Combine and deduplicate
            category_set = set()
            category_set.update([cat[0] for cat in user_categories if cat[0]])
            category_set.update([cat[0] for cat in source_categories if cat[0]])
            category_list = sorted(list(category_set))

            selected_categories = st.multiselect(
                "Categories",
                options=category_list,
                key="filter_categories"
            )

        with col3:
            # Tags Filter
            st.markdown("**Tags**")

            # Get all tags
            tags = session.query(Tag).all()
            tag_list = [tag.name for tag in tags]

            selected_tags = st.multiselect(
                "Select Tags",
                options=tag_list,
                key="filter_tags"
            )

            untagged_only = st.checkbox("Untagged Only", key="filter_untagged")

        # Second row of filters
        col1, col2, col3 = st.columns(3)

        with col1:
            # Amount Range Filter
            st.markdown("**Amount Range**")

            amount_min = st.number_input(
                "Min Amount (₪)",
                value=None,
                step=10.0,
                key="filter_amount_min"
            )

            amount_max = st.number_input(
                "Max Amount (₪)",
                value=None,
                step=10.0,
                key="filter_amount_max"
            )

        with col2:
            # Search Filter
            st.markdown("**Search**")

            search_query = st.text_input(
                "Search in description or amount",
                placeholder="e.g., supermarket, restaurant, 100",
                key="filter_search",
                help="Search by merchant name, description, or amount (e.g., '100' finds ₪100 transactions)"
            )

        with col3:
            # Transaction Type Filter
            st.markdown("**Transaction Type**")

            transaction_type = st.radio(
                "Transaction Type",
                options=["All", "Expenses", "Income"],
                key="filter_type",
                horizontal=True,
                label_visibility="collapsed"
            )

        # Action buttons
        col1, col2, col3, col4 = st.columns([1, 1, 1, 3])

        with col1:
            apply_filters = st.button("🔍 Apply Filters", type="primary", use_container_width=True)

        with col2:
            if st.button("🔄 Clear Filters", use_container_width=True):
                for key in list(st.session_state.keys()):
                    if key.startswith("filter_"):
                        del st.session_state[key]
                st.rerun()

    st.markdown("---")

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

    # Apply institution filter
    if selected_institutions:
        institution_account_ids = session.query(Account.id).filter(
            Account.institution.in_(selected_institutions)
        ).all()
        institution_account_ids = [acc_id[0] for acc_id in institution_account_ids]
        query = query.filter(Transaction.account_id.in_(institution_account_ids))

    # Apply status filter
    if status_filter == "Completed":
        query = query.filter(Transaction.status == "completed")
    elif status_filter == "Pending":
        query = query.filter(Transaction.status == "pending")

    # Apply category filter (check both user_category and category columns)
    if selected_categories:
        query = query.filter(
            or_(
                Transaction.user_category.in_(selected_categories),
                and_(
                    Transaction.user_category.is_(None),
                    Transaction.category.in_(selected_categories)
                )
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
    st.subheader(f"📋 Transactions ({format_number(total_transactions)} found)")

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
        st.markdown("**Bulk Actions**")

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

    st.markdown("---")

    # ============================================================================
    # TRANSACTION TABLE
    # ============================================================================
    if not transactions:
        # Count active filters for better feedback
        active_filters = 0
        if selected_accounts: active_filters += 1
        if selected_institutions: active_filters += 1
        if status_filter != "All": active_filters += 1
        if selected_categories: active_filters += 1
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
        st.markdown("---")
        st.subheader("✏️ Edit Transaction")

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
                    st.markdown("**📋 Original Transaction Info** *(read-only)*")
                    st.text(f"ID: {txn.id}")
                    st.text(f"Date: {format_datetime(txn.transaction_date, '%Y-%m-%d')}")
                    st.text(f"Description: {txn.description}")
                    st.text(f"Amount: {format_currency(txn.original_amount)} {txn.original_currency}")
                    st.text(f"Status: {'✅ Completed' if txn.status == 'completed' else '⏳ Pending'}")
                    if txn.account:
                        st.text(f"Account: {txn.account.institution} ({txn.account.account_type or 'N/A'})")
                    if txn.category:
                        st.text(f"Source Category: {txn.category}")

                with col2:
                    st.markdown("**✏️ Editable Fields**")

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
                    st.markdown("**Tags**")

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
                st.markdown("---")
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
                        st.success(f"✅ Transaction updated: {', '.join(changes_made)}")
                        st.rerun()
                    else:
                        st.info("No changes to save.")


    # ============================================================================
    # SUMMARY FOOTER
    # ============================================================================
    if total_transactions > 0:
        st.markdown("---")
        st.subheader("📊 Summary")

        # Calculate summary statistics
        all_filtered_transactions = query.all()

        total_amount = sum([txn.original_amount for txn in all_filtered_transactions])
        income = sum([txn.original_amount for txn in all_filtered_transactions if txn.original_amount > 0])
        expenses = sum([txn.original_amount for txn in all_filtered_transactions if txn.original_amount < 0])
        avg_transaction = total_amount / len(all_filtered_transactions) if all_filtered_transactions else 0

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Transactions", format_number(total_transactions))

        with col2:
            # Income in green
            st.markdown(f"""
            <div style="padding: 10px 0;">
                <p style="margin: 0; font-size: 0.875rem; color: #666;">Total Income</p>
                <p style="margin: 0; font-size: 1.5rem; font-weight: 600; color: #00897b; font-family: 'SF Mono', monospace;">
                    +₪{income:,.2f}
                </p>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            # Expenses in red
            st.markdown(f"""
            <div style="padding: 10px 0;">
                <p style="margin: 0; font-size: 0.875rem; color: #666;">Total Expenses</p>
                <p style="margin: 0; font-size: 1.5rem; font-weight: 600; color: #c62828; font-family: 'SF Mono', monospace;">
                    −₪{abs(expenses):,.2f}
                </p>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            # Net amount with appropriate color
            net_color = "#00897b" if total_amount >= 0 else "#c62828"
            net_sign = "+" if total_amount >= 0 else "−"
            st.markdown(f"""
            <div style="padding: 10px 0;">
                <p style="margin: 0; font-size: 0.875rem; color: #666;">Net Amount</p>
                <p style="margin: 0; font-size: 1.5rem; font-weight: 600; color: {net_color}; font-family: 'SF Mono', monospace;">
                    {net_sign}₪{abs(total_amount):,.2f}
                </p>
            </div>
            """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error loading transactions: {str(e)}")
    st.exception(e)
    st.info("💡 Make sure the database is initialized with `fin-cli init`")
