"""
CLI utility functions for improved user experience
"""

import re
from contextlib import contextmanager
from datetime import date, datetime
from typing import Optional, Tuple, Generator
from rich.console import Console
from bidi.algorithm import get_display
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich import print as rprint
import typer

console = Console()


# ==================== Date Parsing Utilities ====================

def parse_date(date_str: str, param_name: str = "date") -> date:
    """
    Parse a YYYY-MM-DD date string.

    Args:
        date_str: Date string in YYYY-MM-DD format
        param_name: Name of the parameter for error messages

    Returns:
        Parsed date object

    Raises:
        typer.Exit: If date format is invalid
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        console.print(f"[red]Invalid {param_name} format. Use YYYY-MM-DD[/red]")
        raise typer.Exit(code=1)


def parse_date_range(
    from_date: Optional[str],
    to_date: Optional[str]
) -> Tuple[Optional[date], Optional[date]]:
    """
    Parse optional from/to date strings.

    Args:
        from_date: Optional start date string (YYYY-MM-DD)
        to_date: Optional end date string (YYYY-MM-DD)

    Returns:
        Tuple of (from_date, to_date) as date objects or None

    Raises:
        typer.Exit: If any date format is invalid
    """
    from_date_obj = parse_date(from_date, "from date") if from_date else None
    to_date_obj = parse_date(to_date, "to date") if to_date else None
    return from_date_obj, to_date_obj


# ==================== Service Context Managers ====================

@contextmanager
def get_analytics() -> Generator["AnalyticsService", None, None]:
    """
    Context manager for AnalyticsService.

    Ensures proper cleanup of database session on exit.

    Usage:
        with get_analytics() as analytics:
            stats = analytics.get_overall_stats()
    """
    from services.analytics_service import AnalyticsService
    service = AnalyticsService()
    try:
        yield service
    finally:
        service.close()


@contextmanager
def get_db_session() -> Generator["Session", None, None]:
    """
    Context manager for database session.

    Ensures proper cleanup on exit.

    Usage:
        with get_db_session() as session:
            accounts = session.query(Account).all()
    """
    from db.database import SessionLocal
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def spinner(description: str) -> Generator[None, None, None]:
    """
    Context manager for progress spinner.

    Shows a spinner with description while code executes.

    Usage:
        with spinner("Fetching data..."):
            data = fetch_data()

    Args:
        description: Text to display next to spinner
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(description=description, total=None)
        yield


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


# Hebrew Unicode range pattern
_HEBREW_PATTERN = re.compile(r'[\u0590-\u05FF]')


def contains_hebrew(text: str) -> bool:
    """Check if text contains Hebrew characters"""
    return bool(_HEBREW_PATTERN.search(text))


def fix_rtl(text: Optional[str]) -> str:
    """
    Fix RTL text display for terminals.

    Only applies bidi algorithm if text contains Hebrew characters,
    otherwise returns the original text unchanged.

    Args:
        text: Text that may contain Hebrew characters

    Returns:
        Text with proper RTL display for LTR terminals
    """
    if not text:
        return text or ""

    if contains_hebrew(text):
        return get_display(text)

    return text
