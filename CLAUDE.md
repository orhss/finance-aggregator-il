# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python automation framework for financial institutions (brokers, pension funds, and credit cards) using web scraping with Selenium and API clients. Implements MFA (Multi-Factor Authentication) automation via email retrieval.

**Project Structure**: Reorganized into modular packages - see `README.md` for usage examples.

**Future Development**: See `CLI_PLAN.md` for the planned CLI interface that will unify all scrapers into a single command-line tool with SQLite storage, analytics, and reporting capabilities.

## Development Commands

### Environment Setup
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration
- Environment variables are stored in `.env` (credentials for brokers/pension funds and email)
- Uses `python-dotenv` for loading configuration
- Chrome WebDriver is located in `chrome-linux64/` directory

## Architecture

### Base Class Hierarchy

**Broker API Pattern** (`broker_base.py`):
- `BrokerAPIClient` (ABC): Base for REST API-based brokers
- DTOs: `LoginCredentials`, `AccountInfo`, `BalanceInfo`
- `RequestsHTTPClient`: HTTP wrapper for API calls
- Concrete implementation: `ExtraDeProAPIClient` (excellence_broker_client.py)

**Credit Card Scraper** (`cal_credit_card_client.py`):
- `CALCreditCardScraper`: Automated transaction extraction for CAL (Visa CAL) credit cards
- Two-phase approach: Selenium login → API-based transaction fetching
- Extracts authorization token from browser session/network logs
- Fetches both pending and completed transactions via CAL API
- DTOs: `Transaction`, `CardAccount`, `Installments`
- Handles installment payments across multiple months

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

**Refactoring Status**: See `scraper_refactoring_plan.md` for detailed progress and migration guide.

### Key Design Patterns

**Strategy Pattern**: Separate retriever and automator classes allow different MFA flows per institution

**Template Method**: Base classes define automation flow structure:
- `login()` → `wait_for_mfa_prompt()` → `wait_for_mfa_code()` → `handle_mfa_flow()` → `extract_financial_data()`

**Individual vs Single Field MFA**:
- `handle_mfa_flow_individual_fields()`: 6 separate digit inputs (Migdal)
- `handle_mfa_flow()`: Single OTP field (Phoenix)

**Hybrid Selenium + API Pattern** (CAL scraper):
- Uses Selenium to handle complex login and extract session tokens
- Switches to direct API calls for efficient data retrieval
- Enables performance logging to capture network requests
- Extracts tokens from browser session storage or network logs

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

### CAL Credit Card Scraper Architecture

1. **Login Phase** (Selenium):
   - Opens CAL website and navigates to login iframe
   - Enters credentials in password login tab
   - Captures authorization token from SSO authentication request
   - Extracts card information from browser session storage

2. **Data Fetching Phase** (Direct API):
   - Uses extracted authorization token for API authentication
   - Required headers: `Authorization: CALAuthScheme {token}`, `X-Site-Id: {constant}`
   - Fetches pending transactions: `/getClearanceRequests`
   - Fetches completed transactions by month: `/getCardTransactionsDetails`
   - Default range: 18 months historical + 1 month forward

3. **Transaction Processing**:
   - Converts API responses to standardized `Transaction` objects
   - Handles installment payments (splits into monthly records)
   - Distinguishes between pending and completed transactions
   - Supports multiple cards per account

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

- **Timing is critical**: MFA flows have multiple configurable delays to handle async operations and loader overlays
- **Selector fallbacks**: All element lookups support primary + fallback selectors for robustness
- **Email polling**: `wait_for_mfa_code_with_delay()` waits `email_delay` seconds before checking emails
- **Human-like behavior**: Character-by-character typing with delays to avoid detection
- **Session management**: Always call `cleanup()` to properly close browser and email connections
- **Credentials**: Never commit `.env` file; use environment variables for sensitive data
- **CAL token extraction**: Enable Chrome performance logging (`goog:loggingPrefs`) to capture network requests for token extraction
- **CAL iframe handling**: Login form is in an iframe - must switch context before interacting
- **CAL session storage**: Card info and auth tokens are stored in browser session storage (JSON format)