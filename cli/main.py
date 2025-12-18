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
from cli.commands import init, config

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