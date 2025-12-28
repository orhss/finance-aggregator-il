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
import logging
from typing import Optional
from rich.console import Console
from rich.logging import RichHandler
from rich import print as rprint

# Import command modules
from cli.commands import init, config, sync, accounts, transactions, reports, export, maintenance, tags, rules

# Create main Typer app
app = typer.Typer(
    name="fin-cli",
    help="Financial Data Aggregator CLI - Extract and analyze financial data from multiple sources",
    add_completion=False,
)

# Create console for rich output
console = Console()


def setup_logging(verbose: bool = False, debug: bool = False):
    """Configure logging for the CLI

    Args:
        verbose: Enable INFO level logging
        debug: Enable DEBUG level logging (more detailed)
    """
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    else:
        # Default: only show warnings and errors
        level = logging.WARNING

    # Configure root logger with RichHandler for nice formatting
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(
            console=console,
            show_time=debug,
            show_path=debug,
            rich_tracebacks=True
        )]
    )

    # Also configure specific loggers for our modules
    for logger_name in ['scrapers', 'services']:
        logging.getLogger(logger_name).setLevel(level)

# Register command groups
app.add_typer(init.app, name="init", help="Initialize database")
app.add_typer(config.app, name="config", help="Manage configuration and credentials")
app.add_typer(sync.app, name="sync", help="Synchronize financial data")
app.add_typer(accounts.app, name="accounts", help="Manage accounts")
app.add_typer(transactions.app, name="transactions", help="Manage transactions")
app.add_typer(reports.app, name="reports", help="Generate reports and analytics")
app.add_typer(export.app, name="export", help="Export financial data to CSV or JSON")
app.add_typer(maintenance.app, name="maintenance", help="Database maintenance and verification")
app.add_typer(tags.app, name="tags", help="Manage transaction tags")
app.add_typer(rules.app, name="rules", help="Manage auto-categorization rules")


@app.command()
def version():
    """Show CLI version"""
    from cli import __version__
    rprint(f"[bold blue]fin-cli[/bold blue] version [green]{__version__}[/green]")


@app.callback()
def callback(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output (INFO level)"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug output (DEBUG level)"),
):
    """
    Financial Data Aggregator CLI

    Extracts financial data from Israeli brokers, pension funds, and credit cards.
    Stores data in SQLite for unified access and analysis.
    """
    setup_logging(verbose=verbose, debug=debug)


def main():
    """Entry point for the CLI"""
    app()


if __name__ == "__main__":
    main()