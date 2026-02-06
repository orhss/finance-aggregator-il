"""
Sync command for financial data synchronization
"""

import typer
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from pathlib import Path

from db.database import check_database_exists, DEFAULT_DB_PATH
from cli.utils import get_db_session
from config.settings import load_credentials, get_settings, select_accounts_to_sync, select_pension_accounts_to_sync
from services.broker_service import BrokerService
from services.pension_service import PensionService
from services.credit_card_service import CreditCardService
from services.rules_service import RulesService, RULES_FILE

app = typer.Typer(help="Synchronize financial data from institutions")
console = Console()


@app.command("all")
def sync_all(
    headless: bool = typer.Option(True, "--headless/--visible", help="Run browsers in headless mode"),
    months_back: int = typer.Option(3, "--months-back", help="Months to sync backwards (for credit cards)"),
    months_forward: int = typer.Option(1, "--months-forward", help="Months to sync forward (for credit cards)"),
):
    """
    Sync all financial data sources.

    Continues syncing other institutions even if one fails.
    Shows summary of successes/failures at the end.
    """
    console.print("[bold cyan]Starting full synchronization...[/bold cyan]\n")

    # Check if database exists
    if not check_database_exists():
        console.print("[bold red]Error: Database not initialized. Run 'fin-cli init' first.[/bold red]")
        raise typer.Exit(1)

    # Define sync operations: (name, function, kwargs)
    sync_operations = [
        ("Excellence", sync_excellence, {"headless": headless}),
        ("Meitav", sync_meitav, {"headless": headless}),
        ("Migdal", sync_migdal, {"headless": headless, "account": None}),
        ("Phoenix", sync_phoenix, {"headless": headless, "account": None}),
        ("CAL", sync_cal, {"headless": headless, "months_back": months_back, "months_forward": months_forward, "account": None}),
        ("Max", sync_max, {"headless": headless, "months_back": months_back, "months_forward": months_forward, "account": None}),
        ("Isracard", sync_isracard, {"headless": headless, "months_back": months_back, "months_forward": months_forward, "account": None}),
    ]

    succeeded = []
    failed = []
    skipped = []

    for name, sync_func, kwargs in sync_operations:
        try:
            sync_func(**kwargs)
            succeeded.append(name)
        except typer.Exit as e:
            # typer.Exit(1) means failure, Exit(0) or no code means success
            if e.exit_code != 0:
                failed.append(name)
            else:
                succeeded.append(name)
        except Exception as e:
            console.print(f"[red]✗ {name} failed unexpectedly: {e}[/red]")
            failed.append(name)

    # Print summary
    console.print("\n" + "━" * 60)
    console.print("[bold]Sync Summary[/bold]")
    console.print("━" * 60)

    if succeeded:
        console.print(f"[green]✓ Succeeded ({len(succeeded)}): {', '.join(succeeded)}[/green]")
    if failed:
        console.print(f"[red]✗ Failed ({len(failed)}): {', '.join(failed)}[/red]")

    total = len(succeeded) + len(failed)
    if failed:
        console.print(f"\n[yellow]Completed with errors: {len(succeeded)}/{total} institutions synced successfully[/yellow]")
        if len(failed) == total:
            raise typer.Exit(1)
    else:
        console.print(f"\n[bold green]✓ Full synchronization complete! ({total}/{total} succeeded)[/bold green]")


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

    with get_db_session() as db:
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
                password=credentials.excellence.password,
                headless=headless
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


@app.command("meitav")
def sync_meitav(
    headless: bool = typer.Option(True, "--headless/--visible", help="Run browsers in headless mode"),
):
    """
    Sync Meitav broker data
    """
    console.print("[bold cyan]Syncing Meitav broker...[/bold cyan]")

    # Check database
    if not check_database_exists():
        console.print("[bold red]Error: Database not initialized. Run 'fin-cli init' first.[/bold red]")
        raise typer.Exit(1)

    # Load credentials
    credentials = load_credentials()

    if not credentials.meitav.username or not credentials.meitav.password:
        console.print("[bold red]Error: Meitav credentials not configured.[/bold red]")
        console.print("Run 'fin-cli config setup' to set up credentials.")
        raise typer.Exit(1)

    with get_db_session() as db:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Syncing Meitav (may take a while)...", total=None)

            # Create service and sync
            service = BrokerService(db)
            result = service.sync_meitav(
                username=credentials.meitav.username,
                password=credentials.meitav.password,
                headless=headless
            )

            progress.update(task, completed=True)

        # Display results
        if result.success:
            console.print(f"[green]✓ Success![/green]")
            console.print(f"  Accounts synced: {result.accounts_synced}")
            console.print(f"  Balances added: {result.balances_added}")
            if result.balances_updated:
                console.print(f"  Balances updated: {result.balances_updated}")
        else:
            console.print(f"[red]✗ Failed: {result.error_message}[/red]")
            raise typer.Exit(1)


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

    # Get global email credentials (fallback)
    credentials = load_credentials()
    global_email_address = credentials.email.address
    global_email_password = credentials.email.password

    # Select accounts
    try:
        accounts_to_sync = select_pension_accounts_to_sync(institution, account_filters)
    except ValueError as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(1)

    # Track results
    total_accounts = len(accounts_to_sync)
    succeeded, failed = 0, 0
    errors = []

    with get_db_session() as db:
        # Sync each account sequentially
        for current, (idx, account_creds) in enumerate(accounts_to_sync, 1):
            label = f" ({account_creds.label})" if account_creds.label else ""
            console.print(f"\n[bold cyan][{current}/{total_accounts}] Account {idx}{label}[/bold cyan]")

            # Use per-account email if set, otherwise fallback to global
            email_address = account_creds.email_address or global_email_address
            email_password = account_creds.email_password or global_email_password

            if not email_address or not email_password:
                console.print("[bold red]Error: Email credentials not configured (neither per-account nor global)[/bold red]")
                console.print("Configure via: fin-cli config update-account {institution} {idx} --email-address <email> --email-password <password>")
                failed += 1
                errors.append(f"Account {idx}{label}: Email credentials missing")
                continue

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("  Syncing (MFA may take a while)...", total=None)

                try:
                    service = PensionService(db)
                    # Call the appropriate service method dynamically
                    result = getattr(service, service_method)(
                        user_id=account_creds.user_id,
                        email_address=email_address,  # Per-account or global
                        email_password=email_password,  # Per-account or global
                        headless=headless
                    )

                    progress.update(task, completed=True)

                    if result.success:
                        console.print(f"  [green]✓ Success![/green]")
                        console.print(f"    Balances synced: {result.balances_added + result.balances_updated}")
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

    Used by sync_cal, sync_max, and sync_isracard to avoid code duplication.

    Args:
        institution: 'cal', 'max', or 'isracard'
        service_method: 'sync_cal', 'sync_max', or 'sync_isracard'
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

    # Track results
    total_accounts = len(accounts_to_sync)
    succeeded, failed = 0, 0
    total_cards, total_added, total_updated = 0, 0, 0
    total_unmapped_categories = 0
    errors = []

    with get_db_session() as db:
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

                        # Report unmapped categories
                        if result.unmapped_categories:
                            unmapped_txns = sum(u['count'] for u in result.unmapped_categories)
                            console.print(f"  [yellow]  Unmapped categories: {len(result.unmapped_categories)} ({unmapped_txns} transactions)[/yellow]")
                            total_unmapped_categories += len(result.unmapped_categories)

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

        # Suggest reviewing unmapped categories if any
        if total_unmapped_categories > 0:
            console.print(f"\n[yellow]  {total_unmapped_categories} unmapped categories detected.[/yellow]")
            console.print("  [dim]Run 'fin-cli categories unmapped' to review and map them.[/dim]")

        if failed == total_accounts:
            raise typer.Exit(1)


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


@app.command("isracard")
def sync_isracard(
    headless: bool = typer.Option(True, "--headless/--visible", help="Run browsers in headless mode"),
    months_back: int = typer.Option(3, "--months-back", help="Number of months to fetch backwards"),
    months_forward: int = typer.Option(1, "--months-forward", help="Number of months to fetch forward"),
    account: Optional[List[str]] = typer.Option(None, "--account", "-a", help="Account index or label (default: all)"),
):
    """
    Sync Isracard credit card data (supports multiple accounts)

    Note: Username must be in format 'user_id:card_6_digits' (e.g., '123456789:123456')

    Examples:
        fin-cli sync isracard                    # Sync all accounts
        fin-cli sync isracard --account 0        # Sync first account only
        fin-cli sync isracard --account personal # Sync account labeled "personal"
    """
    if not check_database_exists():
        console.print("[bold red]Error: Database not initialized. Run 'fin-cli init' first.[/bold red]")
        raise typer.Exit(1)

    # Call the generic helper function (DRY - no duplication!)
    _sync_credit_card_multi_account(
        institution='isracard',
        service_method='sync_isracard',
        account_filters=account,
        months_back=months_back,
        months_forward=months_forward,
        headless=headless
    )


if __name__ == "__main__":
    app()