"""
Transaction management CLI commands
"""

import typer
from datetime import date, datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from typing import Optional

from cli.utils import fix_rtl
from services.analytics_service import AnalyticsService

app = typer.Typer(help="Manage transactions")
console = Console()


@app.command("list")
def list_transactions(
    account_id: Optional[int] = typer.Option(None, "--account", "-a", help="Filter by account ID"),
    from_date: Optional[str] = typer.Option(None, "--from", help="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = typer.Option(None, "--to", help="End date (YYYY-MM-DD)"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (pending, completed)"),
    institution: Optional[str] = typer.Option(None, "--institution", "-i", help="Filter by institution"),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum number of transactions to show"),
    offset: int = typer.Option(0, "--offset", help="Number of transactions to skip")
):
    """
    List transactions with filters
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

        # Get transactions
        transactions = analytics.get_transactions(
            account_id=account_id,
            from_date=from_date_obj,
            to_date=to_date_obj,
            status=status,
            institution=institution,
            limit=limit,
            offset=offset
        )

        if not transactions:
            console.print("[yellow]No transactions found matching the criteria[/yellow]")
            return

        # Create table
        table = Table(title="Transactions", show_header=True, header_style="bold cyan")
        table.add_column("ID", style="dim", width=6)
        table.add_column("Date", width=12)
        table.add_column("Description", width=35)
        table.add_column("Amount", justify="right", width=15)
        table.add_column("Status", width=10)
        table.add_column("Account", width=15)

        for txn in transactions:
            # Format amount with color
            amount_str = f"{txn.original_amount:,.2f} {txn.original_currency}"
            if txn.original_amount < 0:
                amount_str = f"[red]{amount_str}[/red]"
            else:
                amount_str = f"[green]{amount_str}[/green]"

            # Status color
            status_str = txn.status or "unknown"
            if txn.status == "pending":
                status_str = f"[yellow]{status_str}[/yellow]"
            elif txn.status == "completed":
                status_str = f"[green]{status_str}[/green]"

            # Get account info
            account = analytics.get_account_by_id(txn.account_id)
            account_str = f"{account.institution}" if account else "Unknown"

            table.add_row(
                str(txn.id),
                txn.transaction_date.strftime("%Y-%m-%d"),
                fix_rtl(txn.description[:35]),
                amount_str,
                status_str,
                account_str
            )

        console.print(table)

        # Show summary
        total_count = analytics.get_transaction_count(
            account_id=account_id,
            from_date=from_date_obj,
            to_date=to_date_obj,
            status=status
        )

        console.print(f"\n[bold]Showing:[/bold] {len(transactions)} of {total_count} transaction(s)")

        if offset + limit < total_count:
            console.print(f"[dim]Use --offset {offset + limit} to see more transactions[/dim]")

        analytics.close()

    except Exception as e:
        console.print(f"[red]Error listing transactions: {str(e)}[/red]")
        raise typer.Exit(code=1)


@app.command("show")
def show_transaction(
    transaction_id: int = typer.Argument(..., help="Transaction ID")
):
    """
    Show detailed information for a specific transaction
    """
    try:
        analytics = AnalyticsService()

        transaction = analytics.get_transaction_by_id(transaction_id)

        if not transaction:
            console.print(f"[red]Transaction with ID {transaction_id} not found[/red]")
            analytics.close()
            raise typer.Exit(code=1)

        # Get account info
        account = analytics.get_account_by_id(transaction.account_id)

        # Create info panel
        info_lines = [
            f"[bold]Transaction ID:[/bold] {transaction.id}",
            f"[bold]External ID:[/bold] {transaction.transaction_id or 'N/A'}",
            "",
            f"[bold cyan]Account Information:[/bold cyan]",
            f"[bold]Account ID:[/bold] {transaction.account_id}",
        ]

        if account:
            info_lines.extend([
                f"[bold]Institution:[/bold] {account.institution}",
                f"[bold]Account Type:[/bold] {account.account_type}",
                f"[bold]Account Number:[/bold] {account.account_number}",
            ])

        info_lines.extend([
            "",
            f"[bold cyan]Transaction Details:[/bold cyan]",
            f"[bold]Date:[/bold] {transaction.transaction_date}",
        ])

        if transaction.processed_date:
            info_lines.append(f"[bold]Processed Date:[/bold] {transaction.processed_date}")

        info_lines.append(f"[bold]Description:[/bold] {fix_rtl(transaction.description)}")

        # Amount information
        amount_color = "green" if transaction.original_amount >= 0 else "red"
        info_lines.append(
            f"[bold]Original Amount:[/bold] [{amount_color}]{transaction.original_amount:,.2f} {transaction.original_currency}[/{amount_color}]"
        )

        if transaction.charged_amount is not None:
            charged_color = "green" if transaction.charged_amount >= 0 else "red"
            info_lines.append(
                f"[bold]Charged Amount:[/bold] [{charged_color}]{transaction.charged_amount:,.2f} {transaction.charged_currency}[/{charged_color}]"
            )

        # Status and type
        status_color = "yellow" if transaction.status == "pending" else "green"
        info_lines.extend([
            f"[bold]Status:[/bold] [{status_color}]{transaction.status or 'unknown'}[/{status_color}]",
            f"[bold]Type:[/bold] {transaction.transaction_type or 'N/A'}",
        ])

        # Category and memo
        if transaction.category:
            info_lines.append(f"[bold]Category:[/bold] {fix_rtl(transaction.category)}")

        if transaction.memo:
            info_lines.append(f"[bold]Memo:[/bold] {fix_rtl(transaction.memo)}")

        # Installment information
        if transaction.installment_number is not None and transaction.installment_total is not None:
            info_lines.extend([
                "",
                f"[bold cyan]Installment:[/bold cyan]",
                f"[bold]Payment:[/bold] {transaction.installment_number} of {transaction.installment_total}",
            ])

        info_lines.append(f"\n[bold]Created At:[/bold] {transaction.created_at.strftime('%Y-%m-%d %H:%M')}")

        info_text = "\n".join(info_lines)
        panel = Panel(info_text, title="Transaction Details", border_style="cyan")
        console.print(panel)

        analytics.close()

    except Exception as e:
        console.print(f"[red]Error showing transaction: {str(e)}[/red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()