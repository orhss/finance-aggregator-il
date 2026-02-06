"""
Maintenance CLI commands for database management
"""

import typer
import shutil
from pathlib import Path
from datetime import datetime, timedelta, date
from rich.console import Console
from rich.table import Table
from rich import box
from sqlalchemy import func

from db.database import get_db_path, migrate_tags_schema, migrate_category_normalization_schema, migrate_merchant_mapping_schema, migrate_budget_schema
from db.models import Account, Transaction, Balance, SyncHistory
from services.analytics_service import AnalyticsService

app = typer.Typer(help="Database maintenance and verification")
console = Console()


@app.command("cleanup")
def cleanup(
    older_than: int = typer.Option(365, "--older-than", help="Remove data older than N days"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be deleted without deleting"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt")
):
    """
    Clean up old data from the database
    """
    try:
        # Calculate cutoff date
        cutoff_date = date.today() - timedelta(days=older_than)

        analytics = AnalyticsService()

        # Count records to be deleted
        old_transactions = (
            analytics.session.query(func.count(Transaction.id))
            .filter(Transaction.transaction_date < cutoff_date)
            .scalar()
        )

        old_balances = (
            analytics.session.query(func.count(Balance.id))
            .filter(Balance.balance_date < cutoff_date)
            .scalar()
        )

        old_sync_history = (
            analytics.session.query(func.count(SyncHistory.id))
            .filter(SyncHistory.started_at < datetime.combine(cutoff_date, datetime.min.time()))
            .scalar()
        )

        if old_transactions == 0 and old_balances == 0 and old_sync_history == 0:
            console.print(f"[yellow]No data found older than {older_than} days ({cutoff_date})[/yellow]")
            analytics.close()
            return

        # Show what will be deleted
        console.print(f"\n[bold]Data cleanup summary (older than {cutoff_date}):[/bold]")
        console.print(f"  Transactions: [yellow]{old_transactions:,}[/yellow]")
        console.print(f"  Balance records: [yellow]{old_balances:,}[/yellow]")
        console.print(f"  Sync history records: [yellow]{old_sync_history:,}[/yellow]")
        console.print()

        if dry_run:
            console.print("[cyan]Dry run mode - no data will be deleted[/cyan]")
            analytics.close()
            return

        # Confirm deletion
        if not confirm:
            proceed = typer.confirm("Do you want to proceed with deletion?")
            if not proceed:
                console.print("[yellow]Cleanup cancelled[/yellow]")
                analytics.close()
                return

        # Delete old transactions
        if old_transactions > 0:
            analytics.session.query(Transaction).filter(
                Transaction.transaction_date < cutoff_date
            ).delete(synchronize_session=False)
            console.print(f"[green]Deleted {old_transactions:,} old transactions[/green]")

        # Delete old balances
        if old_balances > 0:
            analytics.session.query(Balance).filter(
                Balance.balance_date < cutoff_date
            ).delete(synchronize_session=False)
            console.print(f"[green]Deleted {old_balances:,} old balance records[/green]")

        # Delete old sync history
        if old_sync_history > 0:
            analytics.session.query(SyncHistory).filter(
                SyncHistory.started_at < datetime.combine(cutoff_date, datetime.min.time())
            ).delete(synchronize_session=False)
            console.print(f"[green]Deleted {old_sync_history:,} old sync history records[/green]")

        # Commit changes
        analytics.session.commit()

        # Vacuum database to reclaim space
        console.print("\n[cyan]Optimizing database...[/cyan]")
        analytics.session.execute("VACUUM")
        console.print("[green]Database cleanup completed successfully[/green]")

        analytics.close()

    except Exception as e:
        console.print(f"[red]Error during cleanup: {str(e)}[/red]")
        raise typer.Exit(code=1)


@app.command("backup")
def backup(
    output: str = typer.Option(None, "--output", "-o", help="Backup file path (default: financial_data_YYYYMMDD.db)"),
):
    """
    Create a backup of the database
    """
    try:
        # Get database path
        db_path = get_db_path()

        if not db_path.exists():
            console.print("[red]Database file not found. Run 'fin-cli init' first.[/red]")
            raise typer.Exit(code=1)

        # Generate backup filename if not provided
        if output is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output = f"financial_data_{timestamp}.db"

        backup_path = Path(output)

        # Create parent directory if needed
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy database file
        console.print(f"[cyan]Creating backup...[/cyan]")
        shutil.copy2(db_path, backup_path)

        # Get file size
        size_mb = backup_path.stat().st_size / (1024 * 1024)

        console.print(f"[green]Backup created successfully[/green]")
        console.print(f"  Location: {backup_path.absolute()}")
        console.print(f"  Size: {size_mb:.2f} MB")

    except Exception as e:
        console.print(f"[red]Error creating backup: {str(e)}[/red]")
        raise typer.Exit(code=1)


@app.command("verify")
def verify():
    """
    Verify data integrity and show database statistics
    """
    try:
        analytics = AnalyticsService()

        console.print("\n[bold cyan]Database Verification Report[/bold cyan]\n")

        # Check accounts
        total_accounts = analytics.session.query(func.count(Account.id)).scalar()
        active_accounts = analytics.session.query(func.count(Account.id)).filter(Account.is_active == True).scalar()

        accounts_table = Table(title="Accounts", box=box.ROUNDED)
        accounts_table.add_column("Metric", style="bold")
        accounts_table.add_column("Count", justify="right")
        accounts_table.add_row("Total Accounts", str(total_accounts))
        accounts_table.add_row("Active Accounts", str(active_accounts))
        accounts_table.add_row("Inactive Accounts", str(total_accounts - active_accounts))
        console.print(accounts_table)
        console.print()

        # Check transactions
        total_transactions = analytics.session.query(func.count(Transaction.id)).scalar()
        pending_txns = analytics.session.query(func.count(Transaction.id)).filter(Transaction.status == 'pending').scalar()
        completed_txns = analytics.session.query(func.count(Transaction.id)).filter(Transaction.status == 'completed').scalar()

        # Find transactions with missing accounts
        orphaned_txns = (
            analytics.session.query(func.count(Transaction.id))
            .outerjoin(Account, Transaction.account_id == Account.id)
            .filter(Account.id == None)
            .scalar()
        )

        transactions_table = Table(title="Transactions", box=box.ROUNDED)
        transactions_table.add_column("Metric", style="bold")
        transactions_table.add_column("Count", justify="right")
        transactions_table.add_row("Total Transactions", str(total_transactions))
        transactions_table.add_row("Pending", str(pending_txns))
        transactions_table.add_row("Completed", str(completed_txns))
        if orphaned_txns > 0:
            transactions_table.add_row("Orphaned (missing account)", f"[red]{orphaned_txns}[/red]")
        console.print(transactions_table)
        console.print()

        # Check balances
        total_balances = analytics.session.query(func.count(Balance.id)).scalar()

        # Find balances with missing accounts
        orphaned_balances = (
            analytics.session.query(func.count(Balance.id))
            .outerjoin(Account, Balance.account_id == Account.id)
            .filter(Account.id == None)
            .scalar()
        )

        balances_table = Table(title="Balances", box=box.ROUNDED)
        balances_table.add_column("Metric", style="bold")
        balances_table.add_column("Count", justify="right")
        balances_table.add_row("Total Balance Records", str(total_balances))
        if orphaned_balances > 0:
            balances_table.add_row("Orphaned (missing account)", f"[red]{orphaned_balances}[/red]")
        console.print(balances_table)
        console.print()

        # Check sync history
        total_syncs = analytics.session.query(func.count(SyncHistory.id)).scalar()
        successful_syncs = analytics.session.query(func.count(SyncHistory.id)).filter(SyncHistory.status == 'success').scalar()
        failed_syncs = analytics.session.query(func.count(SyncHistory.id)).filter(SyncHistory.status == 'failed').scalar()
        partial_syncs = analytics.session.query(func.count(SyncHistory.id)).filter(SyncHistory.status == 'partial').scalar()

        sync_table = Table(title="Sync History", box=box.ROUNDED)
        sync_table.add_column("Metric", style="bold")
        sync_table.add_column("Count", justify="right")
        sync_table.add_row("Total Syncs", str(total_syncs))
        sync_table.add_row("Successful", f"[green]{successful_syncs}[/green]")
        if failed_syncs > 0:
            sync_table.add_row("Failed", f"[red]{failed_syncs}[/red]")
        if partial_syncs > 0:
            sync_table.add_row("Partial", f"[yellow]{partial_syncs}[/yellow]")
        console.print(sync_table)
        console.print()

        # Database file size
        db_path = get_db_path()
        if db_path.exists():
            size_mb = db_path.stat().st_size / (1024 * 1024)
            console.print(f"[bold]Database Size:[/bold] {size_mb:.2f} MB")
            console.print(f"[bold]Database Location:[/bold] {db_path.absolute()}")
        console.print()

        # Check for issues
        issues = []
        if orphaned_txns > 0:
            issues.append(f"{orphaned_txns} orphaned transactions (missing account reference)")
        if orphaned_balances > 0:
            issues.append(f"{orphaned_balances} orphaned balance records (missing account reference)")

        if issues:
            console.print("[bold red]Issues Found:[/bold red]")
            for issue in issues:
                console.print(f"  - {issue}")
            console.print("\n[yellow]Consider cleaning up orphaned records or restoring from backup[/yellow]")
        else:
            console.print("[bold green]No integrity issues found[/bold green]")

        analytics.close()

    except Exception as e:
        console.print(f"[red]Error during verification: {str(e)}[/red]")
        raise typer.Exit(code=1)


@app.command("migrate")
def migrate():
    """
    Apply pending database migrations.

    Safe to run multiple times - only applies changes that haven't been made yet.
    Does NOT delete any data.
    """
    try:
        db_path = get_db_path()

        if not db_path.exists():
            console.print("[red]Database file not found. Run 'fin-cli init' first.[/red]")
            raise typer.Exit(code=1)

        console.print("[cyan]Checking for pending migrations...[/cyan]\n")

        # Run tags schema migrations
        console.print("[bold]1. Tags schema migrations:[/bold]")
        base_results = migrate_tags_schema(db_path)
        if base_results["added_columns"] or base_results["created_tables"]:
            if base_results["added_columns"]:
                console.print(f"  [green]Added columns:[/green] {', '.join(base_results['added_columns'])}")
            if base_results["created_tables"]:
                console.print(f"  [green]Created tables:[/green] {', '.join(base_results['created_tables'])}")
        else:
            console.print("  [dim]Already up to date[/dim]")

        # Run category normalization migrations
        console.print("\n[bold]2. Category normalization migrations:[/bold]")
        cat_results = migrate_category_normalization_schema(db_path)
        if cat_results["added_columns"] or cat_results["created_tables"]:
            if cat_results["added_columns"]:
                console.print(f"  [green]Added columns:[/green] {', '.join(cat_results['added_columns'])}")
            if cat_results["created_tables"]:
                console.print(f"  [green]Created tables:[/green] {', '.join(cat_results['created_tables'])}")
            if cat_results.get("data_migrated"):
                console.print("  [green]Migrated existing category data to raw_category[/green]")
        else:
            console.print("  [dim]Already up to date[/dim]")

        # Run merchant mapping migrations
        console.print("\n[bold]3. Merchant mapping migrations:[/bold]")
        merchant_results = migrate_merchant_mapping_schema(db_path)
        if merchant_results["created_tables"]:
            console.print(f"  [green]Created tables:[/green] {', '.join(merchant_results['created_tables'])}")
        else:
            console.print("  [dim]Already up to date[/dim]")

        # Run budget migrations
        console.print("\n[bold]4. Budget migrations:[/bold]")
        budget_results = migrate_budget_schema(db_path)
        if budget_results["created_tables"]:
            console.print(f"  [green]Created tables:[/green] {', '.join(budget_results['created_tables'])}")
        else:
            console.print("  [dim]Already up to date[/dim]")

        console.print("\n[green]Migration complete![/green]")

    except Exception as e:
        console.print(f"[red]Error during migration: {str(e)}[/red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()