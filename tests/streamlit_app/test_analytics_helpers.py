"""
Tests for analytics helper functions.

These helpers are extracted from analytics.py for testability
and to reduce duplication between mobile/desktop views.
"""

import pytest
import pandas as pd
from datetime import date, timedelta


# ==================== Period Options Tests ====================

class TestGetPeriodOptions:
    """Tests for get_period_options function."""

    def test_returns_expected_keys(self):
        """Should return all expected period options."""
        from streamlit_app.utils.analytics_helpers import get_period_options

        today = date(2024, 6, 15)
        options = get_period_options(today)

        expected_keys = {"This Month", "Last Month", "Last 3 Months", "Last 6 Months", "This Year"}
        assert set(options.keys()) == expected_keys

    def test_this_month_range(self):
        """This Month should span from 1st to today."""
        from streamlit_app.utils.analytics_helpers import get_period_options

        today = date(2024, 6, 15)
        options = get_period_options(today)

        start, end = options["This Month"]
        assert start == date(2024, 6, 1)
        assert end == today

    def test_last_month_range(self):
        """Last Month should span the entire previous month."""
        from streamlit_app.utils.analytics_helpers import get_period_options

        today = date(2024, 6, 15)
        options = get_period_options(today)

        start, end = options["Last Month"]
        assert start == date(2024, 5, 1)
        assert end == date(2024, 5, 31)

    def test_last_3_months_range(self):
        """Last 3 Months should span 90 days back."""
        from streamlit_app.utils.analytics_helpers import get_period_options

        today = date(2024, 6, 15)
        options = get_period_options(today)

        start, end = options["Last 3 Months"]
        assert end == today
        # Should be approximately 3 months back
        assert start < today - timedelta(days=80)

    def test_this_year_range(self):
        """This Year should span from Jan 1 to today."""
        from streamlit_app.utils.analytics_helpers import get_period_options

        today = date(2024, 6, 15)
        options = get_period_options(today)

        start, end = options["This Year"]
        assert start == date(2024, 1, 1)
        assert end == today

    def test_handles_january(self):
        """Should handle January (last month is December of prev year)."""
        from streamlit_app.utils.analytics_helpers import get_period_options

        today = date(2024, 1, 15)
        options = get_period_options(today)

        start, end = options["Last Month"]
        assert start == date(2023, 12, 1)
        assert end == date(2023, 12, 31)


# ==================== Transaction DataFrame Tests ====================

class TestTransactionsToDataframe:
    """Tests for transactions_to_dataframe function."""

    def test_converts_list_to_dataframe(self):
        """Should convert transaction list to DataFrame with expected columns."""
        from streamlit_app.utils.analytics_helpers import transactions_to_dataframe

        transactions = [
            {
                'id': 1,
                'transaction_date': date(2024, 1, 15),
                'original_amount': -50.0,
                'effective_category': 'Food',
                'description': 'Restaurant',
                'status': 'completed',
                'account_id': 1
            }
        ]

        df = transactions_to_dataframe(transactions)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert 'date' in df.columns
        assert 'amount' in df.columns
        assert 'category' in df.columns
        assert 'is_expense' in df.columns
        assert 'day_of_week' in df.columns

    def test_handles_empty_list(self):
        """Should return empty DataFrame for empty list."""
        from streamlit_app.utils.analytics_helpers import transactions_to_dataframe

        df = transactions_to_dataframe([])

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_marks_expenses_correctly(self):
        """Should mark negative amounts as expenses."""
        from streamlit_app.utils.analytics_helpers import transactions_to_dataframe

        transactions = [
            {'id': 1, 'transaction_date': date(2024, 1, 15), 'original_amount': -50.0,
             'effective_category': 'Food', 'description': 'Test', 'status': 'completed', 'account_id': 1},
            {'id': 2, 'transaction_date': date(2024, 1, 16), 'original_amount': 100.0,
             'effective_category': 'Income', 'description': 'Salary', 'status': 'completed', 'account_id': 1},
        ]

        df = transactions_to_dataframe(transactions)

        assert df[df['id'] == 1]['is_expense'].iloc[0] == True  # noqa: E712
        assert df[df['id'] == 2]['is_expense'].iloc[0] == False  # noqa: E712

    def test_handles_none_category(self):
        """Should default None category to 'Uncategorized'."""
        from streamlit_app.utils.analytics_helpers import transactions_to_dataframe

        transactions = [
            {'id': 1, 'transaction_date': date(2024, 1, 15), 'original_amount': -50.0,
             'effective_category': None, 'description': 'Test', 'status': 'completed', 'account_id': 1}
        ]

        df = transactions_to_dataframe(transactions)

        assert df.iloc[0]['category'] == 'Uncategorized'

    def test_extracts_day_of_week(self):
        """Should extract day of week from date."""
        from streamlit_app.utils.analytics_helpers import transactions_to_dataframe

        # 2024-01-15 is a Monday
        transactions = [
            {'id': 1, 'transaction_date': date(2024, 1, 15), 'original_amount': -50.0,
             'effective_category': 'Food', 'description': 'Test', 'status': 'completed', 'account_id': 1}
        ]

        df = transactions_to_dataframe(transactions)

        assert df.iloc[0]['day_of_week'] == 'Monday'


# ==================== Spending Metrics Tests ====================

class TestCalculateSpendingMetrics:
    """Tests for calculate_spending_metrics function."""

    @pytest.fixture
    def sample_expenses_df(self):
        """Sample expenses DataFrame for testing."""
        return pd.DataFrame({
            'amount': [-100.0, -50.0, -200.0, -50.0],
            'category': ['Food', 'Transport', 'Food', 'Entertainment'],
        })

    def test_calculates_total_spending(self, sample_expenses_df):
        """Should calculate total spending (absolute value)."""
        from streamlit_app.utils.analytics_helpers import calculate_spending_metrics

        metrics = calculate_spending_metrics(sample_expenses_df)

        assert metrics['total_spending'] == 400.0

    def test_calculates_transaction_count(self, sample_expenses_df):
        """Should count total transactions."""
        from streamlit_app.utils.analytics_helpers import calculate_spending_metrics

        metrics = calculate_spending_metrics(sample_expenses_df)

        assert metrics['transaction_count'] == 4

    def test_identifies_top_category(self, sample_expenses_df):
        """Should identify category with highest spending."""
        from streamlit_app.utils.analytics_helpers import calculate_spending_metrics

        metrics = calculate_spending_metrics(sample_expenses_df)

        assert metrics['top_category'] == 'Food'  # Food has 300 total

    def test_calculates_average_transaction(self, sample_expenses_df):
        """Should calculate average transaction amount."""
        from streamlit_app.utils.analytics_helpers import calculate_spending_metrics

        metrics = calculate_spending_metrics(sample_expenses_df)

        assert metrics['avg_transaction'] == 100.0  # 400 / 4

    def test_handles_empty_dataframe(self):
        """Should return zeros for empty DataFrame."""
        from streamlit_app.utils.analytics_helpers import calculate_spending_metrics

        empty_df = pd.DataFrame({'amount': [], 'category': []})
        metrics = calculate_spending_metrics(empty_df)

        assert metrics['total_spending'] == 0
        assert metrics['transaction_count'] == 0
        assert metrics['top_category'] == "—"
        assert metrics['avg_transaction'] == 0


# ==================== Day of Week Spending Tests ====================

class TestGetSpendingByDayOfWeek:
    """Tests for get_spending_by_day_of_week function."""

    def test_returns_ordered_series(self):
        """Should return Series with days in correct order."""
        from streamlit_app.utils.analytics_helpers import get_spending_by_day_of_week

        df = pd.DataFrame({
            'amount': [-100.0, -50.0],
            'day_of_week': ['Monday', 'Friday'],
        })

        result = get_spending_by_day_of_week(df)

        expected_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        assert list(result.index) == expected_order

    def test_aggregates_by_day(self):
        """Should sum amounts per day of week."""
        from streamlit_app.utils.analytics_helpers import get_spending_by_day_of_week

        df = pd.DataFrame({
            'amount': [-100.0, -50.0, -75.0],
            'day_of_week': ['Monday', 'Monday', 'Friday'],
        })

        result = get_spending_by_day_of_week(df)

        assert result['Monday'] == 150.0  # abs(-100) + abs(-50)
        assert result['Friday'] == 75.0

    def test_fills_missing_days_with_zero(self):
        """Should fill missing days with zero."""
        from streamlit_app.utils.analytics_helpers import get_spending_by_day_of_week

        df = pd.DataFrame({
            'amount': [-100.0],
            'day_of_week': ['Monday'],
        })

        result = get_spending_by_day_of_week(df)

        assert result['Tuesday'] == 0
        assert result['Wednesday'] == 0

    def test_handles_empty_dataframe(self):
        """Should return all zeros for empty DataFrame."""
        from streamlit_app.utils.analytics_helpers import get_spending_by_day_of_week

        empty_df = pd.DataFrame({'amount': [], 'day_of_week': []})
        result = get_spending_by_day_of_week(empty_df)

        assert all(v == 0 for v in result.values)
        assert len(result) == 7