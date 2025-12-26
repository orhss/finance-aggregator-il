"""
Reporting and analytics CLI commands
"""

import typer
from datetime import date, datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from typing import Optional, List, Dict, Any

from cli.utils import fix_rtl
from services.analytics_service import AnalyticsService

app = typer.Typer(help="Generate reports and analytics")
console = Console()


# ==================== Visualization Helpers ====================

def make_bar(value: float, max_value: float, width: int = 30, color: str = "cyan") -> str:
    """
    Create an ASCII bar for visualization

    Args:
        value: The value to represent
        max_value: Maximum value (for scaling)
        width: Width of the bar in characters
        color: Rich color for the bar

    Returns:
        Rich-formatted bar string
    """
    if max_value <= 0:
        return ""
    ratio = min(abs(value) / max_value, 1.0)
    filled = int(ratio * width)
    bar = "█" * filled
    return f"[{color}]{bar}[/{color}]"


def make_sparkline(values: List[float], width: int = 6) -> str:
    """
    Create a sparkline using Unicode block characters

    Args:
        values: List of values to visualize
        width: Number of characters in sparkline

    Returns:
        Sparkline string using ▁▂▃▄▅▆▇█ characters
    """
    if not values:
        return ""

    blocks = " ▁▂▃▄▅▆▇█"
    min_val = min(values)
    max_val = max(values)
    range_val = max_val - min_val

    if range_val == 0:
        return "▄" * min(len(values), width)

    # Normalize and map to block characters
    result = []
    for v in values[-width:]:  # Take last 'width' values
        normalized = (v - min_val) / range_val
        block_idx = int(normalized * (len(blocks) - 1))
        result.append(blocks[block_idx])

    return "".join(result)


def get_trend_indicator(current: float, previous: float) -> tuple[str, str]:
    """
    Get trend arrow and color based on change

    Args:
        current: Current value
        previous: Previous value

    Returns:
        Tuple of (arrow, color)
    """
    if previous == 0:
        return "→", "dim"

    change_pct = ((current - previous) / abs(previous)) * 100

    if abs(change_pct) < 2:
        return "→", "dim"
    elif change_pct > 0:
        return "↗", "red"  # Spending up is red (bad)
    else:
        return "↘", "green"  # Spending down is green (good)


def format_change(current: float, previous: float) -> str:
    """
    Format percentage change with color

    Args:
        current: Current value
        previous: Previous value

    Returns:
        Formatted change string with color
    """
    if previous == 0:
        return "[dim]baseline[/dim]"

    change_pct = ((current - previous) / abs(previous)) * 100
    sign = "+" if change_pct > 0 else ""

    if abs(change_pct) < 2:
        return f"[dim]{sign}{change_pct:.1f}%[/dim]"
    elif change_pct > 0:
        return f"[red]{sign}{change_pct:.1f}%[/red]"
    else:
        return f"[green]{change_pct:.1f}%[/green]"


def generate_insights(
    monthly_data: List[Dict[str, Any]],
    category_data: Dict[str, Any]
) -> List[str]:
    """
    Generate automatic insights from spending data

    Args:
        monthly_data: List of monthly spending dicts
        category_data: Category trends data

    Returns:
        List of insight strings
    """
    insights = []

    if not monthly_data:
        return insights

    # Find highest/lowest spending months
    amounts = [(m['total_amount'], m['month'], m['year']) for m in monthly_data]
    if amounts:
        max_month = max(amounts, key=lambda x: abs(x[0]))
        min_month = min(amounts, key=lambda x: abs(x[0]))

        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

        # Highest spending month
        insights.append(
            f"{month_names[max_month[1]-1]} {max_month[2]} had highest spending "
            f"(₪{abs(max_month[0]):,.0f})"
        )

    # Month-over-month trend for last month
    if len(monthly_data) >= 2:
        last = monthly_data[-1]
        prev = monthly_data[-2]
        change_pct = ((last['total_amount'] - prev['total_amount']) /
                      abs(prev['total_amount']) * 100) if prev['total_amount'] else 0

        month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December']

        if abs(change_pct) >= 5:
            direction = "up" if change_pct > 0 else "down"
            insights.append(
                f"{month_names[last['month']-1]} spending {direction} {abs(change_pct):.0f}% "
                f"vs {month_names[prev['month']-1]}"
            )

    # Check for consecutive increases/decreases
    if len(monthly_data) >= 3:
        consecutive_up = 0
        consecutive_down = 0
        for i in range(1, len(monthly_data)):
            if monthly_data[i]['total_amount'] > monthly_data[i-1]['total_amount']:
                consecutive_up += 1
                consecutive_down = 0
            elif monthly_data[i]['total_amount'] < monthly_data[i-1]['total_amount']:
                consecutive_down += 1
                consecutive_up = 0

        if consecutive_up >= 2:
            insights.append(f"Spending trending up for {consecutive_up + 1} consecutive months")
        elif consecutive_down >= 2:
            insights.append(f"Spending trending down for {consecutive_down + 1} consecutive months")

    # Category insights
    if category_data and 'categories' in category_data:
        categories = category_data['categories']
        for cat_name, cat_months in categories.items():
            if len(cat_months) >= 2:
                first_half = sum(m['amount'] for m in cat_months[:len(cat_months)//2])
                second_half = sum(m['amount'] for m in cat_months[len(cat_months)//2:])
                if first_half > 0:
                    change = ((second_half - first_half) / first_half) * 100
                    if change > 20:
                        insights.append(f"{fix_rtl(cat_name)} trending up significantly")
                    elif change < -20:
                        insights.append(f"{fix_rtl(cat_name)} spending decreased")

    return insights[:4]  # Limit to 4 insights


@app.command("stats")
def overall_stats():
    """
    Show overall statistics
    """
    try:
        analytics = AnalyticsService()
        stats = analytics.get_overall_stats()

        # Create info panel
        info_lines = [
            f"[bold cyan]Account Statistics:[/bold cyan]",
            f"[bold]Total Accounts:[/bold] {stats['total_accounts']}",
            "",
            f"[bold cyan]Transaction Statistics:[/bold cyan]",
            f"[bold]Total Transactions:[/bold] {stats['total_transactions']:,}",
            f"[bold]Pending Transactions:[/bold] {stats['pending_transactions']:,}",
            "",
            f"[bold cyan]Balance Information:[/bold cyan]",
            f"[bold]Total Balance:[/bold] {stats['total_balance']:,.2f} ILS",
        ]

        if stats['last_sync']:
            info_lines.extend([
                "",
                f"[bold cyan]Sync Information:[/bold cyan]",
                f"[bold]Last Successful Sync:[/bold] {stats['last_sync'].strftime('%Y-%m-%d %H:%M')}",
            ])
        else:
            info_lines.extend([
                "",
                f"[bold cyan]Sync Information:[/bold cyan]",
                f"[bold]Last Successful Sync:[/bold] [yellow]Never[/yellow]",
            ])

        info_text = "\n".join(info_lines)
        panel = Panel(info_text, title="Overall Statistics", border_style="cyan", box=box.ROUNDED)
        console.print(panel)

        analytics.close()

    except Exception as e:
        console.print(f"[red]Error generating statistics: {str(e)}[/red]")
        raise typer.Exit(code=1)


@app.command("monthly")
def monthly_report(
    year: int = typer.Option(None, "--year", "-y", help="Year (default: current year)"),
    month: int = typer.Option(None, "--month", "-m", help="Month 1-12 (default: current month)"),
    group_by: Optional[str] = typer.Option(None, "--group-by", "-g", help="Group by: tags, status, type, account")
):
    """
    Generate monthly spending report
    """
    try:
        analytics = AnalyticsService()

        # Use current date if not provided
        today = date.today()
        if year is None:
            year = today.year
        if month is None:
            month = today.month

        # Validate month
        if month < 1 or month > 12:
            console.print("[red]Month must be between 1 and 12[/red]")
            raise typer.Exit(code=1)

        # Create header
        month_name = date(year, month, 1).strftime("%B %Y")
        console.print(f"\n[bold cyan]Monthly Report - {month_name}[/bold cyan]\n")

        # If grouping by tags, show tag breakdown
        if group_by == "tags":
            breakdown = analytics.get_monthly_tag_breakdown(year, month)

            if not breakdown:
                console.print("[yellow]No transactions found for this month[/yellow]")
                analytics.close()
                return

            # Create table
            table = Table(title=f"Spending by Tag - {month_name}", show_header=True, header_style="bold cyan", box=box.ROUNDED)
            table.add_column("Tag", style="bold", width=25)
            table.add_column("Amount", justify="right", width=15)
            table.add_column("% of Total", justify="right", width=12)
            table.add_column("Count", justify="right", width=10)

            # Sort by amount descending
            items = sorted(breakdown.items(), key=lambda x: abs(x[1]['total_amount']), reverse=True)

            total_transactions = 0
            grand_total = 0

            # Separate untagged from tagged for display
            tagged_items = [(k, v) for k, v in items if k != '(untagged)']
            untagged_item = next(((k, v) for k, v in items if k == '(untagged)'), None)

            for tag_name, data in tagged_items:
                amount = data['total_amount']
                amount_str = f"₪{amount:,.2f}"
                if amount < 0:
                    amount_str = f"[red]{amount_str}[/red]"
                else:
                    amount_str = f"[green]{amount_str}[/green]"

                table.add_row(
                    f"[cyan]{fix_rtl(tag_name)}[/cyan]",
                    amount_str,
                    f"{data['percentage']:.1f}%",
                    str(data['count'])
                )
                total_transactions += data['count']
                grand_total += abs(amount)

            # Add separator and untagged row
            if untagged_item:
                table.add_section()
                tag_name, data = untagged_item
                amount = data['total_amount']
                amount_str = f"₪{amount:,.2f}"
                if amount < 0:
                    amount_str = f"[red]{amount_str}[/red]"

                table.add_row(
                    f"[dim]{fix_rtl(tag_name)}[/dim]",
                    f"[dim]{amount_str}[/dim]",
                    f"[dim]{data['percentage']:.1f}%[/dim]",
                    f"[dim]{data['count']}[/dim]"
                )
                total_transactions += data['count']
                grand_total += abs(amount)

            # Add total row
            table.add_section()
            table.add_row(
                "[bold]TOTAL[/bold]",
                f"[bold]₪{grand_total:,.2f}[/bold]",
                "[bold]100%[/bold]",
                f"[bold]{total_transactions}[/bold]"
            )

            console.print(table)
            analytics.close()
            return

        # Standard monthly report
        summary = analytics.get_monthly_summary(year, month)

        # Transaction count and amounts
        info_lines = [
            f"[bold]Total Transactions:[/bold] {summary['transaction_count']:,}",
            f"[bold]Total Amount:[/bold] {summary['total_amount']:,.2f} ILS",
        ]

        if summary['total_charged'] > 0:
            info_lines.append(f"[bold]Total Charged:[/bold] {summary['total_charged']:,.2f} ILS")

        info_text = "\n".join(info_lines)
        panel = Panel(info_text, title="Summary", border_style="cyan")
        console.print(panel)
        console.print()

        # By status table
        if summary['by_status'] and (group_by is None or group_by == "status"):
            status_table = Table(title="Transactions by Status", show_header=True, header_style="bold cyan", box=box.ROUNDED)
            status_table.add_column("Status", style="bold")
            status_table.add_column("Count", justify="right")

            for status, count in sorted(summary['by_status'].items()):
                status_color = "yellow" if status == "pending" else "green" if status == "completed" else "white"
                status_table.add_row(f"[{status_color}]{status}[/{status_color}]", str(count))

            console.print(status_table)
            console.print()

        # By type table
        if summary['by_type'] and (group_by is None or group_by == "type"):
            type_table = Table(title="Transactions by Type", show_header=True, header_style="bold cyan", box=box.ROUNDED)
            type_table.add_column("Type", style="bold")
            type_table.add_column("Count", justify="right")

            for txn_type, count in sorted(summary['by_type'].items()):
                type_table.add_row(txn_type, str(count))

            console.print(type_table)
            console.print()

        # By account table
        if summary['by_account'] and (group_by is None or group_by == "account"):
            account_table = Table(title="Transactions by Account", show_header=True, header_style="bold cyan", box=box.ROUNDED)
            account_table.add_column("Account", style="bold")
            account_table.add_column("Count", justify="right")

            for account, count in sorted(summary['by_account'].items(), key=lambda x: x[1], reverse=True):
                account_table.add_row(account, str(count))

            console.print(account_table)

        analytics.close()

    except Exception as e:
        console.print(f"[red]Error generating monthly report: {str(e)}[/red]")
        raise typer.Exit(code=1)


@app.command("spending")
def spending_report(
    tag: Optional[str] = typer.Argument(None, help="Tag name for detailed breakdown"),
    from_date: Optional[str] = typer.Option(None, "--from", help="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = typer.Option(None, "--to", help="End date (YYYY-MM-DD)"),
    month: Optional[int] = typer.Option(None, "--month", "-m", help="Month (1-12)"),
    year: Optional[int] = typer.Option(None, "--year", "-y", help="Year"),
    show_transactions: bool = typer.Option(False, "--transactions", "-t", help="Show transaction list (only with tag)")
):
    """
    Show spending breakdown by category, or detailed breakdown for a specific tag

    Examples:
        fin-cli reports spending                     # All spending by category
        fin-cli reports spending --month 12          # December spending by category
        fin-cli reports spending car                 # Spending tagged 'car' by category
        fin-cli reports spending car --month 12 -t   # With transaction list
    """
    try:
        analytics = AnalyticsService()

        # Handle month/year shortcuts
        from_date_obj = None
        to_date_obj = None

        if month or year:
            from calendar import monthrange
            today = date.today()
            y = year or today.year
            m = month or today.month

            if m < 1 or m > 12:
                console.print("[red]Month must be between 1 and 12[/red]")
                raise typer.Exit(code=1)

            from_date_obj = date(y, m, 1)
            to_date_obj = date(y, m, monthrange(y, m)[1])
        else:
            # Parse explicit dates
            if from_date:
                try:
                    from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
                except ValueError:
                    console.print("[red]Invalid from date format. Use YYYY-MM-DD[/red]")
                    raise typer.Exit(code=1)

            if to_date:
                try:
                    to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()
                except ValueError:
                    console.print("[red]Invalid to date format. Use YYYY-MM-DD[/red]")
                    raise typer.Exit(code=1)

        # Build date range string for display
        date_range_str = ""
        if from_date_obj and to_date_obj:
            if from_date_obj.month == to_date_obj.month and from_date_obj.year == to_date_obj.year:
                date_range_str = f" ({from_date_obj.strftime('%B %Y')})"
            else:
                date_range_str = f" ({from_date_obj} to {to_date_obj})"
        elif from_date_obj:
            date_range_str = f" (from {from_date_obj})"
        elif to_date_obj:
            date_range_str = f" (to {to_date_obj})"

        if tag:
            # Detailed breakdown for specific tag
            data = analytics.get_spending_for_tag(tag, from_date=from_date_obj, to_date=to_date_obj)

            if data['count'] == 0:
                console.print(f"[yellow]No transactions found for tag '{tag}'{date_range_str}[/yellow]")
                analytics.close()
                return

            # Header
            console.print(f"\n[bold cyan]Spending: {fix_rtl(tag)}[/bold cyan]{date_range_str}")
            console.print(f"[bold]Total:[/bold] ₪{data['total_amount']:,.2f}  ({data['count']} transactions)\n")

            # Category breakdown table
            table = Table(title="By Category", show_header=True, header_style="bold cyan", box=box.ROUNDED)
            table.add_column("Category", style="bold", width=25)
            table.add_column("Amount", justify="right", width=15)
            table.add_column("Count", justify="right", width=10)

            # Sort by amount (absolute value)
            sorted_categories = sorted(
                data['by_category'].items(),
                key=lambda x: abs(x[1]['total_amount']),
                reverse=True
            )

            for category, cat_data in sorted_categories:
                amount = cat_data['total_amount']
                amount_str = f"₪{amount:,.2f}"
                if amount < 0:
                    amount_str = f"[red]{amount_str}[/red]"
                else:
                    amount_str = f"[green]{amount_str}[/green]"

                table.add_row(
                    fix_rtl(category),
                    amount_str,
                    str(cat_data['count'])
                )

            console.print(table)

            # Transaction list (optional)
            if show_transactions and data['transactions']:
                console.print()
                txn_table = Table(title="Transactions", show_header=True, header_style="bold cyan", box=box.ROUNDED)
                txn_table.add_column("Date", width=12)
                txn_table.add_column("Description", width=35)
                txn_table.add_column("Amount", justify="right", width=15)
                txn_table.add_column("Category", width=20)

                for txn in data['transactions'][:50]:  # Limit to 50
                    amount = txn['amount']
                    amount_str = f"₪{amount:,.2f}"
                    if amount < 0:
                        amount_str = f"[red]{amount_str}[/red]"
                    else:
                        amount_str = f"[green]{amount_str}[/green]"

                    txn_table.add_row(
                        txn['date'].strftime("%Y-%m-%d"),
                        fix_rtl(txn['description'][:35]) if txn['description'] else "",
                        amount_str,
                        fix_rtl(txn['category'][:20])
                    )

                console.print(txn_table)

                if len(data['transactions']) > 50:
                    console.print(f"[dim]Showing 50 of {len(data['transactions'])} transactions[/dim]")

        else:
            # General category breakdown (no tag filter)
            categories = analytics.get_category_breakdown(from_date=from_date_obj, to_date=to_date_obj)

            if not categories:
                console.print(f"[yellow]No transactions found{date_range_str}[/yellow]")
                analytics.close()
                return

            # Create table
            table = Table(title=f"Spending by Category{date_range_str}", show_header=True, header_style="bold cyan", box=box.ROUNDED)
            table.add_column("Category", style="bold", width=25)
            table.add_column("Amount", justify="right", width=15)
            table.add_column("Count", justify="right", width=10)
            table.add_column("Average", justify="right", width=12)

            # Sort by total amount descending
            sorted_categories = sorted(categories.items(), key=lambda x: x[1]['total_amount'], reverse=True)

            total_transactions = 0
            grand_total = 0

            for category, data in sorted_categories:
                amount = data['total_amount']
                amount_str = f"₪{amount:,.2f}"
                if amount < 0:
                    amount_str = f"[red]{amount_str}[/red]"

                table.add_row(
                    fix_rtl(category) if category else "(uncategorized)",
                    amount_str,
                    str(data['count']),
                    f"₪{data['avg_amount']:,.2f}"
                )
                total_transactions += data['count']
                grand_total += amount

            # Add total row
            table.add_section()
            table.add_row(
                "[bold]TOTAL[/bold]",
                f"[bold]₪{grand_total:,.2f}[/bold]",
                f"[bold]{total_transactions}[/bold]",
                ""
            )

            console.print(table)

        analytics.close()

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error generating spending report: {str(e)}[/red]")
        raise typer.Exit(code=1)


@app.command("balances")
def balance_report(
    account_id: Optional[int] = typer.Option(None, "--account", "-a", help="Show history for specific account"),
    from_date: Optional[str] = typer.Option(None, "--from", help="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = typer.Option(None, "--to", help="End date (YYYY-MM-DD)")
):
    """
    Show account balance report
    """
    try:
        analytics = AnalyticsService()

        if account_id:
            # Show balance history for specific account
            account = analytics.get_account_by_id(account_id)
            if not account:
                console.print(f"[red]Account with ID {account_id} not found[/red]")
                raise typer.Exit(code=1)

            # Parse dates
            from_date_obj = None
            to_date_obj = None

            if from_date:
                try:
                    from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
                except ValueError:
                    console.print("[red]Invalid from date format. Use YYYY-MM-DD[/red]")
                    raise typer.Exit(code=1)

            if to_date:
                try:
                    to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()
                except ValueError:
                    console.print("[red]Invalid to date format. Use YYYY-MM-DD[/red]")
                    raise typer.Exit(code=1)

            balances = analytics.get_balance_history(account_id, from_date_obj, to_date_obj)

            if not balances:
                console.print("[yellow]No balance history found for this account[/yellow]")
                return

            # Create table
            table = Table(
                title=f"Balance History - {account.institution} ({account.account_number})",
                show_header=True,
                header_style="bold cyan",
                box=box.ROUNDED
            )
            table.add_column("Date", width=12)
            table.add_column("Total", justify="right", width=15)
            table.add_column("Available", justify="right", width=15)
            table.add_column("Used", justify="right", width=15)
            table.add_column("P/L", justify="right", width=15)
            table.add_column("P/L %", justify="right", width=10)

            for balance in balances:
                # Profit/loss color
                pl_color = "green" if (balance.profit_loss or 0) >= 0 else "red"
                pl_sign = "+" if (balance.profit_loss or 0) >= 0 else ""
                pl_str = f"[{pl_color}]{pl_sign}{balance.profit_loss:,.2f}[/{pl_color}]" if balance.profit_loss is not None else "-"

                pl_pct_sign = "+" if (balance.profit_loss_percentage or 0) >= 0 else ""
                pl_pct_str = f"[{pl_color}]{pl_pct_sign}{balance.profit_loss_percentage:.2f}%[/{pl_color}]" if balance.profit_loss_percentage is not None else "-"

                table.add_row(
                    balance.balance_date.strftime("%Y-%m-%d"),
                    f"{balance.total_amount:,.2f}",
                    f"{balance.available:,.2f}" if balance.available is not None else "-",
                    f"{balance.used:,.2f}" if balance.used is not None else "-",
                    pl_str,
                    pl_pct_str
                )

            console.print(table)

        else:
            # Show latest balances for all accounts
            latest_balances = analytics.get_latest_balances()

            if not latest_balances:
                console.print("[yellow]No balance data found[/yellow]")
                return

            # Create table
            table = Table(title="Latest Balances", show_header=True, header_style="bold cyan", box=box.ROUNDED)
            table.add_column("Account", width=25)
            table.add_column("Type", width=12)
            table.add_column("Date", width=12)
            table.add_column("Total", justify="right", width=15)
            table.add_column("P/L", justify="right", width=15)
            table.add_column("P/L %", justify="right", width=10)

            total_balance = 0

            for account, balance in latest_balances:
                # Profit/loss color
                pl_color = "green" if (balance.profit_loss or 0) >= 0 else "red"
                pl_sign = "+" if (balance.profit_loss or 0) >= 0 else ""
                pl_str = f"[{pl_color}]{pl_sign}{balance.profit_loss:,.2f}[/{pl_color}]" if balance.profit_loss is not None else "-"

                pl_pct_sign = "+" if (balance.profit_loss_percentage or 0) >= 0 else ""
                pl_pct_str = f"[{pl_color}]{pl_pct_sign}{balance.profit_loss_percentage:.2f}%[/{pl_color}]" if balance.profit_loss_percentage is not None else "-"

                account_name = f"{account.institution} ({account.account_number[:10]}...)" if len(account.account_number) > 10 else f"{account.institution} ({account.account_number})"

                table.add_row(
                    account_name,
                    account.account_type,
                    balance.balance_date.strftime("%Y-%m-%d"),
                    f"{balance.total_amount:,.2f}",
                    pl_str,
                    pl_pct_str
                )

                total_balance += balance.total_amount

            console.print(table)
            console.print(f"\n[bold]Total Balance:[/bold] {total_balance:,.2f} ILS")

        analytics.close()

    except Exception as e:
        console.print(f"[red]Error generating balance report: {str(e)}[/red]")
        raise typer.Exit(code=1)


@app.command("trends")
def spending_trends(
    months: int = typer.Option(6, "--months", "-m", help="Number of months to analyze (default: 6)"),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Filter by tag"),
    card: Optional[str] = typer.Option(None, "--card", "-c", help="Filter by card last 4 digits"),
    show_categories: bool = typer.Option(True, "--categories/--no-categories", help="Show category trends"),
    show_cards: bool = typer.Option(True, "--cards/--no-cards", help="Show card holder breakdown")
):
    """
    Show spending trends over time with visualizations

    Examples:
        fin-cli reports trends                    # Last 6 months overview
        fin-cli reports trends --months 12        # Last 12 months
        fin-cli reports trends --tag groceries    # Trends for specific tag
        fin-cli reports trends --card 1234        # Trends for specific card
    """
    try:
        analytics = AnalyticsService()

        # Get monthly spending data
        monthly_data = analytics.get_monthly_spending_trends(
            months=months,
            tag=tag,
            card_last4=card
        )

        if not monthly_data:
            filter_desc = ""
            if tag:
                filter_desc = f" for tag '{tag}'"
            if card:
                filter_desc += f" for card *{card}"
            console.print(f"[yellow]No transaction data found{filter_desc}[/yellow]")
            analytics.close()
            return

        # Build date range string
        first_month = monthly_data[0]
        last_month = monthly_data[-1]
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        date_range = f"{month_names[first_month['month']-1]} {first_month['year']} - {month_names[last_month['month']-1]} {last_month['year']}"

        # Header panel
        title_parts = ["SPENDING TRENDS REPORT"]
        if tag:
            title_parts.append(f"Tag: {fix_rtl(tag)}")
        if card:
            title_parts.append(f"Card: *{card}")

        header_text = f"[bold cyan]{' | '.join(title_parts)}[/bold cyan]\n[dim]{date_range}[/dim]"
        console.print(Panel(header_text, box=box.DOUBLE))
        console.print()

        # ==================== Monthly Overview Table ====================
        max_amount = max(abs(m['total_amount']) for m in monthly_data) if monthly_data else 1

        monthly_table = Table(
            title="Monthly Spending Overview",
            show_header=True,
            header_style="bold cyan",
            box=box.ROUNDED
        )
        monthly_table.add_column("Month", width=10)
        monthly_table.add_column("Total", justify="right", width=12)
        monthly_table.add_column("vs Prev", justify="right", width=10)
        monthly_table.add_column("Trend", width=35)
        monthly_table.add_column("Count", justify="right", width=8)

        # Calculate average
        total_spending = sum(abs(m['total_amount']) for m in monthly_data)
        avg_spending = total_spending / len(monthly_data) if monthly_data else 0

        # Display months (newest first for readability)
        for i, m in enumerate(reversed(monthly_data)):
            month_str = f"{month_names[m['month']-1]} {m['year']}"
            amount = abs(m['total_amount'])
            amount_str = f"₪{amount:,.0f}"

            # Calculate change vs previous month
            original_idx = len(monthly_data) - 1 - i
            if original_idx > 0:
                prev_amount = abs(monthly_data[original_idx - 1]['total_amount'])
                change_str = format_change(amount, prev_amount)
            else:
                change_str = "[dim]baseline[/dim]"

            # Create bar
            bar = make_bar(amount, max_amount, width=30)

            monthly_table.add_row(
                month_str,
                amount_str,
                change_str,
                bar,
                str(m['transaction_count'])
            )

        # Add average row
        monthly_table.add_section()
        monthly_table.add_row(
            "[bold]Average[/bold]",
            f"[bold]₪{avg_spending:,.0f}[/bold]",
            "",
            f"[dim]{months}-month avg[/dim]",
            ""
        )

        console.print(monthly_table)
        console.print()

        # ==================== Category Trends ====================
        if show_categories and not tag:  # Don't show categories if filtering by tag
            category_data = analytics.get_category_trends(months=months, top_n=5)

            if category_data and category_data.get('categories'):
                cat_table = Table(
                    title="Category Trends (Top 5)",
                    show_header=True,
                    header_style="bold cyan",
                    box=box.ROUNDED
                )
                cat_table.add_column("Category", width=20)
                cat_table.add_column("Total", justify="right", width=12)
                cat_table.add_column("Trend", width=8)
                cat_table.add_column("Sparkline", width=12)

                # Sort by total
                sorted_cats = sorted(
                    category_data['totals'].items(),
                    key=lambda x: x[1],
                    reverse=True
                )

                for cat_name, total in sorted_cats:
                    cat_months = category_data['categories'].get(cat_name, [])
                    amounts = [m['amount'] for m in cat_months]

                    # Calculate trend
                    if len(amounts) >= 2:
                        first_half = sum(amounts[:len(amounts)//2]) or 1
                        second_half = sum(amounts[len(amounts)//2:])
                        trend_pct = ((second_half - first_half) / first_half) * 100

                        if abs(trend_pct) < 5:
                            trend_str = "[dim]→ stable[/dim]"
                        elif trend_pct > 0:
                            trend_str = f"[red]↗ +{trend_pct:.0f}%[/red]"
                        else:
                            trend_str = f"[green]↘ {trend_pct:.0f}%[/green]"
                    else:
                        trend_str = "[dim]—[/dim]"

                    # Sparkline
                    sparkline = make_sparkline(amounts, width=months)

                    cat_table.add_row(
                        fix_rtl(cat_name)[:20],
                        f"₪{total:,.0f}",
                        trend_str,
                        f"[cyan]{sparkline}[/cyan]"
                    )

                console.print(cat_table)
                console.print()
        else:
            category_data = None

        # ==================== Card Holder Breakdown ====================
        if show_cards and not card:  # Don't show if already filtering by card
            card_data = analytics.get_spending_by_card_holder(months=months)

            if card_data:
                card_table = Table(
                    title="By Card Holder (Last 4 Digits)",
                    show_header=True,
                    header_style="bold cyan",
                    box=box.ROUNDED
                )
                card_table.add_column("Card", width=10)
                card_table.add_column("Total", justify="right", width=12)
                card_table.add_column("% Share", justify="right", width=10)
                card_table.add_column("Transactions", justify="right", width=12)

                # Sort by amount
                sorted_cards = sorted(
                    card_data.items(),
                    key=lambda x: x[1]['total_amount'],
                    reverse=True
                )

                for last4, data in sorted_cards:
                    card_table.add_row(
                        f"*{last4}",
                        f"₪{data['total_amount']:,.0f}",
                        f"{data['percentage']:.0f}%",
                        str(data['transaction_count'])
                    )

                console.print(card_table)
                console.print()

        # ==================== Insights ====================
        insights = generate_insights(monthly_data, category_data)

        if insights:
            insight_lines = [f"  • {insight}" for insight in insights]
            insight_text = "\n".join(insight_lines)
            console.print(Panel(
                insight_text,
                title="[bold]Insights[/bold]",
                border_style="dim",
                box=box.ROUNDED
            ))

        analytics.close()

    except Exception as e:
        console.print(f"[red]Error generating trends report: {str(e)}[/red]")
        raise typer.Exit(code=1)


@app.command("history")
def sync_history(
    limit: int = typer.Option(10, "--limit", "-l", help="Number of records to show"),
    institution: Optional[str] = typer.Option(None, "--institution", "-i", help="Filter by institution"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (success, failed, partial)")
):
    """
    Show synchronization history
    """
    try:
        analytics = AnalyticsService()

        history = analytics.get_sync_history(limit=limit, institution=institution, status=status)

        if not history:
            console.print("[yellow]No sync history found[/yellow]")
            return

        # Create table
        table = Table(title="Synchronization History", show_header=True, header_style="bold cyan", box=box.ROUNDED)
        table.add_column("ID", style="dim", width=6)
        table.add_column("Type", width=15)
        table.add_column("Institution", width=15)
        table.add_column("Status", width=10)
        table.add_column("Started", width=18)
        table.add_column("Duration", width=12)
        table.add_column("Added", justify="right", width=8)
        table.add_column("Updated", justify="right", width=8)

        for sync in history:
            # Status color
            status_color = "green" if sync.status == "success" else "red" if sync.status == "failed" else "yellow"
            status_str = f"[{status_color}]{sync.status}[/{status_color}]"

            # Calculate duration
            duration = "-"
            if sync.completed_at and sync.started_at:
                duration_seconds = (sync.completed_at - sync.started_at).total_seconds()
                if duration_seconds < 60:
                    duration = f"{duration_seconds:.0f}s"
                else:
                    duration = f"{duration_seconds / 60:.1f}m"

            table.add_row(
                str(sync.id),
                sync.sync_type,
                sync.institution or "-",
                status_str,
                sync.started_at.strftime("%Y-%m-%d %H:%M"),
                duration,
                str(sync.records_added),
                str(sync.records_updated)
            )

        console.print(table)

        analytics.close()

    except Exception as e:
        console.print(f"[red]Error showing sync history: {str(e)}[/red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()