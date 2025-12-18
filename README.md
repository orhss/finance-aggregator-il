# Financial Data Aggregator

Python automation framework for extracting financial data from Israeli institutions (brokers, pension funds, and credit cards).

## Features

- **Multi-source support**: Brokers, pension funds, and credit card companies
- **MFA automation**: Email-based MFA code retrieval and automated entry
- **Selenium-based scraping**: Human-like browser automation
- **API integration**: Direct API calls where available (CAL credit cards, Excellence broker)
- **Standardized data models**: Unified transaction and balance models across all sources

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

### CAL Credit Card Scraper

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

## Future Development

See `CLI_PLAN.md` for the planned unified CLI interface that will:
- Store all data in SQLite database
- Provide commands for syncing, querying, and exporting data
- Generate analytics and reports
- Support scheduled synchronization

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

3. **Service Layer** (planned):
   - Unified interface for all scrapers
   - Database integration
   - Transaction deduplication

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