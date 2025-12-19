"""
Account management CLI commands
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from typing import Optional

from services.analytics_service import AnalyticsService

app = typer.Typer(help="Manage accounts")
console = Console()


@app.command("list")
def list_accounts(
    type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by account type (broker, pension, credit_card)"),
    institution: Optional[str] = typer.Option(None, "--institution", "-i", help="Filter by institution (excellence, migdal, phoenix, cal)"),
    include_inactive: bool = typer.Option(False, "--include-inactive", help="Include inactive accounts")
):
    """
    List all accounts
    """
    try:
        analytics = AnalyticsService()

        # Get accounts based on filters
        if type:
            accounts = analytics.get_accounts_by_type(type, active_only=not include_inactive)
        elif institution:
            accounts = analytics.get_accounts_by_institution(institution, active_only=not include_inactive)
        else:
            accounts = analytics.get_all_accounts(active_only=not include_inactive)

        if not accounts:
            console.print("[yellow]No accounts found matching the criteria[/yellow]")
            return

        # Create table
        table = Table(title="Accounts", show_header=True, header_style="bold cyan")
        table.add_column("ID", style="dim", width=6)
        table.add_column("Type", width=12)
        table.add_column("Institution", width=15)
        table.add_column("Account Number", width=20)
        table.add_column("Name", width=25)
        table.add_column("Last Synced", width=20)
        table.add_column("Active", width=8)

        for account in accounts:
            last_synced = account.last_synced_at.strftime("%Y-%m-%d %H:%M") if account.last_synced_at else "Never"
            active_status = "[green]Yes[/green]" if account.is_active else "[red]No[/red]"

            table.add_row(
                str(account.id),
                account.account_type,
                account.institution,
                account.account_number,
                account.account_name or "-",
                last_synced,
                active_status
            )

        console.print(table)
        console.print(f"\n[bold]Total:[/bold] {len(accounts)} account(s)")

        analytics.close()

    except Exception as e:
        console.print(f"[red]Error listing accounts: {str(e)}[/red]")
        raise typer.Exit(code=1)


@app.command("show")
def show_account(
    account_id: int = typer.Argument(..., help="Account ID")
):
    """
    Show detailed information for a specific account
    """
    try:
        analytics = AnalyticsService()

        account = analytics.get_account_by_id(account_id)

        if not account:
            console.print(f"[red]Account with ID {account_id} not found[/red]")
            analytics.close()
            raise typer.Exit(code=1)

        # Get latest balance if available
        latest_balance = None
        if account.balances:
            latest_balance = max(account.balances, key=lambda b: b.balance_date)

        # Get transaction count
        transaction_count = analytics.get_transaction_count(account_id=account_id)

        # Create info panel
        info_lines = [
            f"[bold]ID:[/bold] {account.id}",
            f"[bold]Type:[/bold] {account.account_type}",
            f"[bold]Institution:[/bold] {account.institution}",
            f"[bold]Account Number:[/bold] {account.account_number}",
            f"[bold]Account Name:[/bold] {account.account_name or 'N/A'}",
        ]

        if account.card_unique_id:
            info_lines.append(f"[bold]Card ID:[/bold] {account.card_unique_id}")

        info_lines.extend([
            f"[bold]Active:[/bold] {'Yes' if account.is_active else 'No'}",
            f"[bold]Created At:[/bold] {account.created_at.strftime('%Y-%m-%d %H:%M')}",
            f"[bold]Last Synced:[/bold] {account.last_synced_at.strftime('%Y-%m-%d %H:%M') if account.last_synced_at else 'Never'}",
            "",
            f"[bold cyan]Statistics:[/bold cyan]",
            f"[bold]Total Transactions:[/bold] {transaction_count}",
        ])

        if latest_balance:
            info_lines.extend([
                "",
                f"[bold cyan]Latest Balance ({latest_balance.balance_date}):[/bold cyan]",
                f"[bold]Total:[/bold] {latest_balance.total_amount:,.2f} {latest_balance.currency}",
            ])

            if latest_balance.available is not None:
                info_lines.append(f"[bold]Available:[/bold] {latest_balance.available:,.2f} {latest_balance.currency}")

            if latest_balance.used is not None:
                info_lines.append(f"[bold]Used:[/bold] {latest_balance.used:,.2f} {latest_balance.currency}")

            if latest_balance.profit_loss is not None:
                profit_color = "green" if latest_balance.profit_loss >= 0 else "red"
                profit_sign = "+" if latest_balance.profit_loss >= 0 else ""
                info_lines.append(
                    f"[bold]Profit/Loss:[/bold] [{profit_color}]{profit_sign}{latest_balance.profit_loss:,.2f} {latest_balance.currency}[/{profit_color}]"
                )

            if latest_balance.profit_loss_percentage is not None:
                profit_color = "green" if latest_balance.profit_loss_percentage >= 0 else "red"
                profit_sign = "+" if latest_balance.profit_loss_percentage >= 0 else ""
                info_lines.append(
                    f"[bold]Profit/Loss %:[/bold] [{profit_color}]{profit_sign}{latest_balance.profit_loss_percentage:.2f}%[/{profit_color}]"
                )

        info_text = "\n".join(info_lines)
        panel = Panel(info_text, title=f"Account Details", border_style="cyan")
        console.print(panel)

        analytics.close()

    except Exception as e:
        console.print(f"[red]Error showing account: {str(e)}[/red]")
        raise typer.Exit(code=1)


@app.command("summary")
def account_summary():
    """
    Show summary of all accounts
    """
    try:
        analytics = AnalyticsService()
        summary = analytics.get_account_summary()

        # Create table for accounts by type
        type_table = Table(title="Accounts by Type", show_header=True, header_style="bold cyan")
        type_table.add_column("Type", style="bold")
        type_table.add_column("Count", justify="right")

        for account_type, count in summary["by_type"].items():
            type_table.add_row(account_type, str(count))

        console.print(type_table)
        console.print()

        # Create table for accounts by institution
        inst_table = Table(title="Accounts by Institution", show_header=True, header_style="bold cyan")
        inst_table.add_column("Institution", style="bold")
        inst_table.add_column("Count", justify="right")

        for institution, count in summary["by_institution"].items():
            inst_table.add_row(institution, str(count))

        console.print(inst_table)
        console.print(f"\n[bold]Total Accounts:[/bold] {summary['total_accounts']}")

        analytics.close()

    except Exception as e:
        console.print(f"[red]Error generating summary: {str(e)}[/red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()