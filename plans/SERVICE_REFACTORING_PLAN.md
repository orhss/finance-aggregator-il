# Service Layer Refactoring Plan

## Overview

This document outlines a focused refactoring plan for the service layer. Only essential improvements are included - items that address real code duplication, data integrity issues, and performance problems.

**Current State**: Services are functional but have duplicated code and lack transaction management.
**Target State**: DRY, atomic operations with proper transaction handling.

---

## Issues to Address

### Critical (Must Fix)

| ID | Issue | Impact | Files Affected |
|----|-------|--------|----------------|
| C1 | Code Duplication - `_get_or_create_account` | Bug fixes needed in 3 places | broker_service.py, pension_service.py, credit_card_service.py |
| C2 | Code Duplication - `_save_balance` | Bug fixes needed in 2 places | broker_service.py, pension_service.py |
| C3 | No Transaction Management | Risk of partial/corrupt data on failure | All service files |
| C4 | Excessive Database Commits | Multiple commits per sync instead of one | All service files |

### High Priority

| ID | Issue | Impact | Files Affected |
|----|-------|--------|----------------|
| H1 | N+1 Query in `get_monthly_summary` | Calls `get_account_by_id` in loop | analytics_service.py:392 |
| H2 | Magic Strings | Typo-prone, hard to refactor | All files |

### Not Doing (Over-engineering)

The following items from the original plan are **intentionally excluded**:

- **Institution abstraction layer** - Overengineered for 4 institutions. The config would duplicate what's already in scraper classes.
- **Query result caching** - Premature optimization. Dataset is small.
- **95% test coverage goal** - Unrealistic for a personal project.
- **Splitting long methods** - Only worth doing if actively modifying those methods.
- **Bulk transaction operations** - Current transaction volume doesn't justify the complexity.

---

## Implementation Tasks

### Task 1: Create Constants File

**File**: `config/constants.py`

```python
"""
Application constants - eliminates magic strings
"""

class AccountType:
    BROKER = "broker"
    PENSION = "pension"
    CREDIT_CARD = "credit_card"
    SAVINGS = "savings"

    @classmethod
    def all(cls) -> list[str]:
        return [cls.BROKER, cls.PENSION, cls.CREDIT_CARD, cls.SAVINGS]


class Institution:
    EXCELLENCE = "excellence"
    MIGDAL = "migdal"
    PHOENIX = "phoenix"
    CAL = "cal"

    @classmethod
    def all(cls) -> list[str]:
        return [cls.EXCELLENCE, cls.MIGDAL, cls.PHOENIX, cls.CAL]


class SyncType:
    BROKER = "broker"
    PENSION = "pension"
    CREDIT_CARD = "credit_card"


class SyncStatus:
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"


class Currency:
    ILS = "ILS"
    USD = "USD"
    EUR = "EUR"
```

---

### Task 2: Create Base Service Class

**File**: `services/base_service.py`

Extract common methods into a base class:

```python
"""
Base service class with common database operations
"""

from contextlib import contextmanager
from datetime import datetime, date
from typing import Optional, Generator
from sqlalchemy.orm import Session

from db.models import Account, Balance, SyncHistory
from config.constants import SyncStatus


class BaseSyncService:
    """
    Base class for sync services.
    Provides common database operations and transaction management.
    """

    def __init__(self, db_session: Session):
        self.db = db_session

    @contextmanager
    def sync_transaction(
        self,
        sync_type: str,
        institution: str
    ) -> Generator[SyncHistory, None, None]:
        """
        Context manager for atomic sync operations.

        Creates sync history record, handles commit on success,
        rollback on failure.
        """
        sync_record = SyncHistory(
            sync_type=sync_type,
            institution=institution,
            status=SyncStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )
        self.db.add(sync_record)
        self.db.flush()

        try:
            yield sync_record
            sync_record.status = SyncStatus.SUCCESS
            sync_record.completed_at = datetime.utcnow()
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            sync_record.status = SyncStatus.FAILED
            sync_record.completed_at = datetime.utcnow()
            sync_record.error_message = str(e)
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
        Get existing account or create new one.
        Does NOT commit - relies on transaction management.
        """
        account = self.db.query(Account).filter(
            Account.account_type == account_type,
            Account.institution == institution,
            Account.account_number == account_number
        ).first()

        if account:
            account.last_synced_at = datetime.utcnow()
            if account_name:
                account.account_name = account_name
            if card_unique_id:
                account.card_unique_id = card_unique_id
            return account

        account = Account(
            account_type=account_type,
            institution=institution,
            account_number=account_number,
            account_name=account_name,
            card_unique_id=card_unique_id,
            last_synced_at=datetime.utcnow()
        )
        self.db.add(account)
        self.db.flush()
        return account

    def save_balance(
        self,
        account: Account,
        total_amount: float,
        balance_date: Optional[date] = None,
        **kwargs
    ) -> bool:
        """
        Save or update balance for an account.
        Does NOT commit - relies on transaction management.

        Returns True if new balance created, False if updated.
        """
        if balance_date is None:
            balance_date = date.today()

        existing = self.db.query(Balance).filter(
            Balance.account_id == account.id,
            Balance.balance_date == balance_date
        ).first()

        if existing:
            existing.total_amount = total_amount
            for key, value in kwargs.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            return False

        balance = Balance(
            account_id=account.id,
            balance_date=balance_date,
            total_amount=total_amount,
            **{k: v for k, v in kwargs.items() if hasattr(Balance, k)}
        )
        self.db.add(balance)
        return True
```

---

### Task 3: Refactor Services to Use Base Class

**Changes per service:**

1. **BrokerService**: Inherit from `BaseSyncService`, remove `_get_or_create_account` and `_save_balance`, wrap sync in `sync_transaction` context manager.

2. **PensionService**: Same as above.

3. **CreditCardService**: Inherit from `BaseSyncService`, remove `_get_or_create_account`, wrap sync in `sync_transaction` context manager.

**Example refactored sync method:**

```python
# Before
def sync_excellence(self, username, password, currency="ILS"):
    result = BrokerSyncResult()
    sync_record = None
    try:
        sync_record = SyncHistory(...)
        self.db.add(sync_record)
        self.db.commit()  # Commit 1

        # ... do work ...

        db_account = self._get_or_create_account(...)  # Commit 2
        self._save_balance(...)  # Commit 3

        sync_record.status = "success"
        self.db.commit()  # Commit 4
    except Exception as e:
        # error handling

# After
def sync_excellence(self, username, password, currency="ILS"):
    result = BrokerSyncResult()
    try:
        with self.sync_transaction(SyncType.BROKER, Institution.EXCELLENCE) as sync_record:
            result.sync_history_id = sync_record.id

            # ... do work ...

            db_account = self.get_or_create_account(...)  # No commit
            self.save_balance(...)  # No commit

            # Single commit happens automatically on context exit
            result.success = True
    except Exception as e:
        result.error_message = str(e)
    return result
```

---

### Task 4: Fix N+1 Query in AnalyticsService

**File**: `services/analytics_service.py`

**Problem** (line 392):
```python
for txn in transactions:
    account = self.get_account_by_id(txn.account_id)  # N+1 query!
```

**Solution**: Use `joinedload` to eager-load accounts:

```python
from sqlalchemy.orm import joinedload

def get_monthly_summary(self, year: int, month: int) -> Dict[str, Any]:
    transactions = (
        self.session.query(Transaction)
        .options(joinedload(Transaction.account))  # Eager load
        .filter(
            extract('year', Transaction.transaction_date) == year,
            extract('month', Transaction.transaction_date) == month
        )
        .all()
    )

    for txn in transactions:
        account = txn.account  # Already loaded, no extra query
        key = f"{account.institution} ({account.account_type})"
        by_account[key] = by_account.get(key, 0) + 1
```

---

## Expected Results

| Metric | Before | After |
|--------|--------|-------|
| Duplicated methods | 3 | 0 |
| Commits per sync | 3-5 | 1 |
| N+1 queries | 1 | 0 |
| Magic strings in services | ~20 | 0 |

---

## Migration Steps

1. ✅ Create `config/constants.py`
2. ✅ Create `services/base_service.py`
3. ✅ Refactor `BrokerService` to use base class
4. ✅ Refactor `PensionService` to use base class
5. ✅ Refactor `CreditCardService` to use base class
6. ✅ Fix N+1 query in `AnalyticsService`
7. ⬜ Test all sync operations manually

---

## What's NOT Included

To keep this practical, the following are explicitly out of scope:

- Time estimates and weekly schedules
- Institution configuration registry
- Query caching
- Test coverage targets
- Performance benchmarking
- Bulk transaction operations
- Method splitting (unless touched for other reasons)

These can be added later if they become actual pain points.