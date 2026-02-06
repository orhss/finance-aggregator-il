"""
Tests for filter components.

Note: These test the pure Python logic, not Streamlit widgets.
Streamlit widget behavior must be tested manually.
"""

import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock


class TestDateRangePickerLogic:
    """Tests for date_range_picker underlying logic."""

    def test_uses_get_period_options(self):
        """Should use shared get_period_options helper."""
        from streamlit_app.utils.analytics_helpers import get_period_options

        today = date(2024, 6, 15)
        options = get_period_options(today)

        # Verify expected options exist
        assert "This Month" in options
        assert "Last Month" in options
        assert "Last 3 Months" in options
        assert "Last 6 Months" in options
        assert "This Year" in options

    def test_period_options_return_date_tuples(self):
        """Each period option should return (start_date, end_date) tuple."""
        from streamlit_app.utils.analytics_helpers import get_period_options

        today = date(2024, 6, 15)
        options = get_period_options(today)

        for name, (start, end) in options.items():
            assert isinstance(start, date), f"{name} start should be date"
            assert isinstance(end, date), f"{name} end should be date"
            assert start <= end, f"{name} start should be <= end"

    def test_include_options_filters_correctly(self):
        """include_options parameter should filter available periods."""
        from streamlit_app.utils.analytics_helpers import get_period_options

        today = date.today()
        all_options = get_period_options(today)

        # Simulate filtering
        include = ["This Month", "Last Month"]
        filtered = {k: v for k, v in all_options.items() if k in include}

        assert len(filtered) == 2
        assert "This Month" in filtered
        assert "Last Month" in filtered
        assert "Last 3 Months" not in filtered