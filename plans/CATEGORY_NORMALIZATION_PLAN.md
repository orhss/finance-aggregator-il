# Category Normalization Implementation Plan

## Overview

Normalize transaction categories across providers (CAL, Max, Isracard) to enable consistent analytics and reporting. Each provider uses different category names for the same transaction types.

**Status**: ✅ Complete (All Phases Implemented)

**Approach**: Two-tier normalization system:
1. **Provider Mapping** (`CategoryMapping`): Maps provider's `raw_category` → unified `category`
2. **Merchant Mapping** (`MerchantMapping`): Maps transaction description patterns → unified `category` (for providers like Isracard that don't provide categories)

---

## Python Principles

- **DRY**: Extract duplicated logic into reusable functions
- **KISS**: Prefer straightforward solutions over clever ones
- **SIMPLE**: Minimal code to solve the actual problem, no speculative features
- Avoid premature abstraction - three similar lines beats a premature helper

---

## Data Model

### Field Hierarchy (Priority Order)

| Field | Source | Example | Editable |
|-------|--------|---------|----------|
| `user_category` | User manual override | "weekly_shopping" | Yes |
| `category` | Mapping table lookup | "groceries" | No (auto) |
| `raw_category` | Provider API | "סופרמרקט" (CAL) | No |

```python
@property
def effective_category(self) -> Optional[str]:
    return self.user_category or self.category or self.raw_category
```

### Model: CategoryMapping (Provider Categories)

Maps provider's `raw_category` to unified `category`. Used for CAL, Max which provide categories.

```python
class CategoryMapping(Base):
    __tablename__ = "category_mappings"

    id = Column(Integer, primary_key=True)
    provider = Column(String(50), nullable=False)      # "cal", "max", "isracard"
    raw_category = Column(String(255), nullable=False) # Original from provider
    unified_category = Column(String(100), nullable=False)  # Normalized name
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('provider', 'raw_category', name='uq_category_mapping'),
        Index('idx_category_mapping_lookup', 'provider', 'raw_category'),
    )
```

### Model: MerchantMapping (Description Patterns)

Maps transaction description patterns to unified `category`. Used for Isracard (no provider categories).

```python
class MerchantMapping(Base):
    __tablename__ = "merchant_mappings"

    id = Column(Integer, primary_key=True)
    pattern = Column(String(255), nullable=False)      # Merchant pattern to match
    category = Column(String(100), nullable=False)     # Unified category name
    provider = Column(String(50), nullable=True)       # Optional: limit to specific provider
    match_type = Column(String(20), default='startswith')  # 'startswith', 'contains', 'exact'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('pattern', 'provider', name='uq_merchant_mapping'),
        Index('idx_merchant_mapping_pattern', 'pattern'),
    )

    def matches(self, description: str) -> bool:
        """Check if this mapping matches the given description."""
        # Implements startswith/contains/exact matching
```

### Two-Tier Normalization Flow

```
Transaction arrives during sync
        ↓
Has raw_category? ──YES──→ Lookup CategoryMapping ──→ Set category
        │                          ↓
        NO                  No mapping found? → Track as unmapped
        ↓
Lookup MerchantMapping by description pattern
        ↓
Match found? ──YES──→ Set category
        ↓
        NO → category stays NULL (needs manual assignment)
```

---

## Files to Modify

### Database Layer

| File | Changes |
|------|---------|
| `db/models.py` | Add `raw_category` field, add `CategoryMapping` model, update `effective_category` property |
| `db/database.py` | Add migration for `raw_category` column rename, create `category_mappings` table |
| `db/migrations/add_indexes.py` | Add index for `raw_category` |

### Services Layer

| File | Changes |
|------|---------|
| `services/category_service.py` | **NEW** - CRUD for mappings, normalization logic, unmapped detection |
| `services/credit_card_service.py` | Call `normalize_category()` during sync, save to both `raw_category` and `category` |
| `services/analytics_service.py` | Update `effective_category_expr()` to include `raw_category` fallback |
| `services/tag_service.py` | Update category queries to use new field names |
| `services/rules_service.py` | No changes (already uses `user_category`) |

### CLI Commands

| File | Changes |
|------|---------|
| `cli/commands/categories.py` | **NEW** - `analyze`, `list`, `map`, `unmapped`, `apply`, `setup` commands |
| `cli/main.py` | Register `categories` command group |
| `cli/commands/transactions.py` | Update display to show `raw_category` vs `category` |
| `cli/commands/export.py` | Export both `raw_category` and `category` fields |
| `cli/commands/sync.py` | Report unmapped categories after sync |
| `cli/commands/rules.py` | No changes needed |
| `cli/tui/browser.py` | Update search to include `raw_category`, update display |

### Streamlit UI

| File | Changes |
|------|---------|
| `streamlit_app/pages/10_📂_Categories.py` | **NEW** - Mapping management, unmapped view, setup wizard |
| `streamlit_app/pages/1_📊_Dashboard.py` | Add unmapped categories alert widget |
| `streamlit_app/pages/3_💳_Transactions.py` | Show `raw_category` on hover/detail, filter by unified category |
| `streamlit_app/pages/4_📈_Analytics.py` | No changes (uses `effective_category`) |
| `streamlit_app/pages/5_🏷️_Tags.py` | Update category queries |
| `streamlit_app/pages/6_📋_Rules.py` | No changes needed |
| `streamlit_app/components/category_mapper.py` | **NEW** - Mapping table component, inline edit |
| `streamlit_app/components/category_wizard.py` | **NEW** - Initial setup wizard |
| `streamlit_app/components/filters.py` | Update `category_filter()` to use unified categories |
| `streamlit_app/utils/cache.py` | Update category-related cached queries |
| `streamlit_app/utils/session.py` | Update `get_all_categories()` to return unified categories |

### Scrapers

| File | Changes |
|------|---------|
| `scrapers/credit_cards/cal_credit_card_client.py` | Field already named `category` in dataclass - no change needed |
| `scrapers/credit_cards/max_credit_card_client.py` | Field already named `category` in dataclass - no change needed |
| `scrapers/credit_cards/isracard_credit_card_client.py` | Field already named `category` in dataclass - no change needed |

### Other

| File | Changes |
|------|---------|
| `examples/example_cal_usage.py` | Update to use new field names |
| `config/constants.py` | Add `UnifiedCategory` class with standard category names |

---

## Implementation Details

### 1. Database Migration

```sql
-- Step 1: Rename category to raw_category
ALTER TABLE transactions RENAME COLUMN category TO raw_category;

-- Step 2: Add new category column (for normalized values)
ALTER TABLE transactions ADD COLUMN category VARCHAR(100);

-- Step 3: Create category_mappings table
CREATE TABLE category_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider VARCHAR(50) NOT NULL,
    raw_category VARCHAR(255) NOT NULL,
    unified_category VARCHAR(100) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,
    UNIQUE(provider, raw_category)
);

-- Step 4: Create indexes
CREATE INDEX idx_category_mapping_lookup ON category_mappings(provider, raw_category);
CREATE INDEX idx_transactions_raw_category ON transactions(raw_category);
```

### 2. CategoryService

```python
# services/category_service.py

class CategoryService:
    def __init__(self, db_session: Session):
        self.db = db_session

    def normalize_category(self, provider: str, raw_category: str) -> Optional[str]:
        """Lookup unified category from mapping. Returns None if not mapped."""
        mapping = self.db.query(CategoryMapping).filter(
            CategoryMapping.provider == provider,
            CategoryMapping.raw_category == raw_category
        ).first()
        return mapping.unified_category if mapping else None

    def get_unmapped_categories(self) -> List[Dict]:
        """Get all (provider, raw_category) pairs that have no mapping."""
        # Query transactions with raw_category but no category (normalized)
        ...

    def add_mapping(self, provider: str, raw_category: str, unified: str) -> CategoryMapping:
        """Add or update a category mapping."""
        ...

    def apply_mappings_to_transactions(self, provider: Optional[str] = None) -> int:
        """Apply mappings to existing transactions. Returns count updated."""
        ...

    def get_all_mappings(self, provider: Optional[str] = None) -> List[CategoryMapping]:
        """Get all mappings, optionally filtered by provider."""
        ...

    def get_unique_raw_categories(self, provider: Optional[str] = None) -> List[Dict]:
        """Get unique raw categories with transaction counts."""
        ...

    def get_unified_categories(self) -> List[str]:
        """Get list of all unified category names in use."""
        ...

    def rename_unified_category(self, old_name: str, new_name: str) -> int:
        """Rename a unified category across all mappings. Returns count updated."""
        ...

    def merge_unified_categories(self, sources: List[str], target: str) -> int:
        """Merge multiple unified categories into one."""
        ...
```

### 3. CLI Commands

```bash
# Analyze existing transactions
fin-cli categories analyze
# Output:
# Provider    | Unique Categories | Transactions
# ------------|-------------------|-------------
# CAL         | 18                | 1,234
# Max         | 15                | 892
# Isracard    | 14                | 567
#
# Run 'fin-cli categories setup' for interactive setup
# Or 'fin-cli categories unmapped' to see unmapped categories

# Interactive setup wizard
fin-cli categories setup
# Walks through each unique raw category, suggests unified name

# List all mappings
fin-cli categories list [--provider cal|max|isracard]
# Output:
# Provider | Raw Category    | → | Unified      | Transactions
# ---------|-----------------|---|--------------|-------------
# CAL      | סופרמרקט        | → | groceries    | 142
# Max      | מזון וסופר       | → | groceries    | 89

# Show unmapped categories
fin-cli categories unmapped
# Output:
# ⚠ 3 unmapped categories found:
#   Provider | Raw Category     | Transactions
#   ---------|------------------|-------------
#   CAL      | קטגוריה חדשה     | 12
#   Max      | אחר              | 5
#
# Map with: fin-cli categories map <provider> "<raw>" <unified>

# Add/update mapping
fin-cli categories map cal "קטגוריה חדשה" groceries
fin-cli categories map max "אחר" other

# Remove mapping
fin-cli categories unmap cal "קטגוריה חדשה"

# Apply mappings to existing transactions
fin-cli categories apply [--provider cal|max|isracard]
# Output:
# Applied mappings to 1,234 transactions
#   CAL: 567 updated
#   Max: 445 updated
#   Isracard: 222 updated

# List unified categories
fin-cli categories unified
# Output:
# Unified Category | Providers          | Transactions
# -----------------|--------------------|--------------
# groceries        | CAL, Max, Isracard | 523
# fuel             | CAL, Max           | 89
# restaurants      | CAL, Max, Isracard | 234

# Rename unified category
fin-cli categories rename groceries "food_and_groceries"

# Export/import mappings (for backup/sharing)
fin-cli categories export mappings.json
fin-cli categories import mappings.json

# ============ Merchant Pattern Mappings (for Isracard, etc.) ============

# Show uncategorized transactions grouped by merchant pattern
fin-cli categories suggest [--min 2]
# Output:
# Merchant Pattern    | Provider | Transactions | Total Amount
# --------------------|----------|--------------|-------------
# GOOGLE              | ISRACARD | 16           | ₪229
# NETFLIX             | ISRACARD | 12           | ₪659
# PANGO               | ISRACARD | 13           | ₪276

# Assign category to merchant pattern (saves mapping for future)
fin-cli categories assign 1 subscriptions
# Output:
# Assigned 'subscriptions' to 16 transactions
# Created merchant mapping: 'GOOGLE' -> 'subscriptions'
# Future transactions matching this pattern will be auto-categorized

# Interactive wizard for merchant patterns
fin-cli categories assign-wizard [--min 2]

# List all merchant mappings
fin-cli categories merchants [--provider isracard]

# Remove a merchant mapping
fin-cli categories remove-merchant "GOOGLE" [--provider isracard]
```

### 4. Updated Sync Flow

```python
# services/credit_card_service.py

def _save_transaction(self, provider: str, txn_data, account: Account):
    raw_category = txn_data.category  # From scraper

    # Lookup normalized category
    normalized = self.category_service.normalize_category(provider, raw_category)

    transaction = Transaction(
        account_id=account.id,
        raw_category=raw_category,      # Original from provider
        category=normalized,            # Normalized (may be None)
        # ... other fields
    )
    self.db.add(transaction)

    # Track if we have unmapped categories
    if raw_category and not normalized:
        self._unmapped_categories.add((provider, raw_category))
```

### 5. Post-Sync Report

```
✓ Sync completed for CAL

  Transactions: 45 added, 3 updated

  ⚠ 2 unmapped categories detected:
    - "קטגוריה חדשה" (3 transactions)
    - "אחר" (1 transaction)

  Run 'fin-cli categories unmapped' to review
```

### 6. Streamlit Categories Page

**Tab 1: Mappings**
- Table with all mappings (provider, raw → unified, count)
- Inline edit dropdown for unified category
- Bulk select + assign unified category
- Filter by provider

**Tab 2: Unmapped**
- Table of unmapped (provider, raw_category, count, sample merchant)
- Dropdown to select unified category for each
- "Quick map" - select multiple and assign same unified
- Auto-suggest based on similarity to existing mappings

**Tab 3: Unified Categories**
- List of all unified categories with stats
- Click to expand: see all raw categories mapped to it
- Rename unified category
- Merge categories (select 2+, merge into one)
- Delete (must remap transactions first)

**Tab 4: Setup Wizard** (shown if < 50% mapped)
- Step-by-step grouping of similar raw categories
- Fuzzy matching suggestions
- Progress indicator

### 7. Dashboard Alert

```python
# Show if unmapped categories exist
unmapped = category_service.get_unmapped_categories()
if unmapped:
    st.warning(f"⚠️ {len(unmapped)} unmapped categories ({sum(u['count'] for u in unmapped)} transactions)")
    if st.button("Review"):
        st.switch_page("pages/10_📂_Categories.py")
```

### 8. Transaction Browser Updates

- Filter dropdown shows unified categories only
- Table shows unified category
- Hover/expand shows: "groceries (CAL: סופרמרקט)"
- Detail view shows all three: raw, normalized, user override

---

## Standard Unified Categories

Suggested initial set (can be customized):

```python
# config/constants.py

class UnifiedCategory:
    GROCERIES = "groceries"
    RESTAURANTS = "restaurants"
    FUEL = "fuel"
    TRANSPORTATION = "transportation"
    UTILITIES = "utilities"
    HEALTHCARE = "healthcare"
    ENTERTAINMENT = "entertainment"
    SHOPPING = "shopping"
    TRAVEL = "travel"
    EDUCATION = "education"
    INSURANCE = "insurance"
    SUBSCRIPTIONS = "subscriptions"
    HOME = "home"
    CLOTHING = "clothing"
    ELECTRONICS = "electronics"
    GIFTS = "gifts"
    FEES = "fees"
    OTHER = "other"

    @classmethod
    def all(cls) -> List[str]:
        return [v for k, v in vars(cls).items()
                if not k.startswith('_') and isinstance(v, str)]
```

---

## UX/User-Friendliness Guidelines

### Guiding Principles

1. **Don't interrupt workflow** - Unmapped categories shouldn't block syncing or browsing
2. **Progressive disclosure** - Show simple view first, details on demand
3. **Batch over one-by-one** - Let users handle multiple items at once
4. **Smart defaults** - Suggest likely mappings, don't make user start from blank
5. **Forgiving** - Easy to undo, change, or fix mistakes

### Initial Setup Experience

**Problem**: User has 60+ raw categories to map - overwhelming.

**Solution**: Guided wizard with smart grouping

```
┌─────────────────────────────────────────────────────────────────┐
│  📂 Category Setup                                    Step 2/8  │
│  ═══════════════════════════════════════════════════════════════│
│                                                                 │
│  These look like GROCERY categories:                            │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ ☑ CAL: סופרמרקט              (142 txns)  "שופרסל דיזנגוף"   ││
│  │ ☑ Max: מזון וסופר            (89 txns)   "רמי לוי"         ││
│  │ ☑ Isracard: קניות מזון       (67 txns)   "יינות ביתן"      ││
│  │ ☐ CAL: מזון ומשקאות          (23 txns)   "AM:PM"           ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  Map selected to: [ groceries          ▼]                       │
│                                                                 │
│  [← Back]  [Skip Group]  [Map & Continue →]                     │
│                                                                 │
│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 25% complete          │
└─────────────────────────────────────────────────────────────────┘
```

**Key UX elements**:
- Groups similar categories (fuzzy match on Hebrew text)
- Shows sample merchant for context ("what is this category?")
- Shows transaction count (prioritize high-volume categories)
- Pre-selects likely matches, user unchecks exceptions
- Skip button - don't force completion in one session
- Progress bar - user knows how much is left

### Unmapped Categories Alert

**Problem**: User shouldn't have to check manually after every sync.

**Solution**: Non-blocking notification with quick action

```
┌────────────────────────────────────────────────────────────────┐
│ ⚠️ 2 new categories detected                          [Dismiss]│
│                                                                │
│   CAL: "תחבורה ציבורית" (5 txns)     [→ transportation] [Other]│
│   Max: "נסיעות" (3 txns)             [→ transportation] [Other]│
│                                                                │
│   [Map All Suggested]                                          │
└────────────────────────────────────────────────────────────────┘
```

**Key UX elements**:
- Appears as banner, not modal (doesn't block)
- Shows suggested mapping inline (one-click accept)
- "Other" dropdown for different choice
- "Map All" for batch accept when suggestions look good
- Dismissible - user can deal with it later

### Transaction Browser Category Display

**Problem**: Three category fields (raw, normalized, user) - confusing.

**Solution**: Show only what's relevant

| Context | What to Show |
|---------|--------------|
| Table column | Unified category only: "groceries" |
| Hover tooltip | Source info: "groceries (from CAL: סופרמרקט)" |
| Detail panel | All three if different, with labels |
| Filter dropdown | Unified categories only |

**Detail panel example**:
```
Category: groceries
  └─ Provider category: סופרמרקט (CAL)
  └─ Your override: (none)  [Edit]
```

### CLI User Experience

**Problem**: CLI commands can be cryptic.

**Solution**: Helpful output with next-step suggestions

```bash
$ fin-cli categories unmapped

⚠ 3 unmapped categories:

  Provider │ Category         │ Txns │ Sample Merchant
  ─────────┼──────────────────┼──────┼────────────────
  CAL      │ תחבורה ציבורית    │ 12   │ רכבת ישראל
  Max      │ נסיעות            │ 8    │ גט טקסי
  CAL      │ אחר               │ 3    │ PAYPAL

💡 Quick actions:
   fin-cli categories map cal "תחבורה ציבורית" transportation
   fin-cli categories map max "נסיעות" transportation
   fin-cli categories setup   # Interactive wizard
```

### Error Prevention

| Potential Error | Prevention |
|----------------|------------|
| Typo in unified category name | Dropdown/autocomplete from existing list |
| Map to wrong category | Show sample transactions before confirming |
| Delete mapping with transactions | Warn: "142 transactions will become uncategorized" |
| Create duplicate mapping | Block: "CAL סופרמרקט is already mapped to groceries" |

### Streamlit Accessibility

- Keyboard navigation for mapping table
- RTL support for Hebrew category names
- Color-blind friendly status indicators (not just red/green)
- Mobile-responsive layout for mapping wizard

---

## Migration Checklist

### Phase 1: Database & Models ✅
- [x] Add `CategoryMapping` model to `db/models.py`
- [x] Add `raw_category` field to `Transaction` model
- [x] Update `effective_category` property to include `raw_category` fallback
- [x] Add migration in `db/database.py`
- [x] Update indexes in `db/migrations/add_indexes.py`

### Phase 2: Service Layer ✅
- [x] Create `services/category_service.py`
- [x] Update `services/credit_card_service.py` to normalize on sync
- [x] Update `services/analytics_service.py` - update `effective_category_expr()`
- [x] Update `services/tag_service.py` queries

### Phase 3: CLI ✅
- [x] Create `cli/commands/categories.py` with all commands
- [x] Register in `cli/main.py`
- [x] Update `cli/commands/transactions.py` - display raw vs normalized
- [x] Update `cli/commands/export.py` - export both fields
- [x] Update `cli/commands/sync.py` - post-sync unmapped report
- [x] Update `cli/tui/browser.py` - search and display updates

### Phase 4: Streamlit ✅
- [x] Create `streamlit_app/pages/10_📂_Categories.py` - main categories page (includes mapper, wizard tabs)
- [x] Update `streamlit_app/pages/1_📊_Dashboard.py` - unmapped alert
- [x] Update `streamlit_app/pages/3_💳_Transactions.py` - display/filter updates (unmapped filter, raw_category in edit)
- [x] Update `streamlit_app/components/filters.py` - unified_category_filter function
- [x] Update `streamlit_app/utils/session.py` - `get_category_service()`, `get_unified_categories()`, updated `get_all_categories()`

Note: Separate `category_mapper.py` and `category_wizard.py` components were integrated directly into the Categories page as tabs for simplicity.

### Phase 5: Other Updates ✅
- [x] Add `UnifiedCategory` to `config/constants.py`
- [x] Update `CLAUDE.md` with new commands/features

### Phase 6: Merchant Mapping (for providers without categories) ✅
- [x] Add `MerchantMapping` model to `db/models.py`
- [x] Add `migrate_merchant_mapping_schema()` to `db/database.py`
- [x] Add merchant mapping methods to `services/category_service.py`:
  - `add_merchant_mapping()`, `remove_merchant_mapping()`, `get_all_merchant_mappings()`
  - `normalize_by_merchant()` - lookup category by description pattern
  - `bulk_set_category_with_mapping()` - set category AND save mapping
- [x] Update `services/credit_card_service.py` to apply merchant mappings during sync
- [x] Add CLI commands: `suggest`, `assign`, `assign-wizard`, `merchants`, `remove-merchant`
- [x] Add "By Merchant" tab to Streamlit Categories page
- [x] Update maintenance `migrate` command to include merchant mapping migration

---

a## Handling Provider Category Changes

Providers may rename their categories over time (e.g., CAL renames "food" to "nourishment"). This system handles it gracefully:

### Scenario: Provider Renames a Category

1. **Old transactions**: Already have `raw_category="food"` and `category="groceries"` (via existing mapping)
2. **New transactions**: Come in with `raw_category="nourishment"` → detected as **unmapped**
3. **User action**: Add new mapping `("cal", "nourishment") → "groceries"`
4. **Result**: Both old and new transactions now have same unified category

### CLI Workflow

```bash
# After sync, you see:
# ⚠ 1 unmapped category detected:
#   - "nourishment" (5 transactions)

# Check if it's a rename of existing category
fin-cli categories list --provider cal
# Output shows: "food" → groceries (142 transactions)

# Map the new name to same unified category
fin-cli categories map cal "nourishment" groceries

# Optional: Keep old mapping for historical transactions
# (or remove if provider fully deprecated old name)
fin-cli categories unmap cal "food"  # Only if no longer used
```

### Streamlit Workflow

In the **Unmapped** tab:
1. See new category "nourishment" flagged
2. System suggests "groceries" if similar mappings exist for this provider
3. One-click to accept suggestion or pick different unified category

### Design Decisions

- **Keep old mappings**: Old `raw_category` values may still exist in historical transactions
- **Multiple raw → one unified**: Many raw categories can map to same unified (this is the point)
- **No automatic detection**: Provider renames are manual to review (avoids wrong auto-mapping)

---

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| New transaction, no mapping exists | `category` = None, `raw_category` = provider value |
| Mapping added after transactions exist | Run `fin-cli categories apply` to backfill |
| Provider adds new category | Detected as "unmapped" in post-sync report |
| Provider renames category | New name appears as unmapped, map to same unified category |
| User sets `user_category` | Takes precedence over normalized `category` |
| Mapping deleted | Existing transactions keep their `category` value |
| Unified category renamed | All mappings updated, run `apply` to update transactions |
| Empty raw_category from provider | Skip normalization, `category` stays None |
| Same raw_category, different providers | Each provider has its own mapping (provider+raw is unique key) |

---

## Summary

| Component | New Files | Modified Files |
|-----------|-----------|----------------|
| Database | - | 3 (models.py, database.py, add_indexes.py) |
| Services | 1 (category_service.py) | 3 (credit_card, analytics, tag) |
| CLI | 1 (categories.py) | 5 (main, transactions, export, sync, browser) |
| Streamlit | 3 (page + 2 components) | 6 (dashboard, transactions, tags, filters, cache, session) |
| Other | - | 2 (example, constants) |
| **Total** | **5 new files** | **19 modified files** |

---

## Relationship to NLP Categorization Plan

This plan (Category Normalization) and the NLP Categorization Plan serve different purposes:

| Aspect | Category Normalization (this plan) | NLP Categorization |
|--------|-----------------------------------|-------------------|
| Purpose | Unify provider categories | Auto-categorize uncategorized transactions |
| Input | Provider's raw category | Transaction description |
| Output | Normalized category name | Suggested category/rule |
| Mapping | Manual (user creates) | Automatic (ML model) |
| When | During sync | On-demand analysis |

These features complement each other:
1. **Normalization** ensures consistent category names across providers
2. **NLP** helps categorize transactions that have no category from the provider

The NLP feature should use `unified_category` names when making suggestions.