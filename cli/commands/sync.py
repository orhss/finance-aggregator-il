"""
Sync command for financial data synchronization
"""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from pathlib import Path

from db.database import SessionLocal, check_database_exists, DEFAULT_DB_PATH
from config.settings import load_credentials, get_settings
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
    sync_cal(headless=headless, months_back=months_back)
    sync_max(headless=headless, months_back=months_back)

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


@app.command("cal")
def sync_cal(
    headless: bool = typer.Option(True, "--headless/--visible", help="Run browsers in headless mode"),
    months_back: int = typer.Option(3, "--months-back", help="Number of months to fetch backwards"),
    months_forward: int = typer.Option(1, "--months-forward", help="Number of months to fetch forward"),
):
    """
    Sync CAL credit card data
    """
    console.print("[bold cyan]Syncing CAL credit card...[/bold cyan]")

    # Check database
    if not check_database_exists():
        console.print("[bold red]Error: Database not initialized. Run 'fin-cli init' first.[/bold red]")
        raise typer.Exit(1)

    # Load credentials
    credentials = load_credentials()

    if not credentials.cal.username or not credentials.cal.password:
        console.print("[bold red]Error: CAL credentials not configured.[/bold red]")
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
            task = progress.add_task("Syncing CAL...", total=None)

            # Create service and sync
            service = CreditCardService(db)
            result = service.sync_cal(
                username=credentials.cal.username,
                password=credentials.cal.password,
                months_back=months_back,
                months_forward=months_forward,
                headless=headless
            )

            progress.update(task, completed=True)

        # Display results
        if result.success:
            console.print(f"[green]✓ Success![/green]")
            console.print(f"  Cards synced: {result.cards_synced}")
            console.print(f"  Transactions added: {result.transactions_added}")
            console.print(f"  Transactions updated: {result.transactions_updated}")

            # Auto-apply categorization rules to new/updated transactions
            _apply_rules_after_sync(db, result.transactions_added + result.transactions_updated)
        else:
            console.print(f"[red]✗ Failed: {result.error_message}[/red]")
            raise typer.Exit(1)

    finally:
        db.close()


@app.command("max")
def sync_max(
    headless: bool = typer.Option(True, "--headless/--visible", help="Run browsers in headless mode"),
    months_back: int = typer.Option(3, "--months-back", help="Number of months to fetch backwards"),
    months_forward: int = typer.Option(1, "--months-forward", help="Number of months to fetch forward"),
):
    """
    Sync Max credit card data
    """
    console.print("[bold cyan]Syncing Max credit card...[/bold cyan]")

    # Check database
    if not check_database_exists():
        console.print("[bold red]Error: Database not initialized. Run 'fin-cli init' first.[/bold red]")
        raise typer.Exit(1)

    # Load credentials
    credentials = load_credentials()

    if not credentials.max.username or not credentials.max.password:
        console.print("[bold red]Error: Max credentials not configured.[/bold red]")
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
            task = progress.add_task("Syncing Max...", total=None)

            # Create service and sync
            service = CreditCardService(db)
            result = service.sync_max(
                username=credentials.max.username,
                password=credentials.max.password,
                months_back=months_back,
                months_forward=months_forward,
                headless=headless
            )

            progress.update(task, completed=True)

        # Display results
        if result.success:
            console.print(f"[green]✓ Success![/green]")
            console.print(f"  Cards synced: {result.cards_synced}")
            console.print(f"  Transactions added: {result.transactions_added}")
            console.print(f"  Transactions updated: {result.transactions_updated}")

            # Auto-apply categorization rules to new/updated transactions
            _apply_rules_after_sync(db, result.transactions_added + result.transactions_updated)
        else:
            console.print(f"[red]✗ Failed: {result.error_message}[/red]")
            raise typer.Exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    app()