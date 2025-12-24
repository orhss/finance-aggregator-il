# Transaction Tagging & Editing System - Design Document

## Overview

Add a flexible tagging system to transactions and enable editing of transaction category. Tags provide user-defined organization beyond source-provided categories, with full CLI integration for filtering, reporting, and analytics.

## Design Principles

1. **DRY** - Reuse existing service patterns and CLI structures
2. **Simple** - Minimal new abstractions, single-file TUI
3. **Non-destructive** - Original category preserved, user edits are separate fields

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Layer                                │
│  fin-cli transactions browse/tag/untag/edit                      │
│  fin-cli tags list/rename/delete                                │
│  fin-cli reports tags                                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                      Service Layer                               │
│  TagService (NEW)              AnalyticsService (EXTEND)        │
│  - tag_transaction()           - get_tag_breakdown()            │
│  - untag_transaction()         - get_transactions() + tag filter│
│  - update_transaction()                                          │
│  - get_tags() / rename / delete                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                     Database Layer                               │
│  Transaction (MODIFY)   Tag (NEW)        TransactionTag (NEW)   │
│  + user_category        - id             - transaction_id (FK)  │
│                         - name (unique)  - tag_id (FK)          │
│                         - created_at                             │
└─────────────────────────────────────────────────────────────────┘
```

## Database Schema

### New Tables

```sql
-- Tags table
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Transaction-Tag junction table (many-to-many)
CREATE TABLE transaction_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
    UNIQUE(transaction_id, tag_id)
);

CREATE INDEX idx_transaction_tags_transaction ON transaction_tags(transaction_id);
CREATE INDEX idx_transaction_tags_tag ON transaction_tags(tag_id);
```

### Transaction Table Modifications

```sql
ALTER TABLE transactions ADD COLUMN user_category VARCHAR(100);
```

**Field Strategy:**
- `category` - Original from source (CAL, etc.) - never modified
- `user_category` - User's override - editable
- `memo` - Original from source - read-only

**Display Logic:** Show `user_category` if set, otherwise `category`.

### SQLAlchemy Models

```python
# db/models.py (additions)

class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    transaction_tags = relationship("TransactionTag", back_populates="tag", cascade="all, delete-orphan")


class TransactionTag(Base):
    __tablename__ = "transaction_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey('transactions.id', ondelete='CASCADE'), nullable=False)
    tag_id = Column(Integer, ForeignKey('tags.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    transaction = relationship("Transaction", back_populates="transaction_tags")
    tag = relationship("Tag", back_populates="transaction_tags")

    __table_args__ = (
        UniqueConstraint('transaction_id', 'tag_id', name='uq_transaction_tag'),
    )


# Update Transaction model
class Transaction(Base):
    # ... existing fields ...

    user_category = Column(String(100), nullable=True)
    transaction_tags = relationship("TransactionTag", back_populates="transaction", cascade="all, delete-orphan")

    @property
    def tags(self) -> List[str]:
        return [tt.tag.name for tt in self.transaction_tags]

    @property
    def effective_category(self) -> Optional[str]:
        return self.user_category or self.category
```

## Service Layer

### TagService (New File: `services/tag_service.py`)

```python
class TagService:
    """Service for tags and transaction editing"""

    def __init__(self, session: Optional[Session] = None):
        self.session = session or next(get_db())

    # Tag CRUD
    def get_or_create_tag(self, name: str) -> Tag
    def get_all_tags(self) -> List[Tag]
    def rename_tag(self, old_name: str, new_name: str) -> bool
    def delete_tag(self, name: str) -> bool

    # Transaction tagging
    def tag_transaction(self, transaction_id: int, tag_names: List[str]) -> int
    def untag_transaction(self, transaction_id: int, tag_names: List[str]) -> int
    def bulk_tag_by_merchant(self, merchant_pattern: str, tag_names: List[str]) -> int
    def bulk_tag_by_category(self, category: str, tag_names: List[str]) -> int

    # Transaction editing
    def update_transaction(self, transaction_id: int, user_category: str = None) -> bool

    # Stats
    def get_tag_stats(self) -> List[Dict]  # [{name, count, total_amount}, ...]
    def get_untagged_count(self) -> int

    # Migration
    def migrate_categories_to_tags(self) -> Dict[str, int]
```

### AnalyticsService Extensions

```python
# services/analytics_service.py (additions)

def get_transactions(
    self,
    # ... existing params ...
    tags: Optional[List[str]] = None,  # Filter by tags (AND logic)
    untagged_only: bool = False,
) -> List[Transaction]

def get_tag_breakdown(
    self,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> Dict[str, Dict[str, Any]]
# Returns: {tag_name: {count, total_amount, percentage}, ...}
```

## CLI Commands

### Interactive Transaction Browser

```bash
fin-cli transactions browse
fin-cli transactions browse --from 2025-01-01
fin-cli transactions browse --tag groceries
fin-cli transactions browse --untagged
```

#### Browser UI

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Transaction Browser                                    [?] Help  [q] Quit  │
├─────────────────────────────────────────────────────────────────────────────┤
│  Filter: _______________                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ► 2025-12-20  רמי לוי - קניון הזהב              -245.90 ₪   [groceries]   │
│    2025-12-19  wolt - מסעדת שמש                  -89.00 ₪    [dining-out]  │
│    2025-12-18  סונול - תחנת דלק                  -250.00 ₪   [fuel]        │
│    2025-12-17  Netflix                           -49.90 ₪    (untagged)    │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  [Enter] Edit  [t] Tag  [/] Search  [↑↓] Navigate  [q] Quit                │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Keyboard Controls

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate |
| `Enter` | Edit selected transaction |
| `t` | Add tag to selected |
| `/` | Focus search |
| `q` | Quit |

#### Edit Panel (Press Enter)

```
┌────────────────────────────────────────────────────────────────┐
│  Edit Transaction                                    [Esc] Back │
├────────────────────────────────────────────────────────────────┤
│  Date:        2025-12-20                                       │
│  Description: רמי לוי - קניון הזהב                             │
│  Amount:      -245.90 ILS                                      │
│  Category:    סופרמרקט                                         │
│                                                                │
│  User Category: [groceries___________]                         │
│  Tags:          [groceries] [x]  [+Add]                        │
│                                                                │
│                        [Save]  [Cancel]                        │
└────────────────────────────────────────────────────────────────┘
```

### Direct CLI Commands (for scripting)

```bash
# Edit transaction
fin-cli transactions edit <id> --category "groceries"
fin-cli transactions edit --merchant "רמי לוי" --category "groceries"

# Tag transactions
fin-cli transactions tag <id> groceries weekly-shop
fin-cli transactions untag <id> dining-out
fin-cli transactions tag --merchant "רמי לוי" groceries
fin-cli transactions tag --category "מסעדות" dining-out

# List with tag filter
fin-cli transactions list --tag groceries
fin-cli transactions list --untagged
```

### Tag Management

```bash
fin-cli tags list                    # List all tags with counts
fin-cli tags rename "food" "dining"  # Rename (merges if exists)
fin-cli tags delete old-tag          # Delete tag
fin-cli tags migrate                 # Auto-tag from categories
```

### Reports

```bash
fin-cli reports tags                         # Tag breakdown
fin-cli reports tags --from 2025-01-01
fin-cli reports monthly --group-by tags      # Monthly by tag
```

## Example Output

### Tag List
```
┌──────────────────────────────────────────────────────┐
│                      Tags                             │
├──────────────────┬───────┬───────────────────────────┤
│ Tag              │ Count │ Total Amount              │
├──────────────────┼───────┼───────────────────────────┤
│ groceries        │ 145   │ ₪12,450.00                │
│ dining-out       │ 89    │ ₪4,230.00                 │
│ fuel             │ 34    │ ₪2,100.00                 │
├──────────────────┼───────┼───────────────────────────┤
│ (untagged)       │ 45    │ ₪3,200.00                 │
└──────────────────┴───────┴───────────────────────────┘
```

### Tag Breakdown Report
```
┌─────────────────────────────────────────────────────────────────┐
│              Spending by Tag - Dec 2025                          │
├──────────────────┬────────────┬────────────┬────────────────────┤
│ Tag              │ Amount     │ % of Total │ Count              │
├──────────────────┼────────────┼────────────┼────────────────────┤
│ groceries        │ ₪2,450     │ 35.2%      │ 28                 │
│ dining-out       │ ₪1,200     │ 17.3%      │ 15                 │
│ fuel             │ ₪600       │ 8.6%       │ 4                  │
│ (untagged)       │ ₪1,060     │ 15.3%      │ 12                 │
├──────────────────┼────────────┼────────────┼────────────────────┤
│ TOTAL            │ ₪6,950     │ 100%       │ 73                 │
└──────────────────┴────────────┴────────────┴────────────────────┘
```

## Migration

### Database Migration (Idempotent)

```python
def migrate_database(engine):
    """Add tag tables and transaction columns. Safe to run multiple times."""
    with engine.connect() as conn:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        # Add columns to transactions
        if 'transactions' in existing_tables:
            cols = {c['name'] for c in inspector.get_columns('transactions')}
            if 'user_category' not in cols:
                conn.execute(text("ALTER TABLE transactions ADD COLUMN user_category VARCHAR(100)"))

        # Create tags table
        if 'tags' not in existing_tables:
            conn.execute(text("""
                CREATE TABLE tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

        # Create transaction_tags table
        if 'transaction_tags' not in existing_tables:
            conn.execute(text("""
                CREATE TABLE transaction_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
                    UNIQUE(transaction_id, tag_id)
                )
            """))
            conn.execute(text("CREATE INDEX idx_transaction_tags_transaction ON transaction_tags(transaction_id)"))
            conn.execute(text("CREATE INDEX idx_transaction_tags_tag ON transaction_tags(tag_id)"))

        conn.commit()
```

### Migrate Existing Categories

```bash
fin-cli tags migrate              # Auto-tag from existing categories
fin-cli tags migrate --dry-run    # Preview
```

## TUI Implementation

### Single File: `cli/tui/browser.py`

Uses Textual framework (add `textual>=0.45.0` to requirements.txt).

```python
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Header, Footer, Input, Static, Button
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen

class TransactionBrowser(App):
    """Interactive transaction browser"""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("t", "tag", "Tag"),
        ("enter", "edit", "Edit"),
        ("/", "search", "Search"),
    ]

    def __init__(self, filters: dict = None):
        super().__init__()
        self.filters = filters or {}

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="Search...", id="search")
        yield DataTable(id="transactions")
        yield Footer()

    def on_mount(self):
        self.load_transactions()

    def load_transactions(self):
        table = self.query_one("#transactions", DataTable)
        table.clear()
        table.add_columns("Date", "Description", "Amount", "Tags")
        # Load from AnalyticsService with self.filters
        ...

    def action_edit(self):
        row_key = self.query_one("#transactions").cursor_row
        self.push_screen(EditScreen(transaction_id=row_key))

    def action_tag(self):
        row_key = self.query_one("#transactions").cursor_row
        self.push_screen(TagScreen(transaction_id=row_key))


class EditScreen(ModalScreen):
    """Edit transaction modal"""

    def __init__(self, transaction_id: int):
        super().__init__()
        self.transaction_id = transaction_id

    def compose(self) -> ComposeResult:
        yield Container(
            Static("Edit Transaction", classes="title"),
            Input(placeholder="User category", id="category"),
            Horizontal(
                Button("Save", variant="primary", id="save"),
                Button("Cancel", id="cancel"),
            ),
        )

    def on_button_pressed(self, event):
        if event.button.id == "save":
            # Save via TagService
            self.dismiss(True)
        else:
            self.dismiss(False)


class TagScreen(ModalScreen):
    """Add tag modal"""

    def compose(self) -> ComposeResult:
        yield Container(
            Static("Add Tag"),
            Input(placeholder="Tag name", id="tag"),
            Horizontal(
                Button("Add", variant="primary", id="add"),
                Button("Cancel", id="cancel"),
            ),
        )
```

## File Changes Summary

| File | Action | Changes |
|------|--------|---------|
| `requirements.txt` | Modify | Add `textual>=0.45.0` |
| `db/models.py` | Modify | Add `Tag`, `TransactionTag`; update `Transaction` |
| `db/database.py` | Modify | Add migration function |
| `services/tag_service.py` | Create | Tag operations + transaction editing |
| `services/analytics_service.py` | Modify | Add tag filtering and breakdown |
| `cli/commands/tags.py` | Create | `list`, `rename`, `delete`, `migrate` |
| `cli/commands/transactions.py` | Modify | Add `browse`, `tag`, `untag`, `edit` |
| `cli/commands/reports.py` | Modify | Add `tags` report, `--group-by` option |
| `cli/main.py` | Modify | Register tags command group |
| `cli/tui/browser.py` | Create | Single-file TUI browser |

## Implementation Plan

### Phase 1: Database Layer ✅ COMPLETE
**Goal:** Schema changes and models ready

| Task | File | Description | Status |
|------|------|-------------|--------|
| 1.1 | `db/models.py` | Add `Tag` model | ✅ |
| 1.2 | `db/models.py` | Add `TransactionTag` model | ✅ |
| 1.3 | `db/models.py` | Add `user_category` to `Transaction` | ✅ |
| 1.4 | `db/models.py` | Add `tags`, `effective_category` properties | ✅ |
| 1.5 | `db/database.py` | Add `migrate_tags_schema()` function | ✅ |
| 1.6 | - | Test: Run migration on existing DB | ✅ |

**Checkpoint:** `fin-cli init --upgrade` creates new tables/columns

---

### Phase 2: Tag Service ✅ COMPLETE
**Goal:** Core tag operations working

| Task | File | Description | Status |
|------|------|-------------|--------|
| 2.1 | `services/tag_service.py` | Create file with `TagService` class | ✅ |
| 2.2 | `services/tag_service.py` | Implement `get_or_create_tag()` | ✅ |
| 2.3 | `services/tag_service.py` | Implement `get_all_tags()` | ✅ |
| 2.4 | `services/tag_service.py` | Implement `tag_transaction()` | ✅ |
| 2.5 | `services/tag_service.py` | Implement `untag_transaction()` | ✅ |
| 2.6 | `services/tag_service.py` | Implement `rename_tag()`, `delete_tag()` | ✅ |
| 2.7 | `services/tag_service.py` | Implement `update_transaction()` (category edit) | ✅ |
| 2.8 | `services/tag_service.py` | Implement `get_tag_stats()` | ✅ |
| 2.9 | - | Test: Unit tests for TagService | ✅ |

**Checkpoint:** Can tag/untag/edit transactions programmatically

---

### Phase 3: Basic CLI Commands ✅ COMPLETE
**Goal:** Tag management via CLI

| Task | File | Description | Status |
|------|------|-------------|--------|
| 3.1 | `cli/commands/tags.py` | Create file with typer app | ✅ |
| 3.2 | `cli/commands/tags.py` | Implement `tags list` command | ✅ |
| 3.3 | `cli/commands/tags.py` | Implement `tags rename` command | ✅ |
| 3.4 | `cli/commands/tags.py` | Implement `tags delete` command | ✅ |
| 3.5 | `cli/commands/tags.py` | Implement `tags migrate` command | ✅ |
| 3.6 | `cli/main.py` | Register tags command group | ✅ |
| 3.7 | - | Test: Run all tags commands | ✅ |

**Checkpoint:** `fin-cli tags list` shows tags with stats

---

### Phase 4: Transaction CLI Commands ✅ COMPLETE
**Goal:** Tag and edit transactions via CLI

| Task | File | Description | Status |
|------|------|-------------|--------|
| 4.1 | `cli/commands/transactions.py` | Add `transactions tag` command | ✅ |
| 4.2 | `cli/commands/transactions.py` | Add `transactions untag` command | ✅ |
| 4.3 | `cli/commands/transactions.py` | Add `transactions edit` command | ✅ |
| 4.4 | `cli/commands/transactions.py` | Add `--tag` filter to `transactions list` | ✅ |
| 4.5 | `cli/commands/transactions.py` | Add `--untagged` filter to `transactions list` | ✅ |
| 4.6 | `cli/commands/transactions.py` | Update `transactions show` to display tags | ✅ |
| 4.7 | `services/tag_service.py` | Add `bulk_tag_by_merchant()` | ✅ |
| 4.8 | `services/tag_service.py` | Add `bulk_tag_by_category()` | ✅ |
| 4.9 | `services/analytics_service.py` | Add `tags` + `untagged_only` params to `get_transactions()` | ✅ |
| 4.10 | - | Test: Tag transactions via CLI | ✅ |

**Checkpoint:** `fin-cli transactions tag 123 groceries` works

---

### Phase 5: Reports ✅ COMPLETE
**Goal:** Tag-based analytics

| Task | File | Description | Status |
|------|------|-------------|--------|
| 5.1 | `services/analytics_service.py` | Add `get_tag_breakdown()` method | ✅ |
| 5.2 | `services/analytics_service.py` | Add `get_monthly_tag_breakdown()` method | ✅ |
| 5.3 | `cli/commands/reports.py` | Add `reports tags` command | ✅ |
| 5.4 | `cli/commands/reports.py` | Add `--group-by tags` to `reports monthly` | ✅ |
| 5.5 | - | Test: Generate tag reports | ✅ |

**Checkpoint:** `fin-cli reports tags` shows breakdown

---

### Phase 6: Interactive Browser (TUI) ✅ COMPLETE
**Goal:** Browse and edit transactions interactively

| Task | File | Description | Status |
|------|------|-------------|--------|
| 6.1 | `requirements.txt` | Add `textual>=0.45.0` | ✅ |
| 6.2 | `cli/tui/__init__.py` | Create package | ✅ |
| 6.3 | `cli/tui/browser.py` | Create `TransactionBrowser` app shell | ✅ |
| 6.4 | `cli/tui/browser.py` | Implement transaction list with DataTable | ✅ |
| 6.5 | `cli/tui/browser.py` | Implement search/filter | ✅ |
| 6.6 | `cli/tui/browser.py` | Implement `EditScreen` modal | ✅ |
| 6.7 | `cli/tui/browser.py` | Implement `TagScreen` modal | ✅ |
| 6.8 | `cli/commands/transactions.py` | Add `transactions browse` command | ✅ |
| 6.9 | - | Test: Full interactive workflow | ✅ |

**Checkpoint:** `fin-cli transactions browse` opens TUI, can edit and tag

---

### Summary

| Phase | Tasks | Depends On | Status |
|-------|-------|------------|--------|
| 1. Database | 6 | - | ✅ COMPLETE |
| 2. Tag Service | 9 | Phase 1 | ✅ COMPLETE |
| 3. Basic CLI | 7 | Phase 2 | ✅ COMPLETE |
| 4. Transaction CLI | 10 | Phase 2, 3 | ✅ COMPLETE |
| 5. Reports | 5 | Phase 2 | ✅ COMPLETE |
| 6. TUI Browser | 9 | Phase 2, 4 | ✅ COMPLETE |

**Total: 46 tasks across 6 phases - ALL COMPLETE**

Each phase is independently testable. Phases 4 and 5 can run in parallel after Phase 2.