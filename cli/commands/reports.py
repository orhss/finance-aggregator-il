"""
Reporting and analytics CLI commands
"""

import typer
from datetime import date, datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from typing import Optional

from cli.utils import fix_rtl
from services.analytics_service import AnalyticsService

app = typer.Typer(help="Generate reports and analytics")
console = Console()


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
    month: int = typer.Option(None, "--month", "-m", help="Month 1-12 (default: current month)")
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

        summary = analytics.get_monthly_summary(year, month)

        # Create header
        month_name = date(year, month, 1).strftime("%B %Y")
        console.print(f"\n[bold cyan]Monthly Report - {month_name}[/bold cyan]\n")

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
        if summary['by_status']:
            status_table = Table(title="Transactions by Status", show_header=True, header_style="bold cyan", box=box.ROUNDED)
            status_table.add_column("Status", style="bold")
            status_table.add_column("Count", justify="right")

            for status, count in sorted(summary['by_status'].items()):
                status_color = "yellow" if status == "pending" else "green" if status == "completed" else "white"
                status_table.add_row(f"[{status_color}]{status}[/{status_color}]", str(count))

            console.print(status_table)
            console.print()

        # By type table
        if summary['by_type']:
            type_table = Table(title="Transactions by Type", show_header=True, header_style="bold cyan", box=box.ROUNDED)
            type_table.add_column("Type", style="bold")
            type_table.add_column("Count", justify="right")

            for txn_type, count in sorted(summary['by_type'].items()):
                type_table.add_row(txn_type, str(count))

            console.print(type_table)
            console.print()

        # By account table
        if summary['by_account']:
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


@app.command("categories")
def category_breakdown(
    from_date: Optional[str] = typer.Option(None, "--from", help="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = typer.Option(None, "--to", help="End date (YYYY-MM-DD)")
):
    """
    Show transaction breakdown by category
    """
    try:
        analytics = AnalyticsService()

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

        categories = analytics.get_category_breakdown(from_date=from_date_obj, to_date=to_date_obj)

        if not categories:
            console.print("[yellow]No transactions found for category breakdown[/yellow]")
            return

        # Create table
        table = Table(title="Category Breakdown", show_header=True, header_style="bold cyan", box=box.ROUNDED)
        table.add_column("Category", style="bold")
        table.add_column("Count", justify="right")
        table.add_column("Total Amount", justify="right")
        table.add_column("Average", justify="right")

        # Sort by total amount descending
        sorted_categories = sorted(categories.items(), key=lambda x: x[1]['total_amount'], reverse=True)

        total_transactions = 0
        grand_total = 0

        for category, data in sorted_categories:
            table.add_row(
                fix_rtl(category) if category else "Uncategorized",
                str(data['count']),
                f"{data['total_amount']:,.2f} ILS",
                f"{data['avg_amount']:,.2f} ILS"
            )
            total_transactions += data['count']
            grand_total += data['total_amount']

        console.print(table)
        console.print(f"\n[bold]Total Transactions:[/bold] {total_transactions:,}")
        console.print(f"[bold]Grand Total:[/bold] {grand_total:,.2f} ILS")

        analytics.close()

    except Exception as e:
        console.print(f"[red]Error generating category breakdown: {str(e)}[/red]")
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