# Testing Strategy Plan for Fin Project

## Current State

- **No existing test infrastructure** - No `tests/` directory, no `pytest.ini`, no `conftest.py`
- **No testing dependencies** in `requirements.txt`
- **Well-structured codebase** with clear layers: `scrapers → services → db → cli/streamlit_app`

---

## Framework Comparison

### pytest (Recommended)

| Aspect | Details |
|--------|---------|
| **Pros** | Industry standard, excellent fixtures system, `@pytest.mark.parametrize`, rich plugin ecosystem, better assertion messages, less boilerplate |
| **Cons** | Extra dependency (but lightweight) |

### unittest (Built-in)

| Aspect | Details |
|--------|---------|
| **Pros** | Built into Python, no dependencies |
| **Cons** | More boilerplate (`setUp`/`tearDown` vs fixtures), verbose assertions, no parametrize, worse output formatting |

**Verdict**: pytest is the clear winner for modern Python projects. The fixture system alone makes testing significantly easier.

---

## Recommended Dependencies

```
# Testing core
pytest>=8.0.0
pytest-cov>=4.1.0         # Coverage reporting

# Mocking
freezegun>=1.2.0          # Time mocking (dates matter in financial data)
```

**Why not:**
- `pytest-mock` - `unittest.mock` is sufficient and built-in
- `responses` - Not needed for unit tests (no HTTP mocking)
- `vcrpy` - Good for recording real responses, but adds complexity
- `selenium-wire` - We won't unit test Selenium flows

---

## Testability Analysis by Layer

### 1. Services Layer - **High Priority** (Best ROI)

| File | Testability | Notes |
|------|-------------|-------|
| `services/category_service.py` | Excellent | Pure business logic, DB operations easy to mock with in-memory SQLite |
| `services/analytics_service.py` | Excellent | Complex queries, good candidate for tests |
| `services/base_service.py` | Good | Transaction management, critical to test |
| `services/rules_service.py` | Excellent | Rule matching logic is pure functions |
| `services/tag_service.py` | Good | CRUD operations |

### 2. Scrapers - **Lower Priority**

| Component | Testability | Approach |
|-----------|-------------|----------|
| Data parsing (transactions, balances) | Excellent | Pure functions, sample data |
| API clients | Medium | Would need HTTP mocking (future) |
| Selenium flows | Poor for unit tests | Integration/E2E only |

### 3. CLI Commands - **Future**

- Commands use `typer.testing.CliRunner`
- Can test but mostly integration-level

### 4. Streamlit - **Skip**

- Use manual testing or E2E with Playwright if needed later

---

## Test Structure (Unit Tests Only)

```
tests/
├── conftest.py               # Shared fixtures (db session, sample data)
│
├── services/                 # Service layer tests (priority)
│   ├── test_category_service.py
│   ├── test_rules_service.py
│   ├── test_analytics_service.py
│   ├── test_base_service.py
│   └── test_tag_service.py
│
├── scrapers/                 # Scraper tests (future)
│   └── test_parsers.py       # Data parsing only
│
└── fixtures/                 # Sample data files
    └── sample_transactions.json
```

---

## Execution Plan

### Phase 1: Infrastructure Setup

1. Add testing dependencies to `requirements.txt`
2. Create `pytest.ini` with configuration
3. Create `tests/conftest.py` with core fixtures:
   - In-memory SQLite database session
   - Sample account/transaction factories
4. Update `.gitignore` for coverage artifacts

### Phase 2: Backfill Critical Services (Immediate)

Write unit tests for these services in priority order:

| Service | Focus Areas | Test Count (Est.) |
|---------|-------------|-------------------|
| `CategoryService` | `normalize_category`, `add_mapping`, `get_unmapped_categories`, merchant pattern extraction | ~15-20 tests |
| `RulesService` | Rule matching (exact, contains, regex), rule application | ~10-12 tests |
| `AnalyticsService` | Monthly summaries, category spending, date filtering | ~8-10 tests |

### Phase 3: TDD for New Code (Ongoing)

For any new feature or bug fix:
1. Write failing test first
2. Implement minimum code to pass
3. Refactor if needed

---

## Sample conftest.py

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base

@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def sample_account(db_session):
    """Create a sample account for testing."""
    from db.models import Account
    from datetime import datetime

    account = Account(
        account_type="credit_card",
        institution="cal",
        account_number="1234",
        account_name="Test Card",
        last_synced_at=datetime.utcnow()
    )
    db_session.add(account)
    db_session.commit()
    return account
```

---

## Configuration Files

### pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
filterwarnings =
    ignore::DeprecationWarning
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
```

### .coveragerc (optional)

```ini
[run]
source = services,scrapers,cli
omit =
    */tests/*
    */__pycache__/*
    streamlit_app/*

[report]
exclude_lines =
    pragma: no cover
    if __name__ == .__main__.:
```

---

## Pros/Cons Summary

### Adopting TDD

| Pros | Cons |
|------|------|
| Catches bugs before they ship | Initial slowdown (writing tests) |
| Forces better design (testable = modular) | Learning curve if new to TDD |
| Documentation through tests | Some code is hard to test (Selenium) |
| Confidence in refactoring | Maintenance burden for tests |
| Services layer is very testable | 100% coverage is unrealistic for scrapers |

---

## Implementation Steps

### Step 1: Infrastructure
1. Add dependencies to `requirements.txt`
2. Create `pytest.ini`
3. Create `tests/conftest.py` with fixtures
4. Update `.gitignore`
5. Verify: `pytest` runs (0 tests collected)

### Step 2: CategoryService Tests (~15-20 tests)
- `test_normalize_category` - mapping lookup
- `test_add_mapping` - create/update
- `test_get_unmapped_categories` - detection logic
- `test_extract_merchant_pattern` - pattern extraction heuristics
- `test_bulk_set_category_with_mapping` - batch operations

### Step 3: RulesService Tests (~10-12 tests)
- `test_rule_matching` - exact, contains, regex
- `test_apply_rules` - rule execution
- `test_rule_priority` - ordering

### Step 4: AnalyticsService Tests (~8-10 tests)
- `test_get_monthly_summary` - aggregations
- `test_category_spending` - grouping
- `test_date_filtering` - boundary conditions

### Step 5: TDD for New Features (Ongoing)

**Target Coverage**: 70-80% for services layer

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `requirements.txt` | Add: `pytest>=8.0.0`, `pytest-cov>=4.1.0`, `freezegun>=1.2.0` |
| `pytest.ini` | Create - test configuration |
| `.gitignore` | Add: `.coverage`, `htmlcov/`, `.pytest_cache/` |
| `tests/__init__.py` | Create (empty) |
| `tests/conftest.py` | Create - DB fixtures, sample data factories |
| `tests/services/__init__.py` | Create (empty) |
| `tests/services/test_category_service.py` | Create - ~15-20 tests |
| `tests/services/test_rules_service.py` | Create - ~10-12 tests |
| `tests/services/test_analytics_service.py` | Create - ~8-10 tests |

---

## Verification

After setup:
```bash
# Run tests
pytest

# Run with coverage
pytest --cov=services --cov-report=term-missing

# Run only fast unit tests
pytest tests/services -m "not slow"
```