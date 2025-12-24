"""
Tag management CLI commands
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm
from typing import Optional

from services.tag_service import TagService

app = typer.Typer(help="Manage transaction tags")
console = Console()


@app.command("list")
def list_tags(
    sort: str = typer.Option("count", "--sort", "-s", help="Sort by: name, count, amount")
):
    """
    List all tags with usage statistics
    """
    try:
        tag_service = TagService()
        stats = tag_service.get_tag_stats()
        untagged_count = tag_service.get_untagged_count()
        untagged_total = tag_service.get_untagged_total()

        if not stats and untagged_count == 0:
            console.print("[yellow]No tags found. Use 'fin-cli tags migrate' to auto-tag from categories.[/yellow]")
            return

        # Sort stats
        if sort == "name":
            stats.sort(key=lambda x: x["name"].lower())
        elif sort == "amount":
            stats.sort(key=lambda x: abs(x["total_amount"]), reverse=True)
        # Default is already sorted by count

        # Create table
        table = Table(title="Tags", show_header=True, header_style="bold cyan")
        table.add_column("Tag", width=25)
        table.add_column("Count", justify="right", width=10)
        table.add_column("Total Amount", justify="right", width=18)

        for stat in stats:
            amount_str = f"₪{stat['total_amount']:,.2f}"
            if stat['total_amount'] < 0:
                amount_str = f"[red]{amount_str}[/red]"
            else:
                amount_str = f"[green]{amount_str}[/green]"

            table.add_row(
                stat["name"],
                str(stat["count"]),
                amount_str
            )

        # Add separator and untagged row
        if untagged_count > 0:
            table.add_section()
            untagged_amount_str = f"₪{untagged_total:,.2f}"
            if untagged_total < 0:
                untagged_amount_str = f"[red]{untagged_amount_str}[/red]"
            table.add_row(
                "[dim](untagged)[/dim]",
                f"[dim]{untagged_count}[/dim]",
                f"[dim]{untagged_amount_str}[/dim]"
            )

        console.print(table)

        # Summary
        total_tags = len(stats)
        total_tagged = sum(s["count"] for s in stats)
        console.print(f"\n[dim]{total_tags} tags, {total_tagged} tagged transactions, {untagged_count} untagged[/dim]")

    except Exception as e:
        console.print(f"[red]Error listing tags: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("rename")
def rename_tag(
    old_name: str = typer.Argument(..., help="Current tag name"),
    new_name: str = typer.Argument(..., help="New tag name")
):
    """
    Rename a tag. If the new name exists, tags will be merged.
    """
    try:
        tag_service = TagService()

        # Check if old tag exists
        old_tag = tag_service.get_tag_by_name(old_name)
        if not old_tag:
            console.print(f"[red]Tag '{old_name}' not found[/red]")
            raise typer.Exit(code=1)

        # Check if merging
        new_tag = tag_service.get_tag_by_name(new_name)
        if new_tag and new_tag.id != old_tag.id:
            if not Confirm.ask(f"Tag '{new_name}' already exists. Merge '{old_name}' into it?"):
                console.print("[yellow]Cancelled[/yellow]")
                return

        success = tag_service.rename_tag(old_name, new_name)

        if success:
            if new_tag and new_tag.id != old_tag.id:
                console.print(f"[green]Merged tag '{old_name}' into '{new_name}'[/green]")
            else:
                console.print(f"[green]Renamed tag '{old_name}' to '{new_name}'[/green]")
        else:
            console.print(f"[red]Failed to rename tag[/red]")
            raise typer.Exit(code=1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error renaming tag: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("delete")
def delete_tag(
    name: str = typer.Argument(..., help="Tag name to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation")
):
    """
    Delete a tag and remove it from all transactions
    """
    try:
        tag_service = TagService()

        # Check if tag exists
        tag = tag_service.get_tag_by_name(name)
        if not tag:
            console.print(f"[red]Tag '{name}' not found[/red]")
            raise typer.Exit(code=1)

        # Get stats for confirmation
        stats = tag_service.get_tag_stats()
        tag_stat = next((s for s in stats if s["name"].lower() == name.lower()), None)
        count = tag_stat["count"] if tag_stat else 0

        if not force:
            if not Confirm.ask(f"Delete tag '{name}'? ({count} transactions will be untagged)"):
                console.print("[yellow]Cancelled[/yellow]")
                return

        success = tag_service.delete_tag(name)

        if success:
            console.print(f"[green]Deleted tag '{name}'[/green]")
        else:
            console.print(f"[red]Failed to delete tag[/red]")
            raise typer.Exit(code=1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error deleting tag: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("migrate")
def migrate_categories(
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without making changes")
):
    """
    Auto-tag transactions based on their existing categories
    """
    try:
        tag_service = TagService()

        console.print("[cyan]Scanning transactions for categories...[/cyan]")

        results = tag_service.migrate_categories_to_tags(dry_run=dry_run)

        if not results:
            console.print("[yellow]No transactions to migrate. All categories are already tagged or no categories exist.[/yellow]")
            return

        # Display results
        table = Table(
            title="Migration Preview" if dry_run else "Migration Results",
            show_header=True,
            header_style="bold cyan"
        )
        table.add_column("Category → Tag", width=30)
        table.add_column("Transactions", justify="right", width=15)

        total = 0
        for category, count in sorted(results.items(), key=lambda x: x[1], reverse=True):
            table.add_row(category, str(count))
            total += count

        table.add_section()
        table.add_row("[bold]Total[/bold]", f"[bold]{total}[/bold]")

        console.print(table)

        if dry_run:
            console.print("\n[yellow]This was a dry run. Run without --dry-run to apply changes.[/yellow]")
        else:
            console.print(f"\n[green]Successfully tagged {total} transactions across {len(results)} categories[/green]")

    except Exception as e:
        console.print(f"[red]Error migrating categories: {e}[/red]")
        raise typer.Exit(code=1)