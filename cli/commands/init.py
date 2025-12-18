"""
Database initialization command
"""

import typer
from pathlib import Path
from rich import print as rprint
from cli.utils import print_success, print_error, print_info, print_panel, confirm_action
from db.database import init_db, check_database_exists, DEFAULT_DB_PATH, drop_all_tables
from config.settings import get_settings

app = typer.Typer(help="Initialize database", invoke_without_command=True)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    db_path: Path = typer.Option(
        DEFAULT_DB_PATH,
        "--db-path",
        "-d",
        help="Path to SQLite database file"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force reinitialization (will drop existing tables)"
    )
):
    """
    Initialize the financial data database

    Creates a SQLite database with tables for:
    - accounts (broker, pension, credit card accounts)
    - transactions (unified transaction storage)
    - balances (account balance snapshots)
    - sync_history (synchronization logs)
    """
    # If a subcommand is being invoked, skip this
    if ctx.invoked_subcommand is not None:
        return

    try:
        rprint("\n[bold blue]Financial Data Aggregator - Database Initialization[/bold blue]\n")

        # Check if database already exists
        db_exists = check_database_exists(db_path)

        if db_exists and not force:
            print_info(f"Database already exists at: {db_path}")
            rprint("Use [yellow]--force[/yellow] to reinitialize (this will drop all tables)")
            return

        if db_exists and force:
            if not confirm_action("⚠️  This will drop all existing tables and data. Continue?", default=False):
                print_info("Initialization cancelled")
                return

            print_info("Dropping existing tables...")
            drop_all_tables(db_path)

        # Ensure parent directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        print_info(f"Creating database at: {db_path}")
        engine = init_db(db_path)

        # Print success message
        print_success("Database initialized successfully!")

        # Show database info
        info_message = f"""
[bold]Database Location:[/bold] {db_path}
[bold]Size:[/bold] {db_path.stat().st_size} bytes

[bold]Tables Created:[/bold]
  • accounts (account information)
  • transactions (transaction records)
  • balances (balance snapshots)
  • sync_history (sync logs)

[bold]Next Steps:[/bold]
  1. Configure credentials: [cyan]fin-cli config setup[/cyan]
  2. Sync data: [cyan]fin-cli sync --all[/cyan] (coming in Phase 2)
  3. View accounts: [cyan]fin-cli accounts list[/cyan] (coming in Phase 3)
"""
        print_panel(info_message, title="✓ Initialization Complete", style="green")

    except Exception as e:
        print_error(f"Failed to initialize database: {e}")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()