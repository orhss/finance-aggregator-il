# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Navigation Rule**: Always read `.claude/codemap.md` BEFORE using Glob/Grep for code files. The codemap contains the full Python file/function index. Use Glob only for non-code files (plans/*.md, config files, etc.).

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

### Database and Services
- **SQLite database**: `~/.fin/financial_data.db` (initialized via `fin-cli init`)
- **Services layer**: Use services (not scrapers directly) for business logic
- **Transaction deduplication**: Database handles via unique constraints on external IDs