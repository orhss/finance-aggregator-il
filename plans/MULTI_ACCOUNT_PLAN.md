# Multi-Account Support Implementation Plan

## Overview

This plan implements support for multiple accounts per institution across all financial data sources. Users can configure and sync multiple accounts for credit cards (CAL, Max) and pension funds (Migdal, Phoenix).

## Supported Institutions

| Institution Type | Institution | Status | Implementation Date |
|-----------------|-------------|--------|---------------------|
| Credit Card | CAL | ✅ Complete | 2026-01-01 |
| Credit Card | Max | ✅ Complete | 2026-01-01 |
| Pension Fund | Migdal | 🔄 In Progress | TBD |
| Pension Fund | Phoenix | 🔄 In Progress | TBD |

**Note**: The credit card implementation serves as the reference pattern for pension funds. All institutions follow the same architectural approach for consistency.

## DRY (Don't Repeat Yourself) Principles

This implementation follows strict DRY principles to minimize code duplication:

### 1. **Single `manage_cc_account()` function** (`config/settings.py`)
- Handles ALL credit card account operations (list, add, remove, update)
- One function instead of four separate implementations
- Used by all config commands

### 2. **Single `_find_account_index()` helper** (`config/settings.py`)
- Unified logic for finding accounts by index OR label
- Used by all account operations that need to locate an account
- Eliminates duplicate "try as index, then try as label" code

### 3. **Single `_sync_credit_card_multi_account()` helper** (`cli/commands/sync.py`)
- Generic sync logic shared by CAL and Max
- One 80-line function instead of 160+ lines duplicated
- Uses dynamic method dispatch (`getattr(service, service_method)`)

### 4. **Method on `Credentials` class** (`config/settings.py`)
- `get_cc_accounts(institution)` method for DRY access
- Replaces repeated `if institution == 'cal': return credentials.cal` blocks

### 5. **Unified environment variable loading** (`config/settings.py`)
- `_load_numbered_accounts(prefix)` works for CAL and Max
- Single function handles both old and new formats
- Called once per institution instead of duplicated logic

### Benefits
- **~300 fewer lines of code** compared to duplicated approach
- **Single source of truth** for account operations
- **Easier to maintain** - bug fixes apply to all institutions
- **Easy to add new institutions** - just call the generic functions
- **Consistent behavior** across CAL and Max

## Design Decisions

### 1. Sequential vs Parallel Execution

**Decision: Sequential execution (one account at a time)**

**Rationale:**
- **Browser constraints**: Multiple Selenium instances consume excessive memory/CPU
- **Rate limiting**: Banks may detect simultaneous logins as suspicious activity
- **Better UX**: Clear progress indication, easier error tracking
- **MFA support**: Future MFA implementation can't handle multiple simultaneous codes
- **System stability**: Prevents resource exhaustion on user's machine

### 2. Data Model: List vs Dict

**Decision: List with optional labels**

```python
class CreditCardCredentials(BaseModel):
    username: str
    password: str
    label: Optional[str] = None  # "Personal", "Business", etc.

class Credentials(BaseModel):
    cal: List[CreditCardCredentials] = Field(default_factory=list)
    max: List[CreditCardCredentials] = Field(default_factory=list)
```

**Rationale:**
- Natural index-based access (0, 1, 2...)
- Labels are optional metadata for user convenience
- Easy migration: single credential → list with one item
- Maintains order for predictable iteration
- Simpler than forcing users to name every account

**Rejected Alternative: Dict**
```python
cal: Dict[str, CreditCardCredentials]  # Forces naming, no natural order
```

### 3. Account Selection Strategy

**Default behavior**: Sync ALL configured accounts

**Selection options**:
- By index: `--account 0`, `--account 1`
- By label: `--account personal`, `--account business`
- Multiple: `--account 0 --account 2`

**Selection logic**:
1. Try to match as label first
2. If no label match, try to parse as integer index
3. If neither works, raise error

### 4. Error Handling

**Partial success model**: Continue syncing remaining accounts even if one fails

**Exit codes**:
- All succeeded → exit 0
- Some failed → exit 0 (partial success, show summary)
- All failed → exit 1

## CLI Interface

### Account Management Commands

```bash
# List all accounts for an institution
fin-cli config list-accounts cal
fin-cli config list-accounts max

# Output example:
#   0: ****user1 (Personal)
#   1: ****user2 (Business)
#   2: ****user3

# Add account (interactive)
fin-cli config add-account cal
# Prompts: username? password? label? (optional)

# Add account (with arguments)
fin-cli config add-account cal --username "user" --password "pass"
fin-cli config add-account cal --username "user" --password "pass" --label "Personal"

# Remove account by index
fin-cli config remove-account cal 0

# Remove account by label
fin-cli config remove-account cal personal

# Update account credentials
fin-cli config update-account cal 0 --password "newpass"
fin-cli config update-account cal personal --username "newuser"
fin-cli config update-account cal 1 --label "Work"
```

### Sync Commands

```bash
# DEFAULT: Sync all configured accounts (sequential)
fin-cli sync cal
# → Syncs account 0, then 1, then 2...

# Sync specific account by index
fin-cli sync cal --account 0
fin-cli sync cal --account 1

# Sync specific account by label
fin-cli sync cal --account personal
fin-cli sync cal --account business

# Sync multiple specific accounts (still sequential)
fin-cli sync cal --account 0 --account 2
fin-cli sync cal --account personal --account business

# Same pattern for Max
fin-cli sync max
fin-cli sync max --account 0
fin-cli sync max --account work

# Sync all still works (now syncs all accounts for each institution)
fin-cli sync all
```

### Config Display

**Updated `fin-cli config show`:**

```
Current Configuration

Config directory: /Users/user/.fin
Credentials file: /Users/user/.fin/credentials.enc (encrypted)

Credentials
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Institution   ┃ Field              ┃ Value        ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ CAL [0]       │ Username           │ ••••••••••••  │
│ (Personal)    │ Password           │ ••••••••••••  │
│               │                    │              │
│ CAL [1]       │ Username           │ ••••••••••••  │
│ (Business)    │ Password           │ ••••••••••••  │
│               │                    │              │
│ Max [0]       │ Username           │ ••••••••••••  │
│               │ Password           │ ••••••••••••  │
└───────────────┴────────────────────┴──────────────┘
```

## Progress Display

```
Syncing CAL credit card...

[1/3] Account 0 (Personal)
  ⠋ Logging in...
  ✓ Found 2 cards
  ✓ Transactions added: 45
  ✓ Transactions updated: 3

[2/3] Account 1 (Business)
  ⠋ Logging in...
  ✓ Found 1 card
  ✓ Transactions added: 23
  ✓ Transactions updated: 1

[3/3] Account 2
  ✗ Failed: Invalid credentials

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓ Succeeded: 2/3 accounts
  ✗ Failed: 1/3 accounts (see errors above)

  Total cards synced: 3
  Total transactions added: 68
  Total transactions updated: 4
```

## Implementation Details

### 1. Data Model Changes (`config/settings.py`)

**Before:**
```python
class Credentials(BaseModel):
    excellence: BrokerCredentials = Field(default_factory=BrokerCredentials)
    migdal: PensionCredentials = Field(default_factory=PensionCredentials)
    phoenix: PensionCredentials = Field(default_factory=PensionCredentials)
    cal: CreditCardCredentials = Field(default_factory=CreditCardCredentials)  # Single
    max: CreditCardCredentials = Field(default_factory=CreditCardCredentials)  # Single
    email: EmailCredentials = Field(default_factory=EmailCredentials)
```

**After:**
```python
class CreditCardCredentials(BaseModel):
    """Credit card credentials"""
    username: str  # Changed from Optional - required for account
    password: str  # Changed from Optional - required for account
    label: Optional[str] = None  # NEW: Optional label like "Personal", "Business"

class Credentials(BaseModel):
    """All credentials for different institutions"""
    excellence: BrokerCredentials = Field(default_factory=BrokerCredentials)
    migdal: PensionCredentials = Field(default_factory=PensionCredentials)
    phoenix: PensionCredentials = Field(default_factory=PensionCredentials)

    # NEW: Multiple accounts as list
    cal: List[CreditCardCredentials] = Field(default_factory=list)
    max: List[CreditCardCredentials] = Field(default_factory=list)

    email: EmailCredentials = Field(default_factory=EmailCredentials)

    def get_cc_accounts(self, institution: str) -> List[CreditCardCredentials]:
        """Get credit card accounts by institution (DRY helper)"""
        return getattr(self, institution.lower())
```

**Simplified Helper Functions (DRY):**
```python
# Single function to find account by index or label
def _find_account_index(accounts: List[CreditCardCredentials], identifier: str) -> Optional[int]:
    """
    Find account index by identifier (index number or label)

    Returns:
        Index if found, None otherwise
    """
    # Try as index
    try:
        idx = int(identifier)
        return idx if 0 <= idx < len(accounts) else None
    except ValueError:
        pass

    # Try as label
    for idx, account in enumerate(accounts):
        if account.label == identifier:
            return idx

    return None

# Generic credit card account operations
def manage_cc_account(
    institution: str,
    operation: str,
    identifier: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    label: Optional[str] = None
) -> tuple[bool, Optional[List[CreditCardCredentials]]]:
    """
    Generic function for all credit card account operations (DRY)

    Args:
        institution: 'cal' or 'max'
        operation: 'list', 'add', 'remove', 'update'
        identifier: Account index or label (for remove/update)
        username, password, label: Account credentials (for add/update)

    Returns:
        (success, accounts_list) - accounts_list only for 'list' operation
    """
    if institution not in ['cal', 'max']:
        raise ValueError(f"Invalid institution: {institution}")

    credentials = load_credentials()
    accounts = credentials.get_cc_accounts(institution)

    if operation == 'list':
        return True, accounts

    elif operation == 'add':
        accounts.append(CreditCardCredentials(
            username=username,
            password=password,
            label=label
        ))
        save_credentials(credentials)
        return True, None

    elif operation in ['remove', 'update']:
        idx = _find_account_index(accounts, identifier)
        if idx is None:
            return False, None

        if operation == 'remove':
            accounts.pop(idx)
        else:  # update
            if username is not None:
                accounts[idx].username = username
            if password is not None:
                accounts[idx].password = password
            if label is not None:
                accounts[idx].label = label

        save_credentials(credentials)
        return True, None

    raise ValueError(f"Invalid operation: {operation}")

def select_accounts_to_sync(
    institution: str,
    filters: Optional[List[str]] = None
) -> List[Tuple[int, CreditCardCredentials]]:
    """
    Select accounts to sync (simplified)

    Args:
        institution: 'cal' or 'max'
        filters: List of indices or labels (None = all)

    Returns:
        List of (index, account) tuples
    """
    _, accounts = manage_cc_account(institution, 'list')

    if not accounts:
        raise ValueError(f"No {institution.upper()} accounts configured")

    # No filter = all accounts
    if not filters:
        return list(enumerate(accounts))

    # Build selected list
    selected = []
    for filter_str in filters:
        idx = _find_account_index(accounts, filter_str)
        if idx is None:
            raise ValueError(f"Account not found: {filter_str}")
        selected.append((idx, accounts[idx]))

    return selected
```

### 2. Backward Compatibility

**Migration in `load_credentials()`:**
```python
def load_credentials() -> Credentials:
    """
    Load credentials from file or environment variables

    Handles migration from old single-account format to new multi-account format.
    """
    # Try loading from encrypted file first
    if CREDENTIALS_FILE.exists():
        try:
            with open(CREDENTIALS_FILE, 'rb') as f:
                encrypted_data = f.read()

            # Decrypt and parse
            key = get_encryption_key()
            fernet = Fernet(key)
            decrypted_data = fernet.decrypt(encrypted_data)
            raw_data = json.loads(decrypted_data.decode())

            # MIGRATION: Convert old single-account format to list
            for institution in ['cal', 'max']:
                if institution in raw_data:
                    value = raw_data[institution]

                    # Old format: single dict with username/password
                    if isinstance(value, dict) and 'username' in value:
                        raw_data[institution] = [value]  # Wrap in list

                    # Already new format: list of dicts
                    elif isinstance(value, list):
                        pass  # No migration needed

                    # Empty or null
                    else:
                        raw_data[institution] = []

            return Credentials(**raw_data)

        except Exception as e:
            print(f"Warning: Could not decrypt credentials file: {e}")

    # Fallback to environment variables
    return _load_from_environment()

def _load_from_environment() -> Credentials:
    """Load credentials from environment variables"""

    # Load single-account institutions
    excellence = BrokerCredentials(
        username=os.getenv("EXCELLENCE_USERNAME"),
        password=os.getenv("EXCELLENCE_PASSWORD"),
    )

    migdal = PensionCredentials(
        user_id=os.getenv("MIGDAL_USER_ID"),
        email=os.getenv("USER_EMAIL"),
    )

    phoenix = PensionCredentials(
        user_id=os.getenv("PHOENIX_USER_ID"),
        email=os.getenv("USER_EMAIL"),
    )

    email = EmailCredentials(
        address=os.getenv("USER_EMAIL"),
        password=os.getenv("USER_EMAIL_APP_PASSWORD"),
    )

    # Load multi-account credit cards
    cal_accounts = _load_numbered_accounts('CAL')
    max_accounts = _load_numbered_accounts('MAX')

    return Credentials(
        excellence=excellence,
        migdal=migdal,
        phoenix=phoenix,
        cal=cal_accounts,
        max=max_accounts,
        email=email,
    )

def _load_numbered_accounts(prefix: str) -> List[CreditCardCredentials]:
    """
    Load numbered accounts from environment variables

    Supports both:
    - Old format: CAL_USERNAME, CAL_PASSWORD (single account)
    - New format: CAL_1_USERNAME, CAL_1_PASSWORD, CAL_2_USERNAME, etc.

    Args:
        prefix: 'CAL' or 'MAX'

    Returns:
        List of CreditCardCredentials
    """
    accounts = []

    # Try old single-account format first
    username = os.getenv(f"{prefix}_USERNAME")
    password = os.getenv(f"{prefix}_PASSWORD")

    if username and password:
        accounts.append(CreditCardCredentials(
            username=username,
            password=password,
            label=None
        ))
        return accounts

    # Try numbered accounts (CAL_1_*, CAL_2_*, etc.)
    idx = 1
    while True:
        username = os.getenv(f"{prefix}_{idx}_USERNAME")
        password = os.getenv(f"{prefix}_{idx}_PASSWORD")
        label = os.getenv(f"{prefix}_{idx}_LABEL")

        if not username or not password:
            break  # No more accounts

        accounts.append(CreditCardCredentials(
            username=username,
            password=password,
            label=label
        ))
        idx += 1

    return accounts
```

### 3. Config Commands (`cli/commands/config.py`) - Simplified with DRY

All config commands now use the unified `manage_cc_account()` function from `config/settings.py`.

**Add new commands:**
```python
@app.command("list-accounts")
def list_accounts(
    institution: str = typer.Argument(..., help="Institution: cal, max")
):
    """List all configured accounts for an institution"""
    try:
        # Use unified function (DRY)
        success, accounts = manage_cc_account(institution, 'list')

        if not accounts:
            print_info(f"No {institution.upper()} accounts configured")
            print_info(f"Use 'fin-cli config add-account {institution}' to add one")
            return

        # Display table
        table = Table(title=f"{institution.upper()} Accounts", show_header=True, header_style="bold cyan")
        table.add_column("Index", width=8)
        table.add_column("Username", width=20)
        table.add_column("Label", width=20)

        for idx, account in enumerate(accounts):
            masked = account.username[:4] + "****" if len(account.username) > 4 else "****"
            label = account.label or "[dim]No label[/dim]"
            table.add_row(str(idx), masked, label)

        console.print(table)

    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(code=1)

@app.command("add-account")
def add_account(
    institution: str = typer.Argument(..., help="Institution: cal, max"),
    username: Optional[str] = typer.Option(None, "--username", "-u"),
    password: Optional[str] = typer.Option(None, "--password", "-p"),
    label: Optional[str] = typer.Option(None, "--label", "-l"),
):
    """Add a new account for a credit card institution"""
    try:
        # Interactive prompts if not provided
        if not username:
            username = typer.prompt(f"{institution.upper()} username")
        if not password:
            password = typer.prompt(f"{institution.upper()} password", hide_input=True)
        if not label:
            label = typer.prompt("Label (optional, press Enter to skip)", default="") or None

        # Use unified function (DRY)
        manage_cc_account(institution, 'add', username=username, password=password, label=label)

        label_str = f" ({label})" if label else ""
        print_success(f"Added {institution.upper()} account{label_str}")

    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(code=1)


@app.command("remove-account")
def remove_account(
    institution: str = typer.Argument(..., help="Institution: cal, max"),
    identifier: str = typer.Argument(..., help="Account index or label"),
):
    """Remove an account by index or label"""
    try:
        # Use unified function (DRY)
        success, _ = manage_cc_account(institution, 'remove', identifier=identifier)

        if success:
            print_success(f"Removed {institution.upper()} account: {identifier}")
        else:
            print_error(f"Account not found: {identifier}")
            raise typer.Exit(code=1)

    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(code=1)


@app.command("update-account")
def update_account(
    institution: str = typer.Argument(..., help="Institution: cal, max"),
    identifier: str = typer.Argument(..., help="Account index or label"),
    username: Optional[str] = typer.Option(None, "--username", "-u"),
    password: Optional[str] = typer.Option(None, "--password", "-p"),
    label: Optional[str] = typer.Option(None, "--label", "-l"),
):
    """Update account credentials or label"""
    try:
        if not any([username, password, label]):
            print_error("At least one of --username, --password, or --label must be provided")
            raise typer.Exit(code=1)

        # Use unified function (DRY)
        success, _ = manage_cc_account(
            institution, 'update',
            identifier=identifier,
            username=username,
            password=password,
            label=label
        )

        if success:
            print_success(f"Updated {institution.upper()} account: {identifier}")
        else:
            print_error(f"Account not found: {identifier}")
            raise typer.Exit(code=1)

    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(code=1)
```

**Update `show` command:**
```python
@app.command()
def show(
    show_secrets: bool = typer.Option(False, "--show-secrets", "-s", help="Show actual values")
):
    """Show current configuration (credentials are masked by default)"""
    try:
        credentials = load_credentials()

        # ... existing code ...

        table = Table(title="Credentials", show_header=True, header_style="bold magenta")
        table.add_column("Institution", style="cyan", width=20)
        table.add_column("Field", style="green", width=20)
        table.add_column("Value", style="yellow")

        def mask_value(value: Optional[str]) -> str:
            if value is None:
                return "[dim]Not set[/dim]"
            if show_secrets:
                return value
            return "•" * min(len(value), 12)

        # Excellence, Migdal, Phoenix (single accounts - unchanged)
        # ... existing code ...

        # CAL credit cards (multiple accounts - NEW)
        if credentials.cal:
            for idx, account in enumerate(credentials.cal):
                label = f" ({account.label})" if account.label else ""
                table.add_row(f"CAL [{idx}]{label}", "Username", mask_value(account.username))
                table.add_row("", "Password", mask_value(account.password))
                if idx < len(credentials.cal) - 1:  # Add separator between accounts
                    table.add_row("", "", "")
        else:
            table.add_row("CAL", "Username", "[dim]Not configured[/dim]")
            table.add_row("", "Password", "[dim]Not configured[/dim]")

        # Max credit cards (multiple accounts - NEW)
        if credentials.max:
            for idx, account in enumerate(credentials.max):
                label = f" ({account.label})" if account.label else ""
                table.add_row(f"Max [{idx}]{label}", "Username", mask_value(account.username))
                table.add_row("", "Password", mask_value(account.password))
                if idx < len(credentials.max) - 1:
                    table.add_row("", "", "")
        else:
            table.add_row("Max", "Username", "[dim]Not configured[/dim]")
            table.add_row("", "Password", "[dim]Not configured[/dim]")

        # Email (unchanged)
        # ... existing code ...

        console.print(table)

    except Exception as e:
        print_error(f"Failed to load configuration: {e}")
        raise typer.Exit(code=1)
```

### 4. Sync Commands (`cli/commands/sync.py`) - DRY Approach

**Add generic multi-account sync helper (avoids duplication):**
```python
def _sync_credit_card_multi_account(
    institution: str,
    service_method: str,
    account_filters: Optional[List[str]],
    months_back: int,
    months_forward: int,
    headless: bool
):
    """
    Generic multi-account credit card sync (DRY)

    Used by both sync_cal and sync_max to avoid code duplication.

    Args:
        institution: 'cal' or 'max'
        service_method: 'sync_cal' or 'sync_max'
        account_filters: Account selection filters
        months_back, months_forward, headless: Sync parameters
    """
    inst_upper = institution.upper()
    console.print(f"[bold cyan]Syncing {inst_upper} credit card...[/bold cyan]\n")

    # Select accounts
    try:
        accounts_to_sync = select_accounts_to_sync(institution, account_filters)
    except ValueError as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(1)

    # Create database session
    db = SessionLocal()

    # Track results
    total_accounts = len(accounts_to_sync)
    succeeded, failed = 0, 0
    total_cards, total_added, total_updated = 0, 0, 0
    errors = []

    try:
        # Sync each account sequentially
        for current, (idx, account_creds) in enumerate(accounts_to_sync, 1):
            label = f" ({account_creds.label})" if account_creds.label else ""
            console.print(f"\n[bold cyan][{current}/{total_accounts}] Account {idx}{label}[/bold cyan]")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("  Syncing...", total=None)

                try:
                    service = CreditCardService(db)
                    # Call the appropriate service method dynamically
                    result = getattr(service, service_method)(
                        username=account_creds.username,
                        password=account_creds.password,
                        months_back=months_back,
                        months_forward=months_forward,
                        headless=headless
                    )

                    progress.update(task, completed=True)

                    if result.success:
                        console.print(f"  [green]✓ Success![/green]")
                        console.print(f"    Cards synced: {result.cards_synced}")
                        console.print(f"    Transactions added: {result.transactions_added}")
                        console.print(f"    Transactions updated: {result.transactions_updated}")

                        succeeded += 1
                        total_cards += result.cards_synced
                        total_added += result.transactions_added
                        total_updated += result.transactions_updated

                        _apply_rules_after_sync(db, result.transactions_added + result.transactions_updated)
                    else:
                        console.print(f"  [red]✗ Failed: {result.error_message}[/red]")
                        failed += 1
                        errors.append(f"Account {idx}{label}: {result.error_message}")

                except Exception as e:
                    progress.update(task, completed=True)
                    console.print(f"  [red]✗ Failed: {e}[/red]")
                    failed += 1
                    errors.append(f"Account {idx}{label}: {str(e)}")

        # Print summary
        console.print("\n" + "━" * 60)
        console.print("[bold]Summary[/bold]")
        console.print("━" * 60)

        if succeeded > 0:
            console.print(f"  [green]✓ Succeeded: {succeeded}/{total_accounts} accounts[/green]")
        if failed > 0:
            console.print(f"  [red]✗ Failed: {failed}/{total_accounts} accounts[/red]")
            for error in errors:
                console.print(f"    - {error}")

        console.print(f"\n  Total cards synced: {total_cards}")
        console.print(f"  Total transactions added: {total_added}")
        console.print(f"  Total transactions updated: {total_updated}")

        if failed == total_accounts:
            raise typer.Exit(1)

    finally:
        db.close()
```

**Simplified `sync_cal` using helper (DRY):**
```python
@app.command("cal")
def sync_cal(
    headless: bool = typer.Option(True, "--headless/--visible", help="Run browsers in headless mode"),
    months_back: int = typer.Option(3, "--months-back", help="Number of months to fetch backwards"),
    months_forward: int = typer.Option(1, "--months-forward", help="Number of months to fetch forward"),
    account: Optional[List[str]] = typer.Option(None, "--account", "-a", help="Account index or label (default: all)"),
):
    """
    Sync CAL credit card data (supports multiple accounts)

    Examples:
        fin-cli sync cal                    # Sync all accounts
        fin-cli sync cal --account 0        # Sync first account only
        fin-cli sync cal --account personal # Sync account labeled "personal"
        fin-cli sync cal -a 0 -a 2          # Sync accounts 0 and 2
    """
    if not check_database_exists():
        console.print("[bold red]Error: Database not initialized. Run 'fin-cli init' first.[/bold red]")
        raise typer.Exit(1)

    # Call the generic helper function (DRY - no duplication!)
    _sync_credit_card_multi_account(
        institution='cal',
        service_method='sync_cal',
        account_filters=account,
        months_back=months_back,
        months_forward=months_forward,
        headless=headless
    )


@app.command("max")
def sync_max(
    headless: bool = typer.Option(True, "--headless/--visible", help="Run browsers in headless mode"),
    months_back: int = typer.Option(3, "--months-back", help="Number of months to fetch backwards"),
    months_forward: int = typer.Option(1, "--months-forward", help="Number of months to fetch forward"),
    account: Optional[List[str]] = typer.Option(None, "--account", "-a", help="Account index or label (default: all)"),
):
    """
    Sync Max credit card data (supports multiple accounts)

    Examples:
        fin-cli sync max                    # Sync all accounts
        fin-cli sync max --account 0        # Sync first account only
        fin-cli sync max --account work     # Sync account labeled "work"
    """
    if not check_database_exists():
        console.print("[bold red]Error: Database not initialized. Run 'fin-cli init' first.[/bold red]")
        raise typer.Exit(1)

    # Call the generic helper function (DRY - no duplication!)
    _sync_credit_card_multi_account(
        institution='max',
        service_method='sync_max',
        account_filters=account,
        months_back=months_back,
        months_forward=months_forward,
        headless=headless
    )
```

**Update `sync_all`:**
```python
@app.command("all")
def sync_all(
    headless: bool = typer.Option(True, "--headless/--visible", help="Run browsers in headless mode"),
    months_back: int = typer.Option(3, "--months-back", help="Months to sync (for credit cards)"),
):
    """
    Sync all financial data sources

    Note: For credit cards with multiple accounts, all configured accounts will be synced.
    """
    console.print("[bold cyan]Starting full synchronization...[/bold cyan]\n")

    # ... existing database check ...

    # Sync each source
    sync_excellence(headless=headless)
    sync_migdal(headless=headless)
    sync_phoenix(headless=headless)

    # NEW: These now sync all configured accounts
    sync_cal(headless=headless, months_back=months_back, account=None)  # None = all
    sync_max(headless=headless, months_back=months_back, account=None)  # None = all

    console.print("\n[bold green]✓ Full synchronization complete![/bold green]")
```

## Environment Variables

### Format

**Old (backward compatible):**
```bash
CAL_USERNAME=user1
CAL_PASSWORD=pass1
```

**New (numbered accounts):**
```bash
# Account 1
CAL_1_USERNAME=user1
CAL_1_PASSWORD=pass1
CAL_1_LABEL=Personal

# Account 2
CAL_2_USERNAME=user2
CAL_2_PASSWORD=pass2
CAL_2_LABEL=Business

# Same for Max
MAX_1_USERNAME=work_email@company.com
MAX_1_PASSWORD=workpass
MAX_1_LABEL=Work
```

### Loading Priority

1. Check for encrypted credentials file (`.fin/credentials.enc`)
2. If file exists and decrypts successfully, use it (with migration)
3. Otherwise, fall back to environment variables
4. For env vars: Try old single-account format first, then numbered

---

# Phase 4: Pension Multi-Account Extension

## Overview

Extending the credit card multi-account pattern to pension funds (Migdal and Phoenix). This follows the exact same architecture for consistency.

## Key Differences from Credit Cards

### Shared Email for MFA

**Design Decision**: All pension accounts share the same email credentials for MFA code retrieval.

**Rationale**:
- Pension scrapers use email-based MFA (unlike credit card API tokens)
- Email credentials are already stored globally in `EmailCredentials`
- Most users use one email for all MFA codes
- Simpler implementation (no need to manage per-account emails)

**Credential Structure**:
```python
class PensionCredentials(BaseModel):
    """Pension fund credentials"""
    user_id: str  # Required - unique ID for account
    label: Optional[str] = None  # Optional label like "Personal", "Work"
    # Note: email is NOT here - it's global in EmailCredentials

class Credentials(BaseModel):
    # Multi-account pensions
    migdal: List[PensionCredentials] = Field(default_factory=list)
    phoenix: List[PensionCredentials] = Field(default_factory=list)

    # Global email for MFA (shared across all pension accounts)
    email: EmailCredentials = Field(default_factory=EmailCredentials)
```

### Service Method Signature

**Credit Card**:
```python
service.sync_cal(username="user", password="pass", months_back=3, headless=True)
```

**Pension**:
```python
service.sync_migdal(
    user_id="123456789",  # From PensionCredentials
    email_address="user@gmail.com",  # From global EmailCredentials
    email_password="app_password",  # From global EmailCredentials
    headless=True
)
```

## Implementation Details for Pensions

### 1. Data Model Changes (`config/settings.py`)

**Current**:
```python
class PensionCredentials(BaseModel):
    """Pension fund credentials"""
    user_id: Optional[str] = None
    email: Optional[str] = None  # DEPRECATED - not used

class Credentials(BaseModel):
    migdal: PensionCredentials = Field(default_factory=PensionCredentials)  # Single
    phoenix: PensionCredentials = Field(default_factory=PensionCredentials)  # Single
```

**After**:
```python
class PensionCredentials(BaseModel):
    """Pension fund credentials"""
    user_id: str  # Required for account
    label: Optional[str] = None  # NEW: Optional label

class Credentials(BaseModel):
    # Multi-account pensions
    migdal: List[PensionCredentials] = Field(default_factory=list)
    phoenix: List[PensionCredentials] = Field(default_factory=list)

    # Helper method for DRY access
    def get_pension_accounts(self, institution: str) -> List[PensionCredentials]:
        """Get pension accounts by institution (DRY helper)"""
        return getattr(self, institution.lower())
```

### 2. Helper Functions (Reuse from Credit Cards)

**Add to `config/settings.py`**:

```python
def manage_pension_account(
    institution: str,
    operation: str,
    identifier: Optional[str] = None,
    user_id: Optional[str] = None,
    label: Optional[str] = None
) -> tuple[bool, Optional[List[PensionCredentials]]]:
    """
    Generic function for all pension account operations (DRY - mirrors credit cards)

    Args:
        institution: 'migdal' or 'phoenix'
        operation: 'list', 'add', 'remove', 'update'
        identifier: Account index or label (for remove/update)
        user_id: User ID for account (for add/update)
        label: Optional label (for add/update)

    Returns:
        (success, accounts_list) - accounts_list only for 'list' operation
    """
    if institution not in ['migdal', 'phoenix']:
        raise ValueError(f"Invalid institution: {institution}")

    credentials = load_credentials()
    accounts = credentials.get_pension_accounts(institution)

    if operation == 'list':
        return True, accounts

    elif operation == 'add':
        accounts.append(PensionCredentials(
            user_id=user_id,
            label=label
        ))
        save_credentials(credentials)
        return True, None

    elif operation in ['remove', 'update']:
        idx = _find_account_index(accounts, identifier)
        if idx is None:
            return False, None

        if operation == 'remove':
            accounts.pop(idx)
        else:  # update
            if user_id is not None:
                accounts[idx].user_id = user_id
            if label is not None:
                accounts[idx].label = label

        save_credentials(credentials)
        return True, None

    raise ValueError(f"Invalid operation: {operation}")


def select_pension_accounts_to_sync(
    institution: str,
    filters: Optional[List[str]] = None
) -> List[Tuple[int, PensionCredentials]]:
    """
    Select pension accounts to sync (mirrors credit card pattern)

    Args:
        institution: 'migdal' or 'phoenix'
        filters: List of indices or labels (None = all)

    Returns:
        List of (index, account) tuples
    """
    _, accounts = manage_pension_account(institution, 'list')

    if not accounts:
        raise ValueError(f"No {institution.upper()} accounts configured")

    # No filter = all accounts
    if not filters:
        return list(enumerate(accounts))

    # Build selected list
    selected = []
    for filter_str in filters:
        idx = _find_account_index(accounts, filter_str)
        if idx is None:
            raise ValueError(f"Account not found: {filter_str}")
        selected.append((idx, accounts[idx]))

    return selected
```

**Note**: Reuses `_find_account_index()` from credit cards (already works with any credential type with `label` attribute)

### 3. Environment Variables

**Add to `_load_from_environment()` in `config/settings.py`**:

**Old format (backward compatible)**:
```bash
MIGDAL_USER_ID=123456789
PHOENIX_USER_ID=987654321
```

**New format (numbered accounts)**:
```bash
# Migdal accounts
MIGDAL_1_USER_ID=123456789
MIGDAL_1_LABEL=Personal

MIGDAL_2_USER_ID=111222333
MIGDAL_2_LABEL=Work

# Phoenix accounts
PHOENIX_1_USER_ID=987654321
PHOENIX_1_LABEL=Main
```

**Loading function**:
```python
def _load_numbered_pension_accounts(prefix: str) -> List[PensionCredentials]:
    """
    Load numbered pension accounts from environment variables

    Supports both:
    - Old format: MIGDAL_USER_ID (single account)
    - New format: MIGDAL_1_USER_ID, MIGDAL_2_USER_ID, etc.

    Args:
        prefix: 'MIGDAL' or 'PHOENIX'

    Returns:
        List of PensionCredentials
    """
    accounts = []

    # Try old single-account format first
    user_id = os.getenv(f"{prefix}_USER_ID")

    if user_id:
        accounts.append(PensionCredentials(
            user_id=user_id,
            label=None
        ))
        return accounts

    # Try numbered accounts (MIGDAL_1_*, MIGDAL_2_*, etc.)
    idx = 1
    while True:
        user_id = os.getenv(f"{prefix}_{idx}_USER_ID")
        label = os.getenv(f"{prefix}_{idx}_LABEL")

        if not user_id:
            break  # No more accounts

        accounts.append(PensionCredentials(
            user_id=user_id,
            label=label
        ))
        idx += 1

    return accounts
```

**Update `_load_from_environment()`**:
```python
def _load_from_environment() -> Credentials:
    """Load credentials from environment variables"""

    # ... existing broker/email code ...

    # Load multi-account pensions (NEW)
    migdal_accounts = _load_numbered_pension_accounts('MIGDAL')
    phoenix_accounts = _load_numbered_pension_accounts('PHOENIX')

    # Load multi-account credit cards (existing)
    cal_accounts = _load_numbered_accounts('CAL')
    max_accounts = _load_numbered_accounts('MAX')

    return Credentials(
        excellence=excellence,
        migdal=migdal_accounts,  # Changed from single to list
        phoenix=phoenix_accounts,  # Changed from single to list
        cal=cal_accounts,
        max=max_accounts,
        email=email,
    )
```

### 4. Migration Logic

**Add to `load_credentials()` in `config/settings.py`**:

```python
# MIGRATION: Convert old single-account format to list
for institution in ['cal', 'max', 'migdal', 'phoenix']:  # Added pensions
    if institution in raw_data:
        value = raw_data[institution]

        # Old format: single dict with credentials
        if isinstance(value, dict):
            # Credit cards have username/password
            if 'username' in value:
                raw_data[institution] = [value]
            # Pensions have user_id
            elif 'user_id' in value and value['user_id']:
                raw_data[institution] = [value]
            # Empty dict
            else:
                raw_data[institution] = []

        # Already new format: list
        elif isinstance(value, list):
            pass  # No migration needed

        # Empty or null
        else:
            raw_data[institution] = []
```

### 5. Config Commands (`cli/commands/config.py`)

**Extend existing commands to support pensions**:

```python
@app.command("list-accounts")
def list_accounts(
    institution: str = typer.Argument(..., help="Institution: cal, max, migdal, phoenix")
):
    """List all configured accounts for an institution"""
    try:
        # Determine institution type
        if institution in ['cal', 'max']:
            success, accounts = manage_cc_account(institution, 'list')
            field_name = "Username"
            field_getter = lambda acc: acc.username
        elif institution in ['migdal', 'phoenix']:
            success, accounts = manage_pension_account(institution, 'list')
            field_name = "User ID"
            field_getter = lambda acc: acc.user_id
        else:
            raise ValueError(f"Invalid institution: {institution}")

        if not accounts:
            print_info(f"No {institution.upper()} accounts configured")
            print_info(f"Use 'fin-cli config add-account {institution}' to add one")
            return

        # Display table
        table = Table(title=f"{institution.upper()} Accounts", show_header=True, header_style="bold cyan")
        table.add_column("Index", width=8)
        table.add_column(field_name, width=20)
        table.add_column("Label", width=20)

        for idx, account in enumerate(accounts):
            field_value = field_getter(account)
            masked = field_value[:4] + "****" if len(field_value) > 4 else "****"
            label = account.label or "[dim]No label[/dim]"
            table.add_row(str(idx), masked, label)

        console.print(table)

    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(code=1)


@app.command("add-account")
def add_account(
    institution: str = typer.Argument(..., help="Institution: cal, max, migdal, phoenix"),
    username: Optional[str] = typer.Option(None, "--username", "-u", help="Username (for credit cards)"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Password (for credit cards)"),
    user_id: Optional[str] = typer.Option(None, "--user-id", help="User ID (for pensions)"),
    label: Optional[str] = typer.Option(None, "--label", "-l"),
):
    """Add a new account for an institution"""
    try:
        # Credit cards
        if institution in ['cal', 'max']:
            if not username:
                username = typer.prompt(f"{institution.upper()} username")
            if not password:
                password = typer.prompt(f"{institution.upper()} password", hide_input=True)
            if not label:
                label = typer.prompt("Label (optional, press Enter to skip)", default="") or None

            manage_cc_account(institution, 'add', username=username, password=password, label=label)

        # Pensions
        elif institution in ['migdal', 'phoenix']:
            if not user_id:
                user_id = typer.prompt(f"{institution.upper()} user ID")
            if not label:
                label = typer.prompt("Label (optional, press Enter to skip)", default="") or None

            manage_pension_account(institution, 'add', user_id=user_id, label=label)

        else:
            raise ValueError(f"Invalid institution: {institution}")

        label_str = f" ({label})" if label else ""
        print_success(f"Added {institution.upper()} account{label_str}")

    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(code=1)


@app.command("remove-account")
def remove_account(
    institution: str = typer.Argument(..., help="Institution: cal, max, migdal, phoenix"),
    identifier: str = typer.Argument(..., help="Account index or label"),
):
    """Remove an account by index or label"""
    try:
        # Route to appropriate function
        if institution in ['cal', 'max']:
            success, _ = manage_cc_account(institution, 'remove', identifier=identifier)
        elif institution in ['migdal', 'phoenix']:
            success, _ = manage_pension_account(institution, 'remove', identifier=identifier)
        else:
            raise ValueError(f"Invalid institution: {institution}")

        if success:
            print_success(f"Removed {institution.upper()} account: {identifier}")
        else:
            print_error(f"Account not found: {identifier}")
            raise typer.Exit(code=1)

    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(code=1)


@app.command("update-account")
def update_account(
    institution: str = typer.Argument(..., help="Institution: cal, max, migdal, phoenix"),
    identifier: str = typer.Argument(..., help="Account index or label"),
    username: Optional[str] = typer.Option(None, "--username", "-u", help="New username (credit cards only)"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="New password (credit cards only)"),
    user_id: Optional[str] = typer.Option(None, "--user-id", help="New user ID (pensions only)"),
    label: Optional[str] = typer.Option(None, "--label", "-l", help="New label"),
):
    """Update account credentials or label"""
    try:
        # Credit cards
        if institution in ['cal', 'max']:
            if not any([username, password, label]):
                print_error("At least one of --username, --password, or --label must be provided")
                raise typer.Exit(code=1)

            success, _ = manage_cc_account(
                institution, 'update',
                identifier=identifier,
                username=username,
                password=password,
                label=label
            )

        # Pensions
        elif institution in ['migdal', 'phoenix']:
            if not any([user_id, label]):
                print_error("At least one of --user-id or --label must be provided")
                raise typer.Exit(code=1)

            success, _ = manage_pension_account(
                institution, 'update',
                identifier=identifier,
                user_id=user_id,
                label=label
            )

        else:
            raise ValueError(f"Invalid institution: {institution}")

        if success:
            print_success(f"Updated {institution.upper()} account: {identifier}")
        else:
            print_error(f"Account not found: {identifier}")
            raise typer.Exit(code=1)

    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(code=1)
```

**Update `show` command**:
```python
# Add to show() function after credit cards section

# Migdal pension (multiple accounts - NEW)
if credentials.migdal:
    for idx, account in enumerate(credentials.migdal):
        label = f" ({account.label})" if account.label else ""
        table.add_row(f"Migdal [{idx}]{label}", "User ID", mask_value(account.user_id))
        if idx < len(credentials.migdal) - 1:
            table.add_row("", "", "")
else:
    table.add_row("Migdal", "User ID", "[dim]Not configured[/dim]")

# Phoenix pension (multiple accounts - NEW)
if credentials.phoenix:
    for idx, account in enumerate(credentials.phoenix):
        label = f" ({account.label})" if account.label else ""
        table.add_row(f"Phoenix [{idx}]{label}", "User ID", mask_value(account.user_id))
        if idx < len(credentials.phoenix) - 1:
            table.add_row("", "", "")
else:
    table.add_row("Phoenix", "User ID", "[dim]Not configured[/dim]")
```

### 6. Sync Commands (`cli/commands/sync.py`)

**Add generic pension multi-account sync helper**:

```python
def _sync_pension_multi_account(
    institution: str,
    service_method: str,
    account_filters: Optional[List[str]],
    headless: bool
):
    """
    Generic multi-account pension sync (DRY - mirrors credit card pattern)

    Args:
        institution: 'migdal' or 'phoenix'
        service_method: 'sync_migdal' or 'sync_phoenix'
        account_filters: Account selection filters
        headless: Headless mode flag
    """
    inst_upper = institution.upper()
    console.print(f"[bold cyan]Syncing {inst_upper} pension fund...[/bold cyan]\n")

    # Get global email credentials (shared by all accounts)
    credentials = load_credentials()
    email_address = credentials.email.address
    email_password = credentials.email.password

    if not email_address or not email_password:
        console.print("[bold red]Error: Email credentials not configured[/bold red]")
        raise typer.Exit(1)

    # Select accounts
    try:
        accounts_to_sync = select_pension_accounts_to_sync(institution, account_filters)
    except ValueError as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(1)

    # Create database session
    db = SessionLocal()

    # Track results
    total_accounts = len(accounts_to_sync)
    succeeded, failed = 0, 0
    errors = []

    try:
        # Sync each account sequentially
        for current, (idx, account_creds) in enumerate(accounts_to_sync, 1):
            label = f" ({account_creds.label})" if account_creds.label else ""
            console.print(f"\n[bold cyan][{current}/{total_accounts}] Account {idx}{label}[/bold cyan]")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("  Syncing...", total=None)

                try:
                    service = PensionService(db)
                    # Call the appropriate service method dynamically
                    result = getattr(service, service_method)(
                        user_id=account_creds.user_id,
                        email_address=email_address,  # Shared
                        email_password=email_password,  # Shared
                        headless=headless
                    )

                    progress.update(task, completed=True)

                    if result.success:
                        console.print(f"  [green]✓ Success![/green]")
                        console.print(f"    Holdings synced: {result.holdings_count or 0}")
                        succeeded += 1
                    else:
                        console.print(f"  [red]✗ Failed: {result.error_message}[/red]")
                        failed += 1
                        errors.append(f"Account {idx}{label}: {result.error_message}")

                except Exception as e:
                    progress.update(task, completed=True)
                    console.print(f"  [red]✗ Failed: {e}[/red]")
                    failed += 1
                    errors.append(f"Account {idx}{label}: {str(e)}")

        # Print summary
        console.print("\n" + "━" * 60)
        console.print("[bold]Summary[/bold]")
        console.print("━" * 60)

        if succeeded > 0:
            console.print(f"  [green]✓ Succeeded: {succeeded}/{total_accounts} accounts[/green]")
        if failed > 0:
            console.print(f"  [red]✗ Failed: {failed}/{total_accounts} accounts[/red]")
            for error in errors:
                console.print(f"    - {error}")

        if failed == total_accounts:
            raise typer.Exit(1)

    finally:
        db.close()
```

**Update `sync_migdal` command**:
```python
@app.command("migdal")
def sync_migdal(
    headless: bool = typer.Option(True, "--headless/--visible", help="Run browsers in headless mode"),
    account: Optional[List[str]] = typer.Option(None, "--account", "-a", help="Account index or label (default: all)"),
):
    """
    Sync Migdal pension fund data (supports multiple accounts)

    Examples:
        fin-cli sync migdal                    # Sync all accounts
        fin-cli sync migdal --account 0        # Sync first account only
        fin-cli sync migdal --account personal # Sync account labeled "personal"
        fin-cli sync migdal -a 0 -a 2          # Sync accounts 0 and 2
    """
    if not check_database_exists():
        console.print("[bold red]Error: Database not initialized. Run 'fin-cli init' first.[/bold red]")
        raise typer.Exit(1)

    # Call the generic helper function (DRY)
    _sync_pension_multi_account(
        institution='migdal',
        service_method='sync_migdal',
        account_filters=account,
        headless=headless
    )
```

**Update `sync_phoenix` command**:
```python
@app.command("phoenix")
def sync_phoenix(
    headless: bool = typer.Option(True, "--headless/--visible", help="Run browsers in headless mode"),
    account: Optional[List[str]] = typer.Option(None, "--account", "-a", help="Account index or label (default: all)"),
):
    """
    Sync Phoenix pension fund data (supports multiple accounts)

    Examples:
        fin-cli sync phoenix                    # Sync all accounts
        fin-cli sync phoenix --account 0        # Sync first account only
        fin-cli sync phoenix --account work     # Sync account labeled "work"
    """
    if not check_database_exists():
        console.print("[bold red]Error: Database not initialized. Run 'fin-cli init' first.[/bold red]")
        raise typer.Exit(1)

    # Call the generic helper function (DRY)
    _sync_pension_multi_account(
        institution='phoenix',
        service_method='sync_phoenix',
        account_filters=account,
        headless=headless
    )
```

**Update `sync_all`**:
```python
@app.command("all")
def sync_all(
    headless: bool = typer.Option(True, "--headless/--visible", help="Run browsers in headless mode"),
    months_back: int = typer.Option(3, "--months-back", help="Months to sync (for credit cards)"),
):
    """
    Sync all financial data sources

    Note: For institutions with multiple accounts, all configured accounts will be synced.
    """
    console.print("[bold cyan]Starting full synchronization...[/bold cyan]\n")

    # Sync each source (all now support multi-account)
    sync_excellence(headless=headless)

    # Pensions - now sync all accounts
    sync_migdal(headless=headless, account=None)  # None = all
    sync_phoenix(headless=headless, account=None)  # None = all

    # Credit cards - already sync all accounts
    sync_cal(headless=headless, months_back=months_back, account=None)
    sync_max(headless=headless, months_back=months_back, account=None)

    console.print("\n[bold green]✓ Full synchronization complete![/bold green]")
```

## CLI Examples for Pensions

```bash
# List pension accounts
fin-cli config list-accounts migdal
fin-cli config list-accounts phoenix

# Add pension account
fin-cli config add-account migdal --user-id "123456789" --label "Personal"
fin-cli config add-account phoenix --user-id "987654321" --label "Work"

# Remove pension account
fin-cli config remove-account migdal 0
fin-cli config remove-account phoenix personal

# Update pension account
fin-cli config update-account migdal 0 --user-id "new_id"
fin-cli config update-account phoenix personal --label "Business"

# Sync pension accounts
fin-cli sync migdal                    # All accounts
fin-cli sync migdal --account 0        # Specific account by index
fin-cli sync migdal --account personal # Specific account by label
fin-cli sync phoenix -a 0 -a 2         # Multiple accounts

# Sync all (includes all pension accounts)
fin-cli sync all
```

## Implementation Progress - Pensions

**STATUS: 🔄 IN PROGRESS - Pending Implementation**

Target completion date: TBD

### Summary (Estimated)
- **Lines to Change**: ~200 lines (fewer than credit cards due to reuse)
- **Files to Modify**: 3 files (`config/settings.py`, `cli/commands/config.py`, `cli/commands/sync.py`)
- **New Functions to Add**: 3 DRY helper functions (reuse _find_account_index from credit cards)
- **Reuse from Credit Cards**: ~60% code reuse (helper patterns, display logic)
- **Backward Compatible**: ✅ Will auto-migrate old single-account configs
- **Environment Variables**: ✅ Will support both old and new formats

### Phase 4.1: Data Model & Helper Functions 🔄 IN PROGRESS
- [ ] Update `PensionCredentials` model (add `label` field, remove unused `email` field)
- [ ] Change `migdal` and `phoenix` fields from single to `List[PensionCredentials]`
- [ ] Add `get_pension_accounts()` method to `Credentials` class
- [ ] Add `manage_pension_account()` function (mirrors `manage_cc_account`)
- [ ] Add `select_pension_accounts_to_sync()` function (mirrors credit card pattern)
- [ ] Add `_load_numbered_pension_accounts()` for environment variables
- [ ] Update `_load_from_environment()` to load multi-account pensions
- [ ] Add pension migration logic in `load_credentials()`

### Phase 4.2: Config Commands 🔄 PENDING
- [ ] Extend `list-accounts` command to support 'migdal' and 'phoenix'
- [ ] Extend `add-account` command to support pensions (with `--user-id` option)
- [ ] Extend `remove-account` command to support pensions
- [ ] Extend `update-account` command to support pensions
- [ ] Update `show` command to display pension multi-account format

### Phase 4.3: Sync Commands 🔄 PENDING
- [ ] Add `_sync_pension_multi_account()` generic helper
- [ ] Update `sync_migdal()` to support `--account` option
- [ ] Update `sync_phoenix()` to support `--account` option
- [ ] Update `sync_all()` to sync all pension accounts (not just first)
- [ ] Add progress display showing account number and label
- [ ] Add summary display showing success/failure counts
- [ ] Implement partial success handling (continue on error)

### Phase 4.4: Testing 🔄 PENDING
- [ ] Test single pension account migration (old → new format)
- [ ] Test adding/removing/updating pension accounts via CLI
- [ ] Test sync with all pension accounts (no filter)
- [ ] Test sync with specific pension accounts (by index and label)
- [ ] Test sync with multiple pension account filters
- [ ] Test error handling (invalid credentials, MFA failures)
- [ ] Test environment variable loading (old: MIGDAL_USER_ID, new: MIGDAL_1_USER_ID)
- [ ] Test shared email credentials across multiple pension accounts

---

## Implementation Steps

### Phase 1: Data Model & Config Commands
1. Update `CreditCardCredentials` model in `config/settings.py`
2. Change `cal` and `max` fields to `List[CreditCardCredentials]`
3. Add helper functions: `get_credit_card_accounts()`, `add_credit_card_account()`, etc.
4. Add backward compatibility in `load_credentials()`
5. Add environment variable support via `_load_numbered_accounts()`
6. Add new config commands: `list-accounts`, `add-account`, `remove-account`, `update-account`
7. Update `show` command to display multi-account format

### Phase 2: Sync Commands
1. Update `sync_cal()` to handle multiple accounts with `--account` option
2. Update `sync_max()` to handle multiple accounts with `--account` option
3. Update `sync_all()` to sync all accounts for each institution
4. Add progress display showing account number and label
5. Add summary display showing success/failure counts
6. Implement partial success handling (continue on error)

### Phase 3: Testing
1. Test single account migration (old → new format)
2. Test adding/removing/updating accounts via CLI
3. Test sync with all accounts (no filter)
4. Test sync with specific accounts (by index and label)
5. Test sync with multiple account filters
6. Test error handling (invalid credentials on one account)
7. Test environment variable loading (old and new formats)

## Testing Checklist

### Config Management
- [ ] `fin-cli config add-account cal` (interactive)
- [ ] `fin-cli config add-account cal -u user -p pass`
- [ ] `fin-cli config add-account cal -u user -p pass -l Personal`
- [ ] `fin-cli config list-accounts cal`
- [ ] `fin-cli config remove-account cal 0`
- [ ] `fin-cli config remove-account cal personal`
- [ ] `fin-cli config update-account cal 0 --password newpass`
- [ ] `fin-cli config show` displays multiple accounts correctly

### Sync Operations
- [ ] `fin-cli sync cal` (syncs all accounts)
- [ ] `fin-cli sync cal --account 0` (syncs first account)
- [ ] `fin-cli sync cal --account personal` (syncs by label)
- [ ] `fin-cli sync cal -a 0 -a 2` (syncs multiple)
- [ ] `fin-cli sync all` (syncs all institutions including all credit card accounts)
- [ ] Progress display shows correct account numbers and labels
- [ ] Summary shows success/failure counts
- [ ] Partial success works (some accounts fail, others succeed)

### Backward Compatibility
- [ ] Old single-account `.enc` file migrates correctly
- [ ] Old `CAL_USERNAME`/`CAL_PASSWORD` env vars work
- [ ] New numbered env vars work (`CAL_1_USERNAME`, etc.)
- [ ] Mixed old/new doesn't break

### Error Handling
- [ ] Invalid account index shows error
- [ ] Invalid account label shows error
- [ ] No accounts configured shows helpful message
- [ ] Failed login on one account doesn't block others
- [ ] Exit code correct (0 for partial success, 1 for all failed)

## Migration Guide for Users

### If you have existing CAL/Max credentials:

**Option 1: No action needed (automatic migration)**
- Next time you run `fin-cli config show`, your single account will be migrated to the new list format
- Your account will become "Account 0" with no label

**Option 2: Add a label to your existing account**
```bash
fin-cli config update-account cal 0 --label "Personal"
```

### To add a second account:
```bash
fin-cli config add-account cal
# Follow the prompts...
```

### To sync all accounts:
```bash
fin-cli sync cal  # Syncs all configured accounts
```

### To sync only specific accounts:
```bash
fin-cli sync cal --account 0              # First account only
fin-cli sync cal --account personal       # Account labeled "personal"
fin-cli sync cal --account 0 --account 1  # Multiple accounts
```

## Future Enhancements

1. **Parallel sync option**: Add `--parallel` flag for users who want to risk it
2. **Account nicknames**: More flexible naming beyond simple labels
3. **Per-account settings**: Different `months_back` per account
4. **Account groups**: Sync related accounts together ("all personal", "all business")
5. **Account status**: Mark accounts as active/inactive instead of deleting
6. **Dry run**: `--dry-run` flag to show what would be synced without actually syncing