"""
Transaction management CLI commands
"""

import typer
from datetime import date, datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from typing import Optional, List

from cli.utils import fix_rtl
from services.analytics_service import AnalyticsService
from services.tag_service import TagService

app = typer.Typer(help="Manage transactions")
console = Console()


@app.command("browse")
def browse_transactions(
    from_date: Optional[str] = typer.Option(None, "--from", help="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = typer.Option(None, "--to", help="End date (YYYY-MM-DD)"),
    tag: Optional[List[str]] = typer.Option(None, "--tag", "-t", help="Filter by tag"),
    untagged: bool = typer.Option(False, "--untagged", help="Show only untagged transactions"),
    institution: Optional[str] = typer.Option(None, "--institution", "-i", help="Filter by institution")
):
    """
    Interactive transaction browser (TUI)

    Navigate with arrow keys, press Enter or 'e' to edit, 't' to tag, '/' to search.
    """
    try:
        from cli.tui.browser import run_browser

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

        run_browser(
            from_date=from_date_obj,
            to_date=to_date_obj,
            tags=list(tag) if tag else None,
            untagged_only=untagged,
            institution=institution,
        )

    except ImportError as e:
        console.print("[red]TUI requires 'textual' package. Install with: pip install textual[/red]")
        console.print(f"[dim]Error: {e}[/dim]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error launching browser: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("list")
def list_transactions(
    account_id: Optional[int] = typer.Option(None, "--account", "-a", help="Filter by account ID"),
    from_date: Optional[str] = typer.Option(None, "--from", help="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = typer.Option(None, "--to", help="End date (YYYY-MM-DD)"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (pending, completed)"),
    institution: Optional[str] = typer.Option(None, "--institution", "-i", help="Filter by institution"),
    tag: Optional[List[str]] = typer.Option(None, "--tag", "-t", help="Filter by tag (can be repeated for AND logic)"),
    untagged: bool = typer.Option(False, "--untagged", help="Show only untagged transactions"),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum number of transactions to show"),
    offset: int = typer.Option(0, "--offset", help="Number of transactions to skip")
):
    """
    List transactions with filters
    """
    try:
        analytics = AnalyticsService()
        tag_service = TagService()

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
            tags=tag,
            untagged_only=untagged,
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
        table.add_column("Description", width=30)
        table.add_column("Amount", justify="right", width=15)
        table.add_column("Card", width=6)
        table.add_column("Tags", width=18)
        table.add_column("Account", width=10)

        for txn in transactions:
            # Format amount with color
            amount_str = f"{txn.original_amount:,.2f} {txn.original_currency}"
            if txn.original_amount < 0:
                amount_str = f"[red]{amount_str}[/red]"
            else:
                amount_str = f"[green]{amount_str}[/green]"

            # Get tags for transaction
            txn_tags = tag_service.get_transaction_tags(txn.id)
            if txn_tags:
                tags_str = ", ".join([f"[cyan]{fix_rtl(t.name)}[/cyan]" for t in txn_tags[:3]])
                if len(txn_tags) > 3:
                    tags_str += f" [dim]+{len(txn_tags) - 3}[/dim]"
            else:
                tags_str = "[dim](none)[/dim]"

            # Get account info
            account = analytics.get_account_by_id(txn.account_id)
            account_str = f"{account.institution}" if account else "Unknown"
            card_str = account.account_number if account else ""

            table.add_row(
                str(txn.id),
                txn.transaction_date.strftime("%Y-%m-%d"),
                fix_rtl(txn.description[:30]),
                amount_str,
                card_str,
                tags_str,
                account_str
            )

        console.print(table)

        # Show summary
        console.print(f"\n[bold]Showing:[/bold] {len(transactions)} transaction(s)")

        if len(transactions) == limit:
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
        tag_service = TagService()

        transaction = analytics.get_transaction_by_id(transaction_id)

        if not transaction:
            console.print(f"[red]Transaction with ID {transaction_id} not found[/red]")
            analytics.close()
            raise typer.Exit(code=1)

        # Get account info
        account = analytics.get_account_by_id(transaction.account_id)

        # Get tags
        txn_tags = tag_service.get_transaction_tags(transaction_id)

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

        # Category information (original + user override)
        info_lines.append("")
        info_lines.append(f"[bold cyan]Category & Tags:[/bold cyan]")
        if transaction.category:
            info_lines.append(f"[bold]Original Category:[/bold] {fix_rtl(transaction.category)}")
        if hasattr(transaction, 'user_category') and transaction.user_category:
            info_lines.append(f"[bold]User Category:[/bold] [green]{fix_rtl(transaction.user_category)}[/green]")

        # Tags
        if txn_tags:
            tags_str = ", ".join([f"[cyan]{fix_rtl(t.name)}[/cyan]" for t in txn_tags])
            info_lines.append(f"[bold]Tags:[/bold] {tags_str}")
        else:
            info_lines.append(f"[bold]Tags:[/bold] [dim](none)[/dim]")

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


@app.command("tag")
def tag_transaction(
    transaction_id: Optional[int] = typer.Argument(None, help="Transaction ID to tag"),
    tags: List[str] = typer.Argument(..., help="Tag names to add"),
    merchant: Optional[str] = typer.Option(None, "--merchant", "-m", help="Tag all transactions matching merchant pattern"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Tag all transactions in category")
):
    """
    Add tags to transactions

    Examples:
        fin-cli transactions tag 123 groceries
        fin-cli transactions tag 123 groceries weekly-shop
        fin-cli transactions tag --merchant "רמי לוי" groceries
        fin-cli transactions tag --category "מסעדות" dining-out
    """
    try:
        tag_service = TagService()

        if merchant:
            count = tag_service.bulk_tag_by_merchant(merchant, list(tags))
            console.print(f"[green]Tagged {count} transactions matching '{merchant}' with: {', '.join(tags)}[/green]")
        elif category:
            count = tag_service.bulk_tag_by_category(category, list(tags))
            console.print(f"[green]Tagged {count} transactions in category '{category}' with: {', '.join(tags)}[/green]")
        elif transaction_id is not None:
            added = tag_service.tag_transaction(transaction_id, list(tags))
            if added > 0:
                console.print(f"[green]Added {added} tag(s) to transaction {transaction_id}[/green]")
            else:
                console.print(f"[yellow]Transaction {transaction_id} already has all specified tags[/yellow]")
        else:
            console.print("[red]Please provide a transaction ID or use --merchant/--category for bulk tagging[/red]")
            raise typer.Exit(code=1)

    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error tagging transaction: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("untag")
def untag_transaction(
    transaction_id: int = typer.Argument(..., help="Transaction ID"),
    tags: List[str] = typer.Argument(..., help="Tag names to remove")
):
    """
    Remove tags from a transaction

    Example:
        fin-cli transactions untag 123 dining-out
    """
    try:
        tag_service = TagService()

        removed = tag_service.untag_transaction(transaction_id, list(tags))

        if removed > 0:
            console.print(f"[green]Removed {removed} tag(s) from transaction {transaction_id}[/green]")
        else:
            console.print(f"[yellow]Transaction {transaction_id} did not have any of the specified tags[/yellow]")

    except Exception as e:
        console.print(f"[red]Error removing tags: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("edit")
def edit_transaction(
    transaction_id: int = typer.Argument(..., help="Transaction ID"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Set user category (use empty string to clear)")
):
    """
    Edit transaction fields (user category)

    Examples:
        fin-cli transactions edit 123 --category "groceries"
        fin-cli transactions edit 123 --category ""  # Clear user category
    """
    try:
        if category is None:
            console.print("[red]Please specify --category to update[/red]")
            raise typer.Exit(code=1)

        tag_service = TagService()

        success = tag_service.update_transaction(transaction_id, user_category=category)

        if success:
            if category:
                console.print(f"[green]Updated transaction {transaction_id} category to '{category}'[/green]")
            else:
                console.print(f"[green]Cleared user category for transaction {transaction_id}[/green]")
        else:
            console.print(f"[red]Transaction {transaction_id} not found[/red]")
            raise typer.Exit(code=1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error editing transaction: {e}[/red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()