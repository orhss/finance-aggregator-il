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
- **Streamlit Web UI**: Modern, mobile-friendly dashboard for viewing and managing data
- **CLI & TUI**: Full command-line interface with interactive transaction browser
- **Data export**: Export to CSV/JSON with filtering options

## Quick Start

```bash
# 1. Install the CLI
pip install -e .

# 2. Initialize database
fin-cli init

# 3. Configure credentials
fin-cli config setup

# 4. Sync your data
fin-cli sync all

# 5. View your accounts
fin-cli accounts list

# 6. Check your transactions
fin-cli transactions list

# 7. View statistics
fin-cli reports stats

# 8. Set up category mappings (optional)
fin-cli categories analyze
fin-cli categories setup

# 9. Set a monthly budget (optional)
fin-cli budget set 5000
fin-cli budget show
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
├── cli/                   # Command-line interface
│   ├── commands/          # CLI command modules
│   │   ├── accounts.py    # Account listing and details
│   │   ├── budget.py      # Budget management
│   │   ├── categories.py  # Category mapping and normalization
│   │   ├── config.py      # Credential configuration
│   │   ├── export.py      # CSV/JSON export
│   │   ├── maintenance.py # Backup, cleanup, migrations
│   │   ├── reports.py     # Analytics and reports
│   │   ├── rules.py       # Auto-categorization rules
│   │   ├── sync.py        # Data synchronization
│   │   ├── tags.py        # Tag management
│   │   └── transactions.py # Transaction queries
│   ├── tui/               # Terminal UI (transaction browser)
│   └── main.py            # CLI entry point
├── config/                # Configuration management
│   ├── constants.py       # Application constants
│   └── settings.py        # Credentials and settings
├── db/                    # Database layer
│   ├── models.py          # SQLAlchemy models
│   ├── database.py        # Database initialization
│   └── migrations/        # Schema migrations
├── services/              # Business logic layer
│   ├── analytics_service.py   # Queries and reporting
│   ├── budget_service.py      # Budget tracking
│   ├── category_service.py    # Category normalization
│   ├── credit_card_service.py # Credit card sync
│   ├── broker_service.py      # Broker sync
│   ├── pension_service.py     # Pension sync
│   ├── rules_service.py       # Auto-categorization
│   └── tag_service.py         # Tag management
├── scrapers/              # Financial institution scrapers
│   ├── base/              # Modular base components
│   │   ├── broker_base.py     # REST API client base
│   │   ├── email_retriever.py # IMAP MFA code retrieval
│   │   ├── mfa_handler.py     # MFA code entry
│   │   ├── pension_automator.py # Pension login flows
│   │   ├── selenium_driver.py # WebDriver management
│   │   └── web_actions.py     # Form filling, clicking
│   ├── brokers/           # Excellence, Meitav
│   ├── pensions/          # Migdal, Phoenix
│   ├── credit_cards/      # CAL, Max, Isracard
│   └── utils/             # Retry, smart waits
├── streamlit_app/         # Web UI
│   ├── views/             # Page views
│   ├── components/        # Reusable UI components
│   ├── utils/             # Formatting, caching
│   └── app.py             # Main dashboard
├── tests/                 # Test suite
│   ├── services/          # Unit tests
│   ├── integration/       # CLI integration tests
│   └── smoke/             # Import smoke tests
├── plans/                 # Implementation documentation
├── requirements.txt       # Python dependencies
└── CLAUDE.md              # Development guide
```

## Installation

### Option 1: CLI Installation (Recommended)

1. **Clone the repository**:
   ```bash
   cd Fin
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install the package**:
   ```bash
   pip install -e .
   ```

   This installs the CLI tool as `fin-cli` command.

4. **Initialize database**:
   ```bash
   fin-cli init
   ```

5. **Configure credentials**:
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

### Option 2: Docker Installation (Easy Deployment)

1. **Prerequisites**:
   - Docker and Docker Compose installed

2. **Create data directory** (if using existing database):
   ```bash
   mkdir -p ~/.fin
   # Copy your existing financial_data.db, credentials.enc, etc. to ~/.fin/
   ```

3. **Start the application**:
   ```bash
   docker-compose up -d
   ```

4. **Initialize database** (for new installations):
   ```bash
   docker-compose exec fin fin-cli init
   docker-compose exec fin fin-cli config setup
   ```

5. **Access the application**:
   - Streamlit UI: http://localhost:8501
   - CLI commands: `docker-compose exec fin fin-cli <command>`

6. **Stop the application**:
   ```bash
   docker-compose down
   ```

**Key Features**:
- **Data Persistence**: Your `~/.fin/` directory is mounted to the container, so all data (database, credentials) persists between restarts
- **Auto-restart**: Container restarts automatically unless explicitly stopped
- **Customization**: Edit `docker-compose.yml` to change the data directory path

**View Logs**:
```bash
docker-compose logs -f
```

**Run CLI Commands**:
```bash
# Sync all sources
docker-compose exec fin fin-cli sync all

# View accounts
docker-compose exec fin fin-cli accounts list

# View transactions
docker-compose exec fin fin-cli transactions list
```

**Custom Data Path**:
Edit `docker-compose.yml` and modify the volume path:
```yaml
volumes:
  - /custom/path:/root/.fin  # Change left side to your preferred path
```

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

### Option 3: Manual Installation (for development)

1. **Clone the repository**:
   ```bash
   cd Fin
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
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

### Running Tests
```bash
# All tests
pytest

# Unit tests only
pytest tests/services -v

# Integration tests
pytest tests/integration -v

# With coverage
pytest --cov=services --cov=cli
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