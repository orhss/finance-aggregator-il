"""
Tests for CLI utility functions.
"""

import pytest
from datetime import date
from unittest.mock import MagicMock, patch


# ==================== Date Parsing Tests ====================

class TestParseDate:
    """Tests for parse_date function."""

    @pytest.mark.parametrize("date_str,expected", [
        pytest.param("2024-01-15", date(2024, 1, 15), id="standard_date"),
        pytest.param("2023-12-31", date(2023, 12, 31), id="year_end"),
        pytest.param("2024-02-29", date(2024, 2, 29), id="leap_year"),
    ])
    def test_parse_date_valid(self, date_str, expected):
        """Should parse valid YYYY-MM-DD strings."""
        from cli.utils import parse_date
        result = parse_date(date_str)
        assert result == expected

    @pytest.mark.parametrize("invalid_date,param_name", [
        pytest.param("2024/01/15", "date", id="wrong_separator"),
        pytest.param("01-15-2024", "from date", id="wrong_order"),
        pytest.param("not-a-date", "to date", id="invalid_string"),
        pytest.param("2024-13-01", "date", id="invalid_month"),
        pytest.param("2024-01-32", "date", id="invalid_day"),
    ])
    def test_parse_date_invalid_raises_exit(self, invalid_date, param_name):
        """Should raise typer.Exit for invalid date formats."""
        import typer
        from cli.utils import parse_date

        with pytest.raises(typer.Exit) as exc_info:
            parse_date(invalid_date, param_name)

        assert exc_info.value.exit_code == 1


class TestParseDateRange:
    """Tests for parse_date_range function."""

    def test_both_dates_provided(self):
        """Should parse both from and to dates."""
        from cli.utils import parse_date_range

        from_date, to_date = parse_date_range("2024-01-01", "2024-01-31")

        assert from_date == date(2024, 1, 1)
        assert to_date == date(2024, 1, 31)

    def test_only_from_date_provided(self):
        """Should parse from date, return None for to date."""
        from cli.utils import parse_date_range

        from_date, to_date = parse_date_range("2024-01-01", None)

        assert from_date == date(2024, 1, 1)
        assert to_date is None

    def test_only_to_date_provided(self):
        """Should parse to date, return None for from date."""
        from cli.utils import parse_date_range

        from_date, to_date = parse_date_range(None, "2024-01-31")

        assert from_date is None
        assert to_date == date(2024, 1, 31)

    def test_neither_date_provided(self):
        """Should return None for both when neither provided."""
        from cli.utils import parse_date_range

        from_date, to_date = parse_date_range(None, None)

        assert from_date is None
        assert to_date is None

    def test_invalid_from_date_raises_exit(self):
        """Should raise typer.Exit for invalid from date."""
        import typer
        from cli.utils import parse_date_range

        with pytest.raises(typer.Exit):
            parse_date_range("invalid", "2024-01-31")

    def test_invalid_to_date_raises_exit(self):
        """Should raise typer.Exit for invalid to date."""
        import typer
        from cli.utils import parse_date_range

        with pytest.raises(typer.Exit):
            parse_date_range("2024-01-01", "invalid")


# ==================== Service Context Manager Tests ====================

class TestGetAnalytics:
    """Tests for get_analytics context manager."""

    def test_yields_analytics_service(self):
        """Should yield an AnalyticsService instance."""
        from cli.utils import get_analytics

        mock_service = MagicMock()
        with patch('services.analytics_service.AnalyticsService', return_value=mock_service):
            with get_analytics() as service:
                assert service is mock_service

    def test_closes_service_on_normal_exit(self):
        """Should call close() when exiting normally."""
        from cli.utils import get_analytics

        mock_service = MagicMock()
        with patch('services.analytics_service.AnalyticsService', return_value=mock_service):
            with get_analytics() as service:
                pass

        mock_service.close.assert_called_once()

    def test_closes_service_on_exception(self):
        """Should call close() even when exception raised."""
        from cli.utils import get_analytics

        mock_service = MagicMock()
        with patch('services.analytics_service.AnalyticsService', return_value=mock_service):
            with pytest.raises(ValueError):
                with get_analytics() as service:
                    raise ValueError("Test error")

        mock_service.close.assert_called_once()


class TestGetDbSession:
    """Tests for get_db_session context manager."""

    def test_yields_session(self):
        """Should yield a database session."""
        from cli.utils import get_db_session

        mock_session = MagicMock()
        with patch('db.database.SessionLocal', return_value=mock_session):
            with get_db_session() as session:
                assert session is mock_session

    def test_closes_session_on_normal_exit(self):
        """Should call close() when exiting normally."""
        from cli.utils import get_db_session

        mock_session = MagicMock()
        with patch('db.database.SessionLocal', return_value=mock_session):
            with get_db_session() as session:
                pass

        mock_session.close.assert_called_once()

    def test_closes_session_on_exception(self):
        """Should call close() even when exception raised."""
        from cli.utils import get_db_session

        mock_session = MagicMock()
        with patch('db.database.SessionLocal', return_value=mock_session):
            with pytest.raises(ValueError):
                with get_db_session() as session:
                    raise ValueError("Test error")

        mock_session.close.assert_called_once()


# ==================== Spinner Context Manager Tests ====================

class TestSpinner:
    """Tests for spinner context manager."""

    def test_spinner_executes_code_block(self):
        """Should execute code inside the context."""
        from cli.utils import spinner

        executed = False
        with patch('cli.utils.Progress'):
            with spinner("Test..."):
                executed = True

        assert executed

    def test_spinner_creates_progress_with_description(self):
        """Should create Progress and add task with description."""
        from cli.utils import spinner

        mock_progress_instance = MagicMock()
        mock_progress_class = MagicMock(return_value=mock_progress_instance)
        mock_progress_instance.__enter__ = MagicMock(return_value=mock_progress_instance)
        mock_progress_instance.__exit__ = MagicMock(return_value=False)

        with patch('cli.utils.Progress', mock_progress_class):
            with spinner("Loading data..."):
                pass

        # Verify add_task was called with the description
        mock_progress_instance.add_task.assert_called_once()
        call_kwargs = mock_progress_instance.add_task.call_args
        assert "Loading data..." in str(call_kwargs)

    def test_spinner_exits_on_exception(self):
        """Should properly exit Progress context even when exception raised."""
        from cli.utils import spinner

        mock_progress_instance = MagicMock()
        mock_progress_class = MagicMock(return_value=mock_progress_instance)
        mock_progress_instance.__enter__ = MagicMock(return_value=mock_progress_instance)
        mock_progress_instance.__exit__ = MagicMock(return_value=False)

        with patch('cli.utils.Progress', mock_progress_class):
            with pytest.raises(ValueError):
                with spinner("Test..."):
                    raise ValueError("Test error")

        # Verify __exit__ was called (cleanup happened)
        mock_progress_instance.__exit__.assert_called_once()

    def test_spinner_yields_nothing(self):
        """Spinner should not yield any value (simple context manager)."""
        from cli.utils import spinner

        with patch('cli.utils.Progress'):
            with spinner("Test...") as result:
                assert result is None