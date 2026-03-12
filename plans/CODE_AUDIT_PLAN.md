# Code Audit & Refactoring Plan

## Status

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Quick Wins (shared models, CLI utils) | ✅ Complete |
| Phase 2 | Medium Effort (services consolidation) | ✅ Complete |
| Phase 3 | High Effort (Streamlit consolidation) | ✅ Complete |
| Phase 4 | Cleanup & Polish (exceptions, output, exports) | ✅ Complete |

**Last Updated**: 2026-02-06

## Executive Summary

Full codebase audit completed. **~36,000 lines of Python** analyzed across scrapers, services, CLI, and Streamlit layers. Found significant opportunities for consolidation following DRY, KISS, and SIMPLE principles.

| Layer | Current Lines | Potential Reduction | Priority |
|-------|---------------|---------------------|----------|
| Credit Card Scrapers | ~2,400 | 300-400 (15%) | HIGH |
| Services | ~4,000 | 200-300 (6%) | MEDIUM |
| CLI Commands | ~4,500 | 225-335 (6%) | MEDIUM |
| Streamlit App | ~7,000 | 1,500-1,900 (25%) | HIGH |
| **Total** | **~18,000** | **2,225-2,935 (14%)** | |

---

## Phase 1: Quick Wins (1-2 hours each)

### 1.1 Extract Shared Credit Card Models
**Files:** `scrapers/credit_cards/cal_credit_card_client.py`, `max_credit_card_client.py`, `isracard_credit_card_client.py`

**Create:** `scrapers/credit_cards/shared_models.py`

**Extract:**
- `TransactionStatus` enum (identical in all 3)
- `TransactionType` enum (identical in all 3)
- `Installments` dataclass (identical in all 3)
- `Transaction` dataclass (identical in all 3)
- `CardAccount` dataclass (nearly identical)

**Impact:** ~120 lines saved (40 lines × 3 files)

---

### 1.2 Extract Shared Credit Card Exceptions
**Files:** Same as above

**Create:** `scrapers/credit_cards/shared_exceptions.py`

**Extract:**
```python
class CreditCardScraperError(Exception): pass
class CreditCardLoginError(CreditCardScraperError): pass
class CreditCardAPIError(CreditCardScraperError): pass

# Then per-institution:
class CALScraperError(CreditCardScraperError): pass
# etc.
```

**Impact:** ~60 lines saved (20 lines × 3 files)

---

### 1.3 Add CLI Date Parsing Utility
**File:** `cli/utils.py`

**Add:**
```python
def parse_date(date_str: str, param_name: str = "date") -> date:
    """Parse YYYY-MM-DD string or exit with error."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        print_error(f"Invalid {param_name} format. Use YYYY-MM-DD")
        raise typer.Exit(code=1)

def parse_date_range(from_date: Optional[str], to_date: Optional[str]) -> tuple[Optional[date], Optional[date]]:
    """Parse optional date range strings."""
    return (
        parse_date(from_date, "from date") if from_date else None,
        parse_date(to_date, "to date") if to_date else None
    )
```

**Update:** `cli/commands/sync.py`, `transactions.py`, `export.py`, `reports.py`

**Impact:** ~50 lines saved (12+ instances consolidated)

---

### 1.4 Add CLI Service Context Managers
**File:** `cli/utils.py`

**Add:**
```python
@contextmanager
def get_analytics():
    """Context manager for AnalyticsService with proper cleanup."""
    service = AnalyticsService()
    try:
        yield service
    finally:
        service.close()

@contextmanager
def get_db_session():
    """Context manager for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Impact:** ~70 lines saved (15+ instances consolidated)

---

### 1.5 Add CLI Progress Spinner Utility
**File:** `cli/utils.py`

**Add:**
```python
@contextmanager
def spinner(description: str):
    """Context manager for progress spinner."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(description, total=None)
        yield
```

**Update:** `cli/commands/sync.py`, `export.py`

**Impact:** ~30 lines saved (8+ instances consolidated)

---

### 1.6 Remove Unused Imports
**Files:** Multiple (see list below)

**Action:** Remove imports flagged by analysis:
- `cli/utils.py`: Remove `Any`
- `cli/main.py`: Remove `Optional`
- `cli/commands/sync.py`: Remove `DEFAULT_DB_PATH`, `Table`, `get_settings`, `Path`
- `cli/commands/tags.py`: Remove `Optional`, `Panel`
- `cli/commands/config.py`: Remove `Credentials`
- `cli/commands/maintenance.py`: Remove `get_db`
- `cli/commands/transactions.py`: Remove `date`
- `cli/commands/rules.py`: Remove `Panel`
- `cli/commands/export.py`: Remove `Account`, `Balance`, `Transaction`
- `cli/commands/reports.py`: Remove `Text`
- `db/database.py`: Remove `os`

**Impact:** Cleaner imports, faster load times

---

## Phase 2: Medium Effort (2-4 hours each)

### 2.1 Extract Shared Credit Card Helpers
**Create:** `scrapers/credit_cards/shared_helpers.py`

**Extract:**
```python
def get_cookies(driver) -> Dict[str, str]:
    """Extract cookies as dictionary."""
    return {c['name']: c['value'] for c in driver.get_cookies()}

def iterate_months(start_date: date, end_date: date) -> Generator[tuple[int, int], None, None]:
    """Generate (year, month) tuples from end_date backwards to start_date."""
    current = end_date
    while current >= start_date:
        yield current.year, current.month
        if current.month == 1:
            current = current.replace(year=current.year - 1, month=12, day=1)
        else:
            current = current.replace(month=current.month - 1, day=1)

def calculate_date_range(months_back: int, months_forward: int = 1) -> tuple[date, date]:
    """Calculate start and end dates for transaction fetching."""
    today = date.today()
    start = today - timedelta(days=months_back * 30)
    end = today + timedelta(days=months_forward * 30)
    return start, end

def filter_transactions_by_date(transactions: List[Transaction], start: date, end: date) -> List[Transaction]:
    """Filter transactions to date range."""
    return [t for t in transactions if start <= t.date <= end]

def extract_installments(raw_string: str) -> Optional[Installments]:
    """Extract installment info from string like '3/12'."""
    matches = re.findall(r'\d+', raw_string)
    if len(matches) >= 2:
        return Installments(number=int(matches[0]), total=int(matches[1]))
    return None
```

**Update:** All three credit card scrapers

**Impact:** ~150 lines saved

---

### 2.2 Create Credit Card Base Scraper Class
**Create:** `scrapers/credit_cards/base_scraper.py`

**Extract:**
```python
class CreditCardScraperBase:
    """Base class for credit card scrapers with common driver lifecycle."""

    def __init__(self, credentials, headless: bool = True):
        self.credentials = credentials
        self.headless = headless
        self._selenium_driver = None
        self.driver = None

    def setup_driver(self):
        config = DriverConfig(headless=self.headless, ...)
        self._selenium_driver = SeleniumDriver(config)
        self.driver = self._selenium_driver.setup()

    def cleanup(self):
        if self._selenium_driver:
            self._selenium_driver.cleanup()
            self._selenium_driver = None
        self.driver = None

    def __enter__(self):
        self.setup_driver()
        return self

    def __exit__(self, *args):
        self.cleanup()

    @abstractmethod
    def login(self) -> bool: pass

    @abstractmethod
    def fetch_transactions(self, months_back: int) -> List[Transaction]: pass
```

**Impact:** ~100 lines saved (driver setup/cleanup deduplicated)

---

### 2.3 Consolidate Sync Result Classes
**File:** `services/base_service.py`

**Add:**
```python
@dataclass
class SyncResult:
    """Generic sync operation result."""
    success: bool = False
    records_added: int = 0
    records_updated: int = 0
    error_message: Optional[str] = None
    sync_history_id: Optional[int] = None

    # Type-specific counts (optional)
    accounts_synced: int = 0
    cards_synced: int = 0
    balances_added: int = 0
    transactions_added: int = 0
```

**Remove:** `BrokerSyncResult`, `PensionSyncResult`, `CreditCardSyncResult`

**Impact:** ~60 lines saved, single result class to maintain

---

### 2.4 Extract Balance Query Helper
**File:** `services/base_service.py`

**Add:**
```python
def get_balances_by_type(
    self,
    account_type: str,
    institution: Optional[str] = None,
    limit: int = 100
) -> List[Balance]:
    """Get balances for account type with optional institution filter."""
    query = self.db.query(Balance).join(Account)
    if institution:
        query = query.filter(Account.institution == institution)
    query = query.filter(Account.account_type == account_type)
    query = query.order_by(Balance.balance_date.desc())
    return query.limit(limit).all()
```

**Update:** `broker_service.py`, `pension_service.py` to use helper

**Impact:** ~40 lines saved

---

### 2.5 Add Session Mixin for Non-Sync Services
**File:** `services/base_service.py`

**Add:**
```python
class SessionMixin:
    """Mixin providing session management for services."""
    _session: Optional[Session] = None

    @property
    def session(self) -> Session:
        if self._session is None:
            self._session = next(get_db())
        return self._session

    def close(self):
        if self._session:
            self._session.close()
            self._session = None
```

**Update:** `CategoryService`, `TagService`, `RulesService`, `BudgetService` to use mixin

**Impact:** ~40 lines saved

---

### 2.6 CLI Amount Formatting Utilities
**File:** `cli/utils.py`

**Add:**
```python
def format_amount(amount: float, currency: str = "₪", colored: bool = True) -> str:
    """Format amount with optional color (red negative, green positive)."""
    formatted = f"{currency}{abs(amount):,.2f}"
    if amount < 0:
        formatted = f"-{formatted}"
    if not colored:
        return formatted
    color = "red" if amount < 0 else "green"
    return f"[{color}]{formatted}[/{color}]"

def format_status(status: str) -> str:
    """Format status with appropriate color."""
    colors = {"success": "green", "failed": "red", "pending": "yellow", "completed": "green"}
    color = colors.get(status.lower(), "white")
    return f"[{color}]{status}[/{color}]"
```

**Update:** `cli/commands/transactions.py`, `accounts.py`, `reports.py`

**Impact:** ~35 lines saved (10+ instances consolidated)

---

## Phase 3: High Effort (4-8 hours each)

### 3.1 Streamlit: Merge Mobile/Desktop Views
**Files:** `streamlit_app/views/analytics.py`, `transactions.py`, `accounts.py`

**Strategy:**
1. Extract shared business logic (data fetching, calculations) into helper functions
2. Keep single render function that uses responsive components
3. Use `st.columns([1, 2])` with conditional widths instead of separate functions

**Example refactor for analytics.py:**
```python
# Before: 1115 lines with render_mobile_analytics() and render_desktop_analytics()
# After: ~600 lines with shared helpers + responsive rendering

def _fetch_analytics_data(start_date, end_date):
    """Shared data fetching - used by both mobile and desktop."""
    # Extract from both functions
    pass

def _calculate_metrics(transactions):
    """Shared metric calculations."""
    pass

def render_analytics():
    """Single entry point with responsive layout."""
    data = _fetch_analytics_data(start, end)
    metrics = _calculate_metrics(data)

    if is_mobile():
        # Simplified mobile layout
        render_metric_row(metrics[:2])
    else:
        # Full desktop layout
        render_metric_row(metrics)
        render_charts(data)
```

**Impact:** ~500-800 lines saved across 3 view files

---

### 3.2 Streamlit: Consolidate Date Selectors
**Files:** `views/analytics.py`, `views/transactions.py`, `components/filters.py`

**Create:** Single `date_range_picker()` in `components/filters.py`

**Replace:** 3 different implementations with one

**Impact:** ~100 lines saved

---

### 3.3 Streamlit: Simplify Filter Panel
**File:** `components/filters.py`

**Strategy:**
1. Remove `key_prefix` boilerplate - use Streamlit's automatic keying
2. Create `FilterPanel` class that manages related filters together
3. Reduce from 14 separate functions to ~5 composable components

**Impact:** ~150 lines saved

---

### 3.4 Streamlit: Remove Display Wrapper Functions
**File:** `utils/session.py`

**Remove:**
- `get_accounts_display()` - inline the one-line formatting
- `get_transactions_display()` - inline or merge into cache
- `get_dashboard_stats_display()` - inline or merge into cache
- `get_tags_display()` - inline or merge into cache

**Impact:** ~80 lines saved, reduced indirection

---

### 3.5 Consolidate Amount Formatters
**File:** `streamlit_app/utils/formatters.py`

**Current:** 735 lines with overlapping functions
**Target:** ~500 lines

**Consolidate:**
- `format_currency()`, `format_transaction_amount()`, `format_transaction_with_currency()`, `format_amount_delta()` → single `format_amount()` with options

**Impact:** ~150 lines saved

---

## Phase 4: Cleanup & Polish

### 4.1 Fix Broad Exception Handlers
**Current:** 176 instances of `except Exception:`

**Strategy:**
- Replace with specific exceptions where possible
- Add logging for truly generic handlers
- Document why broad handler is needed if unavoidable

**Priority files:**
- `cli/commands/*.py` - most instances here
- `services/*.py` - sync operations

---

### 4.2 Standardize CLI Output
**Current:** Mix of `console.print()` and `print_error/success/warning()`

**Standardize:** Use utilities from `cli/utils.py` consistently

---

### 4.3 Add Missing `__all__` Exports
**Files:** Various `__init__.py` files with unused exports

**Action:** Either use the exports or remove them

---

## Implementation Priority Matrix

| Task | Impact | Effort | Priority | Dependencies |
|------|--------|--------|----------|--------------|
| 1.1 Shared Models | High | Low | P1 | None |
| 1.2 Shared Exceptions | Medium | Low | P1 | None |
| 1.3 CLI Date Parsing | Medium | Low | P1 | None |
| 1.4 CLI Service Context | Medium | Low | P1 | None |
| 1.5 CLI Spinner | Low | Low | P2 | 1.4 |
| 1.6 Unused Imports | Low | Low | P2 | None |
| 2.1 Shared Helpers | High | Medium | P1 | 1.1 |
| 2.2 Base Scraper | High | Medium | P1 | 1.1, 1.2, 2.1 |
| 2.3 Sync Result | Medium | Low | P2 | None |
| 2.4 Balance Query | Medium | Low | P2 | None |
| 2.5 Session Mixin | Medium | Low | P2 | None |
| 2.6 CLI Amount Format | Medium | Low | P2 | None |
| 3.1 Merge Views | Very High | High | P1 | None |
| 3.2 Date Selectors | Medium | Medium | P2 | None |
| 3.3 Filter Panel | Medium | Medium | P2 | None |
| 3.4 Remove Wrappers | Medium | Low | P2 | None |
| 3.5 Formatters | Medium | Medium | P3 | None |
| 4.1 Exception Handlers | Medium | High | P3 | None |
| 4.2 CLI Output | Low | Medium | P3 | None |
| 4.3 Exports | Low | Low | P3 | None |

---

## Recommended Execution Order

### Sprint 1: Foundation (Scrapers + CLI Utils)
1. 1.1 Shared Models
2. 1.2 Shared Exceptions
3. 2.1 Shared Helpers
4. 2.2 Base Scraper
5. 1.3 CLI Date Parsing
6. 1.4 CLI Service Context

**Outcome:** Credit card scrapers consolidated, CLI utilities ready

### Sprint 2: Services + CLI Polish
1. 2.3 Sync Result
2. 2.4 Balance Query
3. 2.5 Session Mixin
4. 1.5 CLI Spinner
5. 2.6 CLI Amount Format
6. 1.6 Unused Imports

**Outcome:** Services layer cleaner, CLI fully DRY

### Sprint 3: Streamlit Consolidation
1. 3.1 Merge Views (largest impact)
2. 3.4 Remove Wrappers
3. 3.2 Date Selectors
4. 3.3 Filter Panel

**Outcome:** Streamlit app significantly smaller

### Sprint 4: Final Cleanup
1. 3.5 Formatters
2. 4.1 Exception Handlers
3. 4.2 CLI Output
4. 4.3 Exports

**Outcome:** Consistent patterns throughout

---

## Success Metrics

- [ ] Total lines reduced by 2,000+ (14%+)
- [ ] No duplicate model definitions
- [ ] CLI utilities consolidated in `cli/utils.py`
- [ ] Credit card scrapers share base class
- [ ] Streamlit views under 600 lines each
- [ ] Zero unused imports
- [ ] Broad exception handlers reduced by 50%

---

## Files to Create

| File | Purpose |
|------|---------|
| `scrapers/credit_cards/shared_models.py` | Shared enums, dataclasses |
| `scrapers/credit_cards/shared_exceptions.py` | Exception hierarchy |
| `scrapers/credit_cards/shared_helpers.py` | Utility functions |
| `scrapers/credit_cards/base_scraper.py` | Base class for scrapers |

## Files with Major Changes

| File | Changes |
|------|---------|
| `cli/utils.py` | Add 6+ new utilities |
| `services/base_service.py` | Add SyncResult, SessionMixin, balance helper |
| `streamlit_app/views/analytics.py` | Merge mobile/desktop (~500 lines saved) |
| `streamlit_app/views/transactions.py` | Merge mobile/desktop (~400 lines saved) |
| `streamlit_app/components/filters.py` | Consolidate date selectors |
| `streamlit_app/utils/formatters.py` | Reduce overlapping functions |

---

*Generated: 2026-02-06*