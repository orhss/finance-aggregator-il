# finance-aggregator-il

Python automation framework for extracting financial data from Israeli institutions (brokers, pension funds, and credit cards).

## Features

- **Multi-source support**: Brokers, pension funds, and credit card companies
- **MFA automation**: Email-based MFA code retrieval and automated entry
- **Selenium-based scraping**: Human-like browser automation
- **API integration**: Direct API calls where available (CAL credit cards, Excellence broker)
- **Standardized data models**: Unified transaction and balance models across all sources

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
```

## Supported Institutions

### Brokers
- **Excellence (ExtradePro)** - REST API client

### Pension Funds
- **Migdal** - Selenium + Email MFA
- **Phoenix** - Selenium + Email MFA

### Credit Cards
- **CAL (Visa CAL)** - Hybrid Selenium login + API data fetching

## Project Structure

```
Fin/
├── scrapers/              # All scraper implementations
│   ├── base/              # Abstract base classes
│   │   ├── broker_base.py
│   │   └── pension_base.py
│   ├── brokers/           # Broker implementations
│   │   └── excellence_broker_client.py
│   ├── pensions/          # Pension fund implementations
│   │   ├── migdal_pension_client.py
│   │   └── phoenix_pension_client.py
│   └── credit_cards/      # Credit card implementations
│       └── cal_credit_card_client.py
├── examples/              # Usage examples
│   └── example_cal_usage.py
├── .env                   # Environment variables (credentials)
├── requirements.txt       # Python dependencies
├── CLAUDE.md             # Development guide for Claude Code
└── CLI_PLAN.md           # Planned CLI interface design
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

   Or set individual credentials:
   ```bash
   fin-cli config set cal.username "myuser"
   fin-cli config set cal.password "mypass"
   fin-cli config set email.address "user@gmail.com"
   ```

### Option 2: Manual Installation (for development)

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

   # Migdal Pension
   MIGDAL_USER_ID=your_id

   # Phoenix Pension
   PHOENIX_USER_ID=your_id

   # CAL Credit Card
   CAL_USERNAME=your_username
   CAL_PASSWORD=your_password

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
fin-cli sync excellence   # Excellence broker
fin-cli sync migdal      # Migdal pension
fin-cli sync phoenix     # Phoenix pension
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

#### Maintenance Commands
```bash
# Create database backup
fin-cli maintenance backup
fin-cli maintenance backup --output /path/to/backup.db

# Clean old data
fin-cli maintenance cleanup --older-than 365
fin-cli maintenance cleanup --older-than 180 --dry-run  # Preview what will be deleted
fin-cli maintenance cleanup --older-than 90 --yes       # Skip confirmation

# Verify database integrity
fin-cli maintenance verify
```

### Programmatic Usage

You can also use the scrapers directly in Python code:

#### CAL Credit Card Scraper

```python
from scrapers.credit_cards import CALCreditCardScraper, CALCredentials

credentials = CALCredentials(
    username="your_username",
    password="your_password"
)

scraper = CALCreditCardScraper(credentials, headless=True)
accounts = scraper.scrape(months_back=3)

for account in accounts:
    print(f"Card {account.account_number}: {len(account.transactions)} transactions")
    for txn in account.transactions:
        print(f"  {txn.date[:10]} | {txn.description} | {txn.charged_amount}")
```

### Excellence Broker

```python
from scrapers.brokers import ExtraDeProAPIClient
from scrapers.base import LoginCredentials

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

### Migdal Pension

```python
from scrapers.pensions import MigdalEmailMFARetriever, MigdalSeleniumMFAAutomator
from scrapers.base import EmailConfig, MFAConfig

email_config = EmailConfig(
    email_address="your_email@gmail.com",
    password="your_app_password"
)

mfa_config = MFAConfig(
    sender_email="noreply@migdal.co.il",
    code_pattern=r'\b\d{6}\b'
)

retriever = MigdalEmailMFARetriever(email_config, mfa_config)
automator = MigdalSeleniumMFAAutomator(retriever, headless=False)

financial_data = automator.execute(
    site_url="https://my.migdal.co.il/mymigdal/process/login",
    credentials={'id': 'your_id'},
    selectors={
        'id_selector': '#username',
        'login_button_selector': 'button[type="submit"]',
        'email_label_selector': 'label[for="otpToEmail"]',
        'continue_button_selector': 'button.form-btn'
    }
)

print(f"Pension balance: {financial_data.get('pension_balance')}")
automator.cleanup()
```

## Examples

See the `examples/` folder for complete, runnable examples:
- `example_cal_usage.py` - CAL credit card transaction extraction with CSV export

## CLI Implementation Status

The unified CLI interface is feature-complete:
- ✅ **Phase 1**: Database initialization and credential management
- ✅ **Phase 2**: Data synchronization for all institutions
- ✅ **Phase 3**: Querying, reporting, and analytics
- ✅ **Phase 4**: Data export (CSV/JSON) and maintenance commands
- 📋 **Phase 5**: Testing and polish (in progress)

See `CLI_PLAN.md` for detailed implementation status and future enhancements.

## Architecture

### Design Patterns

- **Abstract Base Classes**: `BrokerAPIClient`, `EmailMFARetrieverBase`, `SeleniumMFAAutomatorBase`
- **Strategy Pattern**: Separate retriever and automator classes for different MFA flows
- **Template Method**: Base classes define automation flow structure
- **Hybrid Approach**: Selenium for login + direct API calls for data (CAL scraper)

### Key Components

1. **Base Layer** (`scrapers/base/`):
   - Abstract interfaces for all scraper types
   - Common DTOs and exceptions

2. **Implementation Layer** (`scrapers/{brokers,pensions,credit_cards}/`):
   - Institution-specific scraper implementations
   - MFA flow handling
   - Data extraction and normalization

3. **Service Layer**:
   - `BrokerService`, `PensionService`, `CreditCardService` - Data sync services
   - `AnalyticsService` - Querying and reporting
   - Database integration with SQLAlchemy
   - Transaction deduplication logic

## Security Notes

- **Never commit `.env` file** - Contains sensitive credentials
- **Email app passwords**: Use Gmail app-specific passwords, not your main password
- **Credentials storage**: Consider encrypted storage for production use
- **Browser automation**: Implement human-like delays to avoid detection

## Dependencies

- `requests` - HTTP client for API calls
- `selenium` - Browser automation
- `python-dotenv` - Environment variable management

## Development

For detailed development guidelines, see:
- `CLAUDE.md` - Architecture, patterns, and implementation notes
- `CLI_PLAN.md` - Future CLI interface design

## Contributing

1. Follow PEP 8 style guidelines
2. Use type hints for all function signatures
3. Prefer simple solutions (KISS principle)
4. Handle errors explicitly
5. Add tests for new features

## License

Private project - All rights reserved.