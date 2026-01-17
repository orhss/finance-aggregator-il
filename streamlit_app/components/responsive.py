"""
Responsive Layout Components - Reusable utilities for mobile-friendly layouts

This module provides reusable components and utilities for creating responsive
layouts that work well on desktop, tablet, and mobile devices.
"""

import streamlit as st
from typing import List, Optional, Union


def responsive_columns(
    desktop_ratio: List[int],
    mobile_ratio: Optional[List[int]] = None,
    gap: str = "small"
) -> List:
    """
    Create responsive column layout that adapts to screen size

    Args:
        desktop_ratio: Column ratios for desktop (e.g., [2, 1] for 2:1 ratio)
        mobile_ratio: Column ratios for mobile (defaults to [1] - stacked)
        gap: Gap between columns ("small", "medium", "large")

    Returns:
        List of column objects

    Example:
        cols = responsive_columns([2, 1], mobile_ratio=[1, 1])
        with cols[0]:
            st.write("Left column")
        with cols[1]:
            st.write("Right column")
    """
    # On mobile, default to stacking (single column)
    if mobile_ratio is None:
        mobile_ratio = [1] * len(desktop_ratio)

    # Streamlit's st.columns handles responsiveness automatically
    # We provide semantic wrapper for consistency
    return st.columns(desktop_ratio, gap=gap)


def mobile_card(
    title: str,
    content: str,
    icon: Optional[str] = None,
    expandable: bool = False
) -> None:
    """
    Display mobile-friendly card component

    Args:
        title: Card title
        content: Card content
        icon: Optional icon emoji
        expandable: Whether to make card expandable on mobile

    Example:
        mobile_card(
            title="Account Balance",
            content="₪12,345.67",
            icon="💰"
        )
    """
    if expandable:
        with st.expander(f"{icon + ' ' if icon else ''}{title}", expanded=False):
            st.markdown(content)
    else:
        if icon:
            st.markdown(f"### {icon} {title}")
        else:
            st.markdown(f"### {title}")
        st.markdown(content)


def responsive_metrics(
    metrics: List[dict],
    desktop_columns: int = 4,
    mobile_columns: int = 2
) -> None:
    """
    Display metrics in responsive grid

    Args:
        metrics: List of metric dicts with keys: label, value, delta
        desktop_columns: Number of columns on desktop
        mobile_columns: Number of columns on mobile (used for column calculation)

    Example:
        responsive_metrics([
            {"label": "Revenue", "value": "₪100K", "delta": "+10%"},
            {"label": "Expenses", "value": "₪50K", "delta": "-5%"},
        ], desktop_columns=4)
    """
    # Create columns based on desktop layout
    cols = st.columns(desktop_columns)

    for i, metric in enumerate(metrics):
        with cols[i % desktop_columns]:
            st.metric(
                label=metric.get("label", ""),
                value=metric.get("value", ""),
                delta=metric.get("delta")
            )


def responsive_table_config(
    hide_on_mobile: Optional[List[str]] = None,
    truncate_on_mobile: Optional[dict] = None
) -> dict:
    """
    Generate responsive table configuration

    Args:
        hide_on_mobile: List of column names to hide on mobile
        truncate_on_mobile: Dict of {column_name: max_length} for mobile truncation

    Returns:
        Dict of column configurations for st.dataframe

    Example:
        config = responsive_table_config(
            hide_on_mobile=["Account", "Institution"],
            truncate_on_mobile={"Description": 30}
        )
        st.dataframe(df, column_config=config)
    """
    config = {}

    # Note: Streamlit doesn't have built-in responsive column hiding
    # This returns configuration structure for future use
    # For now, we recommend using column selection in table customization

    if truncate_on_mobile:
        for col, max_len in truncate_on_mobile.items():
            config[col] = st.column_config.TextColumn(
                col,
                help=f"Truncated to {max_len} chars on mobile"
            )

    return config


def stacked_layout(sections: List[dict]) -> None:
    """
    Display sections in mobile-friendly stacked layout

    Args:
        sections: List of section dicts with keys: title, content_func

    Example:
        stacked_layout([
            {"title": "Overview", "content_func": lambda: st.write("Overview content")},
            {"title": "Details", "content_func": lambda: st.write("Details content")},
        ])
    """
    for section in sections:
        st.markdown(f"### {section.get('title', '')}")
        if "content_func" in section:
            section["content_func"]()
        st.markdown("---")


def compact_form(
    fields: List[dict],
    submit_text: str = "Submit",
    form_key: str = "compact_form"
) -> Optional[dict]:
    """
    Create compact form layout optimized for mobile

    Args:
        fields: List of field dicts with keys: type, label, key, kwargs
        submit_text: Submit button text
        form_key: Unique form key

    Returns:
        Dict of field values if submitted, None otherwise

    Example:
        result = compact_form([
            {"type": "text_input", "label": "Name", "key": "name"},
            {"type": "number_input", "label": "Amount", "key": "amount"},
        ])
        if result:
            st.write(f"Name: {result['name']}, Amount: {result['amount']}")
    """
    with st.form(form_key):
        values = {}

        for field in fields:
            field_type = field.get("type", "text_input")
            label = field.get("label", "")
            key = field.get("key", "")
            kwargs = field.get("kwargs", {})

            # Create appropriate input based on type
            if field_type == "text_input":
                values[key] = st.text_input(label, **kwargs)
            elif field_type == "number_input":
                values[key] = st.number_input(label, **kwargs)
            elif field_type == "selectbox":
                values[key] = st.selectbox(label, **kwargs)
            elif field_type == "multiselect":
                values[key] = st.multiselect(label, **kwargs)
            elif field_type == "date_input":
                values[key] = st.date_input(label, **kwargs)
            elif field_type == "checkbox":
                values[key] = st.checkbox(label, **kwargs)

        submitted = st.form_submit_button(submit_text, use_container_width=True)

        if submitted:
            return values

    return None


def responsive_tabs(
    tabs: List[str],
    use_expanders_on_mobile: bool = False
) -> List:
    """
    Create responsive tabs that can convert to expanders on mobile

    Args:
        tabs: List of tab names
        use_expanders_on_mobile: If True, suggests using expanders for mobile
                                  (Note: Streamlit tabs work well on mobile already)

    Returns:
        List of tab objects

    Example:
        tabs = responsive_tabs(["Overview", "Details", "Settings"])
        with tabs[0]:
            st.write("Overview content")
    """
    # Streamlit's native tabs are already responsive
    # This is a semantic wrapper for consistency
    return st.tabs(tabs)


def hide_on_mobile(content_func, placeholder_text: Optional[str] = None):
    """
    Conditionally hide content on mobile (conceptual helper)

    Note: Streamlit doesn't provide device detection, so this is a placeholder
    for future implementation. Consider using st.expander for optional content.

    Args:
        content_func: Function that renders content
        placeholder_text: Text to show instead on mobile
    """
    # For now, always show content
    # Future: Could use custom component for device detection
    content_func()


def mobile_friendly_container(
    content_func,
    padding: bool = True,
    border: bool = False
):
    """
    Create mobile-friendly container with optional padding and border

    Args:
        content_func: Function that renders container content
        padding: Whether to add padding
        border: Whether to add border

    Example:
        def content():
            st.write("Container content")

        mobile_friendly_container(content, padding=True)
    """
    if border:
        with st.container(border=True):
            if padding:
                st.markdown("<div style='padding: 1rem'>", unsafe_allow_html=True)
            content_func()
            if padding:
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        with st.container():
            content_func()


def compact_filters(
    filters: List[dict],
    use_expander: bool = True,
    expander_title: str = "🔍 Filters"
) -> dict:
    """
    Create compact filter section optimized for mobile

    Args:
        filters: List of filter dicts (same format as compact_form)
        use_expander: Whether to wrap in expander (recommended for mobile)
        expander_title: Title for expander

    Returns:
        Dict of filter values

    Example:
        filter_values = compact_filters([
            {"type": "date_input", "label": "Start Date", "key": "start"},
            {"type": "selectbox", "label": "Category", "key": "category",
             "kwargs": {"options": ["All", "Food", "Transport"]}},
        ])
    """
    values = {}

    def render_filters():
        for filter_def in filters:
            field_type = filter_def.get("type", "text_input")
            label = filter_def.get("label", "")
            key = filter_def.get("key", "")
            kwargs = filter_def.get("kwargs", {})

            if field_type == "text_input":
                values[key] = st.text_input(label, key=key, **kwargs)
            elif field_type == "number_input":
                values[key] = st.number_input(label, key=key, **kwargs)
            elif field_type == "selectbox":
                values[key] = st.selectbox(label, key=key, **kwargs)
            elif field_type == "multiselect":
                values[key] = st.multiselect(label, key=key, **kwargs)
            elif field_type == "date_input":
                values[key] = st.date_input(label, key=key, **kwargs)
            elif field_type == "slider":
                values[key] = st.slider(label, key=key, **kwargs)

    if use_expander:
        with st.expander(expander_title, expanded=False):
            render_filters()
    else:
        render_filters()

    return values


# CSS helpers for responsive design
MOBILE_FRIENDLY_CSS = """
<style>
/* Responsive font sizes */
@media (max-width: 768px) {
    h1 { font-size: 1.5rem !important; }
    h2 { font-size: 1.3rem !important; }
    h3 { font-size: 1.1rem !important; }

    /* Compact metrics on mobile */
    [data-testid="stMetricValue"] {
        font-size: 1.2rem !important;
    }

    /* Better button sizing */
    .stButton button {
        width: 100% !important;
    }

    /* Compact tables */
    [data-testid="stDataFrame"] {
        font-size: 0.85rem !important;
    }
}

/* Touch-friendly targets */
button, a, [role="button"] {
    min-height: 44px;
    min-width: 44px;
}
</style>
"""


def apply_mobile_styles():
    """Apply mobile-friendly CSS styles"""
    st.markdown(MOBILE_FRIENDLY_CSS, unsafe_allow_html=True)


def responsive_page_config(
    title: str,
    icon: str,
    layout: str = "wide",
    initial_sidebar_state: str = "auto"
) -> None:
    """
    Set responsive page configuration

    Args:
        title: Page title
        icon: Page icon
        layout: Layout mode ("wide" or "centered")
        initial_sidebar_state: Sidebar state ("auto", "expanded", "collapsed")

    Example:
        responsive_page_config(
            title="Dashboard",
            icon="📊",
            layout="wide",
            initial_sidebar_state="auto"  # Auto-collapses on mobile
        )
    """
    st.set_page_config(
        page_title=title,
        page_icon=icon,
        layout=layout,
        initial_sidebar_state=initial_sidebar_state
    )
