"""
Tags Management Page - Create, edit, and manage transaction tags
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from streamlit_app.utils.session import init_session_state
from streamlit_app.utils.formatters import format_currency, format_number, format_category_badge, format_tags
from streamlit_app.components.sidebar import render_minimal_sidebar
from streamlit_app.components.bulk_actions import show_bulk_preview, show_bulk_confirmation
from streamlit_app.components.responsive import apply_mobile_styles
from streamlit_app.components.theme import apply_theme, render_theme_switcher

# Page config
st.set_page_config(
    page_title="Tags - Financial Aggregator",
    page_icon="🏷️",
    layout="wide",
    initial_sidebar_state="auto"  # Auto-collapses on mobile
)

# Initialize session state
init_session_state()

# Apply theme (must be called before any content)
theme = apply_theme()

# Apply mobile-friendly styles
apply_mobile_styles()

# Render sidebar
render_minimal_sidebar()

# Render theme switcher in sidebar
render_theme_switcher("sidebar")

# Page header
st.title("🏷️ Tags Management")
st.markdown("Create, edit, and manage transaction tags")
st.markdown("---")

# Get services
try:
    from db.database import get_session
    from db.models import Tag, TransactionTag, Transaction
    from services.tag_service import TagService
    from sqlalchemy import func, or_, and_

    session = get_session()
    tag_service = TagService(session=session)

    # ============================================================================
    # TAGS OVERVIEW
    # ============================================================================
    st.subheader("📊 Tags Overview")

    # Get tag statistics
    tag_stats = tag_service.get_tag_stats()
    untagged_count = tag_service.get_untagged_count()
    untagged_total = tag_service.get_untagged_total()

    # Calculate total for percentages
    total_transactions = session.query(func.count(Transaction.id)).scalar()
    total_amount = session.query(
        func.coalesce(func.sum(func.coalesce(Transaction.charged_amount, Transaction.original_amount)), 0)
    ).scalar()

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Tags", format_number(len(tag_stats)))

    with col2:
        tagged_count = total_transactions - untagged_count
        st.metric("Tagged Transactions", f"{format_number(tagged_count)} / {format_number(total_transactions)}")

    with col3:
        tagged_pct = (tagged_count / total_transactions * 100) if total_transactions > 0 else 0
        st.metric("Coverage", f"{tagged_pct:.1f}%")

    with col4:
        st.metric("Untagged Amount", format_currency(untagged_total))

    st.markdown("---")

    # ============================================================================
    # CREATE TAG
    # ============================================================================
    with st.expander("➕ Create New Tag", expanded=False):
        col1, col2 = st.columns([3, 1])

        with col1:
            new_tag_name = st.text_input(
                "Tag Name",
                key="new_tag_name",
                placeholder="Enter tag name..."
            )

        with col2:
            st.markdown("<br>", unsafe_allow_html=True)  # Spacing
            if st.button("Create Tag", type="primary", use_container_width=True):
                if new_tag_name and new_tag_name.strip():
                    try:
                        tag = tag_service.get_or_create_tag(new_tag_name.strip())
                        st.toast(f"Created tag: {tag.name}", icon="🏷️")
                        st.rerun()
                    except Exception as e:
                        st.toast(f"Error creating tag: {str(e)}", icon="❌")
                else:
                    st.toast("Please enter a tag name", icon="⚠️")

    st.markdown("---")

    # ============================================================================
    # TAGS TABLE
    # ============================================================================
    st.subheader("📋 All Tags")

    if not tag_stats:
        st.info("No tags found. Create your first tag above!")
    else:
        # Prepare table data
        table_data = []
        for tag_stat in tag_stats:
            pct_of_total = (tag_stat['total_amount'] / total_amount * 100) if total_amount != 0 else 0

            table_data.append({
                'Tag Name': tag_stat['name'],
                'Transactions': format_number(tag_stat['count']),
                'Total Amount': format_currency(tag_stat['total_amount']),
                '% of Total': f"{pct_of_total:.1f}%",
                '_raw_count': tag_stat['count'],
                '_raw_amount': tag_stat['total_amount'],
                '_tag_name': tag_stat['name']
            })

        df_tags = pd.DataFrame(table_data)

        # Sort options
        col1, col2 = st.columns([1, 3])
        with col1:
            sort_by = st.selectbox(
                "Sort by",
                ["Name", "Transaction Count", "Total Amount"],
                key="tag_sort"
            )

        # Apply sorting
        if sort_by == "Name":
            df_tags = df_tags.sort_values('Tag Name')
        elif sort_by == "Transaction Count":
            df_tags = df_tags.sort_values('_raw_count', ascending=False)
        elif sort_by == "Total Amount":
            df_tags = df_tags.sort_values('_raw_amount', ascending=False)

        # Display table
        st.dataframe(
            df_tags[['Tag Name', 'Transactions', 'Total Amount', '% of Total']],
            use_container_width=True,
            hide_index=True
        )

        # Visual tag cloud with badges
        st.markdown("**📌 Quick Tag View**")
        tag_badges_html = format_tags([tag_stat['name'] for tag_stat in tag_stats])
        st.markdown(tag_badges_html, unsafe_allow_html=True)

        st.markdown("---")

        # ============================================================================
        # TAG ACTIONS (Rename, Delete, View Transactions)
        # ============================================================================
        st.subheader("⚡ Tag Actions")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Rename/Merge Tag**")

            # Tag selector for rename
            tag_names = [tag_stat['name'] for tag_stat in tag_stats]
            old_tag_name = st.selectbox(
                "Select tag to rename",
                tag_names,
                key="rename_old_tag"
            )

            new_tag_name_rename = st.text_input(
                "New name",
                key="rename_new_tag",
                placeholder="Enter new name..."
            )

            if st.button("Rename/Merge Tag", type="primary", use_container_width=True):
                if new_tag_name_rename and new_tag_name_rename.strip():
                    # Check if new name exists (for merge warning)
                    existing_tag = tag_service.get_tag_by_name(new_tag_name_rename.strip())
                    if existing_tag and existing_tag.name.lower() != old_tag_name.lower():
                        st.warning(f"⚠️ Tag '{new_tag_name_rename}' already exists. This will merge '{old_tag_name}' into it.")

                    success = tag_service.rename_tag(old_tag_name, new_tag_name_rename.strip())
                    if success:
                        st.toast(f"Successfully renamed/merged tag", icon="✅")
                        st.rerun()
                    else:
                        st.toast(f"Failed to rename tag", icon="❌")
                else:
                    st.toast("Please enter a new name", icon="⚠️")

        with col2:
            st.markdown("**Delete Tag**")

            # Tag selector for delete
            delete_tag_name = st.selectbox(
                "Select tag to delete",
                tag_names,
                key="delete_tag"
            )

            # Get stats for selected tag
            selected_tag_stat = next((t for t in tag_stats if t['name'] == delete_tag_name), None)

            if selected_tag_stat:
                st.caption(f"⚠️ This will remove the tag from {selected_tag_stat['count']} transactions")

            if st.button("Delete Tag", type="secondary", use_container_width=True):
                success = tag_service.delete_tag(delete_tag_name)
                if success:
                    st.toast(f"Deleted tag: {delete_tag_name}", icon="🗑️")
                    st.rerun()
                else:
                    st.toast(f"Failed to delete tag", icon="❌")

        st.markdown("---")

        # ============================================================================
        # VIEW TRANSACTIONS BY TAG
        # ============================================================================
        st.subheader("🔍 View Transactions by Tag")

        view_tag_name = st.selectbox(
            "Select tag to view transactions",
            tag_names,
            key="view_tag"
        )

        if st.button("Show Transactions", type="primary"):
            # Get tag
            tag = tag_service.get_tag_by_name(view_tag_name)
            if tag:
                # Get transactions for this tag
                transactions = session.query(Transaction).join(TransactionTag).filter(
                    TransactionTag.tag_id == tag.id
                ).order_by(Transaction.transaction_date.desc()).limit(100).all()

                if transactions:
                    st.markdown(f"**Showing last 100 transactions tagged with '{view_tag_name}'**")

                    txn_data = []
                    for txn in transactions:
                        txn_data.append({
                            'Date': txn.transaction_date.strftime('%Y-%m-%d'),
                            'Description': txn.description[:60] + '...' if len(txn.description) > 60 else txn.description,
                            'Amount': format_currency(txn.charged_amount if txn.charged_amount else txn.original_amount),
                            'Category': txn.effective_category or 'Uncategorized',
                            'Status': '✅' if txn.status == 'completed' else '⏳'
                        })

                    df_txns = pd.DataFrame(txn_data)
                    st.dataframe(df_txns, use_container_width=True, hide_index=True)

                    # Show categories as badges below the table
                    unique_categories = list(set([txn.effective_category for txn in transactions if txn.effective_category]))
                    if unique_categories:
                        st.markdown("**Categories in these transactions:**")
                        categories_badges_html = " ".join([format_category_badge(cat) for cat in sorted(unique_categories)])
                        st.markdown(categories_badges_html, unsafe_allow_html=True)

                    # Link to full transactions page
                    if st.button("📋 View All Transactions", use_container_width=True):
                        # Set filter in session state and redirect
                        st.session_state.txn_filter_tags = [view_tag_name]
                        st.switch_page("pages/3_💳_Transactions.py")
                else:
                    st.info("No transactions found with this tag")

    st.markdown("---")

    # ============================================================================
    # BULK TAGGING TOOLS
    # ============================================================================
    st.subheader("🔧 Bulk Tagging Tools")

    tab1, tab2, tab3 = st.tabs(["By Merchant Pattern", "By Category", "Migrate Categories to Tags"])

    # ------------------------------------------------------------------------
    # Tab 1: By Merchant Pattern
    # ------------------------------------------------------------------------
    with tab1:
        st.markdown("**Tag transactions matching a merchant pattern**")

        col1, col2 = st.columns(2)

        with col1:
            merchant_pattern = st.text_input(
                "Merchant Pattern",
                key="bulk_merchant_pattern",
                placeholder="e.g., 'wolt', 'pango', 'סופר'",
                help="Case-insensitive substring match in transaction description"
            )

        with col2:
            merchant_tags_input = st.text_input(
                "Tags to Add (comma-separated)",
                key="bulk_merchant_tags",
                placeholder="e.g., delivery, food"
            )

        # Preview button
        if st.button("🔍 Preview Matches", key="preview_merchant"):
            if merchant_pattern and merchant_pattern.strip():
                # Get total count for accurate stats
                total_count = session.query(func.count(Transaction.id)).filter(
                    Transaction.description.ilike(f"%{merchant_pattern}%")
                ).scalar()

                # Find matching transactions for preview
                matching_txns = session.query(Transaction).filter(
                    Transaction.description.ilike(f"%{merchant_pattern}%")
                ).order_by(Transaction.transaction_date.desc()).limit(20).all()

                if matching_txns:
                    # Format preview data
                    preview_data = []
                    for txn in matching_txns:
                        preview_data.append({
                            'Date': txn.transaction_date.strftime('%Y-%m-%d'),
                            'Description': txn.description[:60] + '...' if len(txn.description) > 60 else txn.description,
                            'Amount': format_currency(txn.charged_amount if txn.charged_amount else txn.original_amount),
                            'Current Tags': ', '.join(txn.tags) if txn.tags else 'None'
                        })

                    # Use reusable preview component
                    show_bulk_preview(
                        items=preview_data,
                        title=f"Transactions matching '{merchant_pattern}'",
                        columns=['Date', 'Description', 'Amount', 'Current Tags'],
                        max_preview=20,
                        total_count=total_count
                    )

                    # Show confirmation with tags detail
                    tags_list = [tag.strip() for tag in merchant_tags_input.split(',') if tag.strip()] if merchant_tags_input else []
                    if tags_list:
                        show_bulk_confirmation(
                            operation_name="tag",
                            affected_count=total_count,
                            details=f"with: {', '.join(tags_list)}",
                            warning_threshold=50
                        )

                        # Store preview state
                        st.session_state['merchant_preview_ready'] = True
                        st.session_state['merchant_preview_count'] = total_count
                    else:
                        st.warning("⚠️ Please enter tags to add before applying")
                else:
                    st.warning("No transactions found matching this pattern")
                    st.session_state['merchant_preview_ready'] = False
            else:
                st.toast("Please enter a merchant pattern", icon="⚠️")

        # Apply button (only show if preview was successful)
        if st.session_state.get('merchant_preview_ready', False):
            st.markdown("---")
            col1, col2 = st.columns([1, 3])

            with col1:
                if st.button("✅ Apply Tags", key="apply_merchant", type="primary", use_container_width=True):
                    if merchant_pattern and merchant_pattern.strip() and merchant_tags_input:
                        tags_list = [tag.strip() for tag in merchant_tags_input.split(',') if tag.strip()]

                        if tags_list:
                            try:
                                count = tag_service.bulk_tag_by_merchant(merchant_pattern.strip(), tags_list)
                                st.session_state['merchant_preview_ready'] = False  # Clear state
                                st.toast(f"Tagged {count} transactions with: {', '.join(tags_list)}", icon="🏷️")
                                st.balloons()  # Celebration for bulk operations
                                st.rerun()
                            except Exception as e:
                                st.toast(f"Error applying tags: {str(e)}", icon="❌")
                        else:
                            st.toast("Please enter at least one tag", icon="⚠️")
                    else:
                        st.toast("Please enter both merchant pattern and tags", icon="⚠️")

            with col2:
                if st.button("❌ Cancel", key="cancel_merchant", use_container_width=True):
                    st.session_state['merchant_preview_ready'] = False
                    st.rerun()

    # ------------------------------------------------------------------------
    # Tab 2: By Category
    # ------------------------------------------------------------------------
    with tab2:
        st.markdown("**Tag all transactions in a specific category**")

        # Get all categories
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

        if not category_list:
            st.info("No categories found in your transactions")
        else:
            col1, col2 = st.columns(2)

            with col1:
                selected_category = st.selectbox(
                    "Select Category",
                    category_list,
                    key="bulk_category"
                )

            with col2:
                category_tags_input = st.text_input(
                    "Tags to Add (comma-separated)",
                    key="bulk_category_tags",
                    placeholder="e.g., food, groceries"
                )

            # Preview button
            if st.button("🔍 Preview Matches", key="preview_category"):
                # Count matching transactions
                match_count = session.query(func.count(Transaction.id)).filter(
                    or_(
                        Transaction.user_category == selected_category,
                        and_(
                            Transaction.user_category.is_(None),
                            Transaction.category == selected_category
                        )
                    )
                ).scalar()

                # Get sample transactions
                sample_txns = session.query(Transaction).filter(
                    or_(
                        Transaction.user_category == selected_category,
                        and_(
                            Transaction.user_category.is_(None),
                            Transaction.category == selected_category
                        )
                    )
                ).order_by(Transaction.transaction_date.desc()).limit(20).all()

                if sample_txns:
                    # Format preview data
                    preview_data = []
                    for txn in sample_txns:
                        preview_data.append({
                            'Date': txn.transaction_date.strftime('%Y-%m-%d'),
                            'Description': txn.description[:60] + '...' if len(txn.description) > 60 else txn.description,
                            'Amount': format_currency(txn.charged_amount if txn.charged_amount else txn.original_amount),
                            'Current Tags': ', '.join(txn.tags) if txn.tags else 'None'
                        })

                    # Use reusable preview component
                    show_bulk_preview(
                        items=preview_data,
                        title=f"Transactions in category '{selected_category}'",
                        columns=['Date', 'Description', 'Amount', 'Current Tags'],
                        max_preview=20,
                        total_count=match_count
                    )

                    # Show confirmation with tags detail
                    tags_list = [tag.strip() for tag in category_tags_input.split(',') if tag.strip()] if category_tags_input else []
                    if tags_list:
                        show_bulk_confirmation(
                            operation_name="tag",
                            affected_count=match_count,
                            details=f"with: {', '.join(tags_list)}",
                            warning_threshold=50
                        )

                        # Store preview state
                        st.session_state['category_preview_ready'] = True
                        st.session_state['category_preview_count'] = match_count
                    else:
                        st.warning("⚠️ Please enter tags to add before applying")
                else:
                    st.warning("No transactions found in this category")
                    st.session_state['category_preview_ready'] = False

            # Apply button (only show if preview was successful)
            if st.session_state.get('category_preview_ready', False):
                st.markdown("---")
                col1, col2 = st.columns([1, 3])

                with col1:
                    if st.button("✅ Apply Tags", key="apply_category", type="primary", use_container_width=True):
                        if category_tags_input:
                            tags_list = [tag.strip() for tag in category_tags_input.split(',') if tag.strip()]

                            if tags_list:
                                try:
                                    # Query transactions in category
                                    transactions = session.query(Transaction).filter(
                                        or_(
                                            Transaction.user_category == selected_category,
                                            and_(
                                                Transaction.user_category.is_(None),
                                                Transaction.category == selected_category
                                            )
                                        )
                                    ).all()

                                    count = 0
                                    for txn in transactions:
                                        added = tag_service.tag_transaction(txn.id, tags_list)
                                        if added > 0:
                                            count += 1

                                    st.session_state['category_preview_ready'] = False  # Clear state
                                    st.toast(f"Tagged {count} transactions in category '{selected_category}' with: {', '.join(tags_list)}", icon="🏷️")
                                    st.balloons()  # Celebration for bulk operations
                                    st.rerun()
                                except Exception as e:
                                    st.toast(f"Error applying tags: {str(e)}", icon="❌")
                            else:
                                st.toast("Please enter at least one tag", icon="⚠️")
                        else:
                            st.toast("Please enter tags to apply", icon="⚠️")

                with col2:
                    if st.button("❌ Cancel", key="cancel_category", use_container_width=True):
                        st.session_state['category_preview_ready'] = False
                        st.rerun()

    # ------------------------------------------------------------------------
    # Tab 3: Migrate Categories to Tags
    # ------------------------------------------------------------------------
    with tab3:
        st.markdown("**Automatically create tags from transaction categories**")

        st.info("💡 This will create a tag for each category and tag all transactions accordingly")

        # Dry run preview
        if st.button("Preview Migration", key="preview_migrate"):
            try:
                results = tag_service.migrate_categories_to_tags(dry_run=True)

                if results:
                    st.success(f"Found {len(results)} categories to migrate")

                    migration_data = []
                    for category, count in sorted(results.items(), key=lambda x: x[1], reverse=True):
                        migration_data.append({
                            'Category': category,
                            'Transactions to Tag': format_number(count)
                        })

                    df_migration = pd.DataFrame(migration_data)
                    st.dataframe(df_migration, use_container_width=True, hide_index=True)
                else:
                    st.info("No categories need migration (all transactions are already tagged with their category)")
            except Exception as e:
                st.error(f"Error during dry run: {str(e)}")

        # Execute migration
        if st.button("Execute Migration", key="execute_migrate", type="primary"):
            try:
                results = tag_service.migrate_categories_to_tags(dry_run=False)

                if results:
                    total_tagged = sum(results.values())
                    st.toast(f"Successfully migrated {len(results)} categories, tagged {total_tagged} transactions", icon="✅")
                    st.balloons()  # Celebration for major migration

                    migration_data = []
                    for category, count in sorted(results.items(), key=lambda x: x[1], reverse=True):
                        migration_data.append({
                            'Category': category,
                            'Transactions Tagged': format_number(count)
                        })

                    df_migration = pd.DataFrame(migration_data)
                    st.dataframe(df_migration, use_container_width=True, hide_index=True)

                    st.rerun()
                else:
                    st.info("No categories needed migration")
            except Exception as e:
                st.error(f"Error during migration: {str(e)}")

except Exception as e:
    st.error(f"Error loading tags: {str(e)}")
    st.exception(e)
    st.info("💡 Make sure the database is initialized with `fin-cli init`")
