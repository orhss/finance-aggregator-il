# Financial Data Aggregator CLI - Implementation Plan

## Overview

Build a command-line interface to extract financial data from multiple sources (brokers, pension funds, credit cards) and store it in a SQLite database for unified access and analysis.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI Layer                            │
│  (fin-cli commands: sync, list, export, stats)              │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│                    Service Layer                             │
│  - BrokerService                                             │
│  - PensionService                                            │
│  - CreditCardService                                         │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│                   Database Layer                             │
│  SQLite with tables:                                         │
│  - accounts, transactions, sync_history                      │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│                  Scraper Layer                               │
│  - ExtraDeProAPIClient (Excellence broker)                   │
│  - MigdalSeleniumAutomator (Migdal pension)                  │
│  - PhoenixSeleniumAutomator (Phoenix pension)                │
│  - CALCreditCardScraper (CAL credit cards)                   │
└─────────────────────────────────────────────────────────────┘
```

## Database Schema

### Tables

#### 1. `accounts`
Stores account information across all institutions.

```sql
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_type TEXT NOT NULL,  -- 'broker', 'pension', 'credit_card'
    institution TEXT NOT NULL,    -- 'excellence', 'migdal', 'phoenix', 'cal'
    account_number TEXT NOT NULL,
    account_name TEXT,
    card_unique_id TEXT,         -- For credit cards
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_synced_at TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    UNIQUE(account_type, institution, account_number)
);
```

#### 2. `transactions`
Unified transaction storage for all account types.

```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    transaction_id TEXT,          -- External transaction ID (if available)
    transaction_date DATE NOT NULL,
    processed_date DATE,
    description TEXT NOT NULL,
    original_amount REAL NOT NULL,
    original_currency TEXT NOT NULL,
    charged_amount REAL,
    charged_currency TEXT,
    transaction_type TEXT,        -- 'normal', 'installments', 'credit', 'debit'
    status TEXT,                  -- 'pending', 'completed'
    category TEXT,
    memo TEXT,
    installment_number INTEGER,
    installment_total INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    UNIQUE(account_id, transaction_id, transaction_date, description, original_amount)
);

CREATE INDEX idx_transactions_account ON transactions(account_id);
CREATE INDEX idx_transactions_date ON transactions(transaction_date);
CREATE INDEX idx_transactions_status ON transactions(status);
```

#### 3. `balances`
Snapshot of account balances (for broker/pension accounts).

```sql
CREATE TABLE balances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    balance_date DATE NOT NULL,
    total_amount REAL NOT NULL,
    available REAL,
    used REAL,
    blocked REAL,
    profit_loss REAL,
    profit_loss_percentage REAL,
    currency TEXT DEFAULT 'ILS',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    UNIQUE(account_id, balance_date)
);

CREATE INDEX idx_balances_account ON balances(account_id);
CREATE INDEX idx_balances_date ON balances(balance_date);
```

#### 4. `sync_history`
Track synchronization runs for debugging and monitoring.

```sql
CREATE TABLE sync_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_type TEXT NOT NULL,      -- 'all', 'broker', 'pension', 'credit_card'
    institution TEXT,
    status TEXT NOT NULL,         -- 'success', 'failed', 'partial'
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    records_added INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    error_message TEXT,
    metadata TEXT                 -- JSON with additional info
);

CREATE INDEX idx_sync_history_date ON sync_history(started_at);
CREATE INDEX idx_sync_history_status ON sync_history(status);
```

## CLI Commands

### 1. Configuration Setup
```bash
# Initialize database
fin-cli init

# Configure credentials interactively
fin-cli config

# Set specific credential
fin-cli config set cal.username "myuser"
fin-cli config set cal.password "mypass"

# Show current config (masked)
fin-cli config show
```

### 2. Data Synchronization
```bash
# Sync all sources
fin-cli sync --all

# Sync specific institution
fin-cli sync --broker excellence
fin-cli sync --pension migdal
fin-cli sync --pension phoenix
fin-cli sync --credit-card cal

# Sync with date range
fin-cli sync --credit-card cal --from 2024-01-01 --to 2024-12-31

# Sync with specific options
fin-cli sync --all --headless  # Run browsers in headless mode
fin-cli sync --all --dry-run   # Show what would be synced
```

### 3. Data Querying
```bash
# List all accounts
fin-cli accounts list

# Show account details
fin-cli accounts show <account_id>

# List transactions
fin-cli transactions list --account <account_id>
fin-cli transactions list --from 2024-01-01 --to 2024-12-31
fin-cli transactions list --status pending
fin-cli transactions list --institution cal

# Show transaction details
fin-cli transactions show <transaction_id>
```

### 4. Analytics & Reports
```bash
# Show summary statistics
fin-cli stats

# Monthly spending report
fin-cli report monthly --year 2024 --month 12

# Category breakdown
fin-cli report categories --from 2024-01-01

# Account balance history
fin-cli report balances --account <account_id>

# Export to CSV
fin-cli export transactions --output transactions.csv
fin-cli export balances --output balances.csv

# Export to JSON
fin-cli export transactions --format json --output data.json
```

### 5. Maintenance
```bash
# Show sync history
fin-cli history --limit 10

# Clean old data
fin-cli cleanup --older-than 365  # Remove data older than 365 days

# Verify data integrity
fin-cli verify

# Database backup
fin-cli backup --output backup.db
```

## File Structure

```
Fin/
├── cli/
│   ├── __init__.py
│   ├── main.py              # CLI entry point (Click/Typer framework)
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── init.py          # Database initialization
│   │   ├── config.py        # Configuration management
│   │   ├── sync.py          # Data synchronization
│   │   ├── accounts.py      # Account management
│   │   ├── transactions.py  # Transaction queries
│   │   ├── reports.py       # Analytics and reports
│   │   └── export.py        # Data export
│   └── utils.py             # CLI utilities (spinner, progress, etc.)
│
├── services/
│   ├── __init__.py
│   ├── broker_service.py    # Broker data sync service
│   ├── pension_service.py   # Pension data sync service
│   ├── credit_card_service.py # Credit card data sync service
│   └── analytics_service.py # Analytics and reporting
│
├── db/
│   ├── __init__.py
│   ├── models.py            # SQLAlchemy ORM models
│   ├── database.py          # Database connection and session management
│   ├── migrations.py        # Schema migrations (if needed)
│   └── queries.py           # Common database queries
│
├── config/
│   ├── __init__.py
│   ├── settings.py          # Configuration management
│   └── credentials.json     # Encrypted credentials storage
│
├── broker_base.py           # Existing
├── pension_base.py          # Existing
├── cal_credit_card_client.py # Existing
├── excellence_broker_client.py # Existing
├── migdal_pension_client.py # Existing
├── phoenix_pension_client.py # Existing
│
├── CLAUDE.md
├── CLI_PLAN.md
├── requirements.txt
└── setup.py                 # Package setup for CLI installation
```

## Technology Stack

### Core Dependencies
- **CLI Framework**: `typer` or `click` (typer is more modern, click is battle-tested)
- **Database ORM**: `SQLAlchemy` (or raw sqlite3 for simplicity)
- **Configuration**: `pydantic` + `python-dotenv`
- **Date handling**: `python-dateutil`
- **CLI UI**: `rich` (beautiful tables, progress bars, colors)
- **Credentials**: `keyring` or `cryptography` for secure storage

### Optional Dependencies
- **CSV/Excel export**: `pandas` (or built-in csv module)
- **JSON handling**: Built-in `json` module
- **Testing**: `pytest`, `pytest-mock`

## Implementation Phases

### Phase 1: Foundation (Core Infrastructure) ✓ COMPLETED
**Goal**: Set up database and basic CLI structure

**Tasks**:
1. ✅ Create database schema and models
2. ✅ Set up CLI framework (typer)
3. ✅ Implement `init` command (database initialization)
4. ✅ Implement `config` command (credential management)
5. ⏭️  Create base service layer (deferred to Phase 2)

**Files created**:
- ✅ `db/database.py`, `db/models.py`, `db/__init__.py`
- ✅ `cli/main.py`, `cli/commands/init.py`, `cli/commands/config.py`, `cli/utils.py`
- ✅ `config/settings.py`, `config/__init__.py`
- ✅ `setup.py` (for package installation)
- ✅ Updated `requirements.txt` with CLI dependencies

**Status**: Phase 1 is complete and ready for testing

### Phase 2: Data Integration (Sync Services) ✓ COMPLETED
**Goal**: Connect scrapers to database

**Tasks**:
1. ✅ Implement `BrokerService` (Excellence integration)
2. ✅ Implement `PensionService` (Migdal + Phoenix integration)
3. ✅ Implement `CreditCardService` (CAL integration)
4. ✅ Create unified `sync` command
5. ✅ Add transaction deduplication logic (built into services)

**Files created**:
- ✅ `services/__init__.py`
- ✅ `services/broker_service.py`
- ✅ `services/pension_service.py`
- ✅ `services/credit_card_service.py`
- ✅ `cli/commands/sync.py`
- ✅ Updated `cli/main.py` to include sync command
- ✅ Updated `cli/commands/__init__.py`

**Status**: Phase 2 is complete and ready for use

**Available sync commands**:
- `fin-cli sync all` - Sync all data sources
- `fin-cli sync excellence` - Sync Excellence broker
- `fin-cli sync migdal` - Sync Migdal pension
- `fin-cli sync phoenix` - Sync Phoenix pension
- `fin-cli sync cal` - Sync CAL credit card

### Phase 3: Querying & Reporting (User Interface) ✓ COMPLETED
**Goal**: Enable users to query and analyze data

**Tasks**:
1. ✅ Implement `accounts` commands (list, show, summary)
2. ✅ Implement `transactions` commands (list, show)
3. ✅ Implement `stats` command
4. ✅ Implement `report` commands (monthly, categories, balances, history)
5. ✅ Add rich formatting (tables, colors)

**Files created**:
- ✅ `cli/commands/accounts.py`
- ✅ `cli/commands/transactions.py`
- ✅ `cli/commands/reports.py`
- ✅ `services/analytics_service.py`

**Status**: Phase 3 is complete and ready for use

**Available commands**:
- `fin-cli accounts list` - List all accounts
- `fin-cli accounts show <id>` - Show account details
- `fin-cli accounts summary` - Show accounts summary
- `fin-cli transactions list` - List transactions with filters
- `fin-cli transactions show <id>` - Show transaction details
- `fin-cli reports stats` - Show overall statistics
- `fin-cli reports monthly` - Generate monthly report
- `fin-cli reports categories` - Show category breakdown
- `fin-cli reports balances` - Show balance report
- `fin-cli reports history` - Show sync history

### Phase 4: Export & Maintenance
**Goal**: Data export and system maintenance

**Tasks**:
1. Implement `export` command (CSV, JSON)
2. Implement `history` command
3. Implement `cleanup` command
4. Implement `backup` command
5. Add verification/integrity checks

**Files to create**:
- `cli/commands/export.py`
- `cli/commands/maintenance.py`

### Phase 5: Polish & Testing
**Goal**: Production-ready CLI

**Tasks**:
1. Comprehensive error handling
2. Progress indicators and better UX
3. Unit tests for services
4. Integration tests for CLI commands
5. Documentation and examples

## Configuration Management

### Credential Storage Options

**Option 1: Environment Variables (.env)**
```env
# .env
EXCELLENCE_USERNAME=xxx
EXCELLENCE_PASSWORD=xxx
MIGDAL_USER_ID=xxx
PHOENIX_USER_ID=xxx
CAL_USERNAME=xxx
CAL_PASSWORD=xxx
USER_EMAIL=xxx
USER_EMAIL_APP_PASSWORD=xxx
```

**Option 2: Encrypted Config File (Recommended)**
```json
// config/credentials.json (encrypted)
{
  "excellence": {
    "username": "encrypted_value",
    "password": "encrypted_value"
  },
  "migdal": {
    "user_id": "encrypted_value"
  },
  "phoenix": {
    "user_id": "encrypted_value",
    "email": "encrypted_value"
  },
  "cal": {
    "username": "encrypted_value",
    "password": "encrypted_value"
  },
  "email": {
    "address": "encrypted_value",
    "password": "encrypted_value"
  }
}
```

**Option 3: System Keyring (Most Secure)**
Use OS-native credential storage (macOS Keychain, Windows Credential Manager, Linux Secret Service).

## Error Handling Strategy

### Sync Failures
- Log errors to `sync_history` table
- Support partial success (some accounts succeed, others fail)
- Implement retry logic with exponential backoff
- Send notifications on critical failures (optional)

### Data Validation
- Validate all scraped data before insertion
- Check for duplicates using unique constraints
- Handle missing or malformed data gracefully
- Log validation errors for debugging

## Security Considerations

1. **Credential Storage**:
   - Never commit credentials to git
   - Use encryption for stored credentials
   - Consider system keyring integration

2. **Database Security**:
   - Restrict file permissions on SQLite file
   - Consider encryption at rest for sensitive data
   - Regular backups to secure location

3. **Logging**:
   - Never log credentials
   - Sanitize sensitive data in logs
   - Separate debug logs from production logs

## Future Enhancements

### Nice-to-Have Features
- Web dashboard (Flask/FastAPI + React)
- Automated scheduling (cron-like sync)
- Email/SMS notifications for large transactions
- Budget tracking and alerts
- Multi-currency support with exchange rates
- Data visualization (charts, graphs)
- Machine learning for transaction categorization
- API for third-party integrations
- Multi-user support with authentication

### Additional Data Sources
- More Israeli banks (Leumi, Hapoalim, Discount)
- More credit card companies (Max, Isracard)
- More pension funds (Clal, Harel)
- Investment platforms (eToro, Interactive Brokers)

## Success Metrics

### Phase 1 ✓ COMPLETED
- [x] Database initializes successfully
- [x] Credentials can be stored and retrieved
- [x] `fin-cli init` and `fin-cli config` work

### Phase 2 ✓ COMPLETED
- [x] Can sync all three data sources (broker, pension, credit card)
- [x] No duplicate transactions (deduplication logic implemented in services)
- [x] Sync history tracked correctly (SyncHistory table updated on each sync)

### Phase 3 ✓ COMPLETED
- [x] Can query transactions by date range
- [x] Can view account balances
- [x] Reports generate correctly

### Phase 4
- [ ] Can export to CSV and JSON
- [ ] Cleanup removes old data
- [ ] Backup creates valid database copy

## Timeline Estimate

- **Phase 1 (Foundation)**: 2-3 days
- **Phase 2 (Data Integration)**: 3-4 days
- **Phase 3 (Querying & Reporting)**: 2-3 days
- **Phase 4 (Export & Maintenance)**: 1-2 days
- **Phase 5 (Polish & Testing)**: 2-3 days

**Total**: 10-15 days (assuming part-time development)

## Next Steps

1. Review and approve this plan
2. Choose technology stack (typer vs click, SQLAlchemy vs raw sqlite)
3. Set up development environment
4. Begin Phase 1 implementation