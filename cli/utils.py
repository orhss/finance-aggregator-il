"""
CLI utility functions for improved user experience
"""

from typing import Optional, Any
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich import print as rprint

console = Console()


def print_success(message: str):
    """Print success message in green"""
    rprint(f"[green]✓[/green] {message}")


def print_error(message: str):
    """Print error message in red"""
    rprint(f"[red]✗[/red] {message}")


def print_warning(message: str):
    """Print warning message in yellow"""
    rprint(f"[yellow]⚠[/yellow] {message}")


def print_info(message: str):
    """Print info message in blue"""
    rprint(f"[blue]ℹ[/blue] {message}")


def create_table(title: str, columns: list[str]) -> Table:
    """
    Create a rich table with given title and columns

    Args:
        title: Table title
        columns: List of column names

    Returns:
        Rich Table instance
    """
    table = Table(title=title, show_header=True, header_style="bold magenta")
    for column in columns:
        table.add_column(column)
    return table


def print_panel(content: str, title: Optional[str] = None, style: str = "blue"):
    """
    Print content in a panel

    Args:
        content: Content to display
        title: Optional panel title
        style: Panel border style/color
    """
    panel = Panel(content, title=title, border_style=style)
    console.print(panel)


def create_progress() -> Progress:
    """
    Create a progress bar with spinner

    Returns:
        Rich Progress instance
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    )


def confirm_action(message: str, default: bool = False) -> bool:
    """
    Ask user for confirmation

    Args:
        message: Confirmation message
        default: Default response

    Returns:
        True if user confirms, False otherwise
    """
    import typer
    return typer.confirm(message, default=default)
