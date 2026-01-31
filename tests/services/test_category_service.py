"""
Tests for CategoryService.

Tests category mapping CRUD, normalization, merchant pattern extraction,
and bulk operations.
"""

import pytest
from datetime import date

from services.category_service import CategoryService
from db.models import CategoryMapping, MerchantMapping, Transaction
from tests.conftest import (
    create_account,
    create_transaction,
    create_category_mapping,
    create_merchant_mapping,
)


# ==================== Fixtures ====================

@pytest.fixture
def category_service(db_session):
    """CategoryService instance with test database session."""
    return CategoryService(session=db_session)


@pytest.fixture
def sample_account(db_session):
    """Create a sample credit card account."""
    return create_account(db_session, institution="cal", account_number="1234")


@pytest.fixture
def sample_mapping(db_session):
    """Create a sample category mapping."""
    return create_category_mapping(db_session, "cal", "סופרמרקט", "groceries")


@pytest.fixture
def sample_merchant_mapping(db_session):
    """Create a sample merchant mapping."""
    return create_merchant_mapping(db_session, "NETFLIX", "subscriptions")


# ==================== normalize_category ====================

@pytest.mark.parametrize("provider,raw_category,expected", [
    pytest.param("cal", "סופרמרקט", "groceries", id="existing_mapping"),
    pytest.param("CAL", "סופרמרקט", "groceries", id="case_insensitive_provider"),
    pytest.param("cal", "unknown", None, id="no_mapping"),
])
def test_normalize_category_happy_flow(db_session, category_service, sample_mapping, provider, raw_category, expected):
    """Should return unified category when mapping exists, None otherwise."""
    result = category_service.normalize_category(provider, raw_category)
    assert result == expected


@pytest.mark.parametrize("raw_category,expected", [
    pytest.param(None, None, id="none_input"),
    pytest.param("", None, id="empty_string"),
])
def test_normalize_category_edge_cases(category_service, raw_category, expected):
    """Should handle None and empty inputs gracefully."""
    result = category_service.normalize_category("cal", raw_category)
    assert result == expected


# ==================== normalize_category_cached ====================

def test_normalize_category_cached_caches_lookups(db_session, category_service, sample_mapping):
    """Should cache lookups to avoid repeated DB queries."""
    cache = {}

    result1 = category_service.normalize_category_cached("cal", "סופרמרקט", cache)
    result2 = category_service.normalize_category_cached("cal", "סופרמרקט", cache)

    assert result1 == result2 == "groceries"
    assert ("cal", "סופרמרקט") in cache


def test_normalize_category_cached_stores_none(category_service):
    """Should cache None results for missing mappings."""
    cache = {}

    result = category_service.normalize_category_cached("cal", "missing", cache)

    assert result is None
    assert cache[("cal", "missing")] is None


# ==================== add_mapping ====================

@pytest.mark.parametrize("provider,raw,unified", [
    pytest.param("max", "מזון", "groceries", id="new_mapping"),
    pytest.param("MAX", "test", "category", id="normalizes_provider_case"),
])
def test_add_mapping_creates_new(db_session, category_service, provider, raw, unified):
    """Should create new mapping and normalize provider to lowercase."""
    mapping = category_service.add_mapping(provider, raw, unified)

    assert mapping.provider == provider.lower()
    assert mapping.raw_category == raw
    assert mapping.unified_category == unified

    # Verify persisted
    stored = db_session.query(CategoryMapping).filter_by(
        provider=provider.lower(), raw_category=raw
    ).first()
    assert stored is not None


def test_add_mapping_updates_existing(db_session, category_service, sample_mapping):
    """Should update existing mapping's unified category."""
    mapping = category_service.add_mapping("cal", "סופרמרקט", "food")

    assert mapping.unified_category == "food"

    # Verify only one mapping exists
    count = db_session.query(CategoryMapping).filter_by(
        provider="cal", raw_category="סופרמרקט"
    ).count()
    assert count == 1


# ==================== remove_mapping ====================

@pytest.mark.parametrize("provider,raw,expected", [
    pytest.param("cal", "סופרמרקט", True, id="existing_mapping"),
    pytest.param("cal", "nonexistent", False, id="not_found"),
])
def test_remove_mapping(db_session, category_service, sample_mapping, provider, raw, expected):
    """Should return True if deleted, False if not found."""
    result = category_service.remove_mapping(provider, raw)
    assert result == expected


# ==================== get_all_mappings ====================

def test_get_all_mappings_returns_all(db_session, category_service):
    """Should return all mappings."""
    create_category_mapping(db_session, "cal", "cat1", "unified1")
    create_category_mapping(db_session, "max", "cat2", "unified2")

    mappings = category_service.get_all_mappings()

    assert len(mappings) == 2


def test_get_all_mappings_filters_by_provider(db_session, category_service):
    """Should filter mappings by provider when specified."""
    create_category_mapping(db_session, "cal", "cat1", "unified1")
    create_category_mapping(db_session, "max", "cat2", "unified2")

    mappings = category_service.get_all_mappings(provider="cal")

    assert len(mappings) == 1
    assert mappings[0].provider == "cal"


# ==================== get_unmapped_categories ====================

def test_get_unmapped_categories_detects_unmapped(db_session, category_service, sample_account):
    """Should detect transactions with unmapped raw_category."""
    create_transaction(db_session, sample_account, raw_category="unmapped_cat")

    unmapped = category_service.get_unmapped_categories()

    assert len(unmapped) == 1
    assert unmapped[0]["raw_category"] == "unmapped_cat"
    assert unmapped[0]["provider"] == "cal"


def test_get_unmapped_categories_excludes_mapped(db_session, category_service, sample_account, sample_mapping):
    """Should not detect transactions with mapped categories."""
    create_transaction(db_session, sample_account, raw_category="סופרמרקט")

    unmapped = category_service.get_unmapped_categories()

    assert len(unmapped) == 0


# ==================== extract_merchant_pattern ====================

@pytest.mark.parametrize("description,expected", [
    pytest.param("NETFLIX SUBSCRIPTION", "NETFLIX", id="simple_english"),
    pytest.param("WOLT TLV 123456", "WOLT", id="removes_trailing_numbers"),
    pytest.param("AM PM STORE", "AM PM", id="short_first_word_takes_two"),
    pytest.param("סופר יודה רמת גן", "סופר יודה", id="hebrew_takes_two_words"),
    pytest.param("PANGO TEL AVIV", "PANGO", id="removes_location_suffix"),
])
def test_extract_merchant_pattern_happy_flow(category_service, description, expected):
    """Should extract merchant pattern from description."""
    result = category_service.extract_merchant_pattern(description)
    assert result == expected


@pytest.mark.parametrize("description,expected", [
    pytest.param("", "", id="empty_string"),
    pytest.param(None, "", id="none_input"),
])
def test_extract_merchant_pattern_edge_cases(category_service, description, expected):
    """Should handle empty and None inputs."""
    result = category_service.extract_merchant_pattern(description)
    assert result == expected


# ==================== get_uncategorized_by_merchant ====================

def test_get_uncategorized_by_merchant_groups_by_pattern(db_session, category_service, sample_account):
    """Should group uncategorized transactions by merchant pattern."""
    create_transaction(db_session, sample_account, description="NETFLIX MONTHLY", category=None, raw_category=None)
    create_transaction(db_session, sample_account, description="NETFLIX PREMIUM", category=None, raw_category=None)

    groups = category_service.get_uncategorized_by_merchant()

    netflix_groups = [g for g in groups if "NETFLIX" in g["merchant_pattern"]]
    assert len(netflix_groups) == 1
    assert netflix_groups[0]["count"] == 2


@pytest.mark.parametrize("min_txns,expected_count", [
    pytest.param(1, 1, id="min_1_includes_single"),
    pytest.param(2, 0, id="min_2_excludes_single"),
])
def test_get_uncategorized_by_merchant_min_filter(db_session, category_service, sample_account, min_txns, expected_count):
    """Should filter by minimum transaction count."""
    create_transaction(db_session, sample_account, description="SINGLE", category=None, raw_category=None)

    groups = category_service.get_uncategorized_by_merchant(min_transactions=min_txns)

    assert len(groups) == expected_count


# ==================== bulk_set_category ====================

def test_bulk_set_category_updates_multiple(db_session, category_service, sample_account):
    """Should set category on multiple transactions."""
    txn1 = create_transaction(db_session, sample_account, description="TXN1")
    txn2 = create_transaction(db_session, sample_account, description="TXN2")

    count = category_service.bulk_set_category([txn1.id, txn2.id], "groceries")

    assert count == 2
    db_session.refresh(txn1)
    db_session.refresh(txn2)
    assert txn1.category == txn2.category == "groceries"


def test_bulk_set_category_empty_list(category_service):
    """Should return 0 for empty transaction list."""
    count = category_service.bulk_set_category([], "groceries")
    assert count == 0


# ==================== Merchant Mapping CRUD ====================

def test_add_merchant_mapping_creates_new(db_session, category_service):
    """Should create new merchant mapping."""
    mapping = category_service.add_merchant_mapping("AMAZON", "shopping")

    assert mapping.pattern == "AMAZON"
    assert mapping.category == "shopping"


def test_add_merchant_mapping_updates_existing(db_session, category_service, sample_merchant_mapping):
    """Should update existing merchant mapping."""
    mapping = category_service.add_merchant_mapping("NETFLIX", "entertainment")

    assert mapping.category == "entertainment"
    count = db_session.query(MerchantMapping).filter_by(pattern="NETFLIX").count()
    assert count == 1


@pytest.mark.parametrize("pattern,expected", [
    pytest.param("NETFLIX", True, id="existing"),
    pytest.param("NONEXISTENT", False, id="not_found"),
])
def test_remove_merchant_mapping(db_session, category_service, sample_merchant_mapping, pattern, expected):
    """Should return True if deleted, False if not found."""
    result = category_service.remove_merchant_mapping(pattern)
    assert result == expected


# ==================== normalize_by_merchant ====================

@pytest.mark.parametrize("match_type,description,should_match", [
    pytest.param("startswith", "NETFLIX MONTHLY", True, id="startswith_match"),
    pytest.param("startswith", "MY NETFLIX", False, id="startswith_no_match"),
    pytest.param("contains", "PAYMENT TO UBER EATS", True, id="contains_match"),
    pytest.param("exact", "EXACT MATCH", True, id="exact_match"),
    pytest.param("exact", "EXACT MATCH EXTRA", False, id="exact_no_match"),
])
def test_normalize_by_merchant_match_types(db_session, category_service, match_type, description, should_match):
    """Should match based on match_type."""
    pattern = "NETFLIX" if "NETFLIX" in description else "UBER" if "UBER" in description else "EXACT MATCH"
    create_merchant_mapping(db_session, pattern, "category", match_type=match_type)

    result = category_service.normalize_by_merchant(description)

    if should_match:
        assert result == "category"
    else:
        assert result is None


def test_normalize_by_merchant_no_match(db_session, category_service, sample_merchant_mapping):
    """Should return None when no pattern matches."""
    result = category_service.normalize_by_merchant("SPOTIFY")
    assert result is None


# ==================== bulk_set_category_with_mapping ====================

def test_bulk_set_category_with_mapping_creates_both(db_session, category_service, sample_account):
    """Should set category on transactions AND create mapping."""
    txn = create_transaction(db_session, sample_account, description="MERCHANT")

    result = category_service.bulk_set_category_with_mapping(
        merchant_pattern="MERCHANT",
        category="test_category",
        transaction_ids=[txn.id],
    )

    assert result["transactions_updated"] == 1
    assert result["mapping_created"] is True

    db_session.refresh(txn)
    assert txn.category == "test_category"

    mapping = db_session.query(MerchantMapping).filter_by(pattern="MERCHANT").first()
    assert mapping is not None


def test_bulk_set_category_with_mapping_updates_existing(db_session, category_service, sample_account, sample_merchant_mapping):
    """Should update existing mapping."""
    txn = create_transaction(db_session, sample_account, description="NETFLIX")

    result = category_service.bulk_set_category_with_mapping(
        merchant_pattern="NETFLIX",
        category="entertainment",
        transaction_ids=[txn.id],
    )

    assert result["mapping_created"] is False
    db_session.refresh(sample_merchant_mapping)
    assert sample_merchant_mapping.category == "entertainment"


# ==================== apply_merchant_mappings_to_transaction ====================

def test_apply_merchant_mappings_applies_to_uncategorized(db_session, category_service, sample_account, sample_merchant_mapping):
    """Should apply mapping to transaction without category."""
    txn = create_transaction(db_session, sample_account, description="NETFLIX MONTHLY", category=None)

    result = category_service.apply_merchant_mappings_to_transaction(txn)

    assert result is True
    assert txn.category == "subscriptions"


def test_apply_merchant_mappings_skips_categorized(db_session, category_service, sample_account, sample_merchant_mapping):
    """Should skip transaction that already has category."""
    txn = create_transaction(db_session, sample_account, description="NETFLIX", category="existing")

    result = category_service.apply_merchant_mappings_to_transaction(txn)

    assert result is False
    assert txn.category == "existing"


# ==================== import/export mappings ====================

def test_export_mappings(db_session, category_service, sample_mapping):
    """Should export mappings as list of dicts."""
    exported = category_service.export_mappings()

    assert len(exported) == 1
    assert exported[0]["provider"] == "cal"
    assert exported[0]["raw_category"] == "סופרמרקט"
    assert exported[0]["unified_category"] == "groceries"


@pytest.mark.parametrize("overwrite,expected_action", [
    pytest.param(False, "skipped", id="skip_existing"),
    pytest.param(True, "updated", id="overwrite_existing"),
])
def test_import_mappings_existing(db_session, category_service, sample_mapping, overwrite, expected_action):
    """Should skip or overwrite existing mappings based on flag."""
    mappings = [{"provider": "cal", "raw_category": "סופרמרקט", "unified_category": "food"}]

    result = category_service.import_mappings(mappings, overwrite=overwrite)

    assert result[expected_action] == 1
    db_session.refresh(sample_mapping)
    expected_unified = "food" if overwrite else "groceries"
    assert sample_mapping.unified_category == expected_unified


def test_import_mappings_new(db_session, category_service):
    """Should import new mappings."""
    mappings = [{"provider": "cal", "raw_category": "test", "unified_category": "food"}]

    result = category_service.import_mappings(mappings)

    assert result["added"] == 1