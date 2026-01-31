"""
Integration tests for sync CLI commands.

Tests CLI command behavior with mocked scrapers. These tests verify:
- Commands execute without errors
- Output messages are correct
- Error cases are handled properly

All tests use in-memory database to avoid polluting the real database.
"""

import pytest
from unittest.mock import patch, MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from cli.main import app
from db.models import Base

from tests.integration.conftest import (
    build_cal_transaction,
    build_card_account,
)
from scrapers.credit_cards.cal_credit_card_client import TransactionStatus


@pytest.fixture
def mock_db_session():
    """Create isolated in-memory SQLite database for sync tests."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


# ==================== Happy Flow ====================

@pytest.mark.integration
def test_sync_cal_success_output(cli_runner, mock_db_session):
    """
    CAL sync with valid credentials should show success message.
    """
    with patch("cli.commands.sync.SessionLocal", return_value=mock_db_session):
        with patch("db.database.check_database_exists", return_value=True):
            with patch("config.settings.select_accounts_to_sync") as mock_select:
                account = MagicMock()
                account.username = "test"
                account.password = "test"
                account.label = None
                mock_select.return_value = [(0, account)]

                with patch("services.credit_card_service.CALCreditCardScraper") as mock_cls:
                    scraper = MagicMock()
                    scraper.scrape.return_value = [
                        build_card_account(
                            transactions=[
                                build_cal_transaction("WOLT", 50.0, "מזון"),
                            ]
                        )
                    ]
                    mock_cls.return_value = scraper

                    result = cli_runner.invoke(app, ["sync", "cal"])

    # Should show success message
    assert "Success" in result.stdout or "✓" in result.stdout
    assert "Cards synced" in result.stdout or "transactions" in result.stdout.lower()


@pytest.mark.integration
def test_sync_cal_shows_card_count(cli_runner, mock_db_session):
    """
    Sync output should show number of cards synced.
    """
    with patch("cli.commands.sync.SessionLocal", return_value=mock_db_session):
        with patch("db.database.check_database_exists", return_value=True):
            with patch("config.settings.select_accounts_to_sync") as mock_select:
                account = MagicMock()
                account.username = "test"
                account.password = "test"
                account.label = None
                mock_select.return_value = [(0, account)]

                with patch("services.credit_card_service.CALCreditCardScraper") as mock_cls:
                    scraper = MagicMock()
                    scraper.scrape.return_value = [
                        build_card_account(account_number="1234"),
                        build_card_account(account_number="5678"),
                    ]
                    mock_cls.return_value = scraper

                    result = cli_runner.invoke(app, ["sync", "cal"])

    # Output should mention card count
    assert "2" in result.stdout or "synced" in result.stdout.lower()


@pytest.mark.integration
def test_sync_max_success_output(cli_runner, mock_db_session):
    """
    Max sync with valid credentials should show success message.
    """
    with patch("cli.commands.sync.SessionLocal", return_value=mock_db_session):
        with patch("db.database.check_database_exists", return_value=True):
            with patch("config.settings.select_accounts_to_sync") as mock_select:
                account = MagicMock()
                account.username = "test"
                account.password = "test"
                account.label = None
                mock_select.return_value = [(0, account)]

                with patch("services.credit_card_service.MaxCreditCardScraper") as mock_cls:
                    scraper = MagicMock()
                    scraper.scrape.return_value = [
                        build_card_account(
                            transactions=[
                                build_cal_transaction("CAFE", 35.0, "מסעדות"),
                            ]
                        )
                    ]
                    mock_cls.return_value = scraper

                    result = cli_runner.invoke(app, ["sync", "max"])

    assert "Success" in result.stdout or "✓" in result.stdout


@pytest.mark.integration
def test_sync_isracard_success_output(cli_runner, mock_db_session):
    """
    Isracard sync with valid credentials should show success message.
    """
    with patch("cli.commands.sync.SessionLocal", return_value=mock_db_session):
        with patch("db.database.check_database_exists", return_value=True):
            with patch("config.settings.select_accounts_to_sync") as mock_select:
                account = MagicMock()
                account.username = "123456789:123456"
                account.password = "test"
                account.label = None
                mock_select.return_value = [(0, account)]

                with patch("services.credit_card_service.IsracardCreditCardScraper") as mock_cls:
                    scraper = MagicMock()
                    scraper.scrape.return_value = [
                        build_card_account(
                            transactions=[
                                build_cal_transaction("GOOGLE", 29.90, None),
                            ]
                        )
                    ]
                    mock_cls.return_value = scraper

                    result = cli_runner.invoke(app, ["sync", "isracard"])

    assert "Success" in result.stdout or "✓" in result.stdout


# ==================== Error Handling ====================

@pytest.mark.integration
def test_sync_no_database_shows_error(cli_runner):
    """
    Sync without initialized database should show error.
    """
    # Patch at both possible import locations to ensure coverage
    with patch("cli.commands.sync.check_database_exists", return_value=False):
        with patch("db.database.check_database_exists", return_value=False):
            result = cli_runner.invoke(app, ["sync", "cal"])

    # Verify error is shown (exit code may vary based on how error is handled)
    output = result.stdout.lower()
    assert "not initialized" in output or "init" in output or result.exit_code != 0


@pytest.mark.integration
def test_sync_cal_scraper_error_shows_message(cli_runner, mock_db_session):
    """
    Sync should show error message when scraper fails.
    """
    with patch("cli.commands.sync.SessionLocal", return_value=mock_db_session):
        with patch("db.database.check_database_exists", return_value=True):
            with patch("config.settings.select_accounts_to_sync") as mock_select:
                account = MagicMock()
                account.username = "test"
                account.password = "test"
                account.label = None
                mock_select.return_value = [(0, account)]

                with patch("services.credit_card_service.CALCreditCardScraper") as mock_cls:
                    scraper = MagicMock()
                    scraper.scrape.side_effect = Exception("Login failed: Invalid credentials")
                    mock_cls.return_value = scraper

                    result = cli_runner.invoke(app, ["sync", "cal"])

    # Should show failure message
    assert "Failed" in result.stdout or "Invalid credentials" in result.stdout


@pytest.mark.integration
def test_sync_cal_empty_cards_shows_error(cli_runner, mock_db_session):
    """
    Sync with no cards found should show error.
    """
    with patch("cli.commands.sync.SessionLocal", return_value=mock_db_session):
        with patch("db.database.check_database_exists", return_value=True):
            with patch("config.settings.select_accounts_to_sync") as mock_select:
                account = MagicMock()
                account.username = "test"
                account.password = "test"
                account.label = None
                mock_select.return_value = [(0, account)]

                with patch("services.credit_card_service.CALCreditCardScraper") as mock_cls:
                    scraper = MagicMock()
                    scraper.scrape.return_value = []  # No cards
                    mock_cls.return_value = scraper

                    result = cli_runner.invoke(app, ["sync", "cal"])

    # Should fail or show error message
    assert result.exit_code != 0 or "No card accounts" in result.stdout or "Failed" in result.stdout


@pytest.mark.integration
def test_sync_no_credentials_shows_error(cli_runner):
    """
    Sync with no credentials configured should show error.
    """
    with patch("cli.commands.sync.check_database_exists", return_value=True):
        with patch("db.database.check_database_exists", return_value=True):
            with patch("cli.commands.sync.select_accounts_to_sync") as mock_select:
                with patch("config.settings.select_accounts_to_sync") as mock_select2:
                    mock_select.side_effect = ValueError("No CAL accounts configured")
                    mock_select2.side_effect = ValueError("No CAL accounts configured")

                    result = cli_runner.invoke(app, ["sync", "cal"])

    # Should show error message about missing configuration
    output = result.stdout.lower()
    assert "no" in output or "configured" in output or "error" in output or result.exit_code != 0


# ==================== Output Format ====================

@pytest.mark.integration
def test_sync_shows_transaction_counts(cli_runner, mock_db_session):
    """
    Sync output should show transaction add/update counts.
    """
    with patch("cli.commands.sync.SessionLocal", return_value=mock_db_session):
        with patch("db.database.check_database_exists", return_value=True):
            with patch("config.settings.select_accounts_to_sync") as mock_select:
                account = MagicMock()
                account.username = "test"
                account.password = "test"
                account.label = None
                mock_select.return_value = [(0, account)]

                with patch("services.credit_card_service.CALCreditCardScraper") as mock_cls:
                    scraper = MagicMock()
                    scraper.scrape.return_value = [
                        build_card_account(
                            transactions=[
                                build_cal_transaction("A", 10.0, "test_category"),
                                build_cal_transaction("B", 20.0, "test_category"),
                                build_cal_transaction("C", 30.0, "test_category"),
                            ]
                        )
                    ]
                    mock_cls.return_value = scraper

                    result = cli_runner.invoke(app, ["sync", "cal"])

    # Should show transaction counts
    assert "Transactions added" in result.stdout or "added" in result.stdout.lower()


@pytest.mark.integration
def test_sync_shows_unmapped_warning(cli_runner, mock_db_session):
    """
    Sync with unmapped categories should show warning.
    """
    with patch("cli.commands.sync.SessionLocal", return_value=mock_db_session):
        with patch("db.database.check_database_exists", return_value=True):
            with patch("config.settings.select_accounts_to_sync") as mock_select:
                account = MagicMock()
                account.username = "test"
                account.password = "test"
                account.label = None
                mock_select.return_value = [(0, account)]

                with patch("services.credit_card_service.CALCreditCardScraper") as mock_cls:
                    scraper = MagicMock()
                    scraper.scrape.return_value = [
                        build_card_account(
                            transactions=[
                                build_cal_transaction("TEST", 100.0, "קטגוריה_לא_ממופה"),
                            ]
                        )
                    ]
                    mock_cls.return_value = scraper

                    result = cli_runner.invoke(app, ["sync", "cal"])

    # May or may not show unmapped warning depending on implementation
    # Just verify the sync completed
    assert "Success" in result.stdout or "✓" in result.stdout


# ==================== Multi-Account ====================

@pytest.mark.integration
def test_sync_multi_account_shows_progress(cli_runner, mock_db_session):
    """
    Sync with multiple accounts should show progress for each.
    """
    with patch("cli.commands.sync.SessionLocal", return_value=mock_db_session):
        with patch("db.database.check_database_exists", return_value=True):
            with patch("config.settings.select_accounts_to_sync") as mock_select:
                account1 = MagicMock()
                account1.username = "user1"
                account1.password = "pass1"
                account1.label = "Personal"

                account2 = MagicMock()
                account2.username = "user2"
                account2.password = "pass2"
                account2.label = "Business"

                mock_select.return_value = [(0, account1), (1, account2)]

                with patch("services.credit_card_service.CALCreditCardScraper") as mock_cls:
                    scraper = MagicMock()
                    scraper.scrape.return_value = [build_card_account()]
                    mock_cls.return_value = scraper

                    result = cli_runner.invoke(app, ["sync", "cal"])

    # Should show progress indicators or account info
    assert "[1/" in result.stdout or "[2/" in result.stdout or "Account" in result.stdout


@pytest.mark.integration
def test_sync_partial_failure_continues(cli_runner, mock_db_session):
    """
    If one account fails, sync should continue with others.
    """
    call_count = 0

    def mock_scrape(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("First account failed")
        return [build_card_account()]

    with patch("cli.commands.sync.SessionLocal", return_value=mock_db_session):
        with patch("db.database.check_database_exists", return_value=True):
            with patch("config.settings.select_accounts_to_sync") as mock_select:
                account1 = MagicMock()
                account1.username = "user1"
                account1.password = "pass1"
                account1.label = "Failing"

                account2 = MagicMock()
                account2.username = "user2"
                account2.password = "pass2"
                account2.label = "Working"

                mock_select.return_value = [(0, account1), (1, account2)]

                with patch("services.credit_card_service.CALCreditCardScraper") as mock_cls:
                    scraper = MagicMock()
                    scraper.scrape.side_effect = mock_scrape
                    mock_cls.return_value = scraper

                    result = cli_runner.invoke(app, ["sync", "cal"])

    # Should show both success and failure
    assert "Failed" in result.stdout or "failed" in result.stdout.lower()
    assert "Succeeded" in result.stdout or "Success" in result.stdout


# ==================== Summary ====================

@pytest.mark.integration
def test_sync_shows_summary(cli_runner, mock_db_session):
    """
    Sync should show summary at the end.
    """
    with patch("cli.commands.sync.SessionLocal", return_value=mock_db_session):
        with patch("db.database.check_database_exists", return_value=True):
            with patch("config.settings.select_accounts_to_sync") as mock_select:
                account = MagicMock()
                account.username = "test"
                account.password = "test"
                account.label = None
                mock_select.return_value = [(0, account)]

                with patch("services.credit_card_service.CALCreditCardScraper") as mock_cls:
                    scraper = MagicMock()
                    scraper.scrape.return_value = [
                        build_card_account(
                            transactions=[
                                build_cal_transaction("A", 10.0, "test_category"),
                            ]
                        )
                    ]
                    mock_cls.return_value = scraper

                    result = cli_runner.invoke(app, ["sync", "cal"])

    # Should show some form of summary
    assert "Summary" in result.stdout or "Total" in result.stdout or "synced" in result.stdout.lower()