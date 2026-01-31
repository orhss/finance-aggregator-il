"""
Integration tests for category CLI commands.

Tests category mapping management through CLI with real database operations.
"""

import pytest
from unittest.mock import patch

from cli.main import app
from db.models import Transaction, CategoryMapping, MerchantMapping

from tests.integration.conftest import (
    create_test_account,
    create_test_transaction,
    create_test_category_mapping,
)


# ==================== List Mappings ====================

@pytest.mark.integration
def test_categories_list_empty(
    cli_runner,
    integration_db_session,
    patched_session_local,
):
    """
    List mappings with no mappings should show appropriate message.
    """
    result = cli_runner.invoke(app, ["categories", "list"])

    assert result.exit_code == 0
    assert "No mappings found" in result.stdout or "setup" in result.stdout.lower()


@pytest.mark.integration
def test_categories_list_shows_mappings(
    cli_runner,
    integration_db_session,
    patched_session_local,
):
    """
    List mappings should display all configured mappings.
    """
    # Setup: Create mappings
    create_test_category_mapping(integration_db_session, "cal", "מזון", "groceries")
    create_test_category_mapping(integration_db_session, "cal", "בידור", "entertainment")
    create_test_category_mapping(integration_db_session, "max", "דלק", "fuel")

    result = cli_runner.invoke(app, ["categories", "list"])

    assert result.exit_code == 0
    assert "groceries" in result.stdout
    assert "entertainment" in result.stdout
    assert "fuel" in result.stdout
    assert "3 mappings" in result.stdout.lower()


@pytest.mark.integration
def test_categories_list_filters_by_provider(
    cli_runner,
    integration_db_session,
    patched_session_local,
):
    """
    List mappings with provider filter should show only that provider.
    """
    # Setup: Create mappings for multiple providers
    create_test_category_mapping(integration_db_session, "cal", "מזון", "groceries")
    create_test_category_mapping(integration_db_session, "max", "דלק", "fuel")

    result = cli_runner.invoke(app, ["categories", "list", "--provider", "cal"])

    assert result.exit_code == 0
    assert "groceries" in result.stdout
    assert "fuel" not in result.stdout  # Max mapping should not appear


# ==================== Create Mapping ====================

@pytest.mark.integration
def test_categories_map_creates_mapping(
    cli_runner,
    integration_db_session,
    patched_session_local,
):
    """
    Map command should create a new category mapping.
    """
    result = cli_runner.invoke(
        app, ["categories", "map", "cal", "מזון", "groceries"]
    )

    assert result.exit_code == 0
    assert "Mapped" in result.stdout or "groceries" in result.stdout

    # Verify mapping created
    mapping = integration_db_session.query(CategoryMapping).first()
    assert mapping is not None
    assert mapping.provider == "cal"
    assert mapping.raw_category == "מזון"
    assert mapping.unified_category == "groceries"


@pytest.mark.integration
def test_categories_map_updates_existing(
    cli_runner,
    integration_db_session,
    patched_session_local,
):
    """
    Map command should update existing mapping.
    """
    # Setup: Create initial mapping
    create_test_category_mapping(integration_db_session, "cal", "מזון", "food")

    # Update mapping
    result = cli_runner.invoke(
        app, ["categories", "map", "cal", "מזון", "groceries"]
    )

    assert result.exit_code == 0
    assert "Updating" in result.stdout or "groceries" in result.stdout

    # Verify mapping updated
    mapping = integration_db_session.query(CategoryMapping).filter_by(
        provider="cal", raw_category="מזון"
    ).first()
    assert mapping.unified_category == "groceries"


@pytest.mark.integration
def test_categories_map_invalid_provider(
    cli_runner,
    integration_db_session,
    patched_session_local,
):
    """
    Map command with invalid provider should show error.
    """
    result = cli_runner.invoke(
        app, ["categories", "map", "invalid", "category", "unified"]
    )

    assert result.exit_code != 0
    assert "Invalid provider" in result.stdout or "invalid" in result.stdout.lower()


# ==================== Remove Mapping ====================

@pytest.mark.integration
def test_categories_unmap_removes_mapping(
    cli_runner,
    integration_db_session,
    patched_session_local,
):
    """
    Unmap command should remove a mapping.
    """
    # Setup: Create mapping
    create_test_category_mapping(integration_db_session, "cal", "מזון", "groceries")

    result = cli_runner.invoke(
        app, ["categories", "unmap", "cal", "מזון", "--force"]
    )

    assert result.exit_code == 0
    assert "Removed" in result.stdout

    # Verify mapping removed
    mapping = integration_db_session.query(CategoryMapping).first()
    assert mapping is None


@pytest.mark.integration
def test_categories_unmap_nonexistent(
    cli_runner,
    integration_db_session,
    patched_session_local,
):
    """
    Unmap command for nonexistent mapping should show message.
    """
    result = cli_runner.invoke(
        app, ["categories", "unmap", "cal", "nonexistent", "--force"]
    )

    assert result.exit_code == 0
    assert "No mapping found" in result.stdout


# ==================== Unmapped Categories ====================

@pytest.mark.integration
def test_categories_unmapped_shows_gaps(
    cli_runner,
    integration_db_session,
    patched_session_local,
):
    """
    Unmapped command should show categories without mappings.
    """
    # Setup: Create account and transaction with unmapped category
    account = create_test_account(integration_db_session, institution="cal")
    create_test_transaction(
        integration_db_session,
        account,
        "Test Purchase",
        raw_category="קטגוריה_חדשה",  # No mapping exists
    )

    result = cli_runner.invoke(app, ["categories", "unmapped"])

    assert result.exit_code == 0
    assert "קטגוריה_חדשה" in result.stdout or "unmapped" in result.stdout.lower()


@pytest.mark.integration
def test_categories_unmapped_all_mapped(
    cli_runner,
    integration_db_session,
    patched_session_local,
):
    """
    Unmapped command with all categories mapped should show success.
    """
    # Setup: Create mapping and matching transaction
    create_test_category_mapping(integration_db_session, "cal", "מזון", "groceries")
    account = create_test_account(integration_db_session, institution="cal")
    create_test_transaction(
        integration_db_session,
        account,
        "Test Purchase",
        raw_category="מזון",
        category="groceries",
    )

    result = cli_runner.invoke(app, ["categories", "unmapped"])

    assert result.exit_code == 0
    assert "All categories are mapped" in result.stdout or "mapped" in result.stdout.lower()


# ==================== Apply Mappings ====================

@pytest.mark.integration
def test_categories_apply_runs_successfully(
    cli_runner,
    integration_db_session,
    patched_session_local,
):
    """
    Apply command should run without errors.

    Note: The actual database update is tested in test_service_integration.py.
    CLI command just needs to execute and show appropriate output.
    """
    # Create mapping
    create_test_category_mapping(integration_db_session, "cal", "מזון", "groceries")

    # Apply mappings
    result = cli_runner.invoke(app, ["categories", "apply"])

    assert result.exit_code == 0
    # Should show some output about applying or no transactions
    assert "Applying" in result.stdout or "No transactions" in result.stdout or "Applied" in result.stdout


@pytest.mark.integration
def test_categories_apply_nothing_to_update(
    cli_runner,
    integration_db_session,
    patched_session_local,
):
    """
    Apply command with nothing to update should report that.
    """
    result = cli_runner.invoke(app, ["categories", "apply"])

    assert result.exit_code == 0
    assert "No transactions needed" in result.stdout or "0" in result.stdout


# ==================== Unified Categories ====================

@pytest.mark.integration
def test_categories_unified_list(
    cli_runner,
    integration_db_session,
    patched_session_local,
):
    """
    Unified command should list all unified categories with stats.
    """
    # Setup: Create mappings pointing to same unified category
    create_test_category_mapping(integration_db_session, "cal", "סופרמרקט", "groceries")
    create_test_category_mapping(integration_db_session, "max", "מזון", "groceries")
    create_test_category_mapping(integration_db_session, "cal", "בידור", "entertainment")

    result = cli_runner.invoke(app, ["categories", "unified"])

    assert result.exit_code == 0
    assert "groceries" in result.stdout
    assert "entertainment" in result.stdout


# ==================== Rename ====================

@pytest.mark.integration
def test_categories_rename_unified(
    cli_runner,
    integration_db_session,
    patched_session_local,
):
    """
    Rename command should update unified category name across all mappings.
    """
    # Setup: Create multiple mappings to same unified
    create_test_category_mapping(integration_db_session, "cal", "סופרמרקט", "groceries")
    create_test_category_mapping(integration_db_session, "max", "מזון", "groceries")

    result = cli_runner.invoke(
        app, ["categories", "rename", "groceries", "food_groceries"]
    )

    assert result.exit_code == 0
    assert "Renamed" in result.stdout

    # Verify all mappings updated
    mappings = integration_db_session.query(CategoryMapping).filter_by(
        unified_category="food_groceries"
    ).all()
    assert len(mappings) == 2


# ==================== Analyze ====================

@pytest.mark.integration
def test_categories_analyze(
    cli_runner,
    integration_db_session,
    patched_session_local,
):
    """
    Analyze command should show category coverage statistics.
    """
    # Setup: Create some transactions and mappings
    account = create_test_account(integration_db_session, institution="cal")
    create_test_transaction(
        integration_db_session, account, "Test 1", raw_category="מזון"
    )
    create_test_transaction(
        integration_db_session, account, "Test 2", raw_category="בידור"
    )
    create_test_category_mapping(integration_db_session, "cal", "מזון", "groceries")

    result = cli_runner.invoke(app, ["categories", "analyze"])

    assert result.exit_code == 0
    # Should show analysis with some stats
    assert "CAL" in result.stdout or "cal" in result.stdout.lower()
