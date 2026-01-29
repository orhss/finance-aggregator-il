"""
Organize Page - Unified management for Categories, Rules, and Tags

Consolidates three previously separate pages into one with tabs:
- Categories: Provider and merchant category mappings
- Rules: Auto-categorization and tagging rules
- Tags: Custom transaction labels
"""

import streamlit as st
import pandas as pd
import yaml
from datetime import datetime
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from streamlit_app.utils.session import init_session_state, format_amount_private, get_all_categories, get_all_tags
from streamlit_app.auth import check_authentication
from streamlit_app.utils.cache import invalidate_transaction_cache, invalidate_tag_cache
from streamlit_app.utils.formatters import format_number, format_category_badge, format_tags, format_transaction_with_currency
from streamlit_app.components.sidebar import render_minimal_sidebar
from streamlit_app.components.bulk_actions import show_bulk_preview, show_bulk_confirmation
from streamlit_app.components.theme import apply_theme, render_page_header
from streamlit_app.components.cards import render_metric_row

# Page config
st.set_page_config(
    page_title="Organize - Financial Aggregator",
    page_icon="🏷️",
    layout="wide"
)

# Initialize session state
init_session_state()

# Check authentication (if enabled)
if not check_authentication():
    st.stop()

# Apply theme
theme = apply_theme()

# Render sidebar
render_minimal_sidebar()

# Page header
render_page_header("🏷️ Organize")

# Get services
try:
    from db.database import get_session
    from db.models import Transaction, Account, Tag, TransactionTag
    from services.category_service import CategoryService
    from services.rules_service import RulesService, MatchType, Rule
    from services.tag_service import TagService
    from config.constants import Institution, UnifiedCategory
    from sqlalchemy import func, or_, and_

    session = get_session()
    category_service = CategoryService(session=session)
    rules_service = RulesService(session=session)
    tag_service = TagService(session=session)

    # ========================================================================
    # MAIN TABS
    # ========================================================================
    tab_categories, tab_rules, tab_tags = st.tabs([
        "📂 Categories",
        "📋 Rules",
        "🏷️ Tags"
    ])

    # ========================================================================
    # TAB 1: CATEGORIES
    # ========================================================================
    with tab_categories:
        st.subheader("Category Mappings")
        st.markdown("Normalize categories across credit card providers for consistent analytics.")

        # Category Overview Metrics
        coverage = category_service.get_category_coverage_stats()
        analysis = category_service.analyze_categories()

        categorized_pct = round(100 * coverage['with_unified_category'] / coverage['total'], 1) if coverage['total'] > 0 else 0

        render_metric_row([
            {"value": f"{coverage['total']:,}", "label": "Total Transactions"},
            {"value": f"{coverage['with_unified_category']:,}", "label": "Categorized", "sublabel": f"{categorized_pct}%"},
            {"value": f"{coverage['with_provider_category']:,}", "label": "From Provider"},
            {"value": f"{coverage['needs_attention']:,}", "label": "Needs Attention"},
        ])

        # Action hint
        if coverage['needs_attention'] > 0:
            unmapped_provider_cats = category_service.get_unmapped_categories()
            merchant_groups = category_service.get_uncategorized_by_merchant(min_transactions=1)
            hints = []
            if unmapped_provider_cats:
                hints.append(f"{len(unmapped_provider_cats)} unmapped provider categories")
            if merchant_groups:
                hints.append(f"{sum(g['count'] for g in merchant_groups):,} transactions without provider category")
            if hints:
                st.info("ℹ️ " + " | ".join(hints))

        st.markdown("")  # Spacing

        # Categories Sub-tabs
        cat_tab1, cat_tab2, cat_tab3 = st.tabs(["⚠️ Unmapped", "🏪 By Merchant", "📋 All Mappings"])

        # Get suggestions for dropdowns
        existing_unified = category_service.get_unified_categories()
        standard_categories = UnifiedCategory.all()
        all_suggestions = sorted(set(existing_unified + standard_categories))

        # --- Unmapped Categories ---
        with cat_tab1:
            unmapped = category_service.get_unmapped_categories()

            if not unmapped:
                st.success("All categories are mapped!")
            else:
                total_unmapped_txns = sum(u['count'] for u in unmapped)
                st.warning(f"**{len(unmapped)} categories** affecting **{total_unmapped_txns:,} transactions** are unmapped.")

                # Display unmapped table
                unmapped_data = []
                for item in unmapped:
                    samples = item.get('sample_merchants', []) or ([item.get('sample_merchant')] if item.get('sample_merchant') else [])
                    unmapped_data.append({
                        'Provider': item['provider'].upper(),
                        'Raw Category': item['raw_category'],
                        'Transactions': f"{item['count']:,}",
                        'Samples': ', '.join(samples[:3]) if samples else '-'
                    })

                df_unmapped = pd.DataFrame(unmapped_data)
                st.dataframe(df_unmapped, use_container_width=True, hide_index=True)

                # Quick mapping
                st.markdown("**Quick Map**")
                col1, col2, col3 = st.columns([2, 2, 1])

                with col1:
                    unmapped_options = [f"{u['provider'].upper()} / {u['raw_category']} ({u['count']} txns)" for u in unmapped]
                    quick_map_select = st.selectbox("Unmapped Category", options=unmapped_options, key="cat_quick_map_select")

                with col2:
                    quick_map_unified = st.selectbox("Map to", options=all_suggestions, key="cat_quick_map_unified")

                with col3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("Map", type="primary", use_container_width=True, key="cat_quick_map_btn"):
                        if quick_map_select and quick_map_unified:
                            idx = unmapped_options.index(quick_map_select)
                            item = unmapped[idx]
                            try:
                                category_service.add_mapping(item['provider'], item['raw_category'], quick_map_unified)
                                st.toast(f"Mapped '{item['raw_category']}' -> '{quick_map_unified}'", icon="✅")
                                st.rerun()
                            except Exception as e:
                                st.toast(f"Error: {str(e)}", icon="❌")

        # --- By Merchant ---
        with cat_tab2:
            st.markdown("Group uncategorized transactions by merchant and assign categories in bulk.")
            st.caption("For transactions without provider categories (e.g., Isracard)")

            merchant_groups = category_service.get_uncategorized_by_merchant(min_transactions=1)

            if not merchant_groups:
                st.success("All transactions have categories!")
            else:
                total_uncategorized = sum(g['count'] for g in merchant_groups)
                st.warning(f"**{len(merchant_groups)} merchant patterns** covering **{total_uncategorized:,} transactions** need categories.")

                # Filter
                min_txn_filter = st.selectbox("Min transactions", options=[1, 2, 3, 5, 10], index=0, key="merchant_min_txn")
                filtered_groups = [g for g in merchant_groups if g['count'] >= min_txn_filter]

                if filtered_groups:
                    merchant_data = []
                    for i, group in enumerate(filtered_groups):
                        merchant_data.append({
                            '#': i + 1,
                            'Merchant': group['merchant_pattern'],
                            'Provider': group['provider'].upper(),
                            'Txns': group['count'],
                            'Amount': f"₪{group['total_amount']:,.0f}",
                        })

                    df_merchants = pd.DataFrame(merchant_data)
                    st.dataframe(df_merchants, use_container_width=True, hide_index=True)

                    # Quick categorize
                    st.markdown("**Quick Categorize**")
                    col1, col2, col3 = st.columns([2, 2, 1])

                    with col1:
                        merchant_options = [f"{g['merchant_pattern']} ({g['count']} txns)" for g in filtered_groups]
                        selected_merchant = st.selectbox("Merchant Pattern", options=merchant_options, key="merchant_select")

                    with col2:
                        assign_category = st.selectbox("Category", options=all_suggestions, key="merchant_assign_category")

                    with col3:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("Apply", type="primary", use_container_width=True, key="merchant_apply"):
                            if selected_merchant and assign_category:
                                idx = merchant_options.index(selected_merchant)
                                group = filtered_groups[idx]
                                try:
                                    result = category_service.bulk_set_category_with_mapping(
                                        group['merchant_pattern'], assign_category, group['transaction_ids'], group['provider']
                                    )
                                    msg = f"Categorized {result['transactions_updated']} transactions as '{assign_category}'"
                                    if result['mapping_created']:
                                        msg += " (mapping saved)"
                                    st.toast(msg, icon="✅")
                                    st.rerun()
                                except Exception as e:
                                    st.toast(f"Error: {str(e)}", icon="❌")

        # --- All Mappings ---
        with cat_tab3:
            provider_filter = st.selectbox(
                "Filter by Provider",
                options=["All"] + [p.upper() for p in Institution.credit_cards()],
                key="mappings_provider_filter"
            )

            selected_provider = None if provider_filter == "All" else provider_filter.lower()
            mappings = category_service.get_all_mappings(selected_provider)

            if not mappings:
                st.info("No mappings found. Add mappings using the tabs above.")
            else:
                table_data = []
                for mapping in mappings:
                    table_data.append({
                        'Provider': mapping.provider.upper(),
                        'Raw Category': mapping.raw_category,
                        'Unified Category': mapping.unified_category,
                        'Created': mapping.created_at.strftime('%Y-%m-%d') if mapping.created_at else 'N/A'
                    })

                df_mappings = pd.DataFrame(table_data)
                st.dataframe(df_mappings, use_container_width=True, hide_index=True)
                st.caption(f"{len(mappings)} mappings total")

                # Apply mappings button
                if st.button("Apply Mappings to All Transactions", type="primary", key="apply_all_mappings"):
                    results = category_service.apply_mappings_to_transactions()
                    total = sum(results.values())
                    if total > 0:
                        st.toast(f"Updated {total:,} transactions", icon="✅")
                        st.rerun()
                    else:
                        st.toast("No transactions needed updating", icon="ℹ️")

    # ========================================================================
    # TAB 2: RULES
    # ========================================================================
    with tab_rules:
        st.subheader("Auto-categorization Rules")
        st.markdown("Create rules to automatically categorize and tag transactions based on patterns.")

        # Load rules
        rules = rules_service.get_rules()

        # Rules Overview
        enabled_rules = sum(1 for rule in rules if rule.enabled)
        rules_with_category = sum(1 for rule in rules if rule.category)
        rules_with_tags = sum(1 for rule in rules if rule.tags)

        render_metric_row([
            {"value": f"{enabled_rules} / {len(rules)}", "label": "Total Rules"},
            {"value": format_number(rules_with_category), "label": "With Category"},
            {"value": format_number(rules_with_tags), "label": "With Tags"},
        ])

        st.markdown("")  # Spacing

        # Add New Rule
        with st.expander("➕ Add New Rule", expanded=False):
            col1, col2 = st.columns(2)

            all_categories_for_rules = get_all_categories()
            all_tags_for_rules = get_all_tags()
            category_options = ["(No category)", "(Enter new...)"] + all_categories_for_rules

            with col1:
                rule_pattern = st.text_input("Pattern", key="new_rule_pattern", placeholder="e.g., 'wolt', 'pango'")
                rule_match_type = st.selectbox("Match Type", ["contains", "exact", "starts_with", "ends_with", "regex"], key="new_rule_match_type")
                selected_category = st.selectbox("Category (optional)", options=category_options, key="new_rule_category_select")

                new_category_input = ""
                if selected_category == "(Enter new...)":
                    new_category_input = st.text_input("New category name", key="new_rule_category_new")

            with col2:
                selected_tags = st.multiselect("Tags to Add", options=all_tags_for_rules, key="new_rule_tags_select")
                new_tags_input = st.text_input("New tags (comma-separated)", key="new_rule_tags_new")
                rule_description = st.text_input("Description (optional)", key="new_rule_description")

            if st.button("Add Rule", type="primary", use_container_width=True, key="add_rule_btn"):
                if rule_pattern and rule_pattern.strip():
                    final_category = None
                    if selected_category == "(Enter new...)":
                        final_category = new_category_input.strip() if new_category_input else None
                    elif selected_category != "(No category)":
                        final_category = selected_category

                    tags_list = list(selected_tags)
                    if new_tags_input:
                        tags_list.extend([tag.strip() for tag in new_tags_input.split(',') if tag.strip()])

                    try:
                        new_rule = rules_service.add_rule(
                            pattern=rule_pattern.strip(),
                            category=final_category,
                            tags=tags_list,
                            match_type=MatchType(rule_match_type),
                            description=rule_description.strip() if rule_description else None
                        )
                        st.toast(f"Created rule: {new_rule.pattern}", icon="📋")
                        st.rerun()
                    except Exception as e:
                        st.toast(f"Error: {str(e)}", icon="❌")
                else:
                    st.toast("Please enter a pattern", icon="⚠️")

        st.markdown("")  # Spacing

        # Rules Table
        if not rules:
            st.info("No rules found. Create your first rule above!")
        else:
            table_data = []
            for idx, rule in enumerate(rules):
                table_data.append({
                    '#': idx,
                    'Pattern': rule.pattern,
                    'Match': rule.match_type.value,
                    'Category': rule.category or '-',
                    'Tags': ', '.join(rule.tags) if rule.tags else '-',
                    'Description': rule.description or '-',
                    'On': '✅' if rule.enabled else '❌'
                })

            df_rules = pd.DataFrame(table_data)
            st.dataframe(df_rules, use_container_width=True, hide_index=True)

            # Apply Rules
            st.markdown("")  # Spacing
            col1, col2 = st.columns(2)

            with col1:
                apply_scope = st.radio("Apply to", ["All Transactions", "Uncategorized Only"], horizontal=True, key="rules_apply_scope")

            with col2:
                apply_mode = st.radio("Mode", ["Dry Run", "Apply Changes"], horizontal=True, key="rules_apply_mode")

            if st.button("Run Rules", type="primary", use_container_width=True, key="run_rules_btn"):
                only_uncategorized = (apply_scope == "Uncategorized Only")
                dry_run = (apply_mode == "Dry Run")

                try:
                    results = rules_service.apply_rules(only_uncategorized=only_uncategorized, dry_run=dry_run)
                    processed = results.get('processed', 0)
                    modified = results.get('modified', 0)

                    if dry_run:
                        st.toast(f"Dry run: {modified}/{processed} would be modified", icon="🔍")
                    else:
                        st.toast(f"Applied: {modified}/{processed} modified", icon="✅")
                        if modified > 0:
                            invalidate_transaction_cache()
                            st.rerun()
                except Exception as e:
                    st.toast(f"Error: {str(e)}", icon="❌")

    # ========================================================================
    # TAB 3: TAGS
    # ========================================================================
    with tab_tags:
        st.subheader("Transaction Tags")
        st.markdown("Create and manage custom labels for your transactions.")

        # Tag Statistics
        tag_stats = tag_service.get_tag_stats()
        untagged_count = tag_service.get_untagged_count()
        total_transactions = session.query(func.count(Transaction.id)).scalar()
        total_amount = session.query(
            func.coalesce(func.sum(func.coalesce(Transaction.charged_amount, Transaction.original_amount)), 0)
        ).scalar()

        tagged_count = total_transactions - untagged_count
        tagged_pct = (tagged_count / total_transactions * 100) if total_transactions > 0 else 0
        untagged_total = tag_service.get_untagged_total()

        render_metric_row([
            {"value": format_number(len(tag_stats)), "label": "Total Tags"},
            {"value": f"{format_number(tagged_count)}/{format_number(total_transactions)}", "label": "Tagged Transactions"},
            {"value": f"{tagged_pct:.1f}%", "label": "Coverage"},
            {"value": format_amount_private(untagged_total), "label": "Untagged Amount"},
        ])

        st.markdown("")  # Spacing

        # Create Tag
        with st.expander("➕ Create New Tag", expanded=False):
            col1, col2 = st.columns([3, 1])

            with col1:
                new_tag_name = st.text_input("Tag Name", key="new_tag_name", placeholder="Enter tag name...")

            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Create Tag", type="primary", use_container_width=True, key="create_tag_btn"):
                    if new_tag_name and new_tag_name.strip():
                        try:
                            tag = tag_service.get_or_create_tag(new_tag_name.strip())
                            st.toast(f"Created tag: {tag.name}", icon="🏷️")
                            st.rerun()
                        except Exception as e:
                            st.toast(f"Error: {str(e)}", icon="❌")
                    else:
                        st.toast("Please enter a tag name", icon="⚠️")

        st.markdown("")  # Spacing

        # Tags Table
        if not tag_stats:
            st.info("No tags found. Create your first tag above!")
        else:
            table_data = []
            for tag_stat in tag_stats:
                pct_of_total = (tag_stat['total_amount'] / total_amount * 100) if total_amount != 0 else 0
                table_data.append({
                    'Tag': tag_stat['name'],
                    'Transactions': format_number(tag_stat['count']),
                    'Total Amount': format_amount_private(tag_stat['total_amount']),
                    '% of Total': f"{pct_of_total:.1f}%",
                    '_count': tag_stat['count']
                })

            df_tags = pd.DataFrame(table_data)
            df_tags = df_tags.sort_values('_count', ascending=False)

            st.dataframe(df_tags[['Tag', 'Transactions', 'Total Amount', '% of Total']], use_container_width=True, hide_index=True)

            # Tag cloud
            st.markdown("**Quick Tag View**")
            tag_badges_html = format_tags([tag_stat['name'] for tag_stat in tag_stats])
            st.markdown(tag_badges_html, unsafe_allow_html=True)

            st.markdown("")  # Spacing

            # Tag Actions
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Rename/Merge Tag**")
                tag_names = [tag_stat['name'] for tag_stat in tag_stats]
                old_tag_name = st.selectbox("Select tag to rename", tag_names, key="rename_old_tag")
                new_tag_name_rename = st.text_input("New name", key="rename_new_tag", placeholder="Enter new name...")

                if st.button("Rename Tag", type="primary", use_container_width=True, key="rename_tag_btn"):
                    if new_tag_name_rename and new_tag_name_rename.strip():
                        success = tag_service.rename_tag(old_tag_name, new_tag_name_rename.strip())
                        if success:
                            st.toast("Tag renamed successfully", icon="✅")
                            st.rerun()
                        else:
                            st.toast("Failed to rename tag", icon="❌")

            with col2:
                st.markdown("**Delete Tag**")
                delete_tag_name = st.selectbox("Select tag to delete", tag_names, key="delete_tag")
                selected_tag_stat = next((t for t in tag_stats if t['name'] == delete_tag_name), None)

                if selected_tag_stat:
                    st.caption(f"This will remove the tag from {selected_tag_stat['count']} transactions")

                if st.button("Delete Tag", type="secondary", use_container_width=True, key="delete_tag_btn"):
                    success = tag_service.delete_tag(delete_tag_name)
                    if success:
                        st.toast(f"Deleted tag: {delete_tag_name}", icon="🗑️")
                        st.rerun()
                    else:
                        st.toast("Failed to delete tag", icon="❌")

        # Bulk Tagging
        st.markdown("")  # Spacing
        st.markdown("### Bulk Tagging")

        bulk_tab1, bulk_tab2 = st.tabs(["By Merchant Pattern", "By Category"])

        with bulk_tab1:
            col1, col2 = st.columns(2)

            with col1:
                merchant_pattern = st.text_input("Merchant Pattern", key="bulk_merchant_pattern", placeholder="e.g., 'wolt', 'pango'")

            with col2:
                merchant_tags_input = st.text_input("Tags to Add (comma-separated)", key="bulk_merchant_tags", placeholder="e.g., delivery, food")

            if st.button("Preview Matches", key="preview_merchant", use_container_width=True):
                if merchant_pattern and merchant_pattern.strip():
                    total_count = session.query(func.count(Transaction.id)).filter(
                        Transaction.description.ilike(f"%{merchant_pattern}%")
                    ).scalar()

                    if total_count > 0:
                        st.info(f"Found **{total_count}** matching transactions")
                        st.session_state['merchant_preview_ready'] = True
                        st.session_state['merchant_preview_count'] = total_count
                    else:
                        st.warning("No transactions found matching this pattern")
                        st.session_state['merchant_preview_ready'] = False

            if st.session_state.get('merchant_preview_ready', False):
                if st.button("Apply Tags", type="primary", key="apply_merchant", use_container_width=True):
                    if merchant_pattern and merchant_tags_input:
                        tags_list = [tag.strip() for tag in merchant_tags_input.split(',') if tag.strip()]
                        if tags_list:
                            try:
                                count = tag_service.bulk_tag_by_merchant(merchant_pattern.strip(), tags_list)
                                st.session_state['merchant_preview_ready'] = False
                                st.toast(f"Tagged {count} transactions", icon="🏷️")
                                st.rerun()
                            except Exception as e:
                                st.toast(f"Error: {str(e)}", icon="❌")

        with bulk_tab2:
            user_categories = session.query(Transaction.user_category).filter(Transaction.user_category.isnot(None)).distinct().all()
            source_categories = session.query(Transaction.category).filter(Transaction.category.isnot(None)).distinct().all()
            category_set = set([cat[0] for cat in user_categories if cat[0]] + [cat[0] for cat in source_categories if cat[0]])
            category_list = sorted(list(category_set))

            if not category_list:
                st.info("No categories found in your transactions")
            else:
                col1, col2 = st.columns(2)

                with col1:
                    selected_category = st.selectbox("Select Category", category_list, key="bulk_category")

                with col2:
                    category_tags_input = st.text_input("Tags to Add (comma-separated)", key="bulk_category_tags", placeholder="e.g., food, groceries")

                if st.button("Preview Category Matches", key="preview_category", use_container_width=True):
                    match_count = session.query(func.count(Transaction.id)).filter(
                        or_(
                            Transaction.user_category == selected_category,
                            and_(Transaction.user_category.is_(None), Transaction.category == selected_category)
                        )
                    ).scalar()

                    if match_count > 0:
                        st.info(f"Found **{match_count}** transactions in category '{selected_category}'")
                        st.session_state['category_preview_ready'] = True
                        st.session_state['category_preview_count'] = match_count
                    else:
                        st.warning("No transactions found in this category")
                        st.session_state['category_preview_ready'] = False

                if st.session_state.get('category_preview_ready', False):
                    if st.button("Apply Tags to Category", type="primary", key="apply_category", use_container_width=True):
                        if category_tags_input:
                            tags_list = [tag.strip() for tag in category_tags_input.split(',') if tag.strip()]
                            if tags_list:
                                try:
                                    transactions = session.query(Transaction).filter(
                                        or_(
                                            Transaction.user_category == selected_category,
                                            and_(Transaction.user_category.is_(None), Transaction.category == selected_category)
                                        )
                                    ).all()

                                    count = 0
                                    for txn in transactions:
                                        added = tag_service.tag_transaction(txn.id, tags_list)
                                        if added > 0:
                                            count += 1

                                    st.session_state['category_preview_ready'] = False
                                    st.toast(f"Tagged {count} transactions", icon="🏷️")
                                    st.rerun()
                                except Exception as e:
                                    st.toast(f"Error: {str(e)}", icon="❌")

except Exception as e:
    st.error(f"Error loading page: {str(e)}")
    st.exception(e)
    st.info("Make sure the database is initialized with `fin-cli init`")
