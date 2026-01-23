"""
Categories Management Page - Manage category mappings for cross-provider normalization
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
from streamlit_app.utils.formatters import format_number, format_category_badge
from streamlit_app.components.sidebar import render_minimal_sidebar
from streamlit_app.components.theme import apply_theme, render_theme_switcher

# Page config
st.set_page_config(
    page_title="Categories - Financial Aggregator",
    page_icon="📂",
    layout="wide"
)

# Initialize session state
init_session_state()

# Apply theme
theme = apply_theme()

# Render sidebar
render_minimal_sidebar()

# Render theme switcher in sidebar
render_theme_switcher("sidebar")

# Page header
st.title("📂 Category Management")
st.markdown("Normalize categories across credit card providers for consistent analytics")
st.markdown("---")

# Get services
try:
    from db.database import get_session
    from db.models import Transaction, Account
    from services.category_service import CategoryService
    from config.constants import Institution, UnifiedCategory
    from sqlalchemy import func

    session = get_session()
    category_service = CategoryService(session=session)

    # ============================================================================
    # CATEGORY OVERVIEW
    # ============================================================================
    st.subheader("📊 Category Overview")

    # Get comprehensive coverage stats
    coverage = category_service.get_category_coverage_stats()
    analysis = category_service.analyze_categories()

    # Summary metrics - focus on what matters
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Transactions",
            f"{coverage['total']:,}"
        )

    with col2:
        # Transactions with unified category set
        categorized_pct = round(100 * coverage['with_unified_category'] / coverage['total'], 1) if coverage['total'] > 0 else 0
        st.metric(
            "Categorized",
            f"{coverage['with_unified_category']:,}",
            delta=f"{categorized_pct}% of total",
            delta_color="normal" if categorized_pct >= 80 else "off"
        )

    with col3:
        # From provider (raw_category set)
        st.metric(
            "From Provider",
            f"{coverage['with_provider_category']:,}",
            delta=f"{coverage['without_provider_category']:,} without",
            delta_color="normal"
        )

    with col4:
        # Needs attention (no unified category)
        st.metric(
            "Needs Attention",
            f"{coverage['needs_attention']:,}",
            delta="All categorized!" if coverage['needs_attention'] == 0 else "need category",
            delta_color="normal" if coverage['needs_attention'] == 0 else "inverse"
        )

    # Action hint if there are uncategorized transactions
    if coverage['needs_attention'] > 0:
        # Check where the uncategorized come from
        unmapped_provider_cats = category_service.get_unmapped_categories()
        merchant_groups = category_service.get_uncategorized_by_merchant(min_transactions=1)
        merchant_txn_count = sum(g['count'] for g in merchant_groups)

        hints = []
        if unmapped_provider_cats:
            hints.append(f"**{len(unmapped_provider_cats)} unmapped provider categories** → '⚠️ Unmapped' tab")
        if merchant_groups:
            hints.append(f"**{merchant_txn_count:,} transactions without provider category** → '🏪 By Merchant' tab")

        if hints:
            st.info("ℹ️ " + " | ".join(hints))

    # Provider breakdown table
    if analysis['providers']:
        st.markdown("**Provider Breakdown:**")
        provider_data = []
        for provider in analysis['providers']:
            pct = provider['mapped_pct']
            pct_display = f"{pct}%" if pct >= 80 else f"⚠️ {pct}%"
            provider_data.append({
                'Provider': provider['name'].upper(),
                'Unique Categories': format_number(provider['unique_categories']),
                'Transactions': f"{provider['transactions']:,}",
                'Mapped': f"{provider['mapped_transactions']:,}",
                'Coverage': pct_display
            })

        df_providers = pd.DataFrame(provider_data)
        st.dataframe(df_providers, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ============================================================================
    # CREATE MAPPING
    # ============================================================================
    with st.expander("➕ Add New Mapping", expanded=False):
        col1, col2, col3 = st.columns([1, 2, 2])

        with col1:
            new_provider = st.selectbox(
                "Provider",
                options=[p.upper() for p in Institution.credit_cards()],
                key="new_mapping_provider"
            )

        with col2:
            new_raw_category = st.text_input(
                "Raw Category (from provider)",
                key="new_mapping_raw",
                placeholder="Enter the original category name..."
            )

        with col3:
            # Show existing unified categories + standard ones as suggestions
            existing_unified = category_service.get_unified_categories()
            standard_categories = UnifiedCategory.all()
            all_suggestions = sorted(set(existing_unified + standard_categories))

            new_unified_category = st.selectbox(
                "Unified Category",
                options=[""] + all_suggestions + ["[Custom]"],
                key="new_mapping_unified"
            )

            if new_unified_category == "[Custom]":
                new_unified_category = st.text_input(
                    "Custom unified category",
                    key="new_mapping_unified_custom",
                    placeholder="Enter custom category name..."
                )

        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("Add Mapping", type="primary", use_container_width=True):
                if new_raw_category and new_raw_category.strip() and new_unified_category and new_unified_category.strip():
                    try:
                        mapping = category_service.add_mapping(
                            new_provider.lower(),
                            new_raw_category.strip(),
                            new_unified_category.strip()
                        )
                        st.toast(f"Added mapping: {new_provider}/{new_raw_category} -> {new_unified_category}", icon="✅")
                        st.rerun()
                    except Exception as e:
                        st.toast(f"Error adding mapping: {str(e)}", icon="❌")
                else:
                    st.toast("Please fill in all fields", icon="⚠️")

    st.markdown("---")

    # ============================================================================
    # MAIN TABS
    # ============================================================================
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 All Mappings", "⚠️ Unmapped", "🏪 By Merchant", "📊 Unified Categories", "🔧 Bulk Operations"])

    # ------------------------------------------------------------------------
    # Tab 1: All Mappings
    # ------------------------------------------------------------------------
    with tab1:
        st.subheader("Current Category Mappings")

        # Filter by provider
        filter_col1, filter_col2 = st.columns([1, 4])
        with filter_col1:
            provider_filter = st.selectbox(
                "Filter by Provider",
                options=["All"] + [p.upper() for p in Institution.credit_cards()],
                key="mappings_provider_filter"
            )

        selected_provider = None if provider_filter == "All" else provider_filter.lower()
        mappings = category_service.get_all_mappings(selected_provider)

        if not mappings:
            st.info("No mappings found. Add mappings above or use the setup wizard in Bulk Operations.")
        else:
            # Prepare table data
            table_data = []
            for mapping in mappings:
                table_data.append({
                    'Provider': mapping.provider.upper(),
                    'Raw Category': mapping.raw_category,
                    'Unified Category': mapping.unified_category,
                    'Created': mapping.created_at.strftime('%Y-%m-%d') if mapping.created_at else 'N/A',
                    '_provider': mapping.provider,
                    '_raw': mapping.raw_category
                })

            df_mappings = pd.DataFrame(table_data)

            # Display table
            st.dataframe(
                df_mappings[['Provider', 'Raw Category', 'Unified Category', 'Created']],
                use_container_width=True,
                hide_index=True
            )

            st.caption(f"{len(mappings)} mappings total")

            # Edit/Delete section
            st.markdown("---")
            st.markdown("**Edit or Delete Mapping**")

            col1, col2 = st.columns(2)

            with col1:
                # Select mapping to edit/delete
                mapping_options = [f"{m.provider.upper()} / {m.raw_category}" for m in mappings]
                selected_mapping = st.selectbox(
                    "Select Mapping",
                    options=mapping_options,
                    key="edit_mapping_select"
                )

                if selected_mapping:
                    idx = mapping_options.index(selected_mapping)
                    current_mapping = mappings[idx]

                    # Show current value
                    st.caption(f"Current: {current_mapping.raw_category} -> {current_mapping.unified_category}")

                    # New unified category
                    edit_unified = st.selectbox(
                        "New Unified Category",
                        options=all_suggestions,
                        index=all_suggestions.index(current_mapping.unified_category) if current_mapping.unified_category in all_suggestions else 0,
                        key="edit_mapping_unified"
                    )

                    if st.button("Update Mapping", type="primary", use_container_width=True):
                        try:
                            category_service.add_mapping(
                                current_mapping.provider,
                                current_mapping.raw_category,
                                edit_unified
                            )
                            st.toast(f"Updated mapping to: {edit_unified}", icon="✅")
                            st.rerun()
                        except Exception as e:
                            st.toast(f"Error updating: {str(e)}", icon="❌")

            with col2:
                st.markdown("**Delete Mapping**")
                if selected_mapping:
                    st.warning(f"⚠️ This will remove the mapping for '{current_mapping.raw_category}'")

                    if st.button("Delete Mapping", type="secondary", use_container_width=True):
                        if category_service.remove_mapping(current_mapping.provider, current_mapping.raw_category):
                            st.toast(f"Deleted mapping for {current_mapping.raw_category}", icon="🗑️")
                            st.rerun()
                        else:
                            st.toast("Failed to delete mapping", icon="❌")

    # ------------------------------------------------------------------------
    # Tab 2: Unmapped Categories
    # ------------------------------------------------------------------------
    with tab2:
        st.subheader("Unmapped Categories")
        st.markdown("Categories from your transactions that don't have a unified mapping yet.")

        unmapped = category_service.get_unmapped_categories()

        if not unmapped:
            st.success("All categories are mapped!")
        else:
            # Quick stats
            total_unmapped_txns = sum(u['count'] for u in unmapped)
            st.warning(f"**{len(unmapped)} categories** affecting **{total_unmapped_txns:,} transactions** are unmapped.")

            # Display table
            unmapped_data = []
            for item in unmapped:
                unmapped_data.append({
                    'Provider': item['provider'].upper(),
                    'Raw Category': item['raw_category'],
                    'Transactions': f"{item['count']:,}",
                    'Sample Merchant': item['sample_merchant'] or '-',
                    '_provider': item['provider'],
                    '_raw': item['raw_category'],
                    '_count': item['count']
                })

            df_unmapped = pd.DataFrame(unmapped_data)

            # Sort options
            sort_col1, sort_col2 = st.columns([1, 4])
            with sort_col1:
                sort_by = st.selectbox(
                    "Sort by",
                    ["Transaction Count", "Provider", "Category Name"],
                    key="unmapped_sort"
                )

            if sort_by == "Transaction Count":
                df_unmapped = df_unmapped.sort_values('_count', ascending=False)
            elif sort_by == "Provider":
                df_unmapped = df_unmapped.sort_values('Provider')
            else:
                df_unmapped = df_unmapped.sort_values('Raw Category')

            st.dataframe(
                df_unmapped[['Provider', 'Raw Category', 'Transactions', 'Sample Merchant']],
                use_container_width=True,
                hide_index=True
            )

            # Quick mapping section
            st.markdown("---")
            st.markdown("**Quick Map**")
            st.caption("Select an unmapped category and assign a unified category")

            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                unmapped_options = [f"{u['provider'].upper()} / {u['raw_category']} ({u['count']} txns)" for u in unmapped]
                quick_map_select = st.selectbox(
                    "Unmapped Category",
                    options=unmapped_options,
                    key="quick_map_select"
                )

            with col2:
                quick_map_unified = st.selectbox(
                    "Map to Unified Category",
                    options=all_suggestions,
                    key="quick_map_unified"
                )

            with col3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Map", type="primary", use_container_width=True):
                    if quick_map_select and quick_map_unified:
                        idx = unmapped_options.index(quick_map_select)
                        item = unmapped[idx]
                        try:
                            category_service.add_mapping(
                                item['provider'],
                                item['raw_category'],
                                quick_map_unified
                            )
                            st.toast(f"Mapped '{item['raw_category']}' -> '{quick_map_unified}'", icon="✅")
                            st.rerun()
                        except Exception as e:
                            st.toast(f"Error: {str(e)}", icon="❌")

    # ------------------------------------------------------------------------
    # Tab 3: By Merchant (Uncategorized without provider category)
    # ------------------------------------------------------------------------
    with tab3:
        st.subheader("Categorize by Merchant")
        st.markdown("Group uncategorized transactions by merchant pattern and assign categories in bulk.")
        st.caption("This is for transactions without provider categories (e.g., Isracard)")

        # Get uncategorized by merchant
        merchant_groups = category_service.get_uncategorized_by_merchant(min_transactions=1)

        if not merchant_groups:
            st.success("All transactions have categories!")
        else:
            # Summary
            total_uncategorized = sum(g['count'] for g in merchant_groups)
            st.warning(f"**{len(merchant_groups)} merchant patterns** covering **{total_uncategorized:,} transactions** need categories.")

            # Filter options
            filter_col1, filter_col2 = st.columns([1, 3])
            with filter_col1:
                min_txn_filter = st.selectbox(
                    "Min transactions",
                    options=[1, 2, 3, 5, 10],
                    index=0,
                    key="merchant_min_txn"
                )

            # Filter groups
            filtered_groups = [g for g in merchant_groups if g['count'] >= min_txn_filter]

            if not filtered_groups:
                st.info(f"No merchant patterns with {min_txn_filter}+ transactions.")
            else:
                # Display table
                merchant_data = []
                for i, group in enumerate(filtered_groups):
                    merchant_data.append({
                        '#': i + 1,
                        'Merchant Pattern': group['merchant_pattern'],
                        'Provider': group['provider'].upper(),
                        'Transactions': group['count'],
                        'Total Amount': f"₪{group['total_amount']:,.0f}",
                        'Samples': ', '.join(group['sample_descriptions'][:2]),
                        '_idx': i
                    })

                df_merchants = pd.DataFrame(merchant_data)
                st.dataframe(
                    df_merchants[['#', 'Merchant Pattern', 'Provider', 'Transactions', 'Total Amount', 'Samples']],
                    use_container_width=True,
                    hide_index=True
                )

                # Quick categorize section
                st.markdown("---")
                st.markdown("**Quick Categorize**")

                col1, col2, col3 = st.columns([2, 2, 1])

                with col1:
                    merchant_options = [f"{g['merchant_pattern']} ({g['count']} txns)" for g in filtered_groups]
                    selected_merchant = st.selectbox(
                        "Select Merchant Pattern",
                        options=merchant_options,
                        key="merchant_select"
                    )

                with col2:
                    assign_category = st.selectbox(
                        "Assign Category",
                        options=all_suggestions,
                        key="merchant_assign_category"
                    )

                with col3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("Apply", type="primary", use_container_width=True, key="merchant_apply"):
                        if selected_merchant and assign_category:
                            idx = merchant_options.index(selected_merchant)
                            group = filtered_groups[idx]
                            try:
                                result = category_service.bulk_set_category_with_mapping(
                                    group['merchant_pattern'],
                                    assign_category,
                                    group['transaction_ids'],
                                    group['provider']
                                )
                                msg = f"Categorized {result['transactions_updated']} transactions as '{assign_category}'"
                                if result['mapping_created']:
                                    msg += " (mapping saved for future)"
                                st.toast(msg, icon="✅")
                                st.rerun()
                            except Exception as e:
                                st.toast(f"Error: {str(e)}", icon="❌")

                # Bulk categorize multiple merchants
                st.markdown("---")
                st.markdown("**Bulk Categorize Multiple Merchants**")
                st.caption("Select multiple merchant patterns to categorize at once")

                # Multi-select merchants
                selected_merchants = st.multiselect(
                    "Select Merchants",
                    options=merchant_options,
                    key="bulk_merchant_select"
                )

                if selected_merchants:
                    bulk_category = st.selectbox(
                        "Category for all selected",
                        options=all_suggestions,
                        key="bulk_merchant_category"
                    )

                    total_selected = sum(
                        filtered_groups[merchant_options.index(m)]['count']
                        for m in selected_merchants
                    )
                    st.info(f"Will categorize **{total_selected} transactions** from {len(selected_merchants)} merchants")

                    if st.button(f"Apply to {len(selected_merchants)} Merchants", type="primary", key="bulk_merchant_apply"):
                        try:
                            total_updated = 0
                            mappings_created = 0
                            for m in selected_merchants:
                                idx = merchant_options.index(m)
                                group = filtered_groups[idx]
                                result = category_service.bulk_set_category_with_mapping(
                                    group['merchant_pattern'],
                                    bulk_category,
                                    group['transaction_ids'],
                                    group['provider']
                                )
                                total_updated += result['transactions_updated']
                                if result['mapping_created']:
                                    mappings_created += 1

                            msg = f"Categorized {total_updated} transactions as '{bulk_category}'"
                            if mappings_created > 0:
                                msg += f" ({mappings_created} mappings saved)"
                            st.toast(msg, icon="✅")
                            st.rerun()
                        except Exception as e:
                            st.toast(f"Error: {str(e)}", icon="❌")

    # ------------------------------------------------------------------------
    # Tab 4: Unified Categories
    # ------------------------------------------------------------------------
    with tab4:
        st.subheader("Unified Categories Overview")
        st.markdown("View how raw categories from different providers are normalized.")

        unified_stats = category_service.get_unified_categories_stats()

        if not unified_stats:
            st.info("No unified categories yet. Create mappings to see them here.")
        else:
            # Display table
            unified_data = []
            for stat in unified_stats:
                unified_data.append({
                    'Unified Category': stat['unified_category'],
                    'Providers': ', '.join(p.upper() for p in stat['providers']),
                    'Raw Categories Mapped': format_number(stat['raw_count']),
                    'Transactions': f"{stat['transaction_count']:,}",
                    '_txn_count': stat['transaction_count']
                })

            df_unified = pd.DataFrame(unified_data)
            df_unified = df_unified.sort_values('_txn_count', ascending=False)

            st.dataframe(
                df_unified[['Unified Category', 'Providers', 'Raw Categories Mapped', 'Transactions']],
                use_container_width=True,
                hide_index=True
            )

            # Visual category badges
            st.markdown("**📌 Category Overview**")
            badges_html = " ".join([format_category_badge(stat['unified_category']) for stat in unified_stats])
            st.markdown(badges_html, unsafe_allow_html=True)

            # Rename unified category
            st.markdown("---")
            st.markdown("**Rename Unified Category**")

            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                unified_names = [s['unified_category'] for s in unified_stats]
                rename_old = st.selectbox(
                    "Select Category to Rename",
                    options=unified_names,
                    key="rename_unified_old"
                )

            with col2:
                rename_new = st.text_input(
                    "New Name",
                    key="rename_unified_new",
                    placeholder="Enter new category name..."
                )

            with col3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Rename", type="primary", use_container_width=True):
                    if rename_old and rename_new and rename_new.strip():
                        count = category_service.rename_unified_category(rename_old, rename_new.strip())
                        if count > 0:
                            st.toast(f"Renamed '{rename_old}' to '{rename_new}' ({count} mappings)", icon="✅")
                            st.rerun()
                        else:
                            st.toast("No mappings found to rename", icon="⚠️")
                    else:
                        st.toast("Please enter a new name", icon="⚠️")

    # ------------------------------------------------------------------------
    # Tab 5: Bulk Operations
    # ------------------------------------------------------------------------
    with tab5:
        st.subheader("Bulk Operations")

        bulk_tab1, bulk_tab2, bulk_tab3 = st.tabs(["📥 Setup Wizard", "🔄 Apply Mappings", "📤 Import/Export"])

        # Setup Wizard
        with bulk_tab1:
            st.markdown("**Interactive Setup Wizard**")
            st.markdown("Map all unmapped categories one by one.")

            unmapped_for_wizard = category_service.get_unmapped_categories()

            if not unmapped_for_wizard:
                st.success("All categories are already mapped!")
            else:
                # Initialize wizard state
                if 'wizard_index' not in st.session_state:
                    st.session_state.wizard_index = 0
                if 'wizard_mappings' not in st.session_state:
                    st.session_state.wizard_mappings = []

                current_idx = st.session_state.wizard_index
                total_items = len(unmapped_for_wizard)

                if current_idx < total_items:
                    item = unmapped_for_wizard[current_idx]

                    # Progress bar
                    progress = current_idx / total_items
                    st.progress(progress, text=f"Progress: {current_idx}/{total_items}")

                    # Current item card
                    st.markdown(f"""
                    <div style="padding: 15px; background-color: #f0f2f6; border-radius: 8px; margin: 10px 0;">
                        <strong>Provider:</strong> {item['provider'].upper()}<br>
                        <strong>Raw Category:</strong> {item['raw_category']}<br>
                        <strong>Transactions:</strong> {item['count']:,}<br>
                        <strong>Sample:</strong> {item['sample_merchant'] or 'N/A'}
                    </div>
                    """, unsafe_allow_html=True)

                    # Mapping selection
                    wizard_unified = st.selectbox(
                        "Map to Unified Category",
                        options=["[Skip]"] + all_suggestions + ["[Custom]"],
                        key=f"wizard_unified_{current_idx}"
                    )

                    custom_value = ""
                    if wizard_unified == "[Custom]":
                        custom_value = st.text_input(
                            "Custom category name",
                            key=f"wizard_custom_{current_idx}"
                        )

                    col1, col2, col3 = st.columns([1, 1, 1])

                    with col1:
                        if st.button("⬅️ Previous", disabled=current_idx == 0, use_container_width=True):
                            st.session_state.wizard_index -= 1
                            st.rerun()

                    with col2:
                        if st.button("Skip ➡️", use_container_width=True):
                            st.session_state.wizard_index += 1
                            st.rerun()

                    with col3:
                        if st.button("Save & Next ➡️", type="primary", use_container_width=True):
                            final_category = custom_value if wizard_unified == "[Custom]" else wizard_unified

                            if final_category and final_category not in ["[Skip]", ""]:
                                try:
                                    category_service.add_mapping(
                                        item['provider'],
                                        item['raw_category'],
                                        final_category
                                    )
                                    st.session_state.wizard_mappings.append({
                                        'provider': item['provider'],
                                        'raw': item['raw_category'],
                                        'unified': final_category
                                    })
                                    st.toast(f"Mapped '{item['raw_category']}' -> '{final_category}'", icon="✅")
                                except Exception as e:
                                    st.toast(f"Error: {str(e)}", icon="❌")

                            st.session_state.wizard_index += 1
                            st.rerun()

                else:
                    # Wizard complete
                    st.success("Setup complete!")
                    st.markdown(f"**Mappings created:** {len(st.session_state.wizard_mappings)}")

                    if st.session_state.wizard_mappings:
                        if st.button("Apply Mappings to Transactions", type="primary"):
                            results = category_service.apply_mappings_to_transactions()
                            total = sum(results.values())
                            st.toast(f"Applied mappings to {total:,} transactions", icon="✅")
                            st.balloons()

                    if st.button("Restart Wizard"):
                        st.session_state.wizard_index = 0
                        st.session_state.wizard_mappings = []
                        st.rerun()

        # Apply Mappings
        with bulk_tab2:
            st.markdown("**Apply Mappings to Transactions**")
            st.markdown("Update the `category` field on all transactions based on current mappings.")

            # Show current stats
            current_unmapped = category_service.get_unmapped_count()
            st.info(f"Currently **{current_unmapped:,}** transactions have unmapped categories.")

            col1, col2 = st.columns(2)

            with col1:
                apply_provider = st.selectbox(
                    "Provider (or All)",
                    options=["All Providers"] + [p.upper() for p in Institution.credit_cards()],
                    key="apply_provider"
                )

            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Apply Mappings", type="primary", use_container_width=True):
                    provider_to_apply = None if apply_provider == "All Providers" else apply_provider.lower()
                    results = category_service.apply_mappings_to_transactions(provider_to_apply)
                    total = sum(results.values())

                    if total > 0:
                        st.toast(f"Updated {total:,} transactions", icon="✅")

                        # Show breakdown
                        result_data = [{'Provider': p.upper(), 'Updated': f"{c:,}"} for p, c in results.items() if c > 0]
                        if result_data:
                            st.dataframe(pd.DataFrame(result_data), use_container_width=True, hide_index=True)
                    else:
                        st.toast("No transactions needed updating", icon="ℹ️")

        # Import/Export
        with bulk_tab3:
            st.markdown("**Import/Export Mappings**")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Export Mappings**")
                st.caption("Download your mappings as JSON for backup or sharing.")

                if st.button("Export to JSON", use_container_width=True):
                    import json
                    mappings_export = category_service.export_mappings()

                    st.download_button(
                        label="📥 Download JSON",
                        data=json.dumps(mappings_export, ensure_ascii=False, indent=2),
                        file_name=f"category_mappings_{datetime.now().strftime('%Y%m%d')}.json",
                        mime="application/json"
                    )

            with col2:
                st.markdown("**Import Mappings**")
                st.caption("Upload a JSON file with mappings.")

                uploaded_file = st.file_uploader(
                    "Choose JSON file",
                    type=['json'],
                    key="import_mappings_file"
                )

                overwrite = st.checkbox("Overwrite existing mappings", key="import_overwrite")

                if uploaded_file is not None:
                    if st.button("Import", type="primary", use_container_width=True):
                        try:
                            import json
                            mappings_import = json.loads(uploaded_file.read().decode('utf-8'))
                            results = category_service.import_mappings(mappings_import, overwrite=overwrite)

                            st.success(f"""
                            **Import Complete:**
                            - Added: {results['added']}
                            - Updated: {results['updated']}
                            - Skipped: {results['skipped']}
                            """)
                            st.rerun()
                        except json.JSONDecodeError:
                            st.error("Invalid JSON file")
                        except Exception as e:
                            st.error(f"Error importing: {str(e)}")

except Exception as e:
    st.error(f"Error loading categories: {str(e)}")
    st.exception(e)
    st.info("Make sure the database is initialized with `fin-cli init` and migrations are applied with `fin-cli maintenance migrate`")
