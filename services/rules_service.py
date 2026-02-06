"""
Rules service for auto-categorizing and tagging transactions based on patterns.

Rules are stored in ~/.fin/category_rules.yaml and applied automatically after sync
or manually via `fin rules apply`.
"""

import logging
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

import yaml
from sqlalchemy.orm import Session

from db.models import Transaction
from services.tag_service import TagService
from services.base_service import SessionMixin
from config.settings import CONFIG_DIR

logger = logging.getLogger(__name__)

# Default rules file location
RULES_FILE = CONFIG_DIR / "category_rules.yaml"


class MatchType(Enum):
    """How to match the pattern against transaction description"""
    CONTAINS = "contains"      # Case-insensitive substring match
    EXACT = "exact"            # Exact match (case-insensitive)
    REGEX = "regex"            # Regular expression match
    STARTS_WITH = "starts_with"  # Starts with pattern
    ENDS_WITH = "ends_with"    # Ends with pattern


@dataclass
class Rule:
    """A single categorization/tagging rule"""
    pattern: str
    match_type: MatchType = MatchType.CONTAINS
    category: Optional[str] = None  # Sets user_category
    tags: List[str] = field(default_factory=list)  # Tags to add
    remove_tags: List[str] = field(default_factory=list)  # Tags to remove
    description: Optional[str] = None  # Human-readable description of the rule
    enabled: bool = True

    def matches(self, text: str) -> bool:
        """Check if this rule matches the given text"""
        if not self.enabled:
            return False

        if not text:
            return False

        text_lower = text.lower()
        pattern_lower = self.pattern.lower()

        if self.match_type == MatchType.CONTAINS:
            return pattern_lower in text_lower
        elif self.match_type == MatchType.EXACT:
            return pattern_lower == text_lower
        elif self.match_type == MatchType.STARTS_WITH:
            return text_lower.startswith(pattern_lower)
        elif self.match_type == MatchType.ENDS_WITH:
            return text_lower.endswith(pattern_lower)
        elif self.match_type == MatchType.REGEX:
            try:
                return bool(re.search(self.pattern, text, re.IGNORECASE))
            except re.error:
                logger.warning(f"Invalid regex pattern: {self.pattern}")
                return False

        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary for YAML serialization"""
        result = {"pattern": self.pattern}

        if self.match_type != MatchType.CONTAINS:
            result["match_type"] = self.match_type.value

        if self.category:
            result["category"] = self.category

        if self.tags:
            result["tags"] = self.tags

        if self.remove_tags:
            result["remove_tags"] = self.remove_tags

        if self.description:
            result["description"] = self.description

        if not self.enabled:
            result["enabled"] = False

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Rule":
        """Create rule from dictionary"""
        match_type_str = data.get("match_type", "contains")
        try:
            match_type = MatchType(match_type_str)
        except ValueError:
            logger.warning(f"Unknown match_type '{match_type_str}', defaulting to 'contains'")
            match_type = MatchType.CONTAINS

        return cls(
            pattern=data["pattern"],
            match_type=match_type,
            category=data.get("category"),
            tags=data.get("tags", []),
            remove_tags=data.get("remove_tags", []),
            description=data.get("description"),
            enabled=data.get("enabled", True),
        )


class RulesService(SessionMixin):
    """Service for managing and applying categorization rules"""

    def __init__(self, rules_file: Optional[Path] = None, session: Optional[Session] = None):
        """
        Initialize rules service

        Args:
            rules_file: Path to rules YAML file (default: ~/.fin/category_rules.yaml)
            session: SQLAlchemy session (if None, creates a new one)
        """
        super().__init__(session=session)
        self.rules_file = rules_file or RULES_FILE
        self._rules: List[Rule] = []
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Ensure rules are loaded from file"""
        if not self._loaded:
            self.load_rules()

    def load_rules(self) -> List[Rule]:
        """Load rules from YAML file"""
        self._rules = []

        if not self.rules_file.exists():
            logger.debug(f"Rules file not found: {self.rules_file}")
            self._loaded = True
            return self._rules

        try:
            with open(self.rules_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            rules_data = data.get("rules", [])
            for rule_data in rules_data:
                try:
                    rule = Rule.from_dict(rule_data)
                    self._rules.append(rule)
                except KeyError as e:
                    logger.warning(f"Invalid rule (missing {e}): {rule_data}")
                except Exception as e:
                    logger.warning(f"Error parsing rule: {e}")

            logger.info(f"Loaded {len(self._rules)} rules from {self.rules_file}")

        except yaml.YAMLError as e:
            logger.error(f"Error parsing rules file: {e}")
        except Exception as e:
            logger.error(f"Error loading rules: {e}")

        self._loaded = True
        return self._rules

    def save_rules(self) -> bool:
        """Save rules to YAML file"""
        try:
            # Ensure config directory exists
            self.rules_file.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "rules": [rule.to_dict() for rule in self._rules]
            }

            with open(self.rules_file, "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

            logger.info(f"Saved {len(self._rules)} rules to {self.rules_file}")
            return True

        except Exception as e:
            logger.error(f"Error saving rules: {e}")
            return False

    def get_rules(self) -> List[Rule]:
        """Get all rules"""
        self._ensure_loaded()
        return self._rules.copy()

    def add_rule(
        self,
        pattern: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        remove_tags: Optional[List[str]] = None,
        match_type: MatchType = MatchType.CONTAINS,
        description: Optional[str] = None,
    ) -> Rule:
        """
        Add a new rule

        Args:
            pattern: Pattern to match against transaction description
            category: Category to set (user_category)
            tags: Tags to add
            remove_tags: Tags to remove
            match_type: How to match the pattern
            description: Human-readable description

        Returns:
            The created Rule
        """
        self._ensure_loaded()

        rule = Rule(
            pattern=pattern,
            match_type=match_type,
            category=category,
            tags=tags or [],
            remove_tags=remove_tags or [],
            description=description,
        )
        self._rules.append(rule)
        self.save_rules()
        return rule

    def remove_rule(self, pattern: str) -> bool:
        """
        Remove a rule by pattern

        Args:
            pattern: Pattern of the rule to remove

        Returns:
            True if removed, False if not found
        """
        self._ensure_loaded()

        for i, rule in enumerate(self._rules):
            if rule.pattern.lower() == pattern.lower():
                self._rules.pop(i)
                self.save_rules()
                return True

        return False

    def find_matching_rules(self, description: str, rules: Optional[List[Rule]] = None) -> List[Rule]:
        """
        Find all rules that match a transaction description

        Args:
            description: Transaction description to match
            rules: Optional list of rules to check (defaults to all rules)

        Returns:
            List of matching rules
        """
        self._ensure_loaded()
        rules_to_check = rules if rules is not None else self._rules
        return [rule for rule in rules_to_check if rule.matches(description)]

    def apply_rules_to_transaction(
        self,
        transaction: Transaction,
        dry_run: bool = False,
        rules: Optional[List[Rule]] = None
    ) -> Dict[str, Any]:
        """
        Apply matching rules to a single transaction

        Args:
            transaction: Transaction to process
            dry_run: If True, don't save changes
            rules: Optional list of rules to apply (defaults to all rules)

        Returns:
            Dict with applied changes: {category: str, tags: [str], rules: [str]}
        """
        matching_rules = self.find_matching_rules(transaction.description, rules)

        if not matching_rules:
            return {"category": None, "tags": [], "remove_tags": [], "rules": []}

        result = {
            "category": None,
            "tags": [],
            "remove_tags": [],
            "rules": [rule.pattern for rule in matching_rules],
        }

        # Collect category (first matching rule with category wins)
        for rule in matching_rules:
            if rule.category and not result["category"]:
                result["category"] = rule.category
                break

        # Collect all tags to add from all matching rules
        all_tags = set()
        for rule in matching_rules:
            all_tags.update(rule.tags)
        result["tags"] = list(all_tags)

        # Collect all tags to remove from all matching rules
        all_remove_tags = set()
        for rule in matching_rules:
            all_remove_tags.update(rule.remove_tags)
        result["remove_tags"] = list(all_remove_tags)

        if not dry_run:
            tag_service = TagService(session=self.session)

            # Apply category
            if result["category"] and transaction.user_category != result["category"]:
                transaction.user_category = result["category"]

            # Add tags
            if result["tags"]:
                tag_service.tag_transaction(transaction.id, result["tags"])

            # Remove tags
            if result["remove_tags"]:
                tag_service.untag_transaction(transaction.id, result["remove_tags"])

            self.session.commit()

        return result

    def apply_rules(
        self,
        transaction_ids: Optional[List[int]] = None,
        only_uncategorized: bool = False,
        dry_run: bool = False,
        rule_indices: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Apply rules to multiple transactions

        Args:
            transaction_ids: Specific transaction IDs to process (None = all)
            only_uncategorized: Only process transactions without user_category
            dry_run: If True, don't save changes
            rule_indices: Specific rule indices (0-based) to apply (None = all rules)

        Returns:
            Summary: {processed: int, modified: int, details: [...]}
        """
        self._ensure_loaded()

        if not self._rules:
            return {"processed": 0, "modified": 0, "details": [], "message": "No rules defined"}

        # Filter to specific rules if requested
        if rule_indices is not None:
            rules_to_apply = [self._rules[i] for i in rule_indices if i < len(self._rules)]
        else:
            rules_to_apply = self._rules

        # Build query
        query = self.session.query(Transaction)

        if transaction_ids:
            query = query.filter(Transaction.id.in_(transaction_ids))

        if only_uncategorized:
            query = query.filter(Transaction.user_category.is_(None))

        transactions = query.all()

        results = {
            "processed": 0,
            "modified": 0,
            "details": [],
        }

        for txn in transactions:
            results["processed"] += 1

            changes = self.apply_rules_to_transaction(txn, dry_run=dry_run, rules=rules_to_apply)

            if changes["category"] or changes["tags"] or changes["remove_tags"]:
                results["modified"] += 1
                results["details"].append({
                    "id": txn.id,
                    "description": txn.description,
                    "category": changes["category"],
                    "tags": changes["tags"],
                    "remove_tags": changes["remove_tags"],
                    "matched_rules": changes["rules"],
                })

        if not dry_run:
            self.session.commit()

        return results

    def create_default_rules_file(self) -> bool:
        """Create an empty rules file with format documentation"""
        if self.rules_file.exists():
            return False

        # Ensure config directory exists
        self.rules_file.parent.mkdir(parents=True, exist_ok=True)

        content = """# Category Rules for Fin
#
# These rules automatically set categories and tags on transactions
# based on pattern matching against the transaction description.
#
# Match types:
#   - contains (default): Case-insensitive substring match
#   - exact: Exact match (case-insensitive)
#   - starts_with: Description starts with pattern
#   - ends_with: Description ends with pattern
#   - regex: Regular expression match
#
# Example rules (uncomment and modify to use):
#
#   - pattern: "pango"
#     category: "Transportation"
#     tags: ["parking", "car"]
#     description: "Pango parking app"
#
#   - pattern: "wolt"
#     category: "Food & Dining"
#     tags: ["delivery", "food"]
#
#   - pattern: "סופר"
#     category: "Groceries"
#     tags: ["groceries"]
#     description: "Supermarkets (Hebrew)"
#
# Rules are applied in order. First matching category wins.
# All matching tags are combined.
#
# Add rules using: fin rules add "pattern" -c "Category" -t "tag1,tag2"
# Or edit this file directly.

rules: []
"""
        try:
            with open(self.rules_file, "w", encoding="utf-8") as f:
                f.write(content)

            self._rules = []
            self._loaded = True
            logger.info(f"Created empty rules file at {self.rules_file}")
            return True

        except Exception as e:
            logger.error(f"Error creating rules file: {e}")
            return False
