"""
Rules Management Page - Manage auto-categorization and tagging rules
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

from streamlit_app.utils.session import init_session_state
from streamlit_app.utils.formatters import format_currency, format_number
from streamlit_app.components.sidebar import render_minimal_sidebar
from streamlit_app.components.bulk_actions import show_bulk_confirmation

# Page config
st.set_page_config(
    page_title="Rules - Financial Aggregator",
    page_icon="📋",
    layout="wide"
)

# Initialize session state
init_session_state()

# Render sidebar
render_minimal_sidebar()

# Page header
st.title("📋 Rules Management")
st.markdown("Manage auto-categorization and tagging rules")
st.markdown("---")

# Get services
try:
    from db.database import get_session
    from db.models import Transaction, Tag
    from services.rules_service import RulesService, MatchType, Rule
    from services.tag_service import TagService
    from sqlalchemy import func

    session = get_session()
    rules_service = RulesService(session=session)
    tag_service = TagService(session=session)

    # Load rules
    rules = rules_service.get_rules()

    # ============================================================================
    # RULES OVERVIEW
    # ============================================================================
    st.subheader("📊 Rules Overview")

    col1, col2, col3 = st.columns(3)

    with col1:
        enabled_rules = sum(1 for rule in rules if rule.enabled)
        st.metric("Total Rules", f"{enabled_rules} / {len(rules)}")

    with col2:
        rules_with_category = sum(1 for rule in rules if rule.category)
        st.metric("With Category", format_number(rules_with_category))

    with col3:
        rules_with_tags = sum(1 for rule in rules if rule.tags)
        st.metric("With Tags", format_number(rules_with_tags))

    st.markdown("---")

    # ============================================================================
    # ADD/EDIT RULE
    # ============================================================================
    with st.expander("➕ Add New Rule", expanded=False):
        st.markdown("**Create a new auto-categorization/tagging rule**")

        col1, col2 = st.columns(2)

        with col1:
            rule_pattern = st.text_input(
                "Pattern",
                key="new_rule_pattern",
                placeholder="e.g., 'wolt', 'pango', 'סופר'",
                help="Pattern to match in transaction description"
            )

            rule_match_type = st.selectbox(
                "Match Type",
                ["contains", "exact", "starts_with", "ends_with", "regex"],
                key="new_rule_match_type",
                help="How to match the pattern"
            )

            rule_category = st.text_input(
                "Category (optional)",
                key="new_rule_category",
                placeholder="e.g., Food & Dining"
            )

        with col2:
            rule_tags_input = st.text_input(
                "Tags to Add (comma-separated, optional)",
                key="new_rule_tags",
                placeholder="e.g., delivery, food"
            )

            rule_remove_tags_input = st.text_input(
                "Tags to Remove (comma-separated, optional)",
                key="new_rule_remove_tags",
                placeholder="e.g., uncategorized"
            )

            rule_description = st.text_input(
                "Description (optional)",
                key="new_rule_description",
                placeholder="Human-readable description"
            )

        if st.button("Add Rule", type="primary", use_container_width=True):
            if rule_pattern and rule_pattern.strip():
                # Parse tags
                tags_list = [tag.strip() for tag in rule_tags_input.split(',') if tag.strip()] if rule_tags_input else []
                remove_tags_list = [tag.strip() for tag in rule_remove_tags_input.split(',') if tag.strip()] if rule_remove_tags_input else []

                try:
                    new_rule = rules_service.add_rule(
                        pattern=rule_pattern.strip(),
                        category=rule_category.strip() if rule_category else None,
                        tags=tags_list,
                        remove_tags=remove_tags_list,
                        match_type=MatchType(rule_match_type),
                        description=rule_description.strip() if rule_description else None
                    )
                    st.toast(f"Created rule: {new_rule.pattern}", icon="📋")
                    st.rerun()
                except Exception as e:
                    st.toast(f"Error creating rule: {str(e)}", icon="❌")
            else:
                st.toast("Please enter a pattern", icon="⚠️")

    st.markdown("---")

    # ============================================================================
    # RULES TABLE
    # ============================================================================
    st.subheader("📋 All Rules")

    if not rules:
        st.info("No rules found. Create your first rule above or import from YAML!")

        # Option to create default rules file
        if st.button("Create Default Rules File", type="primary"):
            success = rules_service.create_default_rules_file()
            if success:
                st.success(f"✅ Created default rules file at: {rules_service.rules_file}")
            else:
                st.warning(f"Rules file already exists at: {rules_service.rules_file}")
    else:
        # Prepare table data
        table_data = []
        for idx, rule in enumerate(rules):
            table_data.append({
                'Index': idx,
                'Pattern': rule.pattern,
                'Match Type': rule.match_type.value,
                'Category': rule.category or '-',
                'Tags': ', '.join(rule.tags) if rule.tags else '-',
                'Remove Tags': ', '.join(rule.remove_tags) if rule.remove_tags else '-',
                'Description': rule.description or '-',
                'Enabled': '✅' if rule.enabled else '❌',
                '_rule': rule
            })

        df_rules = pd.DataFrame(table_data)

        # Display table
        st.dataframe(
            df_rules[['Pattern', 'Match Type', 'Category', 'Tags', 'Remove Tags', 'Description', 'Enabled']],
            use_container_width=True,
            hide_index=True
        )

        st.markdown("---")

        # ============================================================================
        # DELETE RULE
        # ============================================================================
        st.subheader("⚡ Rule Actions")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Delete Rule**")

            rule_patterns = [rule.pattern for rule in rules]
            delete_rule_pattern = st.selectbox(
                "Select rule to delete",
                rule_patterns,
                key="delete_rule"
            )

            if st.button("Delete Rule", type="secondary", use_container_width=True):
                success = rules_service.remove_rule(delete_rule_pattern)
                if success:
                    st.toast(f"Deleted rule: {delete_rule_pattern}", icon="🗑️")
                    st.rerun()
                else:
                    st.toast("Failed to delete rule", icon="❌")

        with col2:
            st.markdown("**Test Rule Pattern**")

            test_description = st.text_input(
                "Test Description",
                key="test_description",
                placeholder="Enter transaction description to test..."
            )

            if st.button("Test Against All Rules", use_container_width=True):
                if test_description and test_description.strip():
                    matching_rules = rules_service.find_matching_rules(test_description.strip())

                    if matching_rules:
                        st.success(f"✅ Matched {len(matching_rules)} rule(s):")

                        for rule in matching_rules:
                            st.markdown(f"- **{rule.pattern}** ({rule.match_type.value})")
                            if rule.category:
                                st.markdown(f"  - Category: {rule.category}")
                            if rule.tags:
                                st.markdown(f"  - Tags: {', '.join(rule.tags)}")
                            if rule.remove_tags:
                                st.markdown(f"  - Remove Tags: {', '.join(rule.remove_tags)}")
                    else:
                        st.info("No rules matched this description")
                else:
                    st.warning("Please enter a test description")

    st.markdown("---")

    # ============================================================================
    # APPLY RULES
    # ============================================================================
    st.subheader("🔧 Apply Rules to Transactions")

    st.info("💡 Apply rules to update transaction categories and tags automatically")

    col1, col2 = st.columns(2)

    with col1:
        apply_scope = st.radio(
            "Scope",
            ["All Transactions", "Uncategorized Only"],
            key="apply_scope",
            help="Choose which transactions to process"
        )

    with col2:
        apply_mode = st.radio(
            "Mode",
            ["Dry Run (Preview)", "Apply Changes"],
            key="apply_mode",
            help="Dry run shows what would change without saving"
        )

    # Dry run / Apply
    if st.button("Run", type="primary", use_container_width=True):
        if not rules:
            st.warning("No rules to apply")
        else:
            only_uncategorized = (apply_scope == "Uncategorized Only")
            dry_run = (apply_mode == "Dry Run (Preview)")

            try:
                with st.spinner("Processing transactions..."):
                    results = rules_service.apply_rules(
                        only_uncategorized=only_uncategorized,
                        dry_run=dry_run
                    )

                processed = results.get('processed', 0)
                modified = results.get('modified', 0)
                details = results.get('details', [])

                if dry_run:
                    st.toast(f"Dry run complete: {modified} / {processed} transactions would be modified", icon="🔍")

                    # After dry run, show confirmation for actual apply
                    if modified > 0:
                        show_bulk_confirmation(
                            operation_name="modify with rules",
                            affected_count=modified,
                            details=f"(out of {processed} processed)",
                            warning_threshold=50
                        )
                else:
                    st.toast(f"Applied rules: {modified} / {processed} transactions modified", icon="✅")
                    if modified > 0:
                        st.balloons()  # Celebration for successful bulk operation

                if details:
                    st.markdown(f"**Preview of changes:**" if dry_run else "**Changes applied:**")

                    preview_data = []
                    for detail in details[:50]:
                        preview_data.append({
                            'Description': detail['description'][:50] + '...' if len(detail['description']) > 50 else detail['description'],
                            'Category': detail['category'] or '-',
                            'Tags': ', '.join(detail['tags']) if detail['tags'] else '-',
                            'Remove Tags': ', '.join(detail['remove_tags']) if detail['remove_tags'] else '-',
                            'Matched Rules': ', '.join(detail['matched_rules'][:2]) if detail['matched_rules'] else '-'
                        })

                    df_preview = pd.DataFrame(preview_data)
                    st.dataframe(df_preview, use_container_width=True, hide_index=True)

                    if not dry_run:
                        st.rerun()
                elif processed > 0:
                    st.info("No changes needed - all transactions already match rules")
                else:
                    st.warning("No transactions to process")

            except Exception as e:
                st.error(f"Error applying rules: {str(e)}")
                st.exception(e)

    st.markdown("---")

    # ============================================================================
    # IMPORT/EXPORT
    # ============================================================================
    st.subheader("📁 Import/Export Rules")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Export Rules to YAML**")

        st.caption(f"Rules file: `{rules_service.rules_file}`")

        if st.button("📥 Export Rules", use_container_width=True):
            if rules:
                try:
                    # Read the YAML file
                    with open(rules_service.rules_file, 'r', encoding='utf-8') as f:
                        yaml_content = f.read()

                    st.download_button(
                        label="Download Rules YAML",
                        data=yaml_content,
                        file_name="category_rules.yaml",
                        mime="text/yaml",
                        use_container_width=True
                    )

                    st.success("✅ Ready to download")
                except Exception as e:
                    st.error(f"Error reading rules file: {str(e)}")
            else:
                st.warning("No rules to export")

    with col2:
        st.markdown("**Import Rules from YAML**")

        uploaded_file = st.file_uploader(
            "Upload Rules YAML",
            type=['yaml', 'yml'],
            key="import_rules"
        )

        if uploaded_file is not None:
            if st.button("📤 Import Rules", use_container_width=True, type="primary"):
                try:
                    # Read uploaded file
                    yaml_content = uploaded_file.read().decode('utf-8')

                    # Parse YAML
                    data = yaml.safe_load(yaml_content)
                    rules_data = data.get('rules', [])

                    if not rules_data:
                        st.warning("No rules found in uploaded file")
                    else:
                        # Backup existing rules
                        backup_path = rules_service.rules_file.parent / f"category_rules_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
                        if rules_service.rules_file.exists():
                            import shutil
                            shutil.copy(rules_service.rules_file, backup_path)
                            st.info(f"Created backup: {backup_path.name}")

                        # Write new rules
                        with open(rules_service.rules_file, 'w', encoding='utf-8') as f:
                            f.write(yaml_content)

                        st.toast(f"Imported {len(rules_data)} rules", icon="📥")
                        st.rerun()

                except yaml.YAMLError as e:
                    st.toast(f"Invalid YAML file: {str(e)}", icon="❌")
                except Exception as e:
                    st.toast(f"Error importing rules: {str(e)}", icon="❌")

    # Reset to defaults
    st.markdown("---")

    if st.button("🔄 Create Empty Rules File", type="secondary"):
        if st.session_state.get('confirm_reset'):
            success = rules_service.create_default_rules_file()
            if success:
                st.success("✅ Created empty rules file")
                st.session_state.confirm_reset = False
                st.rerun()
            else:
                st.warning("Rules file already exists")
                st.session_state.confirm_reset = False
        else:
            st.session_state.confirm_reset = True
            st.warning("⚠️ This will create an empty rules file. Click again to confirm.")

    # ============================================================================
    # DOCUMENTATION
    # ============================================================================
    st.markdown("---")

    with st.expander("📖 Rules Documentation", expanded=False):
        st.markdown("""
        ## Rules System

        Rules automatically categorize and tag transactions based on pattern matching.

        ### Match Types

        - **contains** (default): Case-insensitive substring match
        - **exact**: Exact match (case-insensitive)
        - **starts_with**: Description starts with pattern
        - **ends_with**: Description ends with pattern
        - **regex**: Regular expression match

        ### Rule Application

        - Rules are applied in order
        - First matching category wins
        - All matching tags are combined
        - Rules can also remove tags

        ### Example Rules

        ```yaml
        rules:
          - pattern: "wolt"
            category: "Food & Dining"
            tags: ["delivery", "food"]
            description: "Wolt food delivery"

          - pattern: "pango"
            category: "Transportation"
            tags: ["parking", "car"]
            description: "Pango parking app"

          - pattern: "סופר"
            category: "Groceries"
            tags: ["groceries"]
            description: "Supermarkets (Hebrew)"

          - pattern: "^TRANSFER.*"
            match_type: "regex"
            category: "Transfers"
            tags: ["internal"]
            description: "Bank transfers"
        ```

        ### CLI Commands

        ```bash
        # Add a rule
        fin-cli rules add "pattern" -c "Category" -t "tag1,tag2"

        # List rules
        fin-cli rules list

        # Apply rules
        fin-cli rules apply

        # Apply to uncategorized only
        fin-cli rules apply --uncategorized

        # Dry run (preview changes)
        fin-cli rules apply --dry-run
        ```
        """)

except Exception as e:
    st.error(f"Error loading rules: {str(e)}")
    st.exception(e)
    st.info("💡 Make sure the database is initialized with `fin-cli init`")
