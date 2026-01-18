# Multi-Account Support Implementation Plan

## Status Overview

| Institution Type | Institution | Status |
|-----------------|-------------|--------|
| Credit Card | CAL | ✅ Complete |
| Credit Card | Max | ✅ Complete |
| Pension Fund | Migdal | 🔄 Pending |
| Pension Fund | Phoenix | 🔄 Pending |

## Architecture Summary

### Data Model
```python
class CreditCardCredentials(BaseModel):
    username: str
    password: str
    label: Optional[str] = None  # "Personal", "Business", etc.

class PensionCredentials(BaseModel):
    user_id: str
    label: Optional[str] = None

class Credentials(BaseModel):
    cal: List[CreditCardCredentials] = Field(default_factory=list)
    max: List[CreditCardCredentials] = Field(default_factory=list)
    migdal: List[PensionCredentials] = Field(default_factory=list)
    phoenix: List[PensionCredentials] = Field(default_factory=list)
    email: EmailCredentials  # Shared for MFA
```

### Key Design Decisions

1. **Sequential execution** - One account at a time (browser constraints, rate limiting, MFA)
2. **List with optional labels** - Index-based access (0, 1, 2) with optional labels
3. **Partial success model** - Continue syncing if one account fails
4. **Shared email for MFA** - All pension accounts use global EmailCredentials

### DRY Helper Functions (in `config/settings.py`)

| Function | Purpose |
|----------|---------|
| `_find_account_index(accounts, identifier)` | Find by index OR label |
| `manage_cc_account(institution, operation, ...)` | All credit card CRUD ops |
| `manage_pension_account(institution, operation, ...)` | All pension CRUD ops |
| `select_accounts_to_sync(institution, filters)` | Filter accounts for sync |
| `_load_numbered_accounts(prefix)` | Load from env vars |

## CLI Interface

### Account Management
```bash
# List accounts
fin-cli config list-accounts cal|max|migdal|phoenix

# Add account
fin-cli config add-account cal --username "user" --password "pass" --label "Personal"
fin-cli config add-account migdal --user-id "123456789" --label "Personal"

# Remove/Update account (by index or label)
fin-cli config remove-account cal 0
fin-cli config remove-account cal personal
fin-cli config update-account cal 0 --password "newpass" --label "Work"
```

### Sync Commands
```bash
# Sync all configured accounts
fin-cli sync cal
fin-cli sync migdal

# Sync specific accounts
fin-cli sync cal --account 0
fin-cli sync cal --account personal
fin-cli sync cal -a 0 -a 2

# Sync everything
fin-cli sync all
```

## Environment Variables

**Old format (backward compatible):**
```bash
CAL_USERNAME=user1
CAL_PASSWORD=pass1
MIGDAL_USER_ID=123456789
```

**New format (numbered):**
```bash
CAL_1_USERNAME=user1
CAL_1_PASSWORD=pass1
CAL_1_LABEL=Personal

CAL_2_USERNAME=user2
CAL_2_PASSWORD=pass2
CAL_2_LABEL=Business

MIGDAL_1_USER_ID=123456789
MIGDAL_1_LABEL=Personal
```

## Migration

Old single-account credentials auto-migrate to list format on first load.

## Implementation Checklist

### Credit Cards (Complete ✅)
- [x] Data model: `cal`/`max` as `List[CreditCardCredentials]`
- [x] Helper functions: `manage_cc_account()`, `_find_account_index()`
- [x] Config commands: list-accounts, add-account, remove-account, update-account
- [x] Sync with `--account` filter
- [x] Backward compatibility migration
- [x] Environment variable loading

### Pensions (Pending 🔄)
- [ ] Data model: `migdal`/`phoenix` as `List[PensionCredentials]`
- [ ] Helper functions: `manage_pension_account()`, `select_pension_accounts_to_sync()`
- [ ] Config commands: extend for migdal/phoenix
- [ ] Sync with `--account` filter
- [ ] Backward compatibility migration
- [ ] Environment variable loading (MIGDAL_1_USER_ID, etc.)

### Testing Checklist
- [ ] Add/remove/update accounts via CLI
- [ ] Sync all accounts (no filter)
- [ ] Sync specific accounts (by index and label)
- [ ] Partial success (some accounts fail)
- [ ] Old single-account migration
- [ ] Environment variable formats (old and new)

## Progress Display Example
```
Syncing CAL credit card...

[1/3] Account 0 (Personal)
  ✓ Found 2 cards
  ✓ Transactions added: 45

[2/3] Account 1 (Business)
  ✓ Found 1 card
  ✓ Transactions added: 23

[3/3] Account 2
  ✗ Failed: Invalid credentials

Summary
  ✓ Succeeded: 2/3 accounts
  ✗ Failed: 1/3 accounts
  Total transactions added: 68
```

## Files to Modify

| File | Changes |
|------|---------|
| `config/settings.py` | Data models, helper functions, migration logic |
| `cli/commands/config.py` | Account management commands |
| `cli/commands/sync.py` | Multi-account sync helpers, `--account` option |