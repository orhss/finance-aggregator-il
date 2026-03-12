# finance-aggregator-il

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

Python automation framework for extracting and managing financial data from Israeli institutions (brokers, pension funds, and credit cards).

## Features

- **Multi-source support**: Brokers, pension funds, and credit card companies
- **Multi-account support**: Multiple accounts per institution (e.g., personal + business cards)
- **MFA automation**: Email-based MFA code retrieval and automated entry
- **Hybrid scraping**: Selenium login + direct API calls for efficient data fetching
- **Category normalization**: Unified categories across all providers with custom mappings
- **Budget tracking**: Monthly budget goals with progress tracking
- **Rules engine**: Auto-categorize and tag transactions based on patterns
- **React SPA**: Mobile-first React + MUI dashboard with offline PWA support (replaces Streamlit)
- **REST API**: FastAPI backend with JWT auth, SSE sync streaming, and OpenAPI docs
- **Streamlit Web UI**: Legacy dashboard (kept during migration)
- **CLI & TUI**: Full command-line interface with interactive transaction browser
- **Data export**: Export to CSV/JSON with filtering options

## Quick Start

```bash
# 1. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install all dependencies (Python + Node)
make install

# 3. Initialize database
fin-cli init

# 4. Configure credentials
fin-cli config setup

# 5. Start the React app + API (two terminals, or make dev)
make api    # FastAPI on :8000
make web    # React on :3000

# — or with Docker (all three services) —
make up     # streamlit :8501, API :8000, React :3000

# 6. Sync your data
fin-cli sync all
# (or click "Sync" in the React UI at http://localhost:3000)
```

## Supported Institutions

### Brokers
- **Excellence (ExtradePro)** - REST API client
- **Meitav** - REST API client

### Pension Funds
- **Migdal** - Selenium + Email MFA
- **Phoenix** - Selenium + Email MFA

### Credit Cards
- **CAL (Visa CAL)** - Hybrid Selenium login + API data fetching
- **Max** - Hybrid Selenium login + API data fetching
- **Isracard** - Hybrid Selenium login + API data fetching

## Project Structure

```
Fin/
├── api/                   # FastAPI REST backend
│   ├── main.py            # App factory, CORS, health endpoint
│   ├── auth.py            # JWT create/verify
│   ├── deps.py            # Dependency injection (DB, services)
│   ├── routers/           # Route handlers (one file per domain)
│   └── schemas/           # Pydantic request/response models
├── web/                   # React SPA (TypeScript + MUI)
│   ├── src/
│   │   ├── api/           # TanStack Query hooks
│   │   ├── components/    # cards/, charts/, common/, layout/
│   │   ├── contexts/      # Auth, Privacy, Theme
│   │   ├── hooks/         # useDebounce, useDateRange, useLocalStorage
│   │   ├── pages/         # Dashboard, Transactions, Analytics, …
│   │   ├── theme/         # MUI theme (ported from Streamlit palette)
│   │   ├── types/         # TypeScript interfaces mirroring API schemas
│   │   └── utils/         # format.ts, rtl.ts, constants.ts
│   ├── Dockerfile         # Multi-stage: node build → nginx
│   ├── nginx.conf         # SPA fallback + /api proxy + SSE config
│   └── package.json
├── cli/                   # Typer CLI (entry: main.py)
│   ├── commands/          # accounts, budget, categories, sync, …
│   └── tui/               # Interactive transaction browser
├── config/                # Settings, credentials, encryption
├── db/                    # SQLAlchemy models, SQLite, migrations
├── services/              # Business logic (analytics, category, rules, …)
├── scrapers/              # Selenium + API data extraction
│   ├── base/              # SeleniumDriver, MFAHandler, EmailRetriever
│   ├── brokers/           # Excellence, Meitav
│   ├── pensions/          # Migdal, Phoenix
│   └── credit_cards/      # CAL, Max, Isracard
├── streamlit_app/         # Legacy web UI (kept during migration)
├── tests/                 # pytest suite (services/, integration/, smoke/)
├── plans/                 # Architecture documentation
├── Makefile               # Developer shortcuts
└── CLAUDE.md              # Development guide
```

## Installation

### Option 1: Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package manager. This is the recommended installation method.

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Clone and enter the repository**:
   ```bash
   git clone https://github.com/orhasson/finance-aggregator-il.git
   cd Fin
   ```

3. **Install dependencies**:
   ```bash
   uv sync
   ```

   This creates a virtual environment and installs all dependencies including the `fin-cli` command.

4. **Activate the environment** (or use `uv run`):
   ```bash
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   # Or run commands directly: uv run fin-cli init
   ```

5. **Initialize database**:
   ```bash
   fin-cli init
   ```

6. **Configure credentials**:
   ```bash
   fin-cli config setup
   ```

   Or manage accounts individually:
   ```bash
   # Add credit card accounts (supports multiple per institution)
   fin-cli config add-account cal --username "user" --password "pass" --label "Personal"
   fin-cli config add-account cal --username "user2" --password "pass2" --label "Business"

   # List configured accounts
   fin-cli config list-accounts cal

   # Set email for MFA
   fin-cli config set email.address "user@gmail.com"
   fin-cli config set email.password "app_password"
   ```

### Option 2: Docker Deployment (All Services)

Three services run together: React SPA, FastAPI, and legacy Streamlit.

```bash
# Start all services
make up
# or: docker compose up -d

# Initialize on first run
docker compose exec api fin-cli init
docker compose exec api fin-cli config setup
```

| Service | URL | Description |
|---|---|---|
| React SPA | http://localhost:3000 | Primary UI |
| FastAPI | http://localhost:8000 | REST API + Swagger at `/docs` |
| Streamlit | http://localhost:8501 | Legacy UI |

```bash
make logs    # Tail all logs
make down    # Stop everything
```

**Data persistence**: `~/.fin/` is mounted into containers — database and credentials survive restarts.

## React App & REST API

### Running locally

```bash
make install   # Install Python + Node deps (once)
make api       # FastAPI on http://localhost:8000
make web       # React dev server on http://localhost:3000
# or both at once:
make dev
```

The React dev server proxies `/api/*` → `localhost:8000`, so no CORS config needed during development.

### API docs

FastAPI auto-generates Swagger UI at **http://localhost:8000/docs** — useful for exploring endpoints and testing without the UI.

### Authentication

```bash
fin-cli auth add-user admin   # Add a user
fin-cli auth enable            # Require login
```

When auth is disabled the API issues tokens automatically (useful for local-only use). JWT tokens are stored in `localStorage` — compatible with Capacitor for future native mobile packaging.

### Build for production

```bash
make build-web   # Outputs to web/dist/
```

The production build is served by nginx (see `web/nginx.conf`) which proxies `/api/` to the FastAPI container.

## Self-Hosting Guide

### Network Access

To access the app from other devices on your local network (phones, tablets, other computers):

**Option 1: Docker (Recommended)**
Docker deployment is already configured for network access. Access via:
- This machine: http://localhost:8501
- Local network: http://YOUR_IP:8501

Find your IP with `hostname -I` (Linux) or `ipconfig getifaddr en0` (macOS).

**Option 2: Direct Streamlit**
```bash
# Run with network access
./scripts/run_server.sh

# Or manually
streamlit run streamlit_app/app.py --server.address=0.0.0.0 --server.port=8501
```

### Authentication (Recommended for Network Access)

When exposing the app on your local network, enable password protection:

```bash
# 1. Add a user
fin-cli auth add-user admin

# 2. Enable authentication
fin-cli auth enable

# Done! Users must now log in to access the app
```

**Managing Users**:
```bash
fin-cli auth list-users        # List all users
fin-cli auth add-user <name>   # Add new user
fin-cli auth remove-user <name> # Remove user
fin-cli auth change-password <name>  # Change password
fin-cli auth disable           # Disable authentication
fin-cli auth status            # Show current status
```

### Mobile Access

Access from your phone or tablet:
1. Connect to the same WiFi network
2. Open browser and navigate to `http://YOUR_SERVER_IP:8501`
3. The app automatically detects mobile devices and shows a touch-optimized UI

Bookmark the page for quick access, or add to your home screen:
- **iOS**: Share → Add to Home Screen
- **Android**: Menu → Add to Home Screen

### Security Recommendations

| Scenario | Recommendation |
|----------|----------------|
| Local-only (localhost) | Auth optional |
| Home network | Enable auth (multi-user households) |
| Port forwarded / Internet | Use VPN or reverse proxy with HTTPS |

**Important**: This app is designed for local/home network use. If you need internet access, use a VPN or set up a reverse proxy (nginx, Caddy) with HTTPS.

### Option 3: Using pip (Alternative)

If you prefer pip over uv:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/orhasson/finance-aggregator-il.git
   cd Fin
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install the package**:
   ```bash
   pip install -e ".[dev]"
   ```

4. **Configure credentials**:
   Create a `.env` file in the project root:
   ```env
   # Excellence Broker
   EXCELLENCE_USERNAME=your_username
   EXCELLENCE_PASSWORD=your_password

   # Meitav Broker
   MEITAV_USERNAME=your_username
   MEITAV_PASSWORD=your_password

   # Migdal Pension
   MIGDAL_USER_ID=your_id

   # Phoenix Pension
   PHOENIX_USER_ID=your_id

   # Credit Cards (single account)
   CAL_USERNAME=your_username
   CAL_PASSWORD=your_password

   MAX_USERNAME=your_username
   MAX_PASSWORD=your_password

   ISRACARD_USERNAME=your_username
   ISRACARD_PASSWORD=your_password

   # Credit Cards (multi-account, numbered)
   CAL_1_USERNAME=personal_user
   CAL_1_PASSWORD=personal_pass
   CAL_1_LABEL=Personal

   CAL_2_USERNAME=business_user
   CAL_2_PASSWORD=business_pass
   CAL_2_LABEL=Business

   # Email (for MFA)
   USER_EMAIL=your_email@gmail.com
   USER_EMAIL_APP_PASSWORD=your_app_password
   ```

## Usage

### CLI Usage (Recommended)

The CLI provides a unified interface for all scrapers:

#### Initialize and Configure
```bash
# Initialize database
fin-cli init

# Configure credentials interactively
fin-cli config setup

# View current configuration (masked)
fin-cli config show

# Set specific credentials
fin-cli config set cal.username "myuser"
fin-cli config set cal.password "mypass"
```

#### Sync Data
```bash
# Sync all sources
fin-cli sync all

# Sync specific institution
fin-cli sync cal          # CAL credit card
fin-cli sync max          # Max credit card
fin-cli sync isracard     # Isracard credit card
fin-cli sync excellence   # Excellence broker
fin-cli sync meitav       # Meitav broker
fin-cli sync migdal       # Migdal pension
fin-cli sync phoenix      # Phoenix pension

# Sync specific accounts (multi-account support)
fin-cli sync cal --account 0              # By index
fin-cli sync cal --account personal       # By label
fin-cli sync cal -a 0 -a 2                # Multiple accounts
```

#### Query Accounts
```bash
# List all accounts
fin-cli accounts list

# Filter by type or institution
fin-cli accounts list --type broker
fin-cli accounts list --institution cal

# Show detailed account info
fin-cli accounts show 1

# Show accounts summary
fin-cli accounts summary
```

#### Query Transactions
```bash
# List recent transactions (default: 50)
fin-cli transactions list

# Filter by date range
fin-cli transactions list --from 2024-01-01 --to 2024-12-31

# Filter by account
fin-cli transactions list --account 1

# Filter by status
fin-cli transactions list --status pending

# Filter by institution
fin-cli transactions list --institution cal

# Pagination
fin-cli transactions list --limit 100 --offset 50

# Show detailed transaction info
fin-cli transactions show 123
```

#### Reports and Analytics
```bash
# Overall statistics
fin-cli reports stats

# Monthly spending report
fin-cli reports monthly --year 2024 --month 12
fin-cli reports monthly  # Current month

# Category breakdown
fin-cli reports categories
fin-cli reports categories --from 2024-01-01 --to 2024-12-31

# Balance report for all accounts
fin-cli reports balances

# Balance history for specific account
fin-cli reports balances --account 1 --from 2024-01-01

# Sync history
fin-cli reports history --limit 20
fin-cli reports history --institution cal
fin-cli reports history --status success
```

#### Export Data
```bash
# Export transactions to CSV
fin-cli export transactions --output transactions.csv

# Export transactions to JSON
fin-cli export transactions --format json --output data.json

# Export balances
fin-cli export balances --output balances.csv
fin-cli export balances --format json --output balances.json

# Export accounts
fin-cli export accounts --output accounts.csv

# Export with filters
fin-cli export transactions --from 2024-01-01 --to 2024-12-31 --output txns_2024.csv
fin-cli export transactions --account 1 --status pending --output pending.json
```

#### Category Management
```bash
# Analyze category coverage
fin-cli categories analyze

# Interactive setup wizard
fin-cli categories setup

# List all mappings
fin-cli categories list
fin-cli categories list --provider cal

# Show unmapped categories
fin-cli categories unmapped

# Map a category
fin-cli categories map cal "מזון" groceries

# Merchant pattern mappings (for Isracard, etc.)
fin-cli categories suggest                    # Show uncategorized by merchant
fin-cli categories assign-wizard              # Interactive merchant categorization
fin-cli categories merchants                  # List saved merchant mappings
```

#### Budget Management
```bash
# View current month's budget progress
fin-cli budget show

# Set monthly budget
fin-cli budget set 5000

# Delete budget
fin-cli budget delete
```

#### Rules and Tags
```bash
# List auto-categorization rules
fin-cli rules list

# Add a rule
fin-cli rules add "wolt" --category food_delivery --tags delivery

# Apply rules to existing transactions
fin-cli rules apply

# List all tags
fin-cli tags list

# Rename or delete tags
fin-cli tags rename "old_tag" "new_tag"
fin-cli tags delete "unused_tag"
```

#### Maintenance Commands
```bash
# Create database backup
fin-cli maintenance backup
fin-cli maintenance backup --output /path/to/backup.db

# Apply database migrations
fin-cli maintenance migrate

# Clean old data
fin-cli maintenance cleanup --older-than 365
fin-cli maintenance cleanup --older-than 180 --dry-run  # Preview what will be deleted
fin-cli maintenance cleanup --older-than 90 --yes       # Skip confirmation

# Verify database integrity
fin-cli maintenance verify
```

#### Transaction Browser (TUI)
```bash
# Launch interactive transaction browser
fin-cli transactions browse

# Browse with filters
fin-cli transactions browse --from 2024-01-01 --to 2024-12-31
fin-cli transactions browse --account 1
```

**Keybindings:**
- `j/k` or `↑/↓` - Navigate transactions
- `Enter` - View details
- `e` - Edit category
- `t` - Add/remove tags
- `/` - Search
- `q` - Quit

### Streamlit Web UI

Launch the web dashboard:
```bash
# Direct launch
streamlit run streamlit_app/app.py

# With network access
streamlit run streamlit_app/app.py --server.address=0.0.0.0

# Or use the helper script
./scripts/run_server.sh
```

**Features:**
- Dashboard with balance overview and spending charts
- Transaction list with filtering and search
- Analytics with category breakdown and trends
- Category mapping management
- Mobile-friendly responsive design
- Privacy mode (mask balances)

### Programmatic Usage

You can also use the scrapers directly in Python code:

#### Credit Card Scrapers (CAL, Max, Isracard)

```python
from scrapers.credit_cards.cal_credit_card_client import CALCreditCardScraper, CALCredentials
# Also available: MaxCreditCardScraper, IsracardCreditCardScraper

credentials = CALCredentials(
    username="your_username",
    password="your_password"
)

with CALCreditCardScraper(credentials, headless=True) as scraper:
    accounts = scraper.scrape(months_back=3)

    for account in accounts:
        print(f"Card {account.card_number}: {len(account.transactions)} transactions")
        for txn in account.transactions:
            print(f"  {txn.transaction_date} | {txn.description} | {txn.charged_amount}")
```

### Broker Clients (Excellence, Meitav)

```python
from scrapers.brokers.excellence_broker_client import ExtraDeProAPIClient
from scrapers.base.broker_base import LoginCredentials

credentials = LoginCredentials(
    user="your_username",
    password="your_password"
)

client = ExtraDeProAPIClient(credentials)
client.login()
accounts = client.get_accounts()
balance = client.get_balance(accounts[0])
print(f"Total: {balance.total_amount}, P/L: {balance.profit_loss}")
client.logout()
```

### Pension Scrapers (Migdal, Phoenix)

```python
from scrapers.pensions.migdal_pension_client import MigdalEmailMFARetriever, MigdalSeleniumMFAAutomator
from scrapers.base.email_retriever import EmailConfig, MFAConfig

email_config = EmailConfig(
    email_address="your_email@gmail.com",
    password="your_app_password"
)

mfa_config = MFAConfig(
    sender_email="noreply@migdal.co.il",
    code_pattern=r'\b\d{6}\b'
)

with MigdalSeleniumMFAAutomator(
    user_id="your_id",
    email_config=email_config,
    mfa_config=mfa_config,
    headless=False
) as automator:
    financial_data = automator.login_and_extract()
    print(f"Pension balance: {financial_data.get('pension_balance')}")
```

## Examples

See the `examples/` folder for complete, runnable examples:
- `example_cal_usage.py` - CAL credit card transaction extraction with CSV export

## CLI Implementation Status

The unified CLI interface is **feature-complete**:
- ✅ Database initialization and credential management
- ✅ Data synchronization for all institutions (with multi-account support)
- ✅ Querying, reporting, and analytics
- ✅ Data export (CSV/JSON) and maintenance commands
- ✅ Category normalization and merchant mappings
- ✅ Budget tracking
- ✅ Rules engine and tagging
- ✅ Interactive transaction browser (TUI)
- ✅ Unit and integration tests

See `plans/` directory for architecture documentation.

## Architecture

### Design Patterns

- **Modular Composition**: Scraper components (driver, web actions, MFA handler) composed at runtime
- **Strategy Pattern**: Separate retriever and automator classes for different MFA flows
- **Service Layer**: Business logic separated from scrapers and UI
- **Hybrid Scraping**: Selenium for login + direct API calls for data fetching

### Key Components

1. **Scraper Layer** (`scrapers/`):
   - **Base components**: `SeleniumDriver`, `WebActions`, `MFAHandler`, `EmailMFARetriever`
   - **Institution implementations**: CAL, Max, Isracard, Excellence, Meitav, Migdal, Phoenix
   - **Utilities**: Retry with backoff, smart waits

2. **Service Layer** (`services/`):
   - `CreditCardService`, `BrokerService`, `PensionService` - Data sync with transaction management
   - `CategoryService` - Category normalization (provider + merchant mappings)
   - `RulesService` - Auto-categorization based on patterns
   - `AnalyticsService` - Queries, aggregations, reporting
   - `BudgetService` - Monthly budget tracking
   - `TagService` - Transaction tagging

3. **Database Layer** (`db/`):
   - SQLAlchemy models: `Account`, `Transaction`, `Balance`, `Tag`, `CategoryMapping`, `MerchantMapping`
   - SQLite storage with automatic migrations
   - Transaction deduplication via unique constraints

4. **UI Layer**:
   - **CLI** (`cli/`): Typer-based commands for all operations
   - **TUI** (`cli/tui/`): Interactive transaction browser with vim-like keybindings
   - **Web UI** (`streamlit_app/`): Mobile-friendly dashboard with charts and analytics

### Category System

Three-tier category hierarchy with `effective_category` property:
1. `user_category` - Manual override (highest priority)
2. `category` - Normalized via `CategoryMapping` (provider) or `MerchantMapping` (description pattern)
3. `raw_category` - Original from provider API

## Security Notes

- **Never commit `.env` file** - Contains sensitive credentials
- **Email app passwords**: Use Gmail app-specific passwords, not your main password
- **Credentials storage**: Consider encrypted storage for production use
- **Browser automation**: Implement human-like delays to avoid detection

## Dependencies

**Core:**
- `requests` - HTTP client for API calls
- `selenium` - Browser automation
- `sqlalchemy` - Database ORM
- `typer` - CLI framework
- `rich` - Terminal formatting

**Web UI:**
- `streamlit` - Web dashboard framework
- `plotly` - Interactive charts

**Development:**
- `pytest` - Testing framework
- `pytest-cov` - Test coverage
- `python-dotenv` - Environment variable management

## Development

### Setup
```bash
make install       # uv sync + npm install in web/

# Or manually:
uv sync            # Python deps
cd web && npm install  # Node deps
```

### Common commands
```bash
make api           # FastAPI :8000 (auto-reload)
make web           # React :3000 (HMR)
make dev           # Both in parallel
make test          # All Python tests
make lint          # ruff check
make build-web     # Production React build
make help          # Full command list
```

### Running Tests
```bash
uv run pytest                       # All tests
uv run pytest tests/services -v     # Unit tests only
uv run pytest tests/integration -v  # Integration tests
uv run pytest --cov=services --cov=cli  # With coverage
```

### Code Quality
```bash
uv run ruff check .
uv run ruff format .
cd web && npm run lint    # ESLint
```

### Documentation
- `CLAUDE.md` - Architecture, patterns, and implementation notes
- `plans/` - Implementation plans and architecture docs:
  - `CATEGORY_NORMALIZATION_PLAN.md` - Category system design
  - `MULTI_ACCOUNT_PLAN.md` - Multi-account support
  - `SCRAPER_REFACTORING_PLAN.md` - Scraper architecture
  - `SERVICE_REFACTORING_PLAN.md` - Service layer design
  - `INTEGRATION_TESTING_PLAN.md` - Testing strategy

## Contributing

1. Follow PEP 8 style guidelines
2. Use type hints for all function signatures
3. Prefer simple solutions (KISS principle)
4. Handle errors explicitly
5. Add tests for new features

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.

This means you are free to:
- Use, modify, and distribute this software
- Run it for any purpose

Under the following conditions:
- **Source code disclosure**: If you modify and deploy this software (including as a network service), you must make your source code available under the same license
- **License preservation**: Derivative works must also be licensed under AGPL-3.0

For commercial licensing options (e.g., using this in proprietary software without open-sourcing), please contact the maintainer.

See the [LICENSE](LICENSE) file for the full license text.