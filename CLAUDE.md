# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python automation framework for financial institutions (brokers, pension funds, and credit cards) using web scraping with Selenium and API clients. Implements MFA (Multi-Factor Authentication) automation via email retrieval.

**Project Structure**: Reorganized into modular packages with fully implemented CLI, services layer, and SQLite database. See `README.md` for usage examples.

**CLI Implementation**: Fully implemented command-line interface with database storage, analytics, and reporting. See `plans/CLI_PLAN.md` for architecture details.

**Multi-Account Support**: Credit card scrapers support multiple accounts per institution (CAL, Max, Isracard). See `plans/MULTI_ACCOUNT_PLAN.md` for details.

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
```

### Configuration
- **Encrypted credentials**: Stored in `~/.fin/credentials.enc` (managed via `fin-cli config`)
- **Environment variables**: Fallback option in `.env` (for development)
- **Configuration directory**: `~/.fin/` (config.json, credentials.enc, .key, financial_data.db)
- Chrome WebDriver is located in `chrome-linux64/` directory

## Architecture

### Base Class Hierarchy

**Broker API Pattern** (`broker_base.py`):
- `BrokerAPIClient` (ABC): Base for REST API-based brokers
- DTOs: `LoginCredentials`, `AccountInfo`, `BalanceInfo`
- `RequestsHTTPClient`: HTTP wrapper for API calls
- Concrete implementation: `ExtraDeProAPIClient` (excellence_broker_client.py)

**Credit Card Scrapers** (Hybrid Selenium + API Pattern):
All credit card scrapers follow a two-phase approach: Selenium login → API-based data fetching

- **CAL** (`cal_credit_card_client.py`):
  - `CALCreditCardScraper` - Visa CAL credit cards
  - Extracts authorization token from browser session/network logs
  - API endpoints: `/getClearanceRequests`, `/getCardTransactionsDetails`

- **Max** (`max_credit_card_client.py`):
  - `MaxCreditCardScraper` - Max credit cards
  - Similar hybrid approach with token extraction
  - Handles multiple transaction plan types (regular, immediate charge, installments)

- **Isracard** (`isracard_credit_card_client.py`):
  - `IsracardCreditCardScraper` - Isracard credit cards
  - Uses card last 6 digits + user ID for authentication
  - Handles password change prompts

- **Common Features**:
  - DTOs: `Transaction`, `CardAccount`, `Installments`
  - Handles installment payments (splits into monthly records)
  - Fetches both pending and completed transactions
  - Supports multiple cards per account
  - **Multi-account support**: Multiple credentials per institution (see `plans/MULTI_ACCOUNT_PLAN.md`)

**Pension Automation Pattern** (NEW modular architecture):
- **New Base Classes** (recommended):
  - `scrapers/base/email_retriever.py`: `EmailMFARetriever` - Email/IMAP operations with context manager support
  - `scrapers/base/mfa_handler.py`: `MFAHandler` - MFA code entry with single/individual field patterns
  - `scrapers/utils/wait_conditions.py`: `SmartWait` - Condition-based waits replacing time.sleep()
  - `scrapers/utils/retry.py`: `retry_with_backoff` - Exponential backoff decorator
  - `scrapers/exceptions.py`: Structured exception hierarchy
  - `scrapers/config/logging_config.py`: Centralized logging configuration
- **Legacy Base Classes** (`pension_base.py` - DEPRECATED):
  - `EmailMFARetrieverBase` (ABC): DEPRECATED - use `EmailMFARetriever` instead
  - `SeleniumMFAAutomatorBase` (ABC): DEPRECATED - use modular components instead
- Configuration DTOs: `EmailConfig`, `MFAConfig`
- Concrete implementations (refactored to use new modules):
  - Migdal: `MigdalEmailMFARetriever` + `MigdalSeleniumAutomator`
  - Phoenix: `PhoenixEmailMFARetriever` + `PhoenixSeleniumAutomator`

**Refactoring Status**: See `plans/SCRAPER_REFACTORING_PLAN.md` for detailed progress and migration guide.

### Key Design Patterns

**Strategy Pattern**: Separate retriever and automator classes allow different MFA flows per institution

**Template Method**: Base classes define automation flow structure:
- `login()` → `wait_for_mfa_prompt()` → `wait_for_mfa_code()` → `handle_mfa_flow()` → `extract_financial_data()`

**Individual vs Single Field MFA**:
- `handle_mfa_flow_individual_fields()`: 6 separate digit inputs (Migdal)
- `handle_mfa_flow()`: Single OTP field (Phoenix)

**Hybrid Selenium + API Pattern** (Credit card scrapers):
- Uses Selenium to handle complex login and extract session tokens
- Switches to direct API calls for efficient data retrieval
- Enables performance logging to capture network requests
- Extracts tokens from browser session storage or network logs

**Services Layer Pattern** (Business logic separation):
- `services/` directory contains business logic for data synchronization and management
- Services handle database operations, scraper orchestration, and data processing
- Key services:
  - `credit_card_service.py`: Credit card sync with multi-account support
  - `broker_service.py`: Broker data synchronization
  - `pension_service.py`: Pension fund operations
  - `tag_service.py`: Transaction tagging system
  - `rules_service.py`: Automated rule-based tagging
  - `analytics_service.py`: Financial analytics and reporting
- See `plans/SERVICE_REFACTORING_PLAN.md` for architecture details

### MFA Flow Architecture

1. **Email Retrieval** (`EmailMFARetriever` in `scrapers/base/email_retriever.py`):
   - Connects to Gmail via IMAP with context manager support
   - Searches for MFA emails from specific senders
   - Extracts codes using regex patterns (overridden per institution)
   - Timing: `email_delay` before checking, `max_wait_time` for polling
   - Proper logging instead of print statements

2. **MFA Code Entry** (`MFAHandler` in `scrapers/base/mfa_handler.py`):
   - Supports both single-field and individual-field (6 digit) patterns
   - Human-like typing with configurable delays
   - Fallback selector support for robustness
   - Proper error handling with `MFAEntryError`

3. **Web Automation** (Legacy `SeleniumMFAAutomatorBase` - DEPRECATED):
   - Chrome headless browser automation
   - Human-like typing with delays (`enter_id_number_human_like`, `enter_mfa_code_human_like`)
   - Flexible selectors with fallback support
   - Handles loader overlays with configurable delays (`post_login_delay`, `mfa_submission_delay`)

4. **Institution-Specific Flows**:
   - **Migdal**: ID → Email option → Continue → MFA (6 fields) → No submit button
   - **Phoenix**: ID + Email → Login → MFA (single field) → Submit button

### Credit Card Scraper Architecture (Hybrid Pattern)

**General Flow** (applies to CAL, Max, Isracard):

1. **Login Phase** (Selenium):
   - Opens institution website and navigates to login form (may be in iframe)
   - Enters credentials (username/password or ID/card digits)
   - Handles authentication flow (redirects, tabs, etc.)
   - Captures authorization token from network requests or session storage
   - Extracts card/account information from browser session

2. **Data Fetching Phase** (Direct API):
   - Uses extracted authorization token for API authentication
   - Institution-specific headers and endpoints:
     - **CAL**: `Authorization: CALAuthScheme {token}`, endpoints: `/getClearanceRequests`, `/getCardTransactionsDetails`
     - **Max/Isracard**: Similar pattern with different endpoints
   - Fetches pending and completed transactions
   - Default range: 3-18 months historical + 1 month forward

3. **Transaction Processing**:
   - Converts API responses to standardized `Transaction` objects
   - Handles installment payments (splits into monthly records)
   - Distinguishes between pending and completed transactions
   - Supports multiple cards per account
   - Stores in SQLite database via `CreditCardService`

### Project Structure Overview

```
Fin/
├── cli/                    # CLI implementation (Typer-based)
│   ├── main.py            # Entry point
│   ├── commands/          # Command modules (init, config, sync, etc.)
│   └── tui/               # Terminal UI components
├── config/                 # Configuration management
│   ├── settings.py        # Credentials, encryption, multi-account
│   └── constants.py       # App constants
├── db/                     # Database layer
│   ├── models.py          # SQLAlchemy models
│   └── database.py        # Database setup and connection
├── services/               # Business logic layer
│   ├── credit_card_service.py
│   ├── broker_service.py
│   ├── pension_service.py
│   ├── tag_service.py
│   └── rules_service.py
├── scrapers/               # Data extraction layer
│   ├── base/              # Base classes and utilities
│   ├── brokers/           # Broker scrapers
│   ├── pensions/          # Pension fund scrapers
│   ├── credit_cards/      # Credit card scrapers (CAL, Max, Isracard)
│   ├── utils/             # Shared utilities
│   └── exceptions.py      # Custom exceptions
├── plans/                  # Implementation plans and documentation
│   ├── CLI_PLAN.md
│   ├── MULTI_ACCOUNT_PLAN.md
│   ├── SCRAPER_REFACTORING_PLAN.md
│   ├── SERVICE_REFACTORING_PLAN.md
│   └── TAGGING_DESIGN.md
├── examples/               # Usage examples
├── .env                    # Environment variables (dev only)
├── requirements.txt        # Python dependencies
├── setup.py               # Package setup for CLI installation
└── README.md              # User documentation
```

## Code Philosophy (from .cursor/rules)

- Follow PEP 8 style guidelines
- Use type hints for function signatures
- Prefer simple solutions over complex ones (KISS principle)
- Leverage Python's standard library before adding dependencies
- Keep functions small and focused on one task
- Handle errors explicitly, don't ignore exceptions

## Testing Guidelines (from .cursor/rules)

When generating unit tests:
- Use pytest with `pytest.mark.parametrize` and descriptive `id` values
- Mock external dependencies using `mocker` fixture (pytest-mock)
- Create fixtures for recurring mocks (prefix: `mock_` for fixtures, `mocked_` for variables)
- Test categories: Happy flow, Edge cases, Exceptions, Boundary values
- Use function-based tests (no test classes)
- Naming convention: `test_<function_name>_<scenario>`
- Limit to 2-3 tests per category

## Important Implementation Notes

### General Guidelines
- **Timing is critical**: MFA flows have multiple configurable delays to handle async operations and loader overlays
- **Selector fallbacks**: All element lookups support primary + fallback selectors for robustness
- **Email polling**: `wait_for_mfa_code_with_delay()` waits `email_delay` seconds before checking emails
- **Human-like behavior**: Character-by-character typing with delays to avoid detection
- **Session management**: Always call `cleanup()` to properly close browser and email connections

### Credential Management
- **Encrypted storage**: Use `fin-cli config` for encrypted credential management (~/.fin/credentials.enc)
- **Multi-account support**: Credit cards support multiple accounts per institution
  - List-based model with optional labels ("Personal", "Business")
  - Selection by index or label: `fin-cli sync cal --account 0` or `--account personal`
  - See `plans/MULTI_ACCOUNT_PLAN.md` for details
- **Environment variables**: Fallback for development (`.env` file, never commit)

### Credit Card Scrapers (CAL, Max, Isracard)
- **Token extraction**: Enable Chrome performance logging (`goog:loggingPrefs`) to capture network requests
- **Iframe handling**: Login forms may be in iframes - must switch context before interacting
- **Session storage**: Card info and auth tokens stored in browser session storage (JSON format)
- **Institution-specific quirks**:
  - **CAL**: Uses iframe for login, token in network logs or session storage
  - **Max**: Multiple transaction plan types, different API structure
  - **Isracard**: Uses last 6 digits of card + user ID, handles password change prompts

### Database and Services
- **SQLite database**: `~/.fin/financial_data.db` (initialized via `fin-cli init`)
- **Services layer**: Use services (not scrapers directly) for business logic
- **Transaction deduplication**: Database handles via unique constraints on external IDs