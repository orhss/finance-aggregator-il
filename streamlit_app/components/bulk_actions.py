"""
Bulk Actions Components - Reusable preview and confirmation UI for bulk operations

This module provides reusable components for bulk operations across the app.
All bulk actions follow a consistent pattern:
1. Preview affected items
2. Show count and confirmation
3. Execute with feedback
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Callable, Optional


def show_bulk_preview(
    items: List[Dict[str, Any]],
    title: str,
    columns: List[str],
    max_preview: int = 10,
    total_count: Optional[int] = None
) -> None:
    """
    Show preview table for bulk operations

    Args:
        items: List of items to preview (as dictionaries)
        title: Preview section title
        columns: Column names to display
        max_preview: Maximum number of items to show in preview
        total_count: Total count if different from len(items) (for partial previews)
    """
    if not items:
        st.info("No items to preview")
        return

    count = total_count if total_count is not None else len(items)

    st.markdown(f"**{title}**")
    st.info(f"📊 Found **{count}** item(s)")

    # Show preview table
    df = pd.DataFrame(items[:max_preview])
    st.dataframe(df, use_container_width=True, hide_index=True)

    if count > max_preview:
        st.caption(f"Showing first {max_preview} of {count} items")


def show_bulk_confirmation(
    operation_name: str,
    affected_count: int,
    details: Optional[str] = None,
    warning_threshold: int = 50,
    is_destructive: bool = False
) -> None:
    """
    Show confirmation message for bulk operations

    Args:
        operation_name: Name of the operation (e.g., "tag", "delete", "apply rule")
        affected_count: Number of items that will be affected
        details: Additional details to show (e.g., "with tags: food, dining")
        warning_threshold: Show warning if count exceeds this
        is_destructive: If True, use warning styling
    """
    # Build confirmation message
    message = f"This will {operation_name} **{affected_count}** item(s)"
    if details:
        message += f" {details}"

    # Choose appropriate message type
    if is_destructive:
        st.warning(f"⚠️ {message}")
    elif affected_count > warning_threshold:
        st.warning(f"⚠️ {message} (large operation)")
    else:
        st.info(f"ℹ️ {message}")


def bulk_action_workflow(
    preview_button_text: str,
    apply_button_text: str,
    preview_callback: Callable[[], List[Dict[str, Any]]],
    apply_callback: Callable[[], int],
    preview_columns: List[str],
    operation_name: str,
    success_message: str,
    is_destructive: bool = False,
    preview_key: str = "preview",
    apply_key: str = "apply"
) -> None:
    """
    Complete workflow for bulk actions with preview and confirmation

    This is the main function to use for implementing bulk actions.
    It handles the entire flow: preview → confirm → execute → feedback

    Args:
        preview_button_text: Text for preview button (e.g., "Preview Matches")
        apply_button_text: Text for apply button (e.g., "Apply Tags")
        preview_callback: Function that returns list of items to preview
        apply_callback: Function that executes the operation and returns count
        preview_columns: Column names for preview table
        operation_name: Name of operation for confirmation (e.g., "tag")
        success_message: Message to show on success
        is_destructive: Whether this is a destructive operation
        preview_key: Unique key for preview button
        apply_key: Unique key for apply button

    Example:
        ```python
        def preview_matches():
            return db.query().filter(...).all()

        def apply_tags():
            count = service.bulk_tag(...)
            return count

        bulk_action_workflow(
            preview_button_text="Preview Matches",
            apply_button_text="Apply Tags",
            preview_callback=preview_matches,
            apply_callback=apply_tags,
            preview_columns=['Date', 'Description', 'Amount'],
            operation_name="tag",
            success_message="Tagged {count} transactions",
            preview_key="preview_tags",
            apply_key="apply_tags"
        )
        ```
    """
    # Step 1: Preview Button
    if st.button(preview_button_text, key=preview_key):
        # Get preview data
        items = preview_callback()

        if items:
            # Convert to dict format if needed
            if not isinstance(items[0], dict):
                # Assume it's a list of objects with attributes
                items = [
                    {col: getattr(item, col.lower().replace(' ', '_'), None)
                     for col in preview_columns}
                    for item in items
                ]

            # Show preview
            show_bulk_preview(
                items=items,
                title=f"Preview: {operation_name}",
                columns=preview_columns,
                max_preview=20
            )

            # Show confirmation
            show_bulk_confirmation(
                operation_name=operation_name,
                affected_count=len(items),
                is_destructive=is_destructive
            )

            # Store in session state for apply step
            st.session_state[f'{apply_key}_ready'] = True
            st.session_state[f'{apply_key}_count'] = len(items)
        else:
            st.warning("No items found matching your criteria")
            st.session_state[f'{apply_key}_ready'] = False

    # Step 2: Apply Button (only show if preview was successful)
    if st.session_state.get(f'{apply_key}_ready', False):
        expected_count = st.session_state.get(f'{apply_key}_count', 0)

        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button(f"✅ {apply_button_text}", type="primary", key=apply_key, use_container_width=True):
                # Execute the operation
                try:
                    actual_count = apply_callback()

                    # Clear session state
                    st.session_state[f'{apply_key}_ready'] = False

                    # Show success message
                    message = success_message.format(count=actual_count)
                    st.toast(message, icon="✅")

                    # Celebration for bulk operations
                    if actual_count > 10:
                        st.balloons()

                    st.rerun()

                except Exception as e:
                    st.toast(f"Error: {str(e)}", icon="❌")

        with col2:
            if st.button("❌ Cancel", key=f"{apply_key}_cancel", use_container_width=True):
                st.session_state[f'{apply_key}_ready'] = False
                st.rerun()


def quick_bulk_preview(
    query_pattern: str,
    get_matches_func: Callable[[str], List[Any]],
    format_preview_func: Callable[[List[Any]], List[Dict[str, Any]]],
    preview_title: str = "Preview Matches"
) -> Optional[List[Any]]:
    """
    Quick preview helper for pattern-based bulk operations

    Args:
        query_pattern: The search pattern entered by user
        get_matches_func: Function that takes pattern and returns matching items
        format_preview_func: Function that formats items for preview table
        preview_title: Title for the preview section

    Returns:
        List of matching items or None
    """
    if not query_pattern or not query_pattern.strip():
        st.warning("Please enter a search pattern")
        return None

    # Get matches
    matches = get_matches_func(query_pattern.strip())

    if not matches:
        st.warning(f"No items found matching '{query_pattern}'")
        return None

    # Format for preview
    preview_data = format_preview_func(matches)

    # Show preview
    st.info(f"📊 Found **{len(matches)}** matching items")

    # Create DataFrame and display
    df = pd.DataFrame(preview_data[:20])
    st.dataframe(df, use_container_width=True, hide_index=True)

    if len(matches) > 20:
        st.caption(f"Showing first 20 of {len(matches)} items")

    return matches
