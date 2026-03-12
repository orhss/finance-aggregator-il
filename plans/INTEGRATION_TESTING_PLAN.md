# Integration Testing Plan for Fin Project

## Overview

This plan outlines the integration testing strategy for the Fin financial data aggregator. Unit tests are already in place (120 tests passing). This plan focuses on testing component interactions and end-to-end flows.

**Status**: Planning

---

## Current State

### What Exists
- Unit tests: `tests/services/test_*.py` (120 tests)
- Test fixtures: `tests/conftest.py` with factory functions
- In-memory SQLite for test isolation
- Testing guidelines: `.claude/rules/python-unit-tests.md`

### What's Missing
- No CLI integration tests (sync commands, category commands)
- No service integration tests (multi-service workflows)
- No E2E tests for Streamlit UI
- No smoke tests for imports

---

## Tool Comparison

| Tool | Use Case | Pros | Cons |
|------|----------|------|------|
| **typer.testing.CliRunner** | CLI commands | Fast, no subprocess, easy DB mocking | Limited to CLI |
| **Playwright** | Streamlit E2E | Real browser, screenshots, videos | Complex setup, slow, flaky |
| **streamlit.testing.v1** | Streamlit unit-ish | Fast, no browser | Beta, limited capabilities |
| **pytest + mocks** | Service integration | Fast, existing infra | Not true E2E |

### Recommendation

1. **CLI Integration** - High priority, use CliRunner (fast, reliable)
2. **Service Integration** - High priority, mock scrapers only
3. **Streamlit E2E** - Low priority, defer (beta framework, low ROI)

---

## Phase 1: CLI Integration Tests

Test full CLI commands with real services but mocked scrapers.

### New Dependency

```
pytest-mock>=3.12.0
```

### Directory Structure

```
tests/
├── conftest.py                      # Existing unit test fixtures
├── services/                        # Existing unit tests
├── integration/
│   ├── __init__.py
│   ├── conftest.py                  # CLI fixtures, mock scrapers
│   ├── test_sync_commands.py        # fin-cli sync all/cal/max
│   ├── test_category_commands.py    # fin-cli categories map/unmapped
│   └── test_transaction_commands.py # fin-cli transactions list
└── smoke/
    ├── __init__.py
    └── test_imports.py              # Import smoke tests
```

### Test Scenarios

#### Sync Commands

| Test | What it validates |
|------|-------------------|
| `test_sync_cal_success` | Full CAL sync with mocked scraper → DB |
| `test_sync_partial_failure` | One institution fails, others continue |
| `test_sync_creates_sync_history` | Sync history record created with status |
| `test_sync_normalizes_categories` | raw_category → category mapping works |
| `test_sync_applies_rules` | Rules applied to new transactions |
| `test_sync_multi_account` | Multiple accounts per institution |
| `test_sync_empty_credentials` | Error handling for missing credentials |
| `test_sync_scraper_timeout` | Timeout handling |

#### Category Commands

| Test | What it validates |
|------|-------------------|
| `test_categories_list` | Lists all mappings correctly |
| `test_categories_map` | Creates new mapping |
| `test_categories_unmapped` | Detects unmapped categories |
| `test_categories_apply` | Applies mappings to existing transactions |
| `test_categories_suggest` | Shows merchant patterns for Isracard |

#### Transaction Commands

| Test | What it validates |
|------|-------------------|
| `test_transactions_list` | Lists transactions with filters |
| `test_transactions_tag` | Tags a transaction |
| `test_transactions_browse` | TUI browser launches (mock curses) |

### Implementation Pattern

```python
# tests/integration/conftest.py
import pytest
from typer.testing import CliRunner
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base
from cli.main import app

@pytest.fixture
def cli_runner():
    """Typer CLI test runner."""
    return CliRunner()

@pytest.fixture
def integration_db_session():
    """Separate DB session for integration tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def mock_cal_scraper():
    """Mock CAL credit card scraper."""
    with patch("services.credit_card_service.CALCreditCardClient") as mock:
        client = MagicMock()
        client.get_transactions.return_value = [
            {
                "description": "WOLT DELIVERY",
                "amount": 50.0,
                "date": "2024-01-15",
                "category": "מזון",
                "status": "completed"
            },
            {
                "description": "NETFLIX",
                "amount": 49.90,
                "date": "2024-01-14",
                "category": "בידור",
                "status": "completed"
            }
        ]
        client.get_accounts.return_value = [
            {"number": "1234", "name": "Personal Card"}
        ]
        mock.return_value.__enter__.return_value = client
        yield mock

@pytest.fixture
def mock_credentials():
    """Mock credentials loading."""
    with patch("config.settings.load_credentials") as mock:
        mock.return_value = MagicMock(
            cal=[MagicMock(username="test", password="test")],
            max=[],
            isracard=[]
        )
        yield mock
```

```python
# tests/integration/test_sync_commands.py
import pytest
from db.models import Transaction, SyncHistory

@pytest.mark.integration
def test_sync_cal_creates_transactions(
    cli_runner, integration_db_session, mock_cal_scraper, mock_credentials
):
    """Sync CAL should create transactions in database."""
    result = cli_runner.invoke(app, ["sync", "cal"])

    assert result.exit_code == 0
    assert "Synced" in result.stdout or "transactions" in result.stdout.lower()

    # Verify transactions created
    txns = integration_db_session.query(Transaction).all()
    assert len(txns) == 2
    assert txns[0].description == "WOLT DELIVERY"

@pytest.mark.integration
def test_sync_creates_sync_history(
    cli_runner, integration_db_session, mock_cal_scraper, mock_credentials
):
    """Sync should create sync history record."""
    result = cli_runner.invoke(app, ["sync", "cal"])

    history = integration_db_session.query(SyncHistory).first()
    assert history is not None
    assert history.institution == "cal"
    assert history.status == "success"

@pytest.mark.integration
def test_sync_partial_failure_continues(
    cli_runner, integration_db_session, mock_credentials
):
    """If one institution fails, others should still sync."""
    with patch("services.credit_card_service.CALCreditCardClient") as cal_mock:
        cal_mock.return_value.__enter__.side_effect = Exception("CAL auth failed")

        with patch("services.credit_card_service.MaxCreditCardClient") as max_mock:
            max_mock.return_value.__enter__.return_value.get_transactions.return_value = []

            result = cli_runner.invoke(app, ["sync", "all"])

    # Should report partial success
    assert "failed" in result.stdout.lower() or "error" in result.stdout.lower()
    # Max should still have synced
    # (verify based on actual output format)
```

---

## Phase 2: Service Integration Tests

Test multi-service coordination without CLI layer.

### Test Scenarios

| Scenario | Services Involved | Key Assertions |
|----------|-------------------|----------------|
| Sync → Category Normalization | CreditCardService + CategoryService | `category` populated from mapping |
| Sync → Rule Application | CreditCardService + RulesService | `user_category` set by rule |
| Sync → Tag Application | CreditCardService + TagService | Tags created and linked |
| Transaction Rollback | BaseSyncService | No partial data on failure |
| Multi-account Sync | CreditCardService | Accounts correctly separated |

### Implementation Pattern

```python
# tests/integration/test_service_integration.py
import pytest
from services.credit_card_service import CreditCardService
from services.category_service import CategoryService
from tests.conftest import create_category_mapping, create_account

@pytest.mark.integration
def test_sync_applies_category_mapping(db_session, mock_cal_scraper):
    """Synced transactions should have normalized categories."""
    # Setup: Create category mapping
    create_category_mapping(db_session, "cal", "מזון", "groceries")

    # Act: Run sync
    service = CreditCardService(db_session)
    result = service.sync_cal(username="test", password="test")

    # Assert: Transaction has normalized category
    from db.models import Transaction
    txn = db_session.query(Transaction).filter(
        Transaction.description == "WOLT DELIVERY"
    ).first()

    assert txn.raw_category == "מזון"
    assert txn.category == "groceries"
    assert txn.effective_category == "groceries"

@pytest.mark.integration
def test_sync_detects_unmapped_categories(db_session, mock_cal_scraper):
    """Sync should track unmapped categories."""
    # No mapping exists for "בידור"
    service = CreditCardService(db_session)
    result = service.sync_cal(username="test", password="test")

    # Check unmapped tracking
    category_service = CategoryService(db_session)
    unmapped = category_service.get_unmapped_categories()

    assert any(u["raw_category"] == "בידור" for u in unmapped)

@pytest.mark.integration
def test_sync_applies_rules(db_session, mock_cal_scraper, temp_rules_file):
    """Rules should be applied to new transactions during sync."""
    from services.rules_service import RulesService

    # Setup: Create rule for WOLT
    rules_service = RulesService(rules_file=temp_rules_file, session=db_session)
    rules_service.add_rule(pattern="wolt", category="food_delivery", tags=["delivery"])

    # Act: Sync with rule application
    service = CreditCardService(db_session)
    result = service.sync_cal(username="test", password="test")

    # Assert: Rule applied
    from db.models import Transaction
    txn = db_session.query(Transaction).filter(
        Transaction.description == "WOLT DELIVERY"
    ).first()

    assert txn.user_category == "food_delivery"

@pytest.mark.integration
def test_sync_rollback_on_failure(db_session):
    """Sync failure mid-way should rollback all changes."""
    from db.models import Transaction

    initial_count = db_session.query(Transaction).count()

    with patch("services.credit_card_service.CALCreditCardClient") as mock:
        # Return some transactions then raise error
        client = MagicMock()
        client.get_transactions.side_effect = Exception("Connection lost")
        mock.return_value.__enter__.return_value = client

        service = CreditCardService(db_session)
        result = service.sync_cal(username="test", password="test")

    # No new transactions should exist (rollback)
    assert db_session.query(Transaction).count() == initial_count
    assert result.success is False
```

---

## Phase 3: Smoke Tests

Minimal tests to verify imports work.

```python
# tests/smoke/test_imports.py
"""
Smoke tests - verify modules import without errors.
These catch missing dependencies and syntax errors.
"""

def test_cli_imports():
    """CLI modules import successfully."""
    from cli.main import app
    from cli.commands import sync, accounts, transactions, categories
    assert app is not None

def test_services_import():
    """Service modules import successfully."""
    from services.analytics_service import AnalyticsService
    from services.category_service import CategoryService
    from services.credit_card_service import CreditCardService
    from services.rules_service import RulesService
    assert AnalyticsService is not None

def test_streamlit_imports():
    """Streamlit app modules import successfully."""
    # Note: These may require DISPLAY env var on some systems
    try:
        import streamlit_app.main
        import streamlit_app.app
        import streamlit_app.views.accounts
        import streamlit_app.views.transactions
    except ImportError as e:
        pytest.skip(f"Streamlit import requires display: {e}")

def test_models_import():
    """Database models import successfully."""
    from db.models import Account, Transaction, Balance, Tag
    from db.models import CategoryMapping, MerchantMapping, SyncHistory
    assert Account is not None
```

---

## Phase 4: Streamlit E2E (Deferred)

### Why Defer?

1. **streamlit.testing.v1** is still beta with limited capabilities
2. **Playwright setup** is complex for Streamlit's WebSocket architecture
3. **ROI is low** - manual testing covers UI adequately for a personal project
4. **Maintenance burden** - browser tests are notoriously flaky

### When to Revisit

- Critical bug escapes to production that tests would have caught
- Streamlit releases stable testing framework
- Project scope expands (multi-user, production deployment)

### If Implemented Later

```python
# Hypothetical Playwright test (not implementing now)
# tests/e2e/test_streamlit.py

from playwright.sync_api import sync_playwright

def test_dashboard_loads():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("http://localhost:8501")

        # Wait for Streamlit to load
        page.wait_for_selector("[data-testid='stAppViewContainer']")

        # Check dashboard elements
        assert page.locator("text=Dashboard").is_visible()

        browser.close()
```

---

## Implementation Checklist

### Phase 1: CLI Integration
- [ ] Add `pytest-mock>=3.12.0` to `requirements.txt`
- [ ] Create `tests/integration/__init__.py`
- [ ] Create `tests/integration/conftest.py`
- [ ] Create `tests/integration/test_sync_commands.py` (~8 tests)
- [ ] Create `tests/integration/test_category_commands.py` (~5 tests)
- [ ] Create `tests/integration/test_transaction_commands.py` (~4 tests)
- [ ] Update `pytest.ini` with integration marker

### Phase 2: Service Integration
- [ ] Add mock fixtures for all scrapers to conftest.py
- [ ] Create `tests/integration/test_service_integration.py` (~10 tests)
- [ ] Test sync → normalization flow
- [ ] Test sync → rules flow
- [ ] Test transaction rollback

### Phase 3: Smoke Tests
- [ ] Create `tests/smoke/__init__.py`
- [ ] Create `tests/smoke/test_imports.py` (~4 tests)

### Phase 4: Streamlit (Defer)
- [ ] Revisit when testing framework matures

---

## Running Tests

```bash
# Run all tests
pytest

# Run only unit tests (fast)
pytest tests/services -v

# Run only integration tests
pytest tests/integration -v -m integration

# Run smoke tests
pytest tests/smoke -v

# Run with coverage
pytest --cov=services --cov=cli --cov-report=term-missing

# Skip slow tests
pytest -m "not slow"
```

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `requirements.txt` | Add: `pytest-mock>=3.12.0` |
| `pytest.ini` | Add `integration` marker |
| `tests/integration/__init__.py` | Create (empty) |
| `tests/integration/conftest.py` | Create - CLI fixtures, mock scrapers |
| `tests/integration/test_sync_commands.py` | Create (~8 tests) |
| `tests/integration/test_category_commands.py` | Create (~5 tests) |
| `tests/integration/test_transaction_commands.py` | Create (~4 tests) |
| `tests/integration/test_service_integration.py` | Create (~10 tests) |
| `tests/smoke/__init__.py` | Create (empty) |
| `tests/smoke/test_imports.py` | Create (~4 tests) |

---

## Verification

After implementation:

```bash
# Verify integration tests discovered
pytest --collect-only tests/integration

# Verify smoke tests pass
pytest tests/smoke -v

# Verify full suite
pytest -v

# Expected: ~150+ tests (120 unit + 30+ integration/smoke)
```

---

## Summary

| Phase | Priority | Tests | Status |
|-------|----------|-------|--------|
| Unit Tests | N/A | 120 | ✅ Complete |
| CLI Integration | High | ~17 | Planned |
| Service Integration | High | ~10 | Planned |
| Smoke Tests | Medium | ~4 | Planned |
| Streamlit E2E | Low | 0 | Deferred |
| **Total** | | **~151** | |

This plan prioritizes high-ROI integration tests (CLI + services) while deferring complex browser-based E2E tests until frameworks mature.