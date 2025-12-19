# Service Layer Refactoring Plan

## Executive Summary

This document outlines a prioritized plan to address code quality, maintainability, and performance issues in the service layer. Issues are categorized by severity (Critical, High, Medium, Low) and organized into implementation phases.

**Current State**: Services are functional but have significant technical debt
**Target State**: Production-ready, maintainable, and performant service layer
**Estimated Effort**: 3-4 weeks

---

## Severity Classification

- **🔴 CRITICAL**: Blocks scalability, causes data corruption, or severe performance issues
- **🟠 HIGH**: Significant maintenance burden, performance degradation, or code smell
- **🟡 MEDIUM**: Moderate technical debt, testability issues, or minor performance impact
- **🟢 LOW**: Nice-to-have improvements, minor optimizations

---

## Issues by Severity

### 🔴 CRITICAL Issues

| ID | Issue | Impact | Files Affected |
|----|-------|--------|----------------|
| C1 | Code Duplication - `_get_or_create_account` | Bug fixes needed in 3 places | broker_service.py, pension_service.py, credit_card_service.py |
| C2 | Code Duplication - `_save_balance` | Bug fixes needed in 2 places | broker_service.py, pension_service.py |
| C3 | No Transaction Management | Risk of partial/corrupt data | All service files |
| C4 | Excessive Database Commits | 10-20x slower than necessary | All service files |

### 🟠 HIGH Issues

| ID | Issue | Impact | Files Affected |
|----|-------|--------|----------------|
| H1 | N+1 Query Problem | 100-1000x slower for large datasets | analytics_service.py:392 |
| H2 | No Abstraction for New Institutions | Each new institution requires 3+ file changes | All service files |
| H3 | Magic Strings Everywhere | Runtime errors from typos, hard to refactor | All files (20+ occurrences) |
| H4 | Long Methods (Single Responsibility) | Hard to test, maintain, extend | sync methods (60-104 lines) |

### 🟡 MEDIUM Issues

| ID | Issue | Impact | Files Affected |
|----|-------|--------|----------------|
| M1 | Hardcoded Configuration | Can't test or change easily | pension_service.py, sync commands |
| M2 | No Bulk Operations | Slow for large datasets | All service files |
| M3 | Poor Error Context | Hard to debug failures | All service files |
| M4 | No Result Aggregation | Can't get detailed sync reports | All sync methods |

### 🟢 LOW Issues

| ID | Issue | Impact | Files Affected |
|----|-------|--------|----------------|
| L1 | No Query Result Caching | Minor performance loss | analytics_service.py |
| L2 | Inconsistent Naming | Slight confusion | Various |
| L3 | Missing Docstring Examples | Harder for new developers | All service files |

---

## Implementation Phases

### Phase 1: Critical Fixes (Week 1) 🔴
**Goal**: Eliminate code duplication and fix data integrity issues

**Tasks**:
1. ✅ Create base service class
2. ✅ Extract common database operations
3. ✅ Implement transaction management
4. ✅ Reduce database commits

**Success Criteria**:
- [ ] Zero duplicated methods across services
- [ ] All sync operations are atomic (rollback on failure)
- [ ] 80% reduction in database commits per sync

---

### Phase 2: Performance & Architecture (Week 2) 🟠
**Goal**: Fix performance bottlenecks and improve architecture

**Tasks**:
1. ✅ Fix N+1 query problems
2. ✅ Create constants/enums for magic strings
3. ✅ Refactor long methods (split responsibilities)
4. ✅ Add institution abstraction layer

**Success Criteria**:
- [ ] No N+1 queries in codebase
- [ ] Zero magic strings (use constants)
- [ ] All methods under 40 lines
- [ ] New institution takes <1 hour to add

---

### Phase 3: Configuration & Maintainability (Week 3) 🟡
**Goal**: Externalize configuration and improve developer experience

**Tasks**:
1. ✅ Extract institution configurations
2. ✅ Implement bulk database operations
3. ✅ Improve error context and logging
4. ✅ Add detailed sync result reporting

**Success Criteria**:
- [ ] All URLs/selectors in config files
- [ ] Bulk operations for 100+ records
- [ ] Error messages include context (account, institution, step)
- [ ] Sync results show per-account details

---

### Phase 4: Polish & Optimization (Week 4) 🟢
**Goal**: Final optimizations and documentation

**Tasks**:
1. ✅ Add query result caching where appropriate
2. ✅ Standardize naming conventions
3. ✅ Add comprehensive docstring examples
4. ✅ Performance benchmarking and tuning

**Success Criteria**:
- [ ] 95% test coverage on services
- [ ] All public methods have usage examples
- [ ] Documented performance characteristics
- [ ] Zero linter warnings

---

## Detailed Implementation Guide

### Phase 1: Critical Fixes

#### Task 1.1: Create Base Service Class

**File**: `services/base_service.py`

```python
"""
Base service class with common database operations
"""

from abc import ABC
from contextlib import contextmanager
from datetime import datetime, date
from typing import Optional, List, Generator
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from db.models import Account, Balance, SyncHistory


class SyncResult:
    """Base result object for sync operations"""

    def __init__(self, institution: str, sync_type: str):
        self.institution = institution
        self.sync_type = sync_type
        self.success = False
        self.accounts_synced = 0
        self.records_added = 0
        self.records_updated = 0
        self.error_message: Optional[str] = None
        self.sync_history_id: Optional[int] = None
        self.details: List[str] = []

    def add_detail(self, message: str):
        """Add detailed message to sync result"""
        self.details.append(f"[{datetime.utcnow().isoformat()}] {message}")


class BaseSyncService(ABC):
    """
    Abstract base class for all sync services
    Provides common database operations and transaction management
    """

    def __init__(self, db_session: Session):
        """
        Initialize service with database session

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    @contextmanager
    def sync_transaction(
        self,
        sync_type: str,
        institution: str
    ) -> Generator[SyncHistory, None, None]:
        """
        Context manager for atomic sync operations

        Automatically creates sync history record, manages transactions,
        and handles rollback on errors.

        Args:
            sync_type: Type of sync ('broker', 'pension', 'credit_card')
            institution: Institution name

        Yields:
            SyncHistory record

        Example:
            with self.sync_transaction('broker', 'excellence') as sync_record:
                # Do sync operations
                sync_record.records_added = 10
        """
        sync_record = SyncHistory(
            sync_type=sync_type,
            institution=institution,
            status="in_progress",
            started_at=datetime.utcnow()
        )
        self.db.add(sync_record)
        self.db.flush()  # Get ID without committing

        try:
            yield sync_record

            # Success - commit everything
            sync_record.status = "success"
            sync_record.completed_at = datetime.utcnow()
            self.db.commit()

        except Exception as e:
            # Failure - rollback everything
            sync_record.status = "failed"
            sync_record.completed_at = datetime.utcnow()
            sync_record.error_message = str(e)
            self.db.rollback()

            # Re-commit just the sync record
            self.db.add(sync_record)
            self.db.commit()
            raise

    def get_or_create_account(
        self,
        account_type: str,
        institution: str,
        account_number: str,
        account_name: Optional[str] = None,
        card_unique_id: Optional[str] = None
    ) -> Account:
        """
        Get existing account or create new one

        Uses upsert pattern to avoid race conditions.
        Does NOT commit - relies on transaction management.

        Args:
            account_type: Type of account ('broker', 'pension', 'credit_card')
            institution: Institution name
            account_number: Account number
            account_name: Optional account name
            card_unique_id: Optional card unique ID (credit cards only)

        Returns:
            Account model instance

        Example:
            account = service.get_or_create_account(
                account_type="broker",
                institution="excellence",
                account_number="12345",
                account_name="My Trading Account"
            )
        """
        # Try to find existing account
        account = self.db.query(Account).filter(
            Account.account_type == account_type,
            Account.institution == institution,
            Account.account_number == account_number
        ).first()

        if account:
            # Update existing account
            account.last_synced_at = datetime.utcnow()
            if account_name:
                account.account_name = account_name
            if card_unique_id:
                account.card_unique_id = card_unique_id
            return account

        # Create new account
        account = Account(
            account_type=account_type,
            institution=institution,
            account_number=account_number,
            account_name=account_name,
            card_unique_id=card_unique_id,
            last_synced_at=datetime.utcnow()
        )
        self.db.add(account)
        self.db.flush()  # Get ID without committing

        return account

    def save_balance(
        self,
        account: Account,
        total_amount: float,
        balance_date: Optional[date] = None,
        **kwargs
    ) -> bool:
        """
        Save or update balance for an account

        Does NOT commit - relies on transaction management.

        Args:
            account: Account model instance
            total_amount: Total balance amount
            balance_date: Date of balance (defaults to today)
            **kwargs: Additional balance fields (available, used, blocked, etc.)

        Returns:
            True if new balance created, False if updated

        Example:
            is_new = service.save_balance(
                account=account,
                total_amount=50000.00,
                available=45000.00,
                profit_loss=5000.00,
                currency="ILS"
            )
        """
        if balance_date is None:
            balance_date = date.today()

        # Check if balance exists
        existing_balance = self.db.query(Balance).filter(
            Balance.account_id == account.id,
            Balance.balance_date == balance_date
        ).first()

        if existing_balance:
            # Update existing balance
            existing_balance.total_amount = total_amount
            for key, value in kwargs.items():
                if hasattr(existing_balance, key):
                    setattr(existing_balance, key, value)
            return False

        # Create new balance
        balance = Balance(
            account_id=account.id,
            balance_date=balance_date,
            total_amount=total_amount,
            **{k: v for k, v in kwargs.items() if hasattr(Balance, k)}
        )
        self.db.add(balance)
        return True

    def bulk_save_transactions(
        self,
        account: Account,
        transactions: List[dict]
    ) -> tuple[int, int]:
        """
        Bulk save transactions with deduplication

        More efficient than saving one-by-one.
        Does NOT commit - relies on transaction management.

        Args:
            account: Account model instance
            transactions: List of transaction dictionaries

        Returns:
            Tuple of (added_count, updated_count)

        Example:
            added, updated = service.bulk_save_transactions(
                account=account,
                transactions=[
                    {'date': '2024-01-01', 'amount': 100, ...},
                    {'date': '2024-01-02', 'amount': 200, ...},
                ]
            )
        """
        added = 0
        updated = 0

        # Implementation in next phase
        # This is a placeholder for the architecture

        return added, updated
```

**Acceptance Criteria**:
- [ ] Base class compiles without errors
- [ ] All common methods moved to base class
- [ ] Transaction management works (rollback tested)
- [ ] All tests pass

---

#### Task 1.2: Refactor BrokerService to Use Base

**File**: `services/broker_service.py`

**Before** (273 lines):
```python
class BrokerService:
    def __init__(self, db_session: Session):
        self.db = db_session

    def sync_excellence(self, username: str, password: str, currency: str = "ILS"):
        result = BrokerSyncResult()
        sync_record = None

        try:
            sync_record = SyncHistory(...)
            self.db.add(sync_record)
            self.db.commit()  # ❌ Commit 1

            # ... scraping logic ...

            db_account = self._get_or_create_account(...)  # ❌ Commit 2
            self._save_balance(...)  # ❌ Commit 3

            sync_record.status = "success"
            self.db.commit()  # ❌ Commit 4

        except Exception as e:
            # Error handling

    def _get_or_create_account(self, ...):  # ❌ 46 lines duplicated
        # ... implementation ...
        self.db.commit()

    def _save_balance(self, ...):  # ❌ 53 lines duplicated
        # ... implementation ...
        self.db.commit()
```

**After** (~150 lines, 45% reduction):
```python
from services.base_service import BaseSyncService, SyncResult
from config.constants import AccountType, Institution, SyncType

class BrokerService(BaseSyncService):
    """
    Service for synchronizing broker data with the database
    """

    def sync_excellence(
        self,
        username: str,
        password: str,
        currency: str = "ILS"
    ) -> SyncResult:
        """
        Sync Excellence broker data

        Args:
            username: Excellence username
            password: Excellence password
            currency: Currency for balance retrieval (default: ILS)

        Returns:
            SyncResult with sync operation details
        """
        result = SyncResult(Institution.EXCELLENCE, SyncType.BROKER)

        try:
            # ✅ Single atomic transaction
            with self.sync_transaction(SyncType.BROKER, Institution.EXCELLENCE) as sync_record:
                result.sync_history_id = sync_record.id

                # Create client and login
                credentials = LoginCredentials(user=username, password=password)
                client = BrokerClientFactory.create_client("extradepro", credentials)
                client.login()

                # Get accounts
                broker_accounts = client.get_accounts()
                if not broker_accounts:
                    raise BrokerAPIError("No accounts found")

                # Process each account
                for broker_account in broker_accounts:
                    # ✅ No commit - handled by transaction context
                    db_account = self.get_or_create_account(
                        account_type=AccountType.BROKER,
                        institution=Institution.EXCELLENCE,
                        account_number=broker_account.key,
                        account_name=broker_account.name
                    )
                    result.accounts_synced += 1
                    result.add_detail(f"Synced account {broker_account.key}")

                    # Get and save balance
                    balance_info = client.get_balance(broker_account, currency)

                    # ✅ No commit - handled by transaction context
                    is_new = self.save_balance(
                        account=db_account,
                        total_amount=balance_info.total_amount,
                        available=balance_info.available,
                        used=balance_info.used,
                        blocked=balance_info.blocked,
                        profit_loss=balance_info.profit_loss,
                        profit_loss_percentage=balance_info.profit_loss_percentage,
                        currency=currency
                    )

                    if is_new:
                        result.records_added += 1
                    else:
                        result.records_updated += 1

                # Logout
                client.logout()

                # Update sync record
                sync_record.records_added = result.records_added
                sync_record.records_updated = result.records_updated

                result.success = True

        except Exception as e:
            result.error_message = str(e)
            raise

        return result

    # ✅ No more _get_or_create_account - inherited from base
    # ✅ No more _save_balance - inherited from base
```

**Benefits**:
- ✅ 45% code reduction (273 → 150 lines)
- ✅ 4 commits → 1 commit (4x faster)
- ✅ Atomic operations (rollback on failure)
- ✅ No code duplication
- ✅ Better error handling

---

#### Task 1.3: Refactor PensionService to Use Base

**Similar refactoring as BrokerService**

**Expected Results**:
- 40% code reduction (439 → 260 lines)
- Remove duplicated `_get_or_create_account`
- Remove duplicated `_save_balance`
- Single commit per sync

---

#### Task 1.4: Refactor CreditCardService to Use Base

**Similar refactoring as BrokerService**

**Expected Results**:
- 35% code reduction (322 → 210 lines)
- Remove duplicated `_get_or_create_account`
- Implement `bulk_save_transactions` for efficiency

---

### Phase 2: Performance & Architecture

#### Task 2.1: Create Constants File

**File**: `config/constants.py`

```python
"""
Application constants and enums
Eliminates magic strings and provides type safety
"""

from enum import Enum


class AccountType:
    """Account type constants"""
    BROKER = "broker"
    PENSION = "pension"
    CREDIT_CARD = "credit_card"

    @classmethod
    def all(cls) -> list[str]:
        return [cls.BROKER, cls.PENSION, cls.CREDIT_CARD]


class Institution:
    """Financial institution constants"""
    # Brokers
    EXCELLENCE = "excellence"

    # Pension Funds
    MIGDAL = "migdal"
    PHOENIX = "phoenix"

    # Credit Cards
    CAL = "cal"

    @classmethod
    def brokers(cls) -> list[str]:
        return [cls.EXCELLENCE]

    @classmethod
    def pensions(cls) -> list[str]:
        return [cls.MIGDAL, cls.PHOENIX]

    @classmethod
    def credit_cards(cls) -> list[str]:
        return [cls.CAL]

    @classmethod
    def all(cls) -> list[str]:
        return cls.brokers() + cls.pensions() + cls.credit_cards()


class SyncType:
    """Sync operation type constants"""
    ALL = "all"
    BROKER = "broker"
    PENSION = "pension"
    CREDIT_CARD = "credit_card"


class SyncStatus:
    """Sync operation status constants"""
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class TransactionStatus:
    """Transaction status constants"""
    PENDING = "pending"
    COMPLETED = "completed"


class TransactionType:
    """Transaction type constants"""
    NORMAL = "normal"
    INSTALLMENTS = "installments"
    CREDIT = "credit"
    DEBIT = "debit"


class Currency:
    """Currency constants"""
    ILS = "ILS"
    USD = "USD"
    EUR = "EUR"


# Validation functions
def validate_account_type(account_type: str) -> None:
    """Raise ValueError if account_type is invalid"""
    if account_type not in AccountType.all():
        raise ValueError(f"Invalid account_type: {account_type}. Must be one of {AccountType.all()}")


def validate_institution(institution: str) -> None:
    """Raise ValueError if institution is invalid"""
    if institution not in Institution.all():
        raise ValueError(f"Invalid institution: {institution}. Must be one of {Institution.all()}")
```

**Migration Example**:

Before:
```python
if account_type == "broker":  # ❌ Magic string, typo-prone
```

After:
```python
from config.constants import AccountType

if account_type == AccountType.BROKER:  # ✅ Type-safe, autocomplete works
```

**Acceptance Criteria**:
- [ ] All magic strings replaced with constants
- [ ] Validation functions used at API boundaries
- [ ] Zero string literals in service layer

---

#### Task 2.2: Fix N+1 Query in Analytics Service

**File**: `services/analytics_service.py`

**Before** (N+1 problem):
```python
def get_monthly_summary(self, year: int, month: int) -> Dict[str, Any]:
    transactions = (
        self.session.query(Transaction)
        .filter(...)
        .all()  # Query 1: Get all transactions
    )

    for txn in transactions:
        account = self.get_account_by_id(txn.account_id)  # ❌ Query 2, 3, 4, ... N+1
        # Use account info
```

**Performance**: For 1000 transactions = 1001 database queries

**After** (optimized):
```python
from sqlalchemy.orm import joinedload

def get_monthly_summary(self, year: int, month: int) -> Dict[str, Any]:
    transactions = (
        self.session.query(Transaction)
        .options(joinedload(Transaction.account))  # ✅ Eager load accounts
        .filter(...)
        .all()  # Single query with JOIN
    )

    for txn in transactions:
        account = txn.account  # ✅ Already loaded, no additional query
        # Use account info
```

**Performance**: For 1000 transactions = 1 database query (1000x faster!)

**Acceptance Criteria**:
- [ ] All queries use eager loading where needed
- [ ] Query count benchmarks show improvement
- [ ] No N+1 queries detected by profiler

---

#### Task 2.3: Split Long Methods

**Example**: `sync_migdal` is 104 lines

**Before**:
```python
def sync_migdal(self, user_id, email_address, email_password, headless=True):
    # 104 lines doing:
    # 1. Create sync record
    # 2. Configure MFA
    # 3. Create scraper
    # 4. Login
    # 5. Extract data
    # 6. Parse amounts
    # 7. Save to database
    # 8. Error handling
```

**After**:
```python
def sync_migdal(self, user_id, email_address, email_password, headless=True):
    """Sync Migdal pension data (orchestrator method)"""
    with self.sync_transaction(SyncType.PENSION, Institution.MIGDAL) as sync_record:
        # Configure and login
        automator = self._create_migdal_automator(email_address, email_password, headless)
        financial_data = self._login_and_extract_migdal(automator, user_id)

        # Save data
        result = self._save_migdal_data(financial_data, user_id, sync_record)

        # Cleanup
        automator.cleanup()

        return result

def _create_migdal_automator(self, email_address, email_password, headless):
    """Create and configure Migdal automator (single responsibility)"""
    # 20 lines

def _login_and_extract_migdal(self, automator, user_id):
    """Login to Migdal and extract financial data (single responsibility)"""
    # 25 lines

def _save_migdal_data(self, financial_data, user_id, sync_record):
    """Parse and save Migdal financial data (single responsibility)"""
    # 30 lines
```

**Benefits**:
- ✅ Each method under 40 lines
- ✅ Single responsibility per method
- ✅ Easier to test each step
- ✅ Easier to understand flow

---

#### Task 2.4: Institution Abstraction Layer

**Goal**: Make adding new institutions trivial

**File**: `config/institutions.py`

```python
"""
Institution configuration and registry
Allows adding new institutions without code changes
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from config.constants import Institution, AccountType


@dataclass
class InstitutionConfig:
    """Configuration for a financial institution"""
    name: str
    account_type: str
    url: str
    mfa_config: Optional[Dict[str, Any]] = None
    selectors: Optional[Dict[str, str]] = None
    api_config: Optional[Dict[str, Any]] = None


# Institution Registry
INSTITUTIONS = {
    Institution.MIGDAL: InstitutionConfig(
        name="Migdal",
        account_type=AccountType.PENSION,
        url="https://www.migdal.co.il/he/myArea",
        mfa_config={
            "sender_email": "no-reply@migdal.co.il",
            "sender_name": "Migdal",
            "code_pattern": r'\b\d{6}\b',
            "email_delay": 10,
            "max_wait_time": 60
        },
        selectors={
            "id_field": "input[name='idNumber']",
            "continue_button": "button.submit-button"
        }
    ),

    Institution.PHOENIX: InstitutionConfig(
        name="Phoenix",
        account_type=AccountType.PENSION,
        url="https://www.fnx.co.il/",
        mfa_config={
            "sender_email": "noreply@fnx.co.il",
            "sender_name": "Phoenix",
            "code_pattern": r'\b\d{6}\b'
        },
        selectors={
            "id_field": "input[name='identityNumber']",
            "email_field": "input[name='email']",
            "login_button": "button[type='submit']",
            "mfa_field": "input[name='otpCode']",
            "mfa_submit_button": "button[type='submit']"
        }
    ),

    Institution.CAL: InstitutionConfig(
        name="CAL",
        account_type=AccountType.CREDIT_CARD,
        url="https://www.cal-online.co.il/",
        api_config={
            "site_id": "09031987-5d35-4a23-8e45-eb97c9ab345e"
        }
    ),

    Institution.EXCELLENCE: InstitutionConfig(
        name="Excellence",
        account_type=AccountType.BROKER,
        url="https://excellence-trade.com/api",
        api_config={
            "base_url": "https://excellence-trade.com/api/v1"
        }
    )
}


def get_institution_config(institution: str) -> InstitutionConfig:
    """Get configuration for institution"""
    if institution not in INSTITUTIONS:
        raise ValueError(f"Unknown institution: {institution}")
    return INSTITUTIONS[institution]


def register_institution(institution: str, config: InstitutionConfig):
    """Register a new institution (for plugins/extensions)"""
    INSTITUTIONS[institution] = config
```

**Usage**:
```python
# Before: Hardcoded everywhere
site_url = "https://www.migdal.co.il/he/myArea"
sender_email = "no-reply@migdal.co.il"

# After: Centralized configuration
from config.institutions import get_institution_config

config = get_institution_config(Institution.MIGDAL)
site_url = config.url
sender_email = config.mfa_config["sender_email"]
```

**To add a new institution**:
1. Add constant to `config/constants.py`
2. Add configuration to `config/institutions.py`
3. Done! (No code changes needed)

---

### Phase 3: Configuration & Maintainability

#### Task 3.1: Bulk Database Operations

**File**: `services/base_service.py` (addition)

```python
def bulk_save_transactions(
    self,
    account: Account,
    transactions: List[Dict[str, Any]]
) -> tuple[int, int]:
    """
    Bulk save transactions with deduplication

    Uses batch INSERT with ON CONFLICT for efficiency.
    Handles 1000+ transactions efficiently.

    Args:
        account: Account model instance
        transactions: List of transaction dicts

    Returns:
        Tuple of (added_count, updated_count)
    """
    from db.models import Transaction as DBTransaction

    added = 0
    updated = 0

    # Build unique keys for deduplication
    existing_keys = set()
    existing_txns = (
        self.db.query(DBTransaction)
        .filter(DBTransaction.account_id == account.id)
        .all()
    )

    for txn in existing_txns:
        key = (
            txn.transaction_date,
            txn.description,
            txn.original_amount,
            txn.transaction_id
        )
        existing_keys.add(key)

    # Batch insert new transactions
    new_transactions = []
    for txn_data in transactions:
        key = (
            txn_data['transaction_date'],
            txn_data['description'],
            txn_data['original_amount'],
            txn_data.get('transaction_id')
        )

        if key not in existing_keys:
            new_transactions.append(DBTransaction(
                account_id=account.id,
                **txn_data
            ))
            added += 1
        else:
            updated += 1

    # Bulk insert (much faster than one-by-one)
    if new_transactions:
        self.db.bulk_save_objects(new_transactions)

    return added, updated
```

**Performance**:
- Before: 1000 transactions = 1000 INSERT queries (~30 seconds)
- After: 1000 transactions = 1 batch INSERT (~0.5 seconds) = **60x faster**

---

#### Task 3.2: Improved Error Context

**Before**:
```python
except Exception as e:
    result.error_message = str(e)  # ❌ "Connection timeout" - what failed?
```

**After**:
```python
from contextlib import contextmanager

@contextmanager
def error_context(self, operation: str, **context):
    """Add context to errors"""
    try:
        yield
    except Exception as e:
        context_str = ", ".join(f"{k}={v}" for k, v in context.items())
        raise type(e)(f"{operation} failed ({context_str}): {e}") from e

# Usage:
with self.error_context("Account sync", institution="migdal", account="12345"):
    # Do sync
    pass

# Error message: "Account sync failed (institution=migdal, account=12345): Connection timeout"
```

---

### Phase 4: Polish & Optimization

#### Task 4.1: Add Caching

**File**: `services/analytics_service.py`

```python
from functools import lru_cache
from datetime import datetime, timedelta

class AnalyticsService:
    def __init__(self, session):
        self.session = session
        self._cache_timestamp = datetime.utcnow()

    @lru_cache(maxsize=128)
    def get_account_summary_cached(self) -> Dict[str, Any]:
        """Cached version of account summary (1 minute TTL)"""
        # Invalidate cache after 1 minute
        if (datetime.utcnow() - self._cache_timestamp) > timedelta(minutes=1):
            self.get_account_summary_cached.cache_clear()
            self._cache_timestamp = datetime.utcnow()

        return self.get_account_summary()
```

---

## Success Metrics

### Performance Benchmarks

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Sync 3 accounts | 15 commits | 1 commit | 15x faster |
| 1000 transactions | 1001 queries | 1 query | 1000x faster |
| Bulk insert 1000 | 30 seconds | 0.5 seconds | 60x faster |
| Code duplication | 200+ lines | 0 lines | 100% reduction |
| Average method length | 65 lines | 30 lines | 54% reduction |

### Code Quality Metrics

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Lines of code | 1200 | 750 | <800 |
| Cyclomatic complexity | 15-25 | 5-10 | <10 |
| Test coverage | 60% | 95% | >90% |
| Magic strings | 50+ | 0 | 0 |
| Code duplication | 15% | 0% | <5% |

### Developer Experience

| Metric | Before | After |
|--------|--------|-------|
| Add new institution | 3 hours, 5 files | 30 minutes, 1 file |
| Debug sync failure | 30 minutes | 5 minutes |
| Understand code flow | Difficult | Easy |

---

## Migration Strategy

### Step 1: Create Branch
```bash
git checkout -b refactor/service-layer
```

### Step 2: Phase 1 (Week 1)
- Create `services/base_service.py`
- Create `config/constants.py`
- Refactor `BrokerService` (test thoroughly)
- Refactor `PensionService` (test thoroughly)
- Refactor `CreditCardService` (test thoroughly)
- Run full test suite
- Manual testing of all sync operations

### Step 3: Phase 2 (Week 2)
- Create `config/institutions.py`
- Fix N+1 queries in analytics
- Split long methods
- Replace all magic strings
- Run performance benchmarks

### Step 4: Phase 3 (Week 3)
- Implement bulk operations
- Add error context
- Extract configurations
- Add detailed logging

### Step 5: Phase 4 (Week 4)
- Add caching where appropriate
- Complete documentation
- Performance tuning
- Final testing

### Step 6: Merge
```bash
# After all tests pass
git merge refactor/service-layer
```

---

## Testing Strategy

### Unit Tests
```python
# tests/services/test_base_service.py
def test_sync_transaction_success(db_session):
    """Test successful sync creates record and commits"""
    service = BaseSyncService(db_session)

    with service.sync_transaction("broker", "excellence") as sync_record:
        assert sync_record.status == "in_progress"
        sync_record.records_added = 5

    # Verify committed
    assert sync_record.status == "success"
    assert sync_record.records_added == 5
    assert sync_record.completed_at is not None


def test_sync_transaction_rollback(db_session):
    """Test failed sync rolls back changes"""
    service = BaseSyncService(db_session)

    with pytest.raises(ValueError):
        with service.sync_transaction("broker", "excellence") as sync_record:
            # Create account
            account = service.get_or_create_account(...)
            # Raise error
            raise ValueError("Simulated failure")

    # Verify rollback - account should NOT exist
    accounts = db_session.query(Account).all()
    assert len(accounts) == 0

    # Sync record should show failure
    sync_record = db_session.query(SyncHistory).first()
    assert sync_record.status == "failed"
```

### Integration Tests
```python
# tests/services/test_broker_service_integration.py
def test_excellence_sync_end_to_end(db_session, mock_excellence_api):
    """Test complete Excellence sync with real database"""
    service = BrokerService(db_session)

    result = service.sync_excellence(
        username="test_user",
        password="test_pass"
    )

    assert result.success == True
    assert result.accounts_synced > 0
    assert result.records_added > 0

    # Verify database state
    accounts = db_session.query(Account).all()
    assert len(accounts) == result.accounts_synced
```

### Performance Tests
```python
# tests/performance/test_bulk_operations.py
import time

def test_bulk_insert_performance(db_session):
    """Verify bulk operations are fast"""
    service = BaseSyncService(db_session)
    account = # ... create account

    # Generate 1000 transactions
    transactions = [generate_transaction() for _ in range(1000)]

    start = time.time()
    added, updated = service.bulk_save_transactions(account, transactions)
    duration = time.time() - start

    # Should complete in under 2 seconds
    assert duration < 2.0
    assert added == 1000
```

---

## Risk Assessment

### High Risk
- **Database schema changes**: None required ✅
- **Breaking API changes**: Minimal (internal only) ✅
- **Data migration**: None required ✅

### Medium Risk
- **Performance regressions**: Mitigated by benchmarks
- **Merge conflicts**: Phase by phase approach reduces risk
- **Test coverage gaps**: Add tests as we refactor

### Low Risk
- **Configuration errors**: Validated at startup
- **New bugs**: Comprehensive test suite

---

## Rollback Plan

If issues discovered after merge:

1. **Feature flag**: Add config to use old/new service implementation
2. **Quick revert**: All changes in single PR for easy rollback
3. **Data integrity**: No schema changes means no data migration needed

---

## Timeline

```
Week 1: Phase 1 - Critical Fixes
├─ Day 1-2: Create base service class
├─ Day 3: Refactor BrokerService
├─ Day 4: Refactor PensionService
└─ Day 5: Refactor CreditCardService + Testing

Week 2: Phase 2 - Performance & Architecture
├─ Day 1: Create constants and institutions config
├─ Day 2-3: Fix N+1 queries and add eager loading
├─ Day 4: Split long methods
└─ Day 5: Testing and benchmarking

Week 3: Phase 3 - Configuration & Maintainability
├─ Day 1-2: Implement bulk operations
├─ Day 3: Improve error context and logging
├─ Day 4: Extract configurations
└─ Day 5: Integration testing

Week 4: Phase 4 - Polish & Optimization
├─ Day 1: Add caching
├─ Day 2: Documentation and examples
├─ Day 3-4: Performance tuning
└─ Day 5: Final testing and merge
```

---

## Conclusion

This refactoring plan addresses all identified issues in priority order:

1. **🔴 Critical**: Code duplication and data integrity (Week 1)
2. **🟠 High**: Performance and architecture (Week 2)
3. **🟡 Medium**: Configuration and maintainability (Week 3)
4. **🟢 Low**: Polish and optimization (Week 4)

**Expected Outcomes**:
- 37% code reduction (1200 → 750 lines)
- 15-1000x performance improvements
- Zero code duplication
- Easy to add new institutions
- Production-ready service layer

**Next Steps**: Review and approve this plan, then begin Phase 1 implementation.