"""
Tests for RulesService.

Tests rule matching (exact, contains, regex, starts_with, ends_with),
rule CRUD operations, and rule application to transactions.
"""

import pytest
import tempfile
from pathlib import Path

from services.rules_service import Rule, MatchType, RulesService
from db.models import Transaction, Tag
from tests.conftest import create_account, create_transaction, create_tag, tag_transaction


# ==================== Fixtures ====================

@pytest.fixture
def temp_rules_file():
    """Create a temporary rules file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("rules: []\n")
        return Path(f.name)


@pytest.fixture
def rules_service(db_session, temp_rules_file):
    """RulesService instance with temp file and test database session."""
    return RulesService(rules_file=temp_rules_file, session=db_session)


@pytest.fixture
def sample_account(db_session):
    """Create a sample account for testing."""
    return create_account(db_session, institution="cal", account_number="1234")


# ==================== Rule.matches() ====================

@pytest.mark.parametrize("match_type,pattern,text,expected", [
    pytest.param(MatchType.CONTAINS, "wolt", "WOLT TLV DELIVERY", True, id="contains_match"),
    pytest.param(MatchType.CONTAINS, "wolt", "Netflix", False, id="contains_no_match"),
    pytest.param(MatchType.EXACT, "wolt", "WOLT", True, id="exact_match"),
    pytest.param(MatchType.EXACT, "wolt", "WOLT TLV", False, id="exact_no_match"),
    pytest.param(MatchType.STARTS_WITH, "netflix", "NETFLIX SUBSCRIPTION", True, id="starts_with_match"),
    pytest.param(MatchType.STARTS_WITH, "netflix", "My NETFLIX", False, id="starts_with_no_match"),
    pytest.param(MatchType.ENDS_WITH, "delivery", "WOLT DELIVERY", True, id="ends_with_match"),
    pytest.param(MatchType.ENDS_WITH, "delivery", "DELIVERY SERVICE", False, id="ends_with_no_match"),
])
def test_rule_matches_match_types(match_type, pattern, text, expected):
    """Should match based on match_type."""
    rule = Rule(pattern=pattern, match_type=match_type)
    assert rule.matches(text) == expected


@pytest.mark.parametrize("pattern,text,expected", [
    pytest.param(r"wolt.*\d+", "WOLT ORDER 123", True, id="regex_match"),
    pytest.param(r"wolt.*\d+", "WOLT TLV", False, id="regex_no_match"),
])
def test_rule_matches_regex(pattern, text, expected):
    """Should match using regex patterns."""
    rule = Rule(pattern=pattern, match_type=MatchType.REGEX)
    assert rule.matches(text) == expected


def test_rule_matches_invalid_regex():
    """Should handle invalid regex gracefully."""
    rule = Rule(pattern="[invalid", match_type=MatchType.REGEX)
    assert rule.matches("test") is False


@pytest.mark.parametrize("text,expected", [
    pytest.param("", False, id="empty_string"),
    pytest.param(None, False, id="none_input"),
])
def test_rule_matches_edge_cases(text, expected):
    """Should handle empty/None text."""
    rule = Rule(pattern="test", match_type=MatchType.CONTAINS)
    assert rule.matches(text) == expected


def test_rule_matches_disabled_rule():
    """Should not match when rule is disabled."""
    rule = Rule(pattern="test", match_type=MatchType.CONTAINS, enabled=False)
    assert rule.matches("test string") is False


# ==================== Rule.to_dict() / from_dict() ====================

def test_rule_to_dict_minimal():
    """Should serialize with minimal fields."""
    rule = Rule(pattern="test", category="food")
    result = rule.to_dict()

    assert result["pattern"] == "test"
    assert result["category"] == "food"
    assert "match_type" not in result  # Default, omitted
    assert "enabled" not in result  # Default True, omitted


def test_rule_to_dict_full():
    """Should serialize all fields when set."""
    rule = Rule(
        pattern="test",
        match_type=MatchType.REGEX,
        category="food",
        tags=["tag1", "tag2"],
        remove_tags=["old_tag"],
        description="Test rule",
        enabled=False,
    )
    result = rule.to_dict()

    assert result["match_type"] == "regex"
    assert result["tags"] == ["tag1", "tag2"]
    assert result["enabled"] is False


@pytest.mark.parametrize("data,expected_match_type", [
    pytest.param({"pattern": "test"}, MatchType.CONTAINS, id="default_contains"),
    pytest.param({"pattern": "test", "match_type": "regex"}, MatchType.REGEX, id="explicit_regex"),
    pytest.param({"pattern": "test", "match_type": "unknown"}, MatchType.CONTAINS, id="unknown_defaults"),
])
def test_rule_from_dict_match_type(data, expected_match_type):
    """Should parse match_type correctly with defaults."""
    rule = Rule.from_dict(data)
    assert rule.match_type == expected_match_type


# ==================== RulesService CRUD ====================

def test_add_rule(rules_service):
    """Should add rule and persist to file."""
    rule = rules_service.add_rule(pattern="test", category="food", tags=["groceries"])

    assert rule.pattern == "test"
    assert rule.category == "food"
    assert len(rules_service.get_rules()) == 1


@pytest.mark.parametrize("pattern_to_remove,expected", [
    pytest.param("test", True, id="existing_rule"),
    pytest.param("TEST", True, id="case_insensitive"),
    pytest.param("nonexistent", False, id="not_found"),
])
def test_remove_rule(rules_service, pattern_to_remove, expected):
    """Should remove rule by pattern (case-insensitive)."""
    rules_service.add_rule(pattern="test", category="food")
    result = rules_service.remove_rule(pattern_to_remove)
    assert result == expected


def test_get_rules_returns_copy(rules_service):
    """Should return a copy of rules list."""
    rules_service.add_rule(pattern="test")
    rules1 = rules_service.get_rules()
    rules2 = rules_service.get_rules()
    assert rules1 is not rules2


# ==================== find_matching_rules ====================

def test_find_matching_rules_multiple(rules_service):
    """Should find all rules matching a description."""
    rules_service.add_rule(pattern="wolt", tags=["food"])
    rules_service.add_rule(pattern="delivery", tags=["delivery"])
    rules_service.add_rule(pattern="spotify", tags=["music"])

    matches = rules_service.find_matching_rules("WOLT DELIVERY")

    assert len(matches) == 2
    patterns = [m.pattern for m in matches]
    assert "wolt" in patterns
    assert "delivery" in patterns


def test_find_matching_rules_no_match(rules_service):
    """Should return empty list when no rules match."""
    rules_service.add_rule(pattern="wolt")
    matches = rules_service.find_matching_rules("Netflix")
    assert matches == []


# ==================== apply_rules_to_transaction ====================

def test_apply_rules_to_transaction_sets_category(db_session, rules_service, sample_account):
    """Should apply category from first matching rule."""
    rules_service.add_rule(pattern="wolt", category="food")
    txn = create_transaction(db_session, sample_account, description="WOLT DELIVERY")

    result = rules_service.apply_rules_to_transaction(txn)

    assert result["category"] == "food"
    assert txn.user_category == "food"


def test_apply_rules_to_transaction_first_category_wins(db_session, rules_service, sample_account):
    """Should use category from first matching rule only."""
    rules_service.add_rule(pattern="wolt", category="food")
    rules_service.add_rule(pattern="delivery", category="services")
    txn = create_transaction(db_session, sample_account, description="WOLT DELIVERY")

    result = rules_service.apply_rules_to_transaction(txn)

    assert result["category"] == "food"


def test_apply_rules_to_transaction_combines_tags(db_session, rules_service, sample_account):
    """Should combine tags from all matching rules."""
    rules_service.add_rule(pattern="wolt", tags=["food"])
    rules_service.add_rule(pattern="delivery", tags=["delivery"])
    txn = create_transaction(db_session, sample_account, description="WOLT DELIVERY")

    result = rules_service.apply_rules_to_transaction(txn)

    assert set(result["tags"]) == {"food", "delivery"}


def test_apply_rules_to_transaction_dry_run(db_session, rules_service, sample_account):
    """Should not modify transaction in dry_run mode."""
    rules_service.add_rule(pattern="wolt", category="food")
    txn = create_transaction(db_session, sample_account, description="WOLT DELIVERY")

    result = rules_service.apply_rules_to_transaction(txn, dry_run=True)

    assert result["category"] == "food"
    assert txn.user_category is None  # Unchanged


# ==================== apply_rules (batch) ====================

def test_apply_rules_batch(db_session, rules_service, sample_account):
    """Should apply rules to multiple transactions."""
    rules_service.add_rule(pattern="wolt", category="food")
    create_transaction(db_session, sample_account, description="WOLT 1")
    create_transaction(db_session, sample_account, description="WOLT 2")
    create_transaction(db_session, sample_account, description="NETFLIX")

    result = rules_service.apply_rules()

    assert result["processed"] == 3
    assert result["modified"] == 2


def test_apply_rules_only_uncategorized(db_session, rules_service, sample_account):
    """Should only process uncategorized transactions when flag set."""
    rules_service.add_rule(pattern="wolt", category="food")
    txn1 = create_transaction(db_session, sample_account, description="WOLT 1", user_category="existing")
    txn2 = create_transaction(db_session, sample_account, description="WOLT 2")

    result = rules_service.apply_rules(only_uncategorized=True)

    assert result["modified"] == 1
    db_session.refresh(txn1)
    assert txn1.user_category == "existing"


def test_apply_rules_specific_transactions(db_session, rules_service, sample_account):
    """Should apply to specific transaction IDs only."""
    rules_service.add_rule(pattern="wolt", category="food")
    txn1 = create_transaction(db_session, sample_account, description="WOLT 1")
    txn2 = create_transaction(db_session, sample_account, description="WOLT 2")

    result = rules_service.apply_rules(transaction_ids=[txn1.id])

    assert result["processed"] == 1
    db_session.refresh(txn1)
    db_session.refresh(txn2)
    assert txn1.user_category == "food"
    assert txn2.user_category is None


def test_apply_rules_no_rules_defined(rules_service):
    """Should handle case with no rules defined."""
    result = rules_service.apply_rules()
    assert result["message"] == "No rules defined"


# ==================== File operations ====================

def test_load_rules_from_file(temp_rules_file):
    """Should load rules from YAML file."""
    temp_rules_file.write_text("""
rules:
  - pattern: "wolt"
    category: "food"
    tags: ["delivery"]
  - pattern: "netflix"
    category: "entertainment"
""")
    service = RulesService(rules_file=temp_rules_file)
    rules = service.load_rules()

    assert len(rules) == 2
    assert rules[0].pattern == "wolt"


def test_load_rules_file_not_exists(db_session):
    """Should handle missing rules file gracefully."""
    service = RulesService(rules_file=Path("/nonexistent/file.yaml"), session=db_session)
    rules = service.load_rules()
    assert rules == []


def test_create_default_rules_file(db_session):
    """Should create default rules file with documentation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        rules_file = Path(tmpdir) / "rules.yaml"
        service = RulesService(rules_file=rules_file, session=db_session)

        result = service.create_default_rules_file()

        assert result is True
        assert rules_file.exists()
        assert "# Category Rules" in rules_file.read_text()


def test_create_default_rules_file_exists(rules_service, temp_rules_file):
    """Should not overwrite existing rules file."""
    temp_rules_file.write_text("rules:\n  - pattern: existing")

    result = rules_service.create_default_rules_file()

    assert result is False
    assert "existing" in temp_rules_file.read_text()
