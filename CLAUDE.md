# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Navigation Rule**: Always read `.claude/codemap.md` BEFORE using Glob/Grep for code files. The codemap contains the full Python file/function index. Use Glob only for non-code files (plans/*.md, config files, etc.).

## Project Overview

Python automation framework for financial institutions (brokers, pension funds, and credit cards) using web scraping with Selenium and API clients. Implements MFA (Multi-Factor Authentication) automation via email retrieval.

**Stack**: Python services + SQLite + FastAPI REST API + React SPA (MUI, TanStack Query). Streamlit UI is legacy and kept during migration.

**Project Structure**: Reorganized into modular packages with fully implemented CLI, services layer, SQLite database, FastAPI backend, and React frontend.

**Multi-Account Support**: Credit card scrapers support multiple accounts per institution (CAL, Max, Isracard). See `plans/MULTI_ACCOUNT_PLAN.md` for details.

**Category Normalization**: Two-tier system for unified categories:
- **Provider Mapping**: `CategoryMapping` maps provider's `raw_category` → unified `category` (CAL, Max)
- **Merchant Mapping**: `MerchantMapping` maps description patterns → unified `category` (Isracard - no provider categories)
- See @plans/CATEGORY_NORMALIZATION_PLAN.md for full implementation

## Development Commands

### Environment Setup
```bash
make install          # Install everything (uv sync + npm install in web/)

# Or manually:
uv sync               # Python deps
cd web && npm install # Node deps

# Run services
make api              # FastAPI on :8000 (--reload)
make web              # React dev server on :3000
make dev              # Both in parallel (make -j2)
make streamlit        # Legacy Streamlit on :8501

# Docker (all three services)
make up               # Start  (streamlit :8501, api :8000, web :3000)
make down             # Stop
make logs             # Tail logs
```

### CLI Quick Start
```bash
fin-cli init              # Initialize database
fin-cli config setup      # Configure credentials (interactive)
fin-cli sync all          # Sync all financial sources
fin-cli accounts list     # View accounts
fin-cli transactions list # View transactions
fin-cli reports stats     # View statistics
fin-cli maintenance migrate # Apply database migrations

# Category management
fin-cli categories analyze       # Check category mapping coverage
fin-cli categories suggest       # Show uncategorized by merchant (Isracard)
fin-cli categories assign-wizard # Interactive merchant categorization
fin-cli categories merchants     # List saved merchant mappings

# Budget management
fin-cli budget show              # Show current month's budget progress
fin-cli budget set <amount>      # Set monthly budget (e.g., 5000)

# Authentication (for network access)
fin-cli auth add-user <username> # Add user for Streamlit login
fin-cli auth enable              # Enable authentication
fin-cli auth disable             # Disable authentication
fin-cli auth list-users          # List configured users
fin-cli auth status              # Show auth status
```

### Configuration
- **Encrypted credentials**: Stored in `~/.fin/credentials.enc` (managed via `fin-cli config`)
- **Environment variables**: Fallback option in `.env` (for development)
- **Configuration directory**: `~/.fin/` (config.json, credentials.enc, .key, financial_data.db)
- Chrome WebDriver is located in `chrome-linux64/` directory

### Docker Services
| Container | Port | Description |
|---|---|---|
| `fin-api` | 8000 | FastAPI (`uvicorn api.main:app`) |
| `fin-web` | 3000 | React nginx (proxies `/api/` → api:8000) |
| `fin-streamlit` | 8501 | Legacy Streamlit |

All three share `~/.fin/` volume for the SQLite database.

## Codebase Navigation

To refresh the codemap: `python scripts/generate_codemap.py`

## Architecture

### Architecture Patterns

**Broker API Pattern**: REST API-based broker clients using `BrokerAPIClient` base class. See @scrapers/base/broker_base.py for details.

**Credit Card Scrapers (Hybrid Selenium + API)**:
- Two-phase approach: Selenium login/token extraction → Direct API calls for data
- Implementations: CAL, Max, Isracard (see @scrapers/credit_cards/)
- Key quirks:
  - Login forms may be in iframes - must switch context before interacting
  - Token extraction via Chrome performance logging (`goog:loggingPrefs`)
  - Session storage holds card info and auth tokens (JSON format)
- Institution-specific:
  - **CAL**: iframe login, token in network logs or session storage
  - **Max**: Multiple transaction plan types, different API structure
  - **Isracard**: Uses last 6 digits of card + user ID, handles password change prompts
- See @plans/MULTI_ACCOUNT_PLAN.md for multi-account support

**Pension MFA Automation**:
- Modular components: `EmailMFARetriever` (IMAP), `MFAHandler` (code entry), `SmartWait` (timing)
- Institution-specific flows: Migdal (6-field MFA), Phoenix (single-field MFA)
- See @scrapers/base/ and @plans/SCRAPER_REFACTORING_PLAN.md for implementation details

**Services Layer**: Business logic separated from scrapers. Database operations, orchestration, tagging, analytics. See @plans/SERVICE_REFACTORING_PLAN.md for architecture.


### Project Structure Overview

- `api/` - FastAPI REST backend (routers/, schemas/, auth.py, deps.py)
- `web/` - React SPA (src/api/, components/, pages/, contexts/, types/)
- `cli/` - Typer CLI (entry: main.py)
- `config/` - Settings, credentials, encryption
- `db/` - SQLAlchemy models, SQLite
- `services/` - Business logic layer
- `scrapers/` - Selenium + API data extraction
- `streamlit_app/` - Legacy Web UI
- `plans/` - Implementation plans and documentation

For detailed Python file/function navigation, see `.claude/codemap.md`


## FastAPI (`api/`)

### Key files
- `api/main.py` — app factory, CORS, mounts all routers, `/health`
- `api/auth.py` — `create_access_token()`, `decode_token()`, secret auto-created at `~/.fin/jwt_secret.key`
- `api/deps.py` — `get_db()`, `get_current_user()`, service factory functions (`get_analytics`, `get_budget_service`, …)
- `api/routers/` — one file per domain: accounts, transactions, analytics, budget, tags, categories, rules, sync, auth_router
- `api/schemas/` — Pydantic v2 models mirroring db models; `common.py` has `PaginatedResponse[T]`

### Patterns
- **Sync handlers only** — all route functions are `def` (not `async def`) because SQLite doesn't support concurrent async access
- **SSE streaming** — `api/routers/sync.py` uses `asyncio.create_subprocess_exec` to run `fin-cli sync` and stream stdout as Server-Sent Events; auth token passed as URL query param (EventSource doesn't support headers)
- **DI via `deps.py`** — services are injected, never instantiated inside route handlers
- **Auth bypass** — when `is_auth_enabled()` returns False, `get_current_user` returns `"anonymous"` so routes still work without login

### Adding a new endpoint
1. Add Pydantic schema to `api/schemas/<domain>.py`
2. Add route function to `api/routers/<domain>.py` using existing service via `Depends(get_<service>)`
3. Router is already registered in `api/main.py`; no changes needed there

## React App (`web/src/`)

### Key patterns
- **API hooks** — all data fetching via TanStack Query in `web/src/api/`. Each file exports `useXxx()` query hooks and `useMutateXxx()` mutation hooks. Invalidate related query keys on mutation success.
- **`@/` alias** — maps to `src/`; use `@/components/...` not relative paths
- **Grid** — import from `@mui/material/Grid2` (not `Grid`) to get the `size={{ xs, md }}` API
- **Privacy masking** — use `<AmountDisplay amount={n} />` (never format currency inline); reads `maskBalances` from `PrivacyContext`
- **Hebrew/RTL** — wrap user-generated text in `<RtlText text={str} />`; it auto-detects Hebrew and sets `dir="rtl"`
- **Auth** — JWT stored in `localStorage`. `AuthContext` exposes `isAuthenticated`, `setTokens(access, refresh)`, `logout()`. `ProtectedRoute` in `App.tsx` redirects to `/login` if not authenticated.
- **Theme** — `createAppTheme(mode)` in `web/src/theme/index.ts`; primary indigo `#6366f1`, secondary violet `#8b5cf6`

### Key files
- `web/src/main.tsx` — provider tree: QueryClient → AppTheme → Privacy → Router → Auth
- `web/src/App.tsx` — lazy-loaded routes, `ProtectedRoute` wrapper
- `web/src/api/client.ts` — Axios instance with JWT interceptor + auto-refresh on 401
- `web/src/utils/format.ts` — `formatCurrency`, `formatDate`, `formatRelativeDate`, `amountColor`
- `web/src/utils/constants.ts` — `UnifiedCategory` enum, `getCategoryIcon(category)`

### Component conventions
- Files stay under ~150 lines; split complex pages into sub-components
- Cards in `components/cards/`, charts in `components/charts/`, layout in `components/layout/`
- `<EmptyState>`, `<LoadingSkeleton>`, `<AlertCard>` for consistent states

## Important Implementation Notes

### General Guidelines
- **Timing is critical**: MFA flows have multiple configurable delays to handle async operations and loader overlays
- **Selector fallbacks**: All element lookups support primary + fallback selectors for robustness
- **Email polling**: `wait_for_mfa_code_with_delay()` waits `email_delay` seconds before checking emails
- **Human-like behavior**: Character-by-character typing with delays to avoid detection
- **Session management**: Always call `cleanup()` to properly close browser and email connections

### Python Principles
- **DRY**: Extract duplicated logic into reusable functions
- **KISS**: Prefer straightforward solutions over clever ones
- **SIMPLE**: Minimal code to solve the actual problem, no speculative features
- Avoid premature abstraction - three similar lines beats a premature helper

### CLI Patterns

**Date Parsing**: Use `parse_date_range()` from `cli/utils.py` for commands with `--from`/`--to` options:
```python
from cli.utils import parse_date_range

from_date_obj, to_date_obj = parse_date_range(from_date, to_date)
```

**Service Context Managers**: Use `get_analytics()` and `get_db_session()` from `cli/utils.py` for automatic resource cleanup:
```python
from cli.utils import get_analytics, get_db_session

# For analytics queries
with get_analytics() as analytics:
    data = analytics.get_transactions(...)

# For direct database access
with get_db_session() as db:
    service = SomeService(db)
    result = service.do_something()
```

**Why context managers?** Resources are automatically closed even if exceptions occur - no need for `try/finally: analytics.close()`.

**Progress Spinner**: Use `spinner()` from `cli/utils.py` for long-running operations:
```python
from cli.utils import spinner

with spinner("Fetching data..."):
    data = fetch_data()
# Spinner automatically clears when done
```

**Output Utilities**: Use standardized output functions from `cli/utils.py`:
```python
from cli.utils import print_success, print_error, print_warning, print_info

print_success("Operation completed")  # ✓ green
print_error("Something failed")       # ✗ red
print_warning("Check this")           # ⚠ yellow
print_info("FYI")                     # ℹ blue
```

**When to use what:**
- `print_success/error/warning/info` - Simple status messages
- `console.print()` - Complex formatting (tables, panels, custom markup)

### Testing

**When to Write Tests**:
- After implementing new service methods or CLI commands
- When fixing bugs (write a failing test first that reproduces the issue)
- When modifying business logic in `services/`

**Unit Tests**: Follow @.claude/rules/python-unit-tests.md
- Location: `tests/services/`, `tests/scrapers/`
- Target: Services layer (`services/`), credit card scrapers (`scrapers/credit_cards/`)
- Uses in-memory SQLite with factory functions from `tests/conftest.py`

**Integration Tests**: See @plans/INTEGRATION_TESTING_PLAN.md
- Location: `tests/integration/`
- Target: CLI commands, multi-service workflows
- Mock scrapers, use real DB
- Fixtures: `tests/integration/conftest.py`

**Smoke Tests**: Verify imports work
- Location: `tests/smoke/`
- Catch missing dependencies, circular imports

**Running Tests**:
```bash
pytest                          # All tests
pytest tests/services -v        # Unit tests only
pytest tests/integration -v     # Integration tests only
pytest tests/smoke -v           # Smoke tests only
pytest -m integration           # Integration tests by marker
pytest --cov=services           # With coverage
pytest -k "test_sync"           # By name pattern
```

### Package Exports

**Keep `__all__` updated**: When adding new modules to a package, update the `__init__.py`:
- `cli/commands/__init__.py` - All command modules
- `services/__init__.py` - All service classes
- `scrapers/*/` - All scraper classes

This ensures IDE autocomplete works and documents the public API.

### Database and Services
- **SQLite database**: `~/.fin/financial_data.db` (initialized via `fin-cli init`)
- **Services layer**: Use services (not scrapers directly) for business logic
- **Transaction deduplication**: Database handles via unique constraints on external IDs
- **Migrations**: Run `fin-cli maintenance migrate` after schema changes (idempotent, safe to run multiple times)

### Streamlit UI Patterns
- **Shared CSS**: Call `apply_theme()` from `components/theme.py` at the top of each page - it loads shared styles from `styles/main.css` automatically.
- **Privacy-aware formatting**: Always use `format_amount_private()` from `session.py` for financial amounts (balances, totals, transactions). Never use `format_currency()` directly - it ignores the `mask_balances` privacy setting.
- **Display wrappers**: Use `get_accounts_display()` from `session.py` for accounts with pre-formatted balance fields (respects privacy settings).
- **Exception handling**: For database queries, catch `SQLAlchemyError` first, then `Exception` as fallback. Always log exceptions for debugging:
  ```python
  from sqlalchemy.exc import SQLAlchemyError
  import logging
  logger = logging.getLogger(__name__)

  try:
      result = session.query(...).all()
  except SQLAlchemyError as e:
      logger.error(f"Database error: {e}")
      st.error("Database operation failed")
  except Exception as e:
      logger.exception(f"Unexpected error: {e}")
      st.error(f"Error: {e}")
  ```
- **Shared sidebar**: Use `render_minimal_sidebar()` from `components/sidebar.py` - ensures consistent privacy toggle and stats across all pages.
- **Complex HTML rendering**: Don't use `st.markdown(unsafe_allow_html=True)` for nested HTML - Streamlit's sanitizer corrupts it. Use `streamlit.components.v1.html()` instead. See `components/cards.py` for reusable card components.
- **Mobile support**: Use `detect_mobile()` and `is_mobile()` from `utils/mobile.py` at page top. Render mobile view with early `st.stop()` when mobile detected. Mobile components in `components/mobile_ui.py`.

### Category System
Three-field hierarchy with `effective_category` property returning first non-null:
1. `user_category` - Manual override (set by user or rules)
2. `category` - Normalized via `CategoryMapping` (provider) or `MerchantMapping` (description pattern)
3. `raw_category` - Original from provider API (CAL, Max only; Isracard doesn't provide)

**Sync flow**: Transactions with `raw_category` use provider mappings; transactions without use merchant mappings.