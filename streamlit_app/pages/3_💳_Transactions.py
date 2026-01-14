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

from streamlit_app.utils.session import init_session_state, get_db_session
from streamlit_app.utils.formatters import format_currency, format_number, format_datetime
from streamlit_app.utils.rtl import fix_rtl, has_hebrew
from streamlit_app.components.sidebar import render_minimal_sidebar

# Page config
st.set_page_config(
    page_title="Transactions - Financial Aggregator",
    page_icon="💳",
    layout="wide"
)

# Initialize session state
init_session_state()

# Render sidebar
render_minimal_sidebar()

# Page header
st.title("💳 Transactions Browser")
st.markdown("Browse, filter, and manage your financial transactions")
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
        st.warning("⚠️ No transaction data available. Please sync your financial data first.")
        st.info("Go to the **Sync** page to synchronize your accounts.")
        if st.button("🔄 Go to Sync Page", type="primary"):
            st.switch_page("pages/2_🔄_Sync.py")
        st.stop()

    # ============================================================================
    # FILTER PANEL
    # ============================================================================
    with st.expander("🔍 Filters", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            # Date Range Filter
            st.markdown("**Date Range**")
            default_start = date.today() - timedelta(days=90)
            default_end = date.today()

            start_date = st.date_input(
                "From",
                value=default_start,
                max_value=date.today(),
                key="filter_start_date"
            )
            end_date = st.date_input(
                "To",
                value=default_end,
                max_value=date.today(),
                min_value=start_date,
                key="filter_end_date"
            )

        with col2:
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

        with col3:
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

        # Second row of filters
        col1, col2, col3 = st.columns(3)

        with col1:
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

        with col2:
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

        with col3:
            # Search Filter
            st.markdown("**Search**")

            search_query = st.text_input(
                "Search in description",
                placeholder="e.g., supermarket, restaurant",
                key="filter_search"
            )

            transaction_type = st.radio(
                "Transaction Type",
                options=["All", "Expenses", "Income"],
                key="filter_type",
                horizontal=True
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

    # Apply search filter
    if search_query:
        query = query.filter(Transaction.description.ilike(f"%{search_query}%"))

    # Order by date (newest first)
    query = query.order_by(desc(Transaction.transaction_date))

    # Get total count
    total_transactions = query.count()

    # ============================================================================
    # PAGINATION
    # ============================================================================
    st.subheader(f"📋 Transactions ({format_number(total_transactions)} found)")

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
        st.info("No transactions found matching the current filters.")
    else:
        # Create DataFrame for display
        table_data = []
        for txn in transactions:
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

            table_data.append({
                'ID': txn.id,
                'Date': txn.transaction_date.strftime('%Y-%m-%d') if txn.transaction_date else '',
                'Description': description[:50] + '...' if len(description) > 50 else description,
                'Amount': format_currency(txn.original_amount),
                'Category': txn.effective_category or 'Uncategorized',
                'Tags': tags_str,
                'Status': '✅' if txn.status == 'completed' else '⏳',
                'Account': account_name
            })

        df_display = pd.DataFrame(table_data)

        # Display table
        st.dataframe(
            df_display[['Date', 'Description', 'Amount', 'Category', 'Tags', 'Status', 'Account']],
            use_container_width=True,
            hide_index=True,
            height=600
        )

        # ============================================================================
        # TRANSACTION DETAILS (Expandable)
        # ============================================================================
        st.markdown("---")
        st.subheader("🔍 Transaction Details")

        # Select a transaction to view details
        selected_txn_id = st.selectbox(
            "Select a transaction to view details",
            options=[txn.id for txn in transactions],
            format_func=lambda x: f"ID {x}: {next((t.description[:40] for t in transactions if t.id == x), 'Unknown')}",
            key="selected_transaction"
        )

        if selected_txn_id:
            txn = session.query(Transaction).filter(Transaction.id == selected_txn_id).first()

            if txn:
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**Basic Information**")
                    st.text(f"ID: {txn.id}")
                    st.text(f"Date: {format_datetime(txn.transaction_date, '%Y-%m-%d %H:%M')}")
                    st.text(f"Description: {txn.description}")
                    st.text(f"Amount: {format_currency(txn.original_amount)}")
                    st.text(f"Currency: {txn.original_currency}")
                    st.text(f"Status: {txn.status}")

                with col2:
                    st.markdown("**Categorization**")
                    st.text(f"Category: {txn.effective_category or 'None'}")
                    st.text(f"User Category: {txn.user_category or 'None'}")

                    # Get tags
                    txn_tags = session.query(Tag.name).join(
                        TransactionTag,
                        TransactionTag.tag_id == Tag.id
                    ).filter(
                        TransactionTag.transaction_id == txn.id
                    ).all()
                    tags_str = ", ".join([tag[0] for tag in txn_tags]) if txn_tags else "None"
                    st.text(f"Tags: {tags_str}")

                    st.markdown("**Account Information**")
                    if txn.account:
                        st.text(f"Institution: {txn.account.institution}")
                        st.text(f"Type: {txn.account.account_type or 'N/A'}")

                # ============================================================================
                # TRANSACTION EDITING
                # ============================================================================
                st.markdown("---")
                st.markdown("**✏️ Edit Transaction**")

                # Import tag service
                from services.tag_service import TagService
                tag_service_edit = TagService(session=session)

                # Edit Category
                st.markdown("**Edit Category**")

                # Get all categories for suggestions
                user_categories = session.query(Transaction.user_category).filter(
                    Transaction.user_category.isnot(None)
                ).distinct().all()
                source_categories = session.query(Transaction.category).filter(
                    Transaction.category.isnot(None)
                ).distinct().all()

                category_set = set()
                category_set.update([cat[0] for cat in user_categories if cat[0]])
                category_set.update([cat[0] for cat in source_categories if cat[0]])
                category_list = sorted(list(category_set))

                col_cat1, col_cat2 = st.columns([3, 1])

                with col_cat1:
                    # Use selectbox with option for custom input
                    edit_category_mode = st.radio(
                        "Category Mode",
                        ["Select Existing", "Custom"],
                        key=f"cat_mode_{txn.id}",
                        horizontal=True
                    )

                    if edit_category_mode == "Select Existing":
                        new_category = st.selectbox(
                            "Category",
                            ["(Clear Category)"] + category_list,
                            index=0 if not txn.user_category else (category_list.index(txn.user_category) + 1 if txn.user_category in category_list else 0),
                            key=f"edit_cat_select_{txn.id}"
                        )
                    else:
                        new_category = st.text_input(
                            "Custom Category",
                            value=txn.user_category or "",
                            key=f"edit_cat_input_{txn.id}",
                            placeholder="Enter custom category..."
                        )

                with col_cat2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("Update Category", key=f"update_cat_{txn.id}", use_container_width=True):
                        # Determine final category value
                        if edit_category_mode == "Select Existing" and new_category == "(Clear Category)":
                            final_category = None
                        elif new_category:
                            final_category = new_category
                        else:
                            final_category = None

                        try:
                            success = tag_service_edit.update_transaction(txn.id, user_category=final_category)
                            if success:
                                st.success("✅ Category updated!")
                                st.rerun()
                            else:
                                st.error("Failed to update category")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

                # Manage Tags
                st.markdown("---")
                st.markdown("**Manage Tags**")

                # Get all available tags
                all_tags = tag_service_edit.get_all_tags()
                all_tag_names = [tag.name for tag in all_tags]

                # Get current tags for this transaction
                current_tags = [tag[0] for tag in txn_tags] if txn_tags else []

                col_tag1, col_tag2 = st.columns(2)

                with col_tag1:
                    st.markdown("**Add Tags**")

                    # Tags to add (exclude already tagged)
                    available_tags = [tag for tag in all_tag_names if tag not in current_tags]

                    if available_tags:
                        tags_to_add = st.multiselect(
                            "Select tags to add",
                            available_tags,
                            key=f"add_tags_{txn.id}"
                        )

                        if st.button("Add Tags", key=f"add_tags_btn_{txn.id}", use_container_width=True):
                            if tags_to_add:
                                try:
                                    added = tag_service_edit.tag_transaction(txn.id, tags_to_add)
                                    st.success(f"✅ Added {added} tag(s)")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")
                            else:
                                st.warning("Please select at least one tag")
                    else:
                        st.info("All available tags are already applied")

                    # Option to create new tag
                    new_tag_name_inline = st.text_input(
                        "Or create new tag",
                        key=f"new_tag_{txn.id}",
                        placeholder="Enter new tag name..."
                    )

                    if st.button("Create & Add Tag", key=f"create_add_tag_{txn.id}", use_container_width=True):
                        if new_tag_name_inline and new_tag_name_inline.strip():
                            try:
                                tag_service_edit.get_or_create_tag(new_tag_name_inline.strip())
                                added = tag_service_edit.tag_transaction(txn.id, [new_tag_name_inline.strip()])
                                st.success(f"✅ Created and added tag: {new_tag_name_inline.strip()}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                        else:
                            st.warning("Please enter a tag name")

                with col_tag2:
                    st.markdown("**Remove Tags**")

                    if current_tags:
                        tags_to_remove = st.multiselect(
                            "Select tags to remove",
                            current_tags,
                            key=f"remove_tags_{txn.id}"
                        )

                        if st.button("Remove Tags", key=f"remove_tags_btn_{txn.id}", use_container_width=True):
                            if tags_to_remove:
                                try:
                                    removed = tag_service_edit.untag_transaction(txn.id, tags_to_remove)
                                    st.success(f"✅ Removed {removed} tag(s)")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")
                            else:
                                st.warning("Please select at least one tag")
                    else:
                        st.info("No tags to remove")

                # Additional details
                if txn.memo:
                    st.markdown("**Memo**")
                    st.text(txn.memo)

                if txn.installment_number and txn.installment_total:
                    st.markdown("**Installment Information**")
                    st.text(f"Installment: {txn.installment_number} of {txn.installment_total}")

                if txn.transaction_id:
                    st.markdown("**Technical Details**")
                    st.text(f"Transaction ID: {txn.transaction_id}")

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
            st.metric("Total Income", format_currency(income))

        with col3:
            st.metric("Total Expenses", format_currency(abs(expenses)))

        with col4:
            st.metric("Average Transaction", format_currency(avg_transaction))

except Exception as e:
    st.error(f"Error loading transactions: {str(e)}")
    st.exception(e)
    st.info("💡 Make sure the database is initialized with `fin-cli init`")
