"""
Budget CLI commands for managing monthly budgets
"""

import typer
from datetime import date
from rich.console import Console
from rich.panel import Panel
from typing import Optional

from services.budget_service import BudgetService

app = typer.Typer(help="Manage monthly budgets")
console = Console()


def make_progress_bar(percent: float, width: int = 40) -> str:
    """
    Create an ASCII progress bar.

    Args:
        percent: Percentage (0-100+)
        width: Width of the bar in characters

    Returns:
        Progress bar string with color coding
    """
    # Determine color based on percentage
    if percent >= 100:
        color = "red"
    elif percent >= 80:
        color = "yellow"
    else:
        color = "green"

    # Cap display at 100% for the bar itself
    display_percent = min(percent, 100)
    filled = int(display_percent / 100 * width)
    empty = width - filled

    bar = "█" * filled + "░" * empty
    return f"[{color}]{bar}[/{color}]"


@app.command("show")
def show_budget(
    year: Optional[int] = typer.Option(None, "--year", "-y", help="Year (default: current)"),
    month: Optional[int] = typer.Option(None, "--month", "-m", help="Month 1-12 (default: current)"),
):
    """
    Show budget progress for a month.

    Without arguments, shows current month's budget progress.
    """
    try:
        service = BudgetService()
        today = date.today()
        year = year or today.year
        month = month or today.month

        progress = service.get_budget_progress(year, month)
        service.close()

        # Format month name
        month_name = date(year, month, 1).strftime("%B %Y")

        if progress['budget'] is None:
            console.print(f"\n[yellow]No budget set for {month_name}[/yellow]")
            console.print(f"  Spent: [bold]₪{progress['spent']:,.0f}[/bold]")
            console.print(f"\n[dim]Set a budget with: fin-cli budget set <amount>[/dim]")
            return

        # Build progress display
        spent = progress['spent']
        budget = progress['budget']
        remaining = progress['remaining']
        percent = progress['percent_actual']

        # Status text
        if progress['is_over_budget']:
            status = f"[red bold]₪{abs(remaining):,.0f} OVER BUDGET[/red bold]"
        else:
            status = f"[green]₪{remaining:,.0f} remaining[/green]"

        # Create panel
        bar = make_progress_bar(percent)

        content = f"""
[bold]{month_name}[/bold]

Budget:    ₪{budget:,.0f}
Spent:     ₪{spent:,.0f} ({percent:.1f}%)

{bar}

{status}
"""

        console.print(Panel(content.strip(), title="Budget Progress", border_style="blue"))

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(code=1)


@app.command("set")
def set_budget(
    amount: float = typer.Argument(..., help="Budget amount"),
    year: Optional[int] = typer.Option(None, "--year", "-y", help="Year (default: current)"),
    month: Optional[int] = typer.Option(None, "--month", "-m", help="Month 1-12 (default: current)"),
):
    """
    Set monthly budget.

    Examples:
        fin-cli budget set 5000
        fin-cli budget set 6000 --month 2
    """
    try:
        if amount <= 0:
            console.print("[red]Budget amount must be positive[/red]")
            raise typer.Exit(code=1)

        service = BudgetService()
        today = date.today()
        year = year or today.year
        month = month or today.month

        # Validate month
        if not 1 <= month <= 12:
            console.print("[red]Month must be between 1 and 12[/red]")
            raise typer.Exit(code=1)

        service.set_budget(year, month, amount)
        service.close()

        month_name = date(year, month, 1).strftime("%B %Y")
        console.print(f"[green]✓[/green] Budget for {month_name} set to [bold]₪{amount:,.0f}[/bold]")

        # Show progress
        console.print()
        show_budget(year=year, month=month)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(code=1)


@app.command("delete")
def delete_budget(
    year: Optional[int] = typer.Option(None, "--year", "-y", help="Year (default: current)"),
    month: Optional[int] = typer.Option(None, "--month", "-m", help="Month 1-12 (default: current)"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """
    Delete budget for a month.
    """
    try:
        service = BudgetService()
        today = date.today()
        year = year or today.year
        month = month or today.month

        month_name = date(year, month, 1).strftime("%B %Y")

        if not confirm:
            proceed = typer.confirm(f"Delete budget for {month_name}?")
            if not proceed:
                console.print("[yellow]Cancelled[/yellow]")
                return

        deleted = service.delete_budget(year, month)
        service.close()

        if deleted:
            console.print(f"[green]✓[/green] Budget for {month_name} deleted")
        else:
            console.print(f"[yellow]No budget found for {month_name}[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
