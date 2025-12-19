"""
Main CLI entry point for financial data aggregator

Usage:
    fin-cli init
    fin-cli config
    fin-cli sync --all
    fin-cli accounts list
    fin-cli transactions list --from 2024-01-01
"""

import typer
from typing import Optional
from rich.console import Console
from rich import print as rprint

# Import command modules
from cli.commands import init, config, sync, accounts, transactions, reports, export, maintenance

# Create main Typer app
app = typer.Typer(
    name="fin-cli",
    help="Financial Data Aggregator CLI - Extract and analyze financial data from multiple sources",
    add_completion=False,
)

# Create console for rich output
console = Console()

# Register command groups
app.add_typer(init.app, name="init", help="Initialize database")
app.add_typer(config.app, name="config", help="Manage configuration and credentials")
app.add_typer(sync.app, name="sync", help="Synchronize financial data")
app.add_typer(accounts.app, name="accounts", help="Manage accounts")
app.add_typer(transactions.app, name="transactions", help="Manage transactions")
app.add_typer(reports.app, name="reports", help="Generate reports and analytics")
app.add_typer(export.app, name="export", help="Export financial data to CSV or JSON")
app.add_typer(maintenance.app, name="maintenance", help="Database maintenance and verification")


@app.command()
def version():
    """Show CLI version"""
    from cli import __version__
    rprint(f"[bold blue]fin-cli[/bold blue] version [green]{__version__}[/green]")


@app.callback()
def callback():
    """
    Financial Data Aggregator CLI

    Extracts financial data from Israeli brokers, pension funds, and credit cards.
    Stores data in SQLite for unified access and analysis.
    """
    pass


def main():
    """Entry point for the CLI"""
    app()


if __name__ == "__main__":
    main()