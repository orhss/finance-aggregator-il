"""
Category mapping management CLI commands
"""

import json
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from typing import Optional
from pathlib import Path

from services.category_service import CategoryService
from config.constants import Institution, UnifiedCategory
from cli.utils import fix_rtl

app = typer.Typer(help="Manage category mappings")
console = Console()


@app.command("analyze")
def analyze_categories():
    """
    Analyze category coverage across providers
    """
    try:
        service = CategoryService()
        analysis = service.analyze_categories()

        # Provider breakdown table
        table = Table(title="Category Analysis", show_header=True, header_style="bold cyan")
        table.add_column("Provider", width=15)
        table.add_column("Unique Categories", justify="right", width=18)
        table.add_column("Transactions", justify="right", width=15)
        table.add_column("Mapped %", justify="right", width=12)

        for provider in analysis['providers']:
            pct_color = "green" if provider['mapped_pct'] >= 80 else "yellow" if provider['mapped_pct'] >= 50 else "red"
            table.add_row(
                provider['name'].upper(),
                str(provider['unique_categories']),
                f"{provider['transactions']:,}",
                f"[{pct_color}]{provider['mapped_pct']}%[/{pct_color}]"
            )

        # Totals row
        totals = analysis['totals']
        table.add_section()
        pct_color = "green" if totals['mapped_pct'] >= 80 else "yellow" if totals['mapped_pct'] >= 50 else "red"
        table.add_row(
            "[bold]Total[/bold]",
            f"[bold]{totals['unique_categories']}[/bold]",
            f"[bold]{totals['transactions']:,}[/bold]",
            f"[bold][{pct_color}]{totals['mapped_pct']}%[/{pct_color}][/bold]"
        )

        console.print(table)

        # Next steps hint
        if totals['mapped_pct'] < 100:
            console.print("\n[dim]Run 'fin-cli categories unmapped' to see unmapped categories[/dim]")
            console.print("[dim]Run 'fin-cli categories setup' for interactive mapping wizard[/dim]")

    except Exception as e:
        console.print(f"[red]Error analyzing categories: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("list")
def list_mappings(
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Filter by provider (cal, max, isracard)")
):
    """
    List all category mappings
    """
    try:
        service = CategoryService()
        mappings = service.get_all_mappings(provider)

        if not mappings:
            if provider:
                console.print(f"[yellow]No mappings found for {provider}[/yellow]")
            else:
                console.print("[yellow]No mappings found. Run 'fin-cli categories setup' to create mappings.[/yellow]")
            return

        # Group by provider for display
        table = Table(title="Category Mappings", show_header=True, header_style="bold cyan")
        table.add_column("Provider", width=10)
        table.add_column("Raw Category", width=25)
        table.add_column("", width=3)
        table.add_column("Unified Category", width=20)

        current_provider = None
        for mapping in mappings:
            if current_provider and mapping.provider != current_provider:
                table.add_section()
            current_provider = mapping.provider

            table.add_row(
                mapping.provider.upper(),
                fix_rtl(mapping.raw_category),
                "->",
                mapping.unified_category
            )

        console.print(table)
        console.print(f"\n[dim]{len(mappings)} mappings total[/dim]")

    except Exception as e:
        console.print(f"[red]Error listing mappings: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("unmapped")
def unmapped_categories(
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Filter by provider (cal, max, isracard)")
):
    """
    Show categories that have no mapping
    """
    try:
        service = CategoryService()
        unmapped = service.get_unmapped_categories(provider)

        if not unmapped:
            console.print("[green]All categories are mapped![/green]")
            return

        table = Table(title="Unmapped Categories", show_header=True, header_style="bold yellow")
        table.add_column("Provider", width=10)
        table.add_column("Raw Category", width=30)
        table.add_column("Transactions", justify="right", width=12)
        table.add_column("Sample Merchant", width=30)

        for item in unmapped:
            table.add_row(
                item['provider'].upper(),
                fix_rtl(item['raw_category']),
                str(item['count']),
                fix_rtl(item['sample_merchant'] or '-')
            )

        console.print(table)

        total_txns = sum(u['count'] for u in unmapped)
        console.print(f"\n[yellow]{len(unmapped)} unmapped categories ({total_txns:,} transactions)[/yellow]")

        # Quick actions hint
        console.print("\n[dim]Quick actions:[/dim]")
        if unmapped:
            first = unmapped[0]
            console.print(f"  [dim]fin-cli categories map {first['provider']} \"{first['raw_category']}\" <unified>[/dim]")
        console.print("  [dim]fin-cli categories setup   # Interactive wizard[/dim]")

    except Exception as e:
        console.print(f"[red]Error getting unmapped categories: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("map")
def map_category(
    provider: str = typer.Argument(..., help="Provider name (cal, max, isracard)"),
    raw_category: str = typer.Argument(..., help="Raw category name from provider"),
    unified_category: str = typer.Argument(..., help="Unified category name")
):
    """
    Add or update a category mapping
    """
    try:
        # Validate provider
        valid_providers = [p.lower() for p in Institution.credit_cards()]
        if provider.lower() not in valid_providers:
            console.print(f"[red]Invalid provider '{provider}'. Valid: {', '.join(valid_providers)}[/red]")
            raise typer.Exit(code=1)

        service = CategoryService()

        # Check if mapping already exists
        existing = service.get_mapping(provider, raw_category)
        if existing:
            if existing.unified_category == unified_category:
                console.print(f"[yellow]Mapping already exists: {provider}/{raw_category} -> {unified_category}[/yellow]")
                return
            console.print(f"[yellow]Updating existing mapping: {existing.unified_category} -> {unified_category}[/yellow]")

        mapping = service.add_mapping(provider, raw_category, unified_category)
        console.print(f"[green]Mapped {provider.upper()}/{fix_rtl(raw_category)} -> {unified_category}[/green]")

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error creating mapping: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("unmap")
def unmap_category(
    provider: str = typer.Argument(..., help="Provider name (cal, max, isracard)"),
    raw_category: str = typer.Argument(..., help="Raw category name from provider"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation")
):
    """
    Remove a category mapping
    """
    try:
        service = CategoryService()

        # Check if mapping exists
        existing = service.get_mapping(provider, raw_category)
        if not existing:
            console.print(f"[yellow]No mapping found for {provider}/{raw_category}[/yellow]")
            return

        if not force:
            if not Confirm.ask(f"Remove mapping {provider.upper()}/{fix_rtl(raw_category)} -> {existing.unified_category}?"):
                console.print("[yellow]Cancelled[/yellow]")
                return

        success = service.remove_mapping(provider, raw_category)

        if success:
            console.print(f"[green]Removed mapping for {provider.upper()}/{fix_rtl(raw_category)}[/green]")
        else:
            console.print(f"[red]Failed to remove mapping[/red]")
            raise typer.Exit(code=1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error removing mapping: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("apply")
def apply_mappings(
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Apply only for specific provider")
):
    """
    Apply mappings to existing transactions
    """
    try:
        service = CategoryService()

        console.print("[cyan]Applying category mappings to transactions...[/cyan]")

        results = service.apply_mappings_to_transactions(provider)

        if not any(results.values()):
            console.print("[yellow]No transactions needed updating[/yellow]")
            return

        table = Table(title="Mappings Applied", show_header=True, header_style="bold green")
        table.add_column("Provider", width=15)
        table.add_column("Transactions Updated", justify="right", width=20)

        for prov, count in results.items():
            if count > 0:
                table.add_row(prov.upper(), f"{count:,}")

        total = sum(results.values())
        table.add_section()
        table.add_row("[bold]Total[/bold]", f"[bold]{total:,}[/bold]")

        console.print(table)
        console.print(f"[green]Applied mappings to {total:,} transactions[/green]")

    except Exception as e:
        console.print(f"[red]Error applying mappings: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("unified")
def list_unified():
    """
    List unified categories with statistics
    """
    try:
        service = CategoryService()
        stats = service.get_unified_categories_stats()

        if not stats:
            console.print("[yellow]No unified categories found. Create mappings first.[/yellow]")
            return

        table = Table(title="Unified Categories", show_header=True, header_style="bold cyan")
        table.add_column("Unified Category", width=20)
        table.add_column("Providers", width=20)
        table.add_column("Raw Categories", justify="right", width=15)
        table.add_column("Transactions", justify="right", width=15)

        for stat in stats:
            table.add_row(
                stat['unified_category'],
                ", ".join(p.upper() for p in stat['providers']),
                str(stat['raw_count']),
                f"{stat['transaction_count']:,}"
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error listing unified categories: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("rename")
def rename_unified(
    old_name: str = typer.Argument(..., help="Current unified category name"),
    new_name: str = typer.Argument(..., help="New unified category name")
):
    """
    Rename a unified category across all mappings
    """
    try:
        service = CategoryService()

        count = service.rename_unified_category(old_name, new_name)

        if count == 0:
            console.print(f"[yellow]No mappings found for unified category '{old_name}'[/yellow]")
            return

        console.print(f"[green]Renamed '{old_name}' to '{new_name}' ({count} mappings updated)[/green]")
        console.print("[dim]Run 'fin-cli categories apply' to update transaction normalized categories[/dim]")

    except Exception as e:
        console.print(f"[red]Error renaming unified category: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("export")
def export_mappings(
    output: Path = typer.Argument(..., help="Output file path (JSON)")
):
    """
    Export all mappings to JSON file
    """
    try:
        service = CategoryService()
        mappings = service.export_mappings()

        with open(output, 'w', encoding='utf-8') as f:
            json.dump(mappings, f, ensure_ascii=False, indent=2)

        console.print(f"[green]Exported {len(mappings)} mappings to {output}[/green]")

    except Exception as e:
        console.print(f"[red]Error exporting mappings: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("import")
def import_mappings(
    input_file: Path = typer.Argument(..., help="Input file path (JSON)"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing mappings")
):
    """
    Import mappings from JSON file
    """
    try:
        if not input_file.exists():
            console.print(f"[red]File not found: {input_file}[/red]")
            raise typer.Exit(code=1)

        with open(input_file, 'r', encoding='utf-8') as f:
            mappings = json.load(f)

        service = CategoryService()
        results = service.import_mappings(mappings, overwrite=overwrite)

        console.print(f"[green]Imported mappings:[/green]")
        console.print(f"  Added: {results['added']}")
        console.print(f"  Updated: {results['updated']}")
        console.print(f"  Skipped: {results['skipped']}")

        if results['added'] > 0 or results['updated'] > 0:
            console.print("\n[dim]Run 'fin-cli categories apply' to update transaction categories[/dim]")

    except json.JSONDecodeError:
        console.print(f"[red]Invalid JSON file: {input_file}[/red]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error importing mappings: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("setup")
def setup_wizard():
    """
    Interactive setup wizard for category mappings
    """
    try:
        service = CategoryService()

        # Get unmapped categories
        unmapped = service.get_unmapped_categories()

        if not unmapped:
            console.print("[green]All categories are already mapped![/green]")
            return

        console.print(Panel(
            f"Found [yellow]{len(unmapped)}[/yellow] unmapped categories.\n"
            "For each category, enter a unified name or press Enter to skip.",
            title="Category Setup Wizard"
        ))

        # Get existing unified categories for suggestions
        existing_unified = service.get_unified_categories()
        if existing_unified:
            console.print(f"\n[dim]Existing unified categories: {', '.join(existing_unified)}[/dim]")

        # Suggest standard categories
        standard = UnifiedCategory.all()
        console.print(f"[dim]Standard categories: {', '.join(standard)}[/dim]\n")

        mapped_count = 0
        skipped_count = 0

        for i, item in enumerate(unmapped, 1):
            console.print(f"\n[bold][{i}/{len(unmapped)}] {item['provider'].upper()}[/bold]")
            console.print(f"  Raw category: [cyan]{fix_rtl(item['raw_category'])}[/cyan]")
            console.print(f"  Transactions: {item['count']}")
            if item['sample_merchant']:
                console.print(f"  Sample: {fix_rtl(item['sample_merchant'])}")

            unified = Prompt.ask(
                "  Map to",
                default="",
            )

            if unified.strip():
                service.add_mapping(item['provider'], item['raw_category'], unified.strip())
                console.print(f"  [green]Mapped to '{unified.strip()}'[/green]")
                mapped_count += 1
            else:
                console.print("  [yellow]Skipped[/yellow]")
                skipped_count += 1

        # Summary
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Mapped: {mapped_count}")
        console.print(f"  Skipped: {skipped_count}")

        if mapped_count > 0:
            if Confirm.ask("\nApply mappings to existing transactions?"):
                results = service.apply_mappings_to_transactions()
                total = sum(results.values())
                console.print(f"[green]Applied mappings to {total:,} transactions[/green]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Setup interrupted[/yellow]")
    except Exception as e:
        console.print(f"[red]Error in setup wizard: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("suggest")
def suggest_categories(
    min_transactions: int = typer.Option(2, "--min", "-m", help="Minimum transactions per merchant"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Filter by provider")
):
    """
    Show uncategorized transactions grouped by merchant pattern.

    For transactions without provider categories (e.g., Isracard), this groups
    them by merchant name and lets you assign categories in bulk.
    """
    try:
        service = CategoryService()

        # Get total counts for context
        total_all = service.get_total_transaction_count()
        with_provider_cat = service.get_transactions_with_provider_category_count()
        without_provider_cat = total_all - with_provider_cat

        console.print(Panel(
            f"[bold]Transaction Overview[/bold]\n\n"
            f"Total transactions: {total_all:,}\n"
            f"With provider category: {with_provider_cat:,}\n"
            f"Without provider category: [yellow]{without_provider_cat:,}[/yellow]",
            title="Category Coverage"
        ))

        if without_provider_cat == 0:
            console.print("[green]All transactions have provider categories![/green]")
            return

        # Get uncategorized by merchant
        merchant_groups = service.get_uncategorized_by_merchant(
            min_transactions=min_transactions,
            provider=provider
        )

        if not merchant_groups:
            console.print(f"[yellow]No merchant patterns with {min_transactions}+ transactions found.[/yellow]")
            console.print("[dim]Try lowering --min or check if transactions already have user_category set[/dim]")
            return

        # Display table
        table = Table(title="Uncategorized by Merchant", show_header=True, header_style="bold yellow")
        table.add_column("#", width=4, justify="right")
        table.add_column("Merchant Pattern", width=25)
        table.add_column("Provider", width=10)
        table.add_column("Transactions", justify="right", width=12)
        table.add_column("Total Amount", justify="right", width=15)
        table.add_column("Sample", width=30)

        for i, group in enumerate(merchant_groups, 1):
            table.add_row(
                str(i),
                fix_rtl(group['merchant_pattern']),
                group['provider'].upper(),
                str(group['count']),
                f"₪{group['total_amount']:,.0f}",
                fix_rtl(group['sample_descriptions'][0][:30]) if group['sample_descriptions'] else '-'
            )

        console.print(table)

        total_uncategorized = sum(g['count'] for g in merchant_groups)
        console.print(f"\n[yellow]{len(merchant_groups)} merchant patterns ({total_uncategorized:,} transactions)[/yellow]")

        # Quick actions hint
        console.print("\n[dim]Quick actions:[/dim]")
        console.print("  [dim]fin-cli categories assign 1 groceries   # Assign by row number[/dim]")
        console.print("  [dim]fin-cli categories assign-wizard        # Interactive wizard[/dim]")

        # Store groups in a temporary way for the assign command (via session state)
        # For CLI, we'll need the assign command to re-fetch the groups

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("assign")
def assign_merchant_category(
    row_number: int = typer.Argument(..., help="Row number from 'suggest' output"),
    category: str = typer.Argument(..., help="Category to assign"),
    min_transactions: int = typer.Option(2, "--min", "-m", help="Same min as used in suggest")
):
    """
    Assign a category to a merchant pattern from 'suggest' output.
    """
    try:
        service = CategoryService()

        # Re-fetch the merchant groups
        merchant_groups = service.get_uncategorized_by_merchant(min_transactions=min_transactions)

        if not merchant_groups:
            console.print("[yellow]No uncategorized merchant groups found.[/yellow]")
            return

        if row_number < 1 or row_number > len(merchant_groups):
            console.print(f"[red]Invalid row number. Must be 1-{len(merchant_groups)}[/red]")
            raise typer.Exit(code=1)

        group = merchant_groups[row_number - 1]

        # Confirm
        console.print(f"Assigning category '[cyan]{category}[/cyan]' to:")
        console.print(f"  Merchant: [bold]{fix_rtl(group['merchant_pattern'])}[/bold]")
        console.print(f"  Transactions: {group['count']}")

        if not Confirm.ask("Proceed?"):
            console.print("[yellow]Cancelled[/yellow]")
            return

        # Apply and save mapping for future transactions
        result = service.bulk_set_category_with_mapping(
            group['merchant_pattern'],
            category,
            group['transaction_ids'],
            group['provider']
        )
        console.print(f"[green]Assigned '{category}' to {result['transactions_updated']} transactions[/green]")
        if result['mapping_created']:
            console.print(f"[green]Created merchant mapping: '{group['merchant_pattern']}' -> '{category}'[/green]")
            console.print("[dim]Future transactions matching this pattern will be auto-categorized[/dim]")

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("assign-wizard")
def assign_wizard(
    min_transactions: int = typer.Option(2, "--min", "-m", help="Minimum transactions per merchant")
):
    """
    Interactive wizard to assign categories to uncategorized merchants.
    """
    try:
        service = CategoryService()

        merchant_groups = service.get_uncategorized_by_merchant(min_transactions=min_transactions)

        if not merchant_groups:
            console.print("[green]No uncategorized merchants found![/green]")
            return

        # Get suggestions for unified categories
        existing_unified = service.get_unified_categories()
        standard = UnifiedCategory.all()
        all_categories = sorted(set(existing_unified + standard))

        console.print(Panel(
            f"Found [yellow]{len(merchant_groups)}[/yellow] merchant patterns without categories.\n"
            "For each merchant, enter a category name or press Enter to skip.\n\n"
            f"[dim]Available categories: {', '.join(all_categories[:10])}{'...' if len(all_categories) > 10 else ''}[/dim]",
            title="Merchant Category Wizard"
        ))

        assigned_count = 0
        skipped_count = 0
        total_txns_assigned = 0

        for i, group in enumerate(merchant_groups, 1):
            console.print(f"\n[bold][{i}/{len(merchant_groups)}] {fix_rtl(group['merchant_pattern'])}[/bold]")
            console.print(f"  Provider: {group['provider'].upper()}")
            console.print(f"  Transactions: {group['count']}")
            console.print(f"  Total amount: ₪{group['total_amount']:,.0f}")
            if group['sample_descriptions']:
                console.print(f"  Samples: {fix_rtl(', '.join(group['sample_descriptions'][:2]))}")

            category = Prompt.ask(
                "  Category",
                default="",
            )

            if category.strip():
                result = service.bulk_set_category_with_mapping(
                    group['merchant_pattern'],
                    category.strip(),
                    group['transaction_ids'],
                    group['provider']
                )
                console.print(f"  [green]Assigned '{category.strip()}' to {result['transactions_updated']} transactions[/green]")
                if result['mapping_created']:
                    console.print(f"  [dim]Mapping saved for future '{group['merchant_pattern']}' transactions[/dim]")
                assigned_count += 1
                total_txns_assigned += result['transactions_updated']
            else:
                console.print("  [yellow]Skipped[/yellow]")
                skipped_count += 1

        # Summary
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Merchants assigned: {assigned_count}")
        console.print(f"  Merchants skipped: {skipped_count}")
        console.print(f"  Transactions categorized: {total_txns_assigned:,}")

    except KeyboardInterrupt:
        console.print("\n[yellow]Wizard interrupted[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("merchants")
def list_merchant_mappings(
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Filter by provider")
):
    """
    List all merchant pattern mappings.

    Shows patterns that will be used to auto-categorize future transactions.
    """
    try:
        service = CategoryService()
        mappings = service.get_all_merchant_mappings(provider)

        if not mappings:
            console.print("[yellow]No merchant mappings found.[/yellow]")
            console.print("[dim]Use 'fin-cli categories assign' or 'assign-wizard' to create mappings[/dim]")
            return

        table = Table(title="Merchant Mappings", show_header=True, header_style="bold cyan")
        table.add_column("#", width=4, justify="right")
        table.add_column("Pattern", width=25)
        table.add_column("Category", width=20)
        table.add_column("Provider", width=10)
        table.add_column("Match Type", width=12)

        for i, mapping in enumerate(mappings, 1):
            table.add_row(
                str(i),
                fix_rtl(mapping.pattern),
                mapping.category,
                mapping.provider.upper() if mapping.provider else "All",
                mapping.match_type
            )

        console.print(table)
        console.print(f"\n[dim]{len(mappings)} merchant mappings total[/dim]")
        console.print("[dim]These patterns auto-categorize future transactions during sync[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("remove-merchant")
def remove_merchant_mapping(
    pattern: str = typer.Argument(..., help="Merchant pattern to remove"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Provider filter"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation")
):
    """
    Remove a merchant pattern mapping.
    """
    try:
        service = CategoryService()

        mapping = service.get_merchant_mapping(pattern, provider)
        if not mapping:
            console.print(f"[yellow]No mapping found for pattern '{pattern}'[/yellow]")
            return

        if not force:
            console.print(f"Remove mapping: '{fix_rtl(pattern)}' -> '{mapping.category}'")
            if not Confirm.ask("Proceed?"):
                console.print("[yellow]Cancelled[/yellow]")
                return

        if service.remove_merchant_mapping(pattern, provider):
            console.print(f"[green]Removed merchant mapping for '{fix_rtl(pattern)}'[/green]")
        else:
            console.print("[red]Failed to remove mapping[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)
