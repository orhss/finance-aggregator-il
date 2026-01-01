"""
Sync command for financial data synchronization
"""

import typer
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from pathlib import Path

from db.database import SessionLocal, check_database_exists, DEFAULT_DB_PATH
from config.settings import load_credentials, get_settings, select_accounts_to_sync
from services.broker_service import BrokerService
from services.pension_service import PensionService
from services.credit_card_service import CreditCardService
from services.rules_service import RulesService, RULES_FILE

app = typer.Typer(help="Synchronize financial data from institutions")
console = Console()


@app.command("all")
def sync_all(
    headless: bool = typer.Option(True, "--headless/--visible", help="Run browsers in headless mode"),
    months_back: int = typer.Option(3, "--months-back", help="Months to sync (for credit cards)"),
):
    """
    Sync all financial data sources
    """
    console.print("[bold cyan]Starting full synchronization...[/bold cyan]\n")

    # Check if database exists
    if not check_database_exists():
        console.print("[bold red]Error: Database not initialized. Run 'fin-cli init' first.[/bold red]")
        raise typer.Exit(1)

    # Load credentials
    credentials = load_credentials()

    # Sync each source
    sync_excellence(headless=headless)
    sync_migdal(headless=headless)
    sync_phoenix(headless=headless)
    # Credit cards now sync all configured accounts
    sync_cal(headless=headless, months_back=months_back, account=None)  # None = all accounts
    sync_max(headless=headless, months_back=months_back, account=None)  # None = all accounts

    console.print("\n[bold green]✓ Full synchronization complete![/bold green]")


@app.command("excellence")
def sync_excellence(
    headless: bool = typer.Option(True, "--headless/--visible", help="Run browsers in headless mode"),
):
    """
    Sync Excellence broker data
    """
    console.print("[bold cyan]Syncing Excellence broker...[/bold cyan]")

    # Check database
    if not check_database_exists():
        console.print("[bold red]Error: Database not initialized. Run 'fin-cli init' first.[/bold red]")
        raise typer.Exit(1)

    # Load credentials
    credentials = load_credentials()

    if not credentials.excellence.username or not credentials.excellence.password:
        console.print("[bold red]Error: Excellence credentials not configured.[/bold red]")
        console.print("Run 'fin-cli config' to set up credentials.")
        raise typer.Exit(1)

    # Create database session
    db = SessionLocal()

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Syncing Excellence...", total=None)

            # Create service and sync
            service = BrokerService(db)
            result = service.sync_excellence(
                username=credentials.excellence.username,
                password=credentials.excellence.password
            )

            progress.update(task, completed=True)

        # Display results
        if result.success:
            console.print(f"[green]✓ Success![/green]")
            console.print(f"  Accounts synced: {result.accounts_synced}")
            console.print(f"  Balances added: {result.balances_added}")
        else:
            console.print(f"[red]✗ Failed: {result.error_message}[/red]")
            raise typer.Exit(1)

    finally:
        db.close()


@app.command("migdal")
def sync_migdal(
    headless: bool = typer.Option(True, "--headless/--visible", help="Run browsers in headless mode"),
):
    """
    Sync Migdal pension data
    """
    console.print("[bold cyan]Syncing Migdal pension...[/bold cyan]")

    # Check database
    if not check_database_exists():
        console.print("[bold red]Error: Database not initialized. Run 'fin-cli init' first.[/bold red]")
        raise typer.Exit(1)

    # Load credentials
    credentials = load_credentials()

    if not credentials.migdal.user_id or not credentials.email.address or not credentials.email.password:
        console.print("[bold red]Error: Migdal credentials not configured.[/bold red]")
        console.print("Run 'fin-cli config' to set up credentials.")
        raise typer.Exit(1)

    # Create database session
    db = SessionLocal()

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Syncing Migdal (this may take a while due to MFA)...", total=None)

            # Create service and sync
            service = PensionService(db)
            result = service.sync_migdal(
                user_id=credentials.migdal.user_id,
                email_address=credentials.email.address,
                email_password=credentials.email.password,
                headless=headless
            )

            progress.update(task, completed=True)

        # Display results
        if result.success:
            console.print(f"[green]✓ Success![/green]")
            console.print(f"  Accounts synced: {result.accounts_synced}")
            console.print(f"  Balances added: {result.balances_added}")
            if result.financial_data:
                console.print(f"  Data: {result.financial_data}")
        else:
            console.print(f"[red]✗ Failed: {result.error_message}[/red]")
            raise typer.Exit(1)

    finally:
        db.close()


@app.command("phoenix")
def sync_phoenix(
    headless: bool = typer.Option(True, "--headless/--visible", help="Run browsers in headless mode"),
):
    """
    Sync Phoenix pension data
    """
    console.print("[bold cyan]Syncing Phoenix pension...[/bold cyan]")

    # Check database
    if not check_database_exists():
        console.print("[bold red]Error: Database not initialized. Run 'fin-cli init' first.[/bold red]")
        raise typer.Exit(1)

    # Load credentials
    credentials = load_credentials()

    if not credentials.phoenix.user_id or not credentials.email.address or not credentials.email.password:
        console.print("[bold red]Error: Phoenix credentials not configured.[/bold red]")
        console.print("Run 'fin-cli config' to set up credentials.")
        raise typer.Exit(1)

    # Create database session
    db = SessionLocal()

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Syncing Phoenix (this may take a while due to MFA)...", total=None)

            # Create service and sync
            service = PensionService(db)
            result = service.sync_phoenix(
                user_id=credentials.phoenix.user_id,
                email_address=credentials.email.address,
                email_password=credentials.email.password,
                headless=headless
            )

            progress.update(task, completed=True)

        # Display results
        if result.success:
            console.print(f"[green]✓ Success![/green]")
            console.print(f"  Accounts synced: {result.accounts_synced}")
            console.print(f"  Balances added: {result.balances_added}")
            if result.financial_data:
                console.print(f"  Data: {result.financial_data}")
        else:
            console.print(f"[red]✗ Failed: {result.error_message}[/red]")
            raise typer.Exit(1)

    finally:
        db.close()


def _apply_rules_after_sync(db, transaction_count: int) -> None:
    """Apply categorization rules after sync if rules file exists"""
    if not RULES_FILE.exists():
        return

    if transaction_count == 0:
        return

    try:
        rules_service = RulesService(session=db)
        rules = rules_service.get_rules()

        if not rules:
            return

        # Apply rules only to transactions without user_category
        result = rules_service.apply_rules(only_uncategorized=True)

        if result["modified"] > 0:
            console.print(f"  [blue]Rules applied:[/blue] {result['modified']} transactions auto-categorized")

    except Exception as e:
        # Don't fail sync if rules application fails
        console.print(f"  [yellow]Warning: Could not apply rules: {e}[/yellow]")


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


if __name__ == "__main__":
    app()