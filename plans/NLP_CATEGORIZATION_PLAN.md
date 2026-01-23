# NLP-Based Auto-Categorization Plan

## Overview

Implement an NLP-based system that analyzes uncategorized transactions, finds patterns, and suggests categorization rules that users can accept or decline.

**Status**: 🔄 Planned (Lower Priority)

**Prerequisite**: Category Normalization must be implemented first (see `CATEGORY_NORMALIZATION_PLAN.md`). NLP suggestions will use unified category names.

**Note**: The **Merchant Mapping** feature (implemented in Category Normalization Phase 6) addresses the primary use case of categorizing transactions without provider categories (e.g., Isracard). The NLP feature would add:
- Automatic pattern detection (vs manual merchant assignment)
- Similarity-based suggestions (learning from categorized transactions)
- Handling edge cases where merchant names vary

---

## Python Principles

- **DRY**: Extract duplicated logic into reusable functions
- **KISS**: Prefer straightforward solutions over clever ones
- **SIMPLE**: Minimal code to solve the actual problem, no speculative features
- Avoid premature abstraction - three similar lines beats a premature helper

---

## Goals

1. Reduce manual categorization effort
2. Learn from user's existing categorized transactions
3. Output rule suggestions (not auto-apply)
4. User reviews and accepts/declines suggestions
5. Accepted suggestions become rules via existing `RulesService`

## Approach: TF-IDF Similarity

### Why TF-IDF (Not Embeddings)

| Factor | TF-IDF | Embeddings |
|--------|--------|------------|
| Dependencies | `scikit-learn` (small) | `sentence-transformers` + `torch` (~500MB) |
| Speed | <1ms per transaction | ~5-10ms per transaction |
| Israeli merchants | Learns from your data | Pre-trained knowledge limited |
| Complexity | Simple | More complex |
| Good enough? | Yes, for merchant name matching | Overkill for this use case |

**Decision**: Start with TF-IDF. Can upgrade to embeddings later if needed.

### How TF-IDF Works

1. **Term Frequency (TF)**: How often a word appears in a description
2. **Inverse Document Frequency (IDF)**: How rare/common a word is across all descriptions
3. **TF-IDF = TF × IDF**: Words unique to certain descriptions get high scores

This identifies "signature" words for each category (e.g., "WOLT" → Food).

### Limitations

- No semantic understanding ("Uber" vs "Gett" won't match automatically)
- Learns only from your categorized transactions
- Works best when same merchant appears multiple times

## Architecture

### Data Flow

```
1. Collect categorized transactions (training data)
                ↓
2. Build TF-IDF model from descriptions
                ↓
3. Find uncategorized transactions
                ↓
4. Group by merchant pattern (extract common prefixes)
                ↓
5. For each group: find most similar category
                ↓
6. Output suggestions with confidence scores
                ↓
7. User accepts/declines → creates rules via RulesService
```

### New Files

| File | Purpose |
|------|---------|
| `services/categorization_service.py` | Core logic: pattern detection, similarity, suggestions |
| `cli/commands/categorize.py` | CLI commands: suggest, review, accept |
| `streamlit_app/pages/9_🤖_Categorize.py` | Streamlit UI for suggestions |

### Modified Files

| File | Changes |
|------|---------|
| `requirements.txt` | Add `scikit-learn>=1.0.0` |
| `streamlit_app/utils/session.py` | Add `get_categorization_service()` |

## Service Layer

### Data Classes

```python
@dataclass
class RuleSuggestion:
    pattern: str                    # e.g., "WOLT"
    suggested_category: str         # e.g., "Food & Dining"
    confidence: float               # 0.0 - 1.0
    matching_transactions: int      # How many uncategorized would match
    example_descriptions: List[str] # Examples of matching uncategorized
    similar_categorized: List[str]  # Examples of similar categorized ones
    is_new_category: bool           # True if no good match found
```

### CategorizationService

```python
class CategorizationService:
    def __init__(self, session: Session):
        self.session = session
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),  # Unigrams and bigrams
            max_features=5000
        )
        self._model_built = False
        self._category_vectors = {}  # category -> mean TF-IDF vector

    def build_model(self) -> dict:
        """
        Build TF-IDF model from categorized transactions.

        Returns:
            {
                "transaction_count": int,
                "category_count": int,
                "categories": List[str]
            }
        """
        pass

    def extract_merchant_pattern(self, description: str) -> str:
        """
        Extract merchant name from description.

        Heuristics:
        - First 1-2 words (before location/date)
        - Remove common suffixes (TLV, ONLINE, etc.)
        - Handle Hebrew text

        Examples:
        - "WOLT TLV 123456" → "WOLT"
        - "PANGO PARKING TEL AVIV" → "PANGO"
        - "סופר יודה רמת גן" → "סופר יודה"
        """
        pass

    def find_uncategorized_patterns(self) -> Dict[str, List[Transaction]]:
        """
        Group uncategorized transactions by merchant pattern.

        Returns:
            {"WOLT": [txn1, txn2, ...], "PANGO": [txn3, ...]}
        """
        pass

    def suggest_category(
        self,
        descriptions: List[str],
        min_confidence: float = 0.3
    ) -> Tuple[Optional[str], float, List[str]]:
        """
        Find most similar category for given descriptions.

        Args:
            descriptions: List of transaction descriptions
            min_confidence: Minimum confidence to return a category

        Returns:
            (category or None, confidence, list of similar descriptions)
        """
        pass

    def generate_suggestions(
        self,
        min_confidence: float = 0.3,
        min_transactions: int = 2
    ) -> List[RuleSuggestion]:
        """
        Main method: generate all rule suggestions.

        Args:
            min_confidence: Minimum confidence to include suggestion
            min_transactions: Minimum uncategorized transactions to suggest

        Returns:
            List of RuleSuggestion sorted by matching_transactions desc
        """
        pass

    def get_existing_categories(self) -> List[str]:
        """Get list of all categories currently in use."""
        pass

    def get_stats(self) -> dict:
        """
        Get categorization statistics.

        Returns:
            {
                "categorized_count": int,
                "uncategorized_count": int,
                "category_count": int,
                "top_categories": [(name, count), ...]
            }
        """
        pass
```

## CLI Interface

### Commands

```bash
# Show current stats
fin-cli categorize stats

# Output:
# Categorization Status
# ─────────────────────
# Categorized:    245 transactions
# Uncategorized:   38 transactions
# Categories:      12 learned
#
# Top categories:
#   Food & Dining     87 transactions
#   Transportation    45 transactions
#   Groceries         32 transactions

# Generate and show suggestions
fin-cli categorize suggest [--min-confidence 0.5] [--min-transactions 2]

# Output:
# Building model from 245 categorized transactions...
# Found 4 rule suggestions:
#
# [1] Pattern: "WOLT"
#     Category: Food & Dining (87% confidence)
#     Based on: "WOLT TLV", "WOLT HAIFA" (23 similar)
#     Would apply to: 12 uncategorized transactions
#
# [2] Pattern: "PANGO"
#     Category: Transportation (72% confidence)
#     Based on: "PANGO PARKING TLV" (15 similar)
#     Would apply to: 8 uncategorized transactions
#
# [3] Pattern: "AM:PM"
#     ⚠️  No good match (34% best: Groceries)
#     Suggest new category or skip
#     Would apply to: 5 uncategorized transactions
#
# [4] Pattern: "סופר יודה"
#     Category: Groceries (91% confidence)
#     Based on: "שופרסל", "רמי לוי" (18 similar)
#     Would apply to: 3 uncategorized transactions
#
# Commands:
#   fin-cli categorize accept 1 2 4
#   fin-cli categorize accept --all
#   fin-cli categorize review

# Accept specific suggestions (creates rules)
fin-cli categorize accept 1 2 4

# Output:
# Created 3 rules:
#   ✓ "WOLT" → Food & Dining
#   ✓ "PANGO" → Transportation
#   ✓ "סופר יודה" → Groceries
#
# Run 'fin-cli rules apply' to apply to existing transactions.

# Accept all suggestions
fin-cli categorize accept --all

# Interactive review (one by one)
fin-cli categorize review

# Output:
# [1/4] Pattern: "WOLT"
#       Suggested: Food & Dining (87%)
#       Matching transactions: 12
#
#       (a)ccept / (d)ecline / (e)dit category / (s)kip: a
#       ✓ Created rule: "WOLT" → Food & Dining
#
# [2/4] Pattern: "PANGO"
#       Suggested: Transportation (72%)
#       Matching transactions: 8
#
#       (a)ccept / (d)ecline / (e)dit category / (s)kip: e
#       Enter category: Parking
#       ✓ Created rule: "PANGO" → Parking
#
# [3/4] Pattern: "AM:PM"
#       ⚠️  No good match found (34% best: Groceries)
#
#       (c)reate new category / (a)ssign existing / (s)kip: c
#       Enter new category name: Convenience Store
#       ✓ Created rule: "AM:PM" → Convenience Store
#
# Summary:
#   Created: 3 rules
#   Skipped: 1 suggestions
```

## Streamlit UI

### Page Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  🤖 Auto-Categorize                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Categorized  │  │ Uncategorized│  │ Categories   │          │
│  │     245      │  │      38      │  │      12      │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                 │
│  [🔍 Generate Suggestions]                                      │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 4 Suggestions Found               [Accept All] [Clear]   │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │                                                          │   │
│  │  ☑️  WOLT                                        87% 🟢  │   │
│  │      → Food & Dining                                     │   │
│  │      12 transactions • Similar: "WOLT TLV", "WOLT HAIFA" │   │
│  │      [Accept] [Change Category ▼] [Decline]              │   │
│  │  ─────────────────────────────────────────────────────── │   │
│  │  ☑️  PANGO                                       72% 🟡  │   │
│  │      → Transportation                                    │   │
│  │      8 transactions • Similar: "PANGO PARKING"           │   │
│  │      [Accept] [Change Category ▼] [Decline]              │   │
│  │  ─────────────────────────────────────────────────────── │   │
│  │  ⚠️  AM:PM                                       34% 🔴  │   │
│  │      → No good match found                               │   │
│  │      5 transactions                                      │   │
│  │      New category: [Convenience Store    ] [Create] [Skip]│   │
│  │  ─────────────────────────────────────────────────────── │   │
│  │  ☑️  סופר יודה                                   91% 🟢  │   │
│  │      → Groceries                                         │   │
│  │      3 transactions • Similar: "שופרסל", "רמי לוי"       │   │
│  │      [Accept] [Change Category ▼] [Decline]              │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 📋 Rules to Create (3)                                   │   │
│  │                                                          │   │
│  │   • "WOLT" → Food & Dining (12 transactions)             │   │
│  │   • "PANGO" → Transportation (8 transactions)            │   │
│  │   • "סופר יודה" → Groceries (3 transactions)             │   │
│  │                                                          │   │
│  │ [✓ Create 3 Rules]                 Total: 23 transactions│   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### UI Components

| Component | Description |
|-----------|-------------|
| **Stats row** | Three metric cards showing categorized/uncategorized/categories |
| **Generate button** | Triggers suggestion generation, shows spinner |
| **Suggestion cards** | Expandable cards with confidence badge, examples, actions |
| **Confidence badge** | 🟢 >70%, 🟡 50-70%, 🔴 <50% |
| **Category dropdown** | Change suggested category to existing one |
| **New category input** | For low-confidence suggestions |
| **Preview panel** | Shows rules that will be created |
| **Create button** | Creates rules via RulesService |

### Session State

```python
# streamlit_app/pages/9_🤖_Categorize.py

if "categorize_suggestions" not in st.session_state:
    st.session_state.categorize_suggestions = []

if "categorize_accepted" not in st.session_state:
    st.session_state.categorize_accepted = set()  # indices of accepted suggestions

if "categorize_declined" not in st.session_state:
    st.session_state.categorize_declined = set()

if "categorize_overrides" not in st.session_state:
    st.session_state.categorize_overrides = {}  # index -> new category name
```

### Integration Points

**Transactions page nudge** (optional enhancement):

```python
# In streamlit_app/pages/3_💳_Transactions.py

uncategorized_count = get_uncategorized_count()
if uncategorized_count > 0:
    st.info(f"💡 {uncategorized_count} uncategorized transactions. [Auto-categorize →](/Categorize)")
```

## UX/User-Friendliness Guidelines

### Guiding Principles

1. **Suggestions, not automation** - User always reviews before rules are created
2. **Transparency** - Show why a suggestion was made (similar transactions)
3. **Confidence clarity** - Visual indicators make confidence obvious at a glance
4. **Batch efficiency** - Handle multiple suggestions without repetitive clicks
5. **Non-destructive** - Easy to undo, rules can be deleted later

### Suggestion Cards Design

**Problem**: User needs to quickly evaluate if a suggestion is correct.

**Solution**: Show evidence, not just the suggestion

```
┌─────────────────────────────────────────────────────────────────┐
│  🟢 High Confidence (87%)                                       │
│                                                                 │
│  Pattern: "WOLT"                                                │
│  Suggested category: restaurants                                │
│                                                                 │
│  ┌─ Why this suggestion? ─────────────────────────────────────┐ │
│  │ Similar to your categorized transactions:                  │ │
│  │   • "WOLT TLV" → restaurants (Jan 15)                      │ │
│  │   • "WOLT HAIFA" → restaurants (Jan 12)                    │ │
│  │   • "WOLT TEL AVIV" → restaurants (Jan 8)                  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Will categorize 12 transactions:                               │
│    "WOLT RAANANA", "WOLT HERZLIYA", "WOLT NETANYA"...          │
│                                                                 │
│  [✓ Accept]  [Change Category ▼]  [✗ Decline]                   │
└─────────────────────────────────────────────────────────────────┘
```

**Key UX elements**:
- Confidence badge with color (🟢 >70%, 🟡 50-70%, 🔴 <50%)
- "Why" section shows learning evidence
- Preview of affected transactions
- Three clear actions: accept, modify, decline

### Low Confidence Handling

**Problem**: Low confidence suggestions might be wrong - don't want user to blindly accept.

**Solution**: Different UI treatment for uncertain suggestions

```
┌─────────────────────────────────────────────────────────────────┐
│  🔴 Low Confidence (34%)                                        │
│                                                                 │
│  Pattern: "AM:PM"                                               │
│  Best guess: groceries (but not sure)                           │
│                                                                 │
│  ⚠️ This pattern doesn't closely match any of your existing     │
│     categorized transactions.                                   │
│                                                                 │
│  Options:                                                       │
│  ○ Use suggested: groceries                                     │
│  ○ Choose different: [Select category ▼]                        │
│  ○ Create new category: [convenience_store    ]                 │
│  ○ Skip for now                                                 │
│                                                                 │
│  [Apply Choice]                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Batch Operations

**Problem**: 20 suggestions = 20 individual decisions = tedious.

**Solution**: Smart batch actions

```
┌─────────────────────────────────────────────────────────────────┐
│  20 Suggestions Found                                           │
│                                                                 │
│  Quick Actions:                                                 │
│  [Accept All High Confidence (12)] - 87%+ confidence            │
│  [Accept All (18)]                 - Excludes 2 low confidence  │
│                                                                 │
│  Or review individually below...                                │
└─────────────────────────────────────────────────────────────────┘
```

### Preview Before Commit

**Problem**: User wants to see full impact before creating rules.

**Solution**: Confirmation panel with summary

```
┌─────────────────────────────────────────────────────────────────┐
│  📋 Ready to Create 5 Rules                                     │
│                                                                 │
│  Pattern          │ Category       │ Transactions               │
│  ─────────────────┼────────────────┼────────────────────────────│
│  WOLT             │ restaurants    │ 12                         │
│  PANGO            │ transportation │ 8                          │
│  סופר יודה         │ groceries      │ 6                          │
│  AM:PM            │ convenience    │ 5                          │
│  גט טקסי           │ transportation │ 4                          │
│                                                                 │
│  Total: 35 transactions will be categorized                     │
│                                                                 │
│  [← Back to Edit]              [✓ Create 5 Rules]               │
└─────────────────────────────────────────────────────────────────┘
```

### Transactions Page Nudge

**Problem**: User might not know this feature exists.

**Solution**: Contextual, dismissible nudge

```
┌────────────────────────────────────────────────────────────────┐
│ 💡 38 transactions don't have categories yet.                  │
│    [Auto-suggest categories →]                    [Don't show] │
└────────────────────────────────────────────────────────────────┘
```

- Only shows if uncategorized count > threshold (e.g., 10)
- "Don't show" respects user preference (session/permanent)
- Links directly to categorization page

### CLI User Experience

```bash
$ fin-cli categorize suggest

Building model from 245 categorized transactions... done

┌──────────────────────────────────────────────────────────────────┐
│  4 Suggestions Found                                             │
│                                                                  │
│  #  │ Pattern    │ Category       │ Conf │ Txns │ Similar to     │
│  ───┼────────────┼────────────────┼──────┼──────┼────────────────│
│  1  │ WOLT       │ restaurants    │ 87%  │ 12   │ WOLT TLV       │
│  2  │ PANGO      │ transportation │ 72%  │ 8    │ PANGO PARKING  │
│  3  │ AM:PM      │ ⚠️ groceries?  │ 34%  │ 5    │ (low match)    │
│  4  │ סופר יודה   │ groceries      │ 91%  │ 3    │ שופרסל         │
└──────────────────────────────────────────────────────────────────┘

Quick commands:
  fin-cli categorize accept 1 2 4     # Accept specific suggestions
  fin-cli categorize accept --high    # Accept all high confidence (>70%)
  fin-cli categorize review           # Interactive one-by-one review
```

### Error Prevention & Recovery

| Situation | UX Solution |
|-----------|-------------|
| Accepted wrong suggestion | Rules page shows recently created rules with "Undo" |
| Want to re-run after changes | "Refresh Suggestions" button (re-analyzes) |
| Model seems wrong | "Reset & Rebuild Model" in settings |
| Created rule but transactions not updated | Auto-prompt: "Apply rules to existing transactions?" |

### Accessibility

- Keyboard shortcuts: `a` accept, `d` decline, `n` next suggestion
- Screen reader labels for confidence badges
- High contrast mode support
- RTL support for Hebrew merchant names and categories

---

## Edge Cases

| Case | Handling |
|------|----------|
| No categorized transactions | Show message: "Need at least 5 categorized transactions to learn patterns" |
| No uncategorized transactions | Show success message: "All transactions categorized!" |
| Very low confidence (<30%) | Mark as "New category needed", don't pre-select category |
| Pattern already has a rule | Skip, don't suggest duplicate rules |
| Hebrew + English mixed | TF-IDF handles both, tokenizes by whitespace |
| Single transaction for pattern | Skip by default (configurable via `min_transactions`) |

## Implementation Checklist

### Phase 1: Service Layer
- [ ] Add `scikit-learn` to requirements.txt
- [ ] Create `services/categorization_service.py`
- [ ] Implement `build_model()` with TF-IDF
- [ ] Implement `extract_merchant_pattern()`
- [ ] Implement `find_uncategorized_patterns()`
- [ ] Implement `suggest_category()`
- [ ] Implement `generate_suggestions()`
- [ ] Implement `get_stats()`
- [ ] Unit tests for service

### Phase 2: CLI
- [ ] Create `cli/commands/categorize.py`
- [ ] Implement `stats` command
- [ ] Implement `suggest` command
- [ ] Implement `accept` command
- [ ] Implement `review` command (interactive)
- [ ] Register commands in `cli/main.py`

### Phase 3: Streamlit UI
- [ ] Create `streamlit_app/pages/9_🤖_Categorize.py`
- [ ] Add `get_categorization_service()` to session utils
- [ ] Implement stats cards
- [ ] Implement suggestion generation
- [ ] Implement suggestion cards with actions
- [ ] Implement preview panel
- [ ] Implement rule creation
- [ ] Add cache invalidation after rule creation

### Phase 4: Polish
- [ ] Add nudge to Transactions page
- [ ] Add to navigation/sidebar
- [ ] Test with real data
- [ ] Handle RTL text display

## Future Enhancements

### Upgrade to Embeddings (If Needed)

If TF-IDF doesn't catch enough patterns, swap vectorizer:

```python
# Before (TF-IDF)
from sklearn.feature_extraction.text import TfidfVectorizer
self.vectorizer = TfidfVectorizer()
vectors = self.vectorizer.fit_transform(descriptions)

# After (Embeddings)
from sentence_transformers import SentenceTransformer
self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
vectors = self.model.encode(descriptions)
```

Same API, same flow, just different vectorization.

### Tag Suggestions

Same approach can suggest tags:
- Build model from tagged transactions
- Suggest tags for untagged transactions
- Lower priority than categories

### Learning from Corrections

When user edits a category:
- Store correction
- Weight corrections higher in model
- Improve over time

## Dependencies

```
# requirements.txt additions
scikit-learn>=1.0.0
```

No other new dependencies required.

## Integration with Category Normalization

**Important**: This NLP feature must use **unified categories** from the Category Normalization system (see `CATEGORY_NORMALIZATION_PLAN.md`).

### Key Integration Points

1. **Suggestions use unified categories**: When suggesting a category, use the normalized `unified_category` names (e.g., "groceries") not raw provider categories (e.g., "סופרמרקט")

2. **Training data**: Build model from transactions using `effective_category` which returns the normalized category

3. **New category suggestions**: If NLP suggests a new category that doesn't exist in `UnifiedCategory`, prompt user to either:
   - Map it to an existing unified category
   - Create a new unified category (updates `config/constants.py`)

4. **Rules created**: When user accepts an NLP suggestion, the rule sets `user_category` to a unified category name

### Code Example

```python
# In CategorizationService.suggest_category()
def get_existing_categories(self) -> List[str]:
    """Get unified categories, not raw provider categories."""
    from config.constants import UnifiedCategory

    # Return standard unified categories
    return UnifiedCategory.all()

def generate_suggestions(self, ...):
    # When suggesting, match against unified categories only
    unified_cats = self.get_existing_categories()

    for pattern, transactions in uncategorized_patterns.items():
        suggested, confidence, similar = self.suggest_category(
            descriptions=[t.description for t in transactions],
            valid_categories=unified_cats  # Only suggest from unified list
        )
```

### User Flow

```
NLP suggests: "WOLT" → "restaurants" (unified category)
                        ↓
User accepts → Creates rule: pattern="WOLT", user_category="restaurants"
                        ↓
Rule applies → Transaction.user_category = "restaurants"
                        ↓
effective_category returns "restaurants" (unified, consistent across providers)
```

## References

- Existing `RulesService`: `services/rules_service.py`
- Existing `TagService`: `services/tag_service.py`
- Transaction model: `db/models.py`
- Streamlit patterns: `streamlit_app/pages/6_📋_Rules.py`
- **Category Normalization**: `plans/CATEGORY_NORMALIZATION_PLAN.md`