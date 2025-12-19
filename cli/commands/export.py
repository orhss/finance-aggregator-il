"""
Export CLI commands for financial data
"""

import typer
import csv
import json
from pathlib import Path
from datetime import date, datetime
from typing import Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from services.analytics_service import AnalyticsService
from db.models import Transaction, Balance, Account

app = typer.Typer(help="Export financial data to CSV or JSON")
console = Console()


def serialize_date(obj):
    """
    JSON serializer for datetime objects
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


@app.command("transactions")
def export_transactions(
    output: str = typer.Option(..., "--output", "-o", help="Output file path"),
    format: str = typer.Option("csv", "--format", "-f", help="Export format (csv, json)"),
    account_id: Optional[int] = typer.Option(None, "--account", "-a", help="Filter by account ID"),
    institution: Optional[str] = typer.Option(None, "--institution", "-i", help="Filter by institution"),
    from_date: Optional[str] = typer.Option(None, "--from", help="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = typer.Option(None, "--to", help="End date (YYYY-MM-DD)"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (pending, completed)"),
):
    """
    Export transactions to CSV or JSON
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

        # Validate format
        if format.lower() not in ["csv", "json"]:
            console.print("[red]Invalid format. Use 'csv' or 'json'[/red]")
            raise typer.Exit(code=1)

        # Fetch transactions
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task(description="Fetching transactions...", total=None)

            transactions = analytics.get_transactions(
                account_id=account_id,
                institution=institution,
                from_date=from_date_obj,
                to_date=to_date_obj,
                status=status,
                limit=None  # Get all transactions
            )

        if not transactions:
            console.print("[yellow]No transactions found with the given filters[/yellow]")
            analytics.close()
            return

        # Export based on format
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format.lower() == "csv":
            export_transactions_csv(transactions, output_path)
        else:
            export_transactions_json(transactions, output_path)

        console.print(f"[green]Successfully exported {len(transactions)} transactions to {output}[/green]")
        analytics.close()

    except Exception as e:
        console.print(f"[red]Error exporting transactions: {str(e)}[/red]")
        raise typer.Exit(code=1)


def export_transactions_csv(transactions: list, output_path: Path):
    """
    Export transactions to CSV format
    """
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'id', 'account_id', 'institution', 'account_number',
            'transaction_id', 'transaction_date', 'processed_date',
            'description', 'original_amount', 'original_currency',
            'charged_amount', 'charged_currency', 'transaction_type',
            'status', 'category', 'memo', 'installment_number',
            'installment_total', 'created_at'
        ]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for txn in transactions:
            writer.writerow({
                'id': txn.id,
                'account_id': txn.account_id,
                'institution': txn.account.institution if txn.account else '',
                'account_number': txn.account.account_number if txn.account else '',
                'transaction_id': txn.transaction_id or '',
                'transaction_date': txn.transaction_date.isoformat() if txn.transaction_date else '',
                'processed_date': txn.processed_date.isoformat() if txn.processed_date else '',
                'description': txn.description or '',
                'original_amount': txn.original_amount,
                'original_currency': txn.original_currency or '',
                'charged_amount': txn.charged_amount or '',
                'charged_currency': txn.charged_currency or '',
                'transaction_type': txn.transaction_type or '',
                'status': txn.status or '',
                'category': txn.category or '',
                'memo': txn.memo or '',
                'installment_number': txn.installment_number or '',
                'installment_total': txn.installment_total or '',
                'created_at': txn.created_at.isoformat() if txn.created_at else '',
            })


def export_transactions_json(transactions: list, output_path: Path):
    """
    Export transactions to JSON format
    """
    data = []
    for txn in transactions:
        data.append({
            'id': txn.id,
            'account_id': txn.account_id,
            'institution': txn.account.institution if txn.account else None,
            'account_number': txn.account.account_number if txn.account else None,
            'transaction_id': txn.transaction_id,
            'transaction_date': txn.transaction_date,
            'processed_date': txn.processed_date,
            'description': txn.description,
            'original_amount': txn.original_amount,
            'original_currency': txn.original_currency,
            'charged_amount': txn.charged_amount,
            'charged_currency': txn.charged_currency,
            'transaction_type': txn.transaction_type,
            'status': txn.status,
            'category': txn.category,
            'memo': txn.memo,
            'installment_number': txn.installment_number,
            'installment_total': txn.installment_total,
            'created_at': txn.created_at,
        })

    with open(output_path, 'w', encoding='utf-8') as jsonfile:
        json.dump(data, jsonfile, indent=2, default=serialize_date, ensure_ascii=False)


@app.command("balances")
def export_balances(
    output: str = typer.Option(..., "--output", "-o", help="Output file path"),
    format: str = typer.Option("csv", "--format", "-f", help="Export format (csv, json)"),
    account_id: Optional[int] = typer.Option(None, "--account", "-a", help="Filter by account ID"),
    from_date: Optional[str] = typer.Option(None, "--from", help="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = typer.Option(None, "--to", help="End date (YYYY-MM-DD)"),
):
    """
    Export account balances to CSV or JSON
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

        # Validate format
        if format.lower() not in ["csv", "json"]:
            console.print("[red]Invalid format. Use 'csv' or 'json'[/red]")
            raise typer.Exit(code=1)

        # Fetch balances
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task(description="Fetching balances...", total=None)

            if account_id:
                balances = analytics.get_balance_history(account_id, from_date_obj, to_date_obj)
            else:
                # Get all balances
                balances = analytics.get_all_balances(from_date_obj, to_date_obj)

        if not balances:
            console.print("[yellow]No balances found with the given filters[/yellow]")
            analytics.close()
            return

        # Export based on format
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format.lower() == "csv":
            export_balances_csv(balances, output_path)
        else:
            export_balances_json(balances, output_path)

        console.print(f"[green]Successfully exported {len(balances)} balance records to {output}[/green]")
        analytics.close()

    except Exception as e:
        console.print(f"[red]Error exporting balances: {str(e)}[/red]")
        raise typer.Exit(code=1)


def export_balances_csv(balances: list, output_path: Path):
    """
    Export balances to CSV format
    """
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'id', 'account_id', 'institution', 'account_number',
            'balance_date', 'total_amount', 'available', 'used',
            'blocked', 'profit_loss', 'profit_loss_percentage',
            'currency', 'created_at'
        ]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for balance in balances:
            writer.writerow({
                'id': balance.id,
                'account_id': balance.account_id,
                'institution': balance.account.institution if balance.account else '',
                'account_number': balance.account.account_number if balance.account else '',
                'balance_date': balance.balance_date.isoformat() if balance.balance_date else '',
                'total_amount': balance.total_amount,
                'available': balance.available or '',
                'used': balance.used or '',
                'blocked': balance.blocked or '',
                'profit_loss': balance.profit_loss or '',
                'profit_loss_percentage': balance.profit_loss_percentage or '',
                'currency': balance.currency or 'ILS',
                'created_at': balance.created_at.isoformat() if balance.created_at else '',
            })


def export_balances_json(balances: list, output_path: Path):
    """
    Export balances to JSON format
    """
    data = []
    for balance in balances:
        data.append({
            'id': balance.id,
            'account_id': balance.account_id,
            'institution': balance.account.institution if balance.account else None,
            'account_number': balance.account.account_number if balance.account else None,
            'balance_date': balance.balance_date,
            'total_amount': balance.total_amount,
            'available': balance.available,
            'used': balance.used,
            'blocked': balance.blocked,
            'profit_loss': balance.profit_loss,
            'profit_loss_percentage': balance.profit_loss_percentage,
            'currency': balance.currency,
            'created_at': balance.created_at,
        })

    with open(output_path, 'w', encoding='utf-8') as jsonfile:
        json.dump(data, jsonfile, indent=2, default=serialize_date, ensure_ascii=False)


@app.command("accounts")
def export_accounts(
    output: str = typer.Option(..., "--output", "-o", help="Output file path"),
    format: str = typer.Option("csv", "--format", "-f", help="Export format (csv, json)"),
    account_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by type (broker, pension, credit_card)"),
    institution: Optional[str] = typer.Option(None, "--institution", "-i", help="Filter by institution"),
):
    """
    Export accounts to CSV or JSON
    """
    try:
        analytics = AnalyticsService()

        # Validate format
        if format.lower() not in ["csv", "json"]:
            console.print("[red]Invalid format. Use 'csv' or 'json'[/red]")
            raise typer.Exit(code=1)

        # Fetch accounts
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task(description="Fetching accounts...", total=None)

            if account_type:
                accounts = analytics.get_accounts_by_type(account_type)
            elif institution:
                accounts = analytics.get_accounts_by_institution(institution)
            else:
                accounts = analytics.get_all_accounts()

        if not accounts:
            console.print("[yellow]No accounts found with the given filters[/yellow]")
            analytics.close()
            return

        # Export based on format
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format.lower() == "csv":
            export_accounts_csv(accounts, output_path)
        else:
            export_accounts_json(accounts, output_path)

        console.print(f"[green]Successfully exported {len(accounts)} accounts to {output}[/green]")
        analytics.close()

    except Exception as e:
        console.print(f"[red]Error exporting accounts: {str(e)}[/red]")
        raise typer.Exit(code=1)


def export_accounts_csv(accounts: list, output_path: Path):
    """
    Export accounts to CSV format
    """
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'id', 'account_type', 'institution', 'account_number',
            'account_name', 'card_unique_id', 'is_active',
            'created_at', 'last_synced_at'
        ]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for account in accounts:
            writer.writerow({
                'id': account.id,
                'account_type': account.account_type,
                'institution': account.institution,
                'account_number': account.account_number,
                'account_name': account.account_name or '',
                'card_unique_id': account.card_unique_id or '',
                'is_active': account.is_active,
                'created_at': account.created_at.isoformat() if account.created_at else '',
                'last_synced_at': account.last_synced_at.isoformat() if account.last_synced_at else '',
            })


def export_accounts_json(accounts: list, output_path: Path):
    """
    Export accounts to JSON format
    """
    data = []
    for account in accounts:
        data.append({
            'id': account.id,
            'account_type': account.account_type,
            'institution': account.institution,
            'account_number': account.account_number,
            'account_name': account.account_name,
            'card_unique_id': account.card_unique_id,
            'is_active': account.is_active,
            'created_at': account.created_at,
            'last_synced_at': account.last_synced_at,
        })

    with open(output_path, 'w', encoding='utf-8') as jsonfile:
        json.dump(data, jsonfile, indent=2, default=serialize_date, ensure_ascii=False)


if __name__ == "__main__":
    app()