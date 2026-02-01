"""
Loading State Components - Enhanced loading indicators and progress tracking

This module provides reusable loading state components for better UX during
async operations and data loading.
"""

import streamlit as st
from typing import List, Optional
import time


def show_progress_steps(
    steps: List[str],
    current_step: int,
    total_steps: Optional[int] = None
) -> None:
    """
    Display multi-step progress indicator

    Args:
        steps: List of step descriptions
        current_step: Current step index (0-based)
        total_steps: Total number of steps (defaults to len(steps))

    Example:
        show_progress_steps(
            steps=["Loading data", "Processing", "Rendering"],
            current_step=1
        )
    """
    total = total_steps or len(steps)

    # Progress bar
    progress = (current_step + 1) / total
    st.progress(progress, text=f"Step {current_step + 1} of {total}")

    # Step descriptions
    for i, step in enumerate(steps):
        if i < current_step:
            # Completed step
            st.markdown(f"✅ {step}")
        elif i == current_step:
            # Current step
            st.markdown(f"🔄 **{step}**...")
        else:
            # Upcoming step
            st.markdown(f"⏳ {step}")


def contextual_spinner(
    operation: str,
    data_type: str = "data",
    count: Optional[int] = None
) -> str:
    """
    Generate contextual spinner text based on operation

    Args:
        operation: Type of operation (loading, processing, saving, etc.)
        data_type: Type of data being operated on
        count: Optional count of items

    Returns:
        Formatted spinner text

    Example:
        text = contextual_spinner("loading", "transactions", 1500)
        # Returns: "Loading 1,500 transactions..."
    """
    operation_verbs = {
        'loading': 'Loading',
        'processing': 'Processing',
        'saving': 'Saving',
        'analyzing': 'Analyzing',
        'calculating': 'Calculating',
        'fetching': 'Fetching',
        'updating': 'Updating',
        'syncing': 'Syncing'
    }

    verb = operation_verbs.get(operation.lower(), operation.capitalize())

    if count:
        return f"{verb} {count:,} {data_type}..."
    else:
        return f"{verb} {data_type}..."


def skeleton_table(rows: int = 5, columns: int = 5) -> None:
    """
    Display skeleton loading state for tables

    Args:
        rows: Number of skeleton rows
        columns: Number of skeleton columns
    """
    import pandas as pd

    # Create empty dataframe with placeholder values
    data = {f"Column {i+1}": ["..." for _ in range(rows)] for i in range(columns)}
    df = pd.DataFrame(data)

    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption("⏳ Loading data...")


def skeleton_metrics(count: int = 4) -> None:
    """
    Display skeleton loading state for metric cards

    Args:
        count: Number of metric placeholders
    """
    cols = st.columns(count)

    for col in cols:
        with col:
            st.metric(
                label="Loading...",
                value="---",
                delta=None
            )


def show_loading_message(
    message: str,
    submessage: Optional[str] = None,
    show_spinner: bool = True
) -> None:
    """
    Display enhanced loading message with optional submessage

    Args:
        message: Main loading message
        submessage: Optional additional context
        show_spinner: Whether to show spinner animation
    """
    if show_spinner:
        st.spinner(message)

    st.markdown(f"**{message}**")
    if submessage:
        st.caption(submessage)


def estimated_time_message(
    seconds: int,
    operation: str = "This operation"
) -> str:
    """
    Generate estimated time message

    Args:
        seconds: Estimated seconds
        operation: Description of operation

    Returns:
        Formatted message

    Example:
        msg = estimated_time_message(45, "Syncing transactions")
        # Returns: "Syncing transactions may take about 45 seconds..."
    """
    if seconds < 60:
        time_str = f"{seconds} seconds"
    else:
        minutes = seconds // 60
        time_str = f"{minutes} minute{'s' if minutes > 1 else ''}"

    return f"{operation} may take about {time_str}..."


class ProgressTracker:
    """
    Context manager for tracking multi-step operations

    Example:
        with ProgressTracker(steps=["Load", "Process", "Save"]) as tracker:
            tracker.update(0, "Loading data from database")
            # ... do work ...
            tracker.update(1, "Processing 1000 records")
            # ... do work ...
            tracker.update(2, "Saving results")
    """

    def __init__(
        self,
        steps: List[str],
        show_time_estimate: bool = False
    ):
        self.steps = steps
        self.current_step = 0
        self.show_time_estimate = show_time_estimate
        self.container = None

    def __enter__(self):
        # Create container for progress display
        self.container = st.empty()
        self._render()
        return self

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        # Clear the container on completion
        if self.container:
            self.container.empty()
        return False

    def update(self, step: int, message: Optional[str] = None):
        """Update to specific step with optional message"""
        self.current_step = step
        if message:
            self.steps[step] = message
        self._render()

    def _render(self):
        """Render current progress state"""
        if not self.container:
            return

        with self.container.container():
            total = len(self.steps)
            progress = (self.current_step + 1) / total

            # Progress bar
            st.progress(progress, text=f"Step {self.current_step + 1} of {total}")

            # Current step message
            st.caption(f"🔄 {self.steps[self.current_step]}...")


def cache_status_indicator(
    is_cached: bool,
    cache_age_seconds: Optional[int] = None
) -> None:
    """
    Show indicator for cached vs fresh data

    Args:
        is_cached: Whether data is from cache
        cache_age_seconds: Age of cached data in seconds
    """
    if is_cached:
        if cache_age_seconds:
            if cache_age_seconds < 60:
                age_str = f"{cache_age_seconds}s"
            else:
                age_str = f"{cache_age_seconds // 60}m"
            st.caption(f"⚡ Cached data ({age_str} old)")
        else:
            st.caption("⚡ Cached data")
    else:
        st.caption("🔄 Fresh data")


def show_data_freshness(
    last_sync_time: Optional[str] = None,
    next_sync_time: Optional[str] = None
) -> None:
    """
    Display data freshness information

    Args:
        last_sync_time: When data was last synced (formatted string)
        next_sync_time: When data will be refreshed (formatted string)
    """
    info_parts = []

    if last_sync_time:
        info_parts.append(f"Last updated: {last_sync_time}")

    if next_sync_time:
        info_parts.append(f"Next refresh: {next_sync_time}")

    if info_parts:
        st.caption(" • ".join(info_parts))
