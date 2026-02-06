# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Navigation Rule**: Always read `.claude/codemap.md` BEFORE using Glob/Grep for code files. The codemap contains the full Python file/function index. Use Glob only for non-code files (plans/*.md, config files, etc.).

## Project Overview

Python automation framework for financial institutions (brokers, pension funds, and credit cards) using web scraping with Selenium and API clients. Implements MFA (Multi-Factor Authentication) automation via email retrieval.

**Project Structure**: Reorganized into modular packages with fully implemented CLI, services layer, and SQLite database. See `README.md` for usage examples.

**CLI Implementation**: Fully implemented command-line interface with database storage, analytics, and reporting. See `plans/CLI_PLAN.md` for architecture details.

**Multi-Account Support**: Credit card scrapers support multiple accounts per institution (CAL, Max, Isracard). See `plans/MULTI_ACCOUNT_PLAN.md` for details.

**Category Normalization**: Two-tier system for unified categories:
- **Provider Mapping**: `CategoryMapping` maps provider's `raw_category` → unified `category` (CAL, Max)
- **Merchant Mapping**: `MerchantMapping` maps description patterns → unified `category` (Isracard - no provider categories)
- See @plans/CATEGORY_NORMALIZATION_PLAN.md for full implementation

## Development Commands

### Environment Setup
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies and CLI tool
pip install -r requirements.txt
pip install -e .  # Installs fin-cli command
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

### Docker Deployment
```bash
# Build and start services
docker-compose up -d

# Initialize database (first time only)
docker-compose exec fin fin-cli init
docker-compose exec fin fin-cli config setup

# Run CLI commands inside container
docker-compose exec fin fin-cli sync all
docker-compose exec fin fin-cli accounts list
docker-compose exec fin fin-cli transactions list

# View Streamlit UI
# Open browser to http://localhost:8501

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Configuration
- **Encrypted credentials**: Stored in `~/.fin/credentials.enc` (managed via `fin-cli config`)
- **Environment variables**: Fallback option in `.env` (for development)
- **Configuration directory**: `~/.fin/` (config.json, credentials.enc, .key, financial_data.db)
- Chrome WebDriver is located in `chrome-linux64/` directory

### Docker Configuration
- **Base image**: Python 3.12-slim
- **Exposed ports**: 8501 (Streamlit UI)
- **Data persistence**: Host `~/.fin/` directory mounted to `/root/.fin` in container
- **Services**: Combined Streamlit UI + CLI tool in single container
- **Health check**: Streamlit health endpoint monitored every 30s
- **Auto-restart**: Container restarts automatically unless explicitly stopped
- **Customization**: Edit `docker-compose.yml` to change data directory path

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

- `cli/` - Typer CLI (entry: main.py)
- `config/` - Settings, credentials, encryption
- `db/` - SQLAlchemy models, SQLite
- `services/` - Business logic layer
- `scrapers/` - Selenium + API data extraction
- `streamlit_app/` - Web UI
- `plans/` - Implementation plans and documentation

For detailed file/function navigation, see `.claude/codemap.md`


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

### Database and Services
- **SQLite database**: `~/.fin/financial_data.db` (initialized via `fin-cli init`)
- **Services layer**: Use services (not scrapers directly) for business logic
- **Transaction deduplication**: Database handles via unique constraints on external IDs
- **Migrations**: Run `fin-cli maintenance migrate` after schema changes (idempotent, safe to run multiple times)

### Streamlit UI Patterns
- **Shared CSS**: Call `apply_theme()` from `components/theme.py` at the top of each page - it loads shared styles from `styles/main.css` automatically.
- **Privacy-aware formatting**: Always use `format_amount_private()` from `session.py` for financial amounts (balances, totals, transactions). Never use `format_currency()` directly - it ignores the `mask_balances` privacy setting.
- **Display wrappers**: Use `get_accounts_display()`, `get_dashboard_stats_display()` etc. from `session.py` - they combine cached data with pre-formatted `_display` fields.
- **Shared sidebar**: Use `render_minimal_sidebar()` from `components/sidebar.py` - ensures consistent privacy toggle and stats across all pages.
- **Complex HTML rendering**: Don't use `st.markdown(unsafe_allow_html=True)` for nested HTML - Streamlit's sanitizer corrupts it. Use `streamlit.components.v1.html()` instead. See `components/cards.py` for reusable card components.
- **Mobile support**: Use `detect_mobile()` and `is_mobile()` from `utils/mobile.py` at page top. Render mobile view with early `st.stop()` when mobile detected. Mobile components in `components/mobile_ui.py`.

### Category System
Three-field hierarchy with `effective_category` property returning first non-null:
1. `user_category` - Manual override (set by user or rules)
2. `category` - Normalized via `CategoryMapping` (provider) or `MerchantMapping` (description pattern)
3. `raw_category` - Original from provider API (CAL, Max only; Isracard doesn't provide)

**Sync flow**: Transactions with `raw_category` use provider mappings; transactions without use merchant mappings.