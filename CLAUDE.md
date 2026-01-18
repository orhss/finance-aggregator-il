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

## Architecture

### Architecture Patterns

**Broker API Pattern**: REST API-based broker clients using `BrokerAPIClient` base class. See @ scrapers/base/broker_base.py for details.

**Credit Card Scrapers (Hybrid Selenium + API)**:
- Two-phase approach: Selenium login/token extraction → Direct API calls for data
- Implementations: CAL, Max, Isracard (see @ scrapers/credit_cards/)
- Key quirk: Login forms may be in iframes, tokens extracted from network logs or session storage
- See @ plans/MULTI_ACCOUNT_PLAN.md for multi-account support details

**Pension MFA Automation**:
- Modular components: `EmailMFARetriever` (IMAP), `MFAHandler` (code entry), `SmartWait` (timing)
- Institution-specific flows: Migdal (6-field MFA), Phoenix (single-field MFA)
- See @ scrapers/base/ and @ plans/SCRAPER_REFACTORING_PLAN.md for implementation details

**Services Layer**: Business logic separated from scrapers. Database operations, orchestration, tagging, analytics. See @ plans/SERVICE_REFACTORING_PLAN.md for architecture.


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
├── streamlit_app/          # Streamlit web UI
│   ├── app.py             # Main entry point
│   ├── pages/             # Multi-page app pages
│   ├── components/        # Reusable UI components
│   └── utils/             # UI utilities
├── plans/                  # Implementation plans and documentation
│   ├── CLI_PLAN.md
│   ├── MULTI_ACCOUNT_PLAN.md
│   ├── SCRAPER_REFACTORING_PLAN.md
│   ├── SERVICE_REFACTORING_PLAN.md
│   ├── STREAMLIT_UI_PLAN.md
│   └── TAGGING_DESIGN.md
├── examples/               # Usage examples
├── Dockerfile              # Docker container configuration
├── docker-compose.yml      # Docker Compose orchestration
├── .dockerignore          # Files excluded from Docker build
├── .env                    # Environment variables (dev only)
├── requirements.txt        # Python dependencies
├── setup.py               # Package setup for CLI installation
└── README.md              # User documentation
```


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