"""
CLI commands for managing category/tag rules
"""

import typer
from typing import Optional, List
from rich.console import Console
from rich.table import Table

from services.rules_service import RulesService, MatchType, RULES_FILE
from cli.utils import fix_rtl

app = typer.Typer(help="Manage auto-categorization rules")
console = Console()


@app.command("list")
def list_rules():
    """List all defined rules"""
    service = RulesService()
    rules = service.get_rules()

    if not rules:
        console.print(f"[yellow]No rules defined.[/yellow]")
        console.print(f"Create rules file at: {RULES_FILE}")
        console.print(f"Or run: [bold]fin rules init[/bold] to create example rules")
        return

    table = Table(title=f"Category Rules ({len(rules)} rules)")
    table.add_column("#", style="dim", width=4)
    table.add_column("Pattern", style="cyan")
    table.add_column("Match", style="dim", width=10)
    table.add_column("Category", style="green")
    table.add_column("Add Tags", style="blue")
    table.add_column("Remove Tags", style="red")
    table.add_column("Description", style="dim")

    for i, rule in enumerate(rules, 1):
        status = "" if rule.enabled else "[dim](disabled)[/dim] "
        table.add_row(
            str(i),
            status + fix_rtl(rule.pattern),
            rule.match_type.value,
            fix_rtl(rule.category) if rule.category else "-",
            ", ".join(fix_rtl(t) for t in rule.tags) if rule.tags else "-",
            ", ".join(fix_rtl(t) for t in rule.remove_tags) if rule.remove_tags else "-",
            fix_rtl(rule.description) if rule.description else "",
        )

    console.print(table)
    console.print(f"\n[dim]Rules file: {RULES_FILE}[/dim]")


@app.command("add")
def add_rule(
    pattern: str = typer.Argument(..., help="Pattern to match in transaction description"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Category to set"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Comma-separated tags to add"),
    remove_tags: Optional[str] = typer.Option(None, "--remove-tags", "-r", help="Comma-separated tags to remove"),
    match_type: str = typer.Option("contains", "--match", "-m",
        help="Match type: contains, exact, starts_with, ends_with, regex"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Rule description"),
):
    """Add a new categorization rule"""
    if not category and not tags and not remove_tags:
        console.print("[red]Error: Must specify at least --category, --tags, or --remove-tags[/red]")
        raise typer.Exit(1)

    try:
        match_type_enum = MatchType(match_type)
    except ValueError:
        console.print(f"[red]Error: Invalid match type '{match_type}'[/red]")
        console.print(f"Valid types: {', '.join(m.value for m in MatchType)}")
        raise typer.Exit(1)

    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    remove_tag_list = [t.strip() for t in remove_tags.split(",")] if remove_tags else []

    service = RulesService()
    rule = service.add_rule(
        pattern=pattern,
        category=category,
        tags=tag_list,
        remove_tags=remove_tag_list,
        match_type=match_type_enum,
        description=description,
    )

    console.print(f"[green]Rule added:[/green]")
    console.print(f"  Pattern: [cyan]{pattern}[/cyan] ({match_type})")
    if category:
        console.print(f"  Category: [green]{category}[/green]")
    if tag_list:
        console.print(f"  Tags to add: [blue]{', '.join(tag_list)}[/blue]")
    if remove_tag_list:
        console.print(f"  Tags to remove: [red]{', '.join(remove_tag_list)}[/red]")


@app.command("remove")
def remove_rule(
    pattern_or_index: str = typer.Argument(..., help="Pattern or rule number (#) to remove"),
):
    """Remove a rule by pattern or index number (from 'rules list')"""
    service = RulesService()

    # Check if it's a number (index)
    try:
        index = int(pattern_or_index)
        rules = service.get_rules()
        if 1 <= index <= len(rules):
            pattern = rules[index - 1].pattern
            if service.remove_rule(pattern):
                console.print(f"[green]Rule #{index} removed:[/green] {pattern}")
            else:
                console.print(f"[red]Failed to remove rule #{index}[/red]")
        else:
            console.print(f"[yellow]Invalid rule number: {index}. Use 'fin rules list' to see rule numbers.[/yellow]")
        return
    except ValueError:
        pass  # Not a number, treat as pattern

    if service.remove_rule(pattern_or_index):
        console.print(f"[green]Rule removed:[/green] {pattern_or_index}")
    else:
        console.print(f"[yellow]Rule not found:[/yellow] {pattern_or_index}")
        console.print("[dim]Tip: Use rule number from 'fin rules list' instead, e.g. 'fin rules remove 3'[/dim]")


@app.command("apply")
def apply_rules(
    rule: Optional[List[str]] = typer.Option(None, "--rule", "-r", help="Apply specific rule(s) by number or pattern (can repeat)"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be changed without applying"),
    only_uncategorized: bool = typer.Option(False, "--uncategorized", "-u",
        help="Only apply to transactions without user_category"),
    transaction_id: Optional[int] = typer.Option(None, "--id", help="Apply to specific transaction ID"),
):
    """Apply rules to transactions

    Examples:
        fin-cli rules apply                    # Apply all rules
        fin-cli rules apply -r 3               # Apply only rule #3
        fin-cli rules apply -r 3 -r 5          # Apply rules #3 and #5
        fin-cli rules apply -r "סופר"          # Apply rule with pattern "סופר"
        fin-cli rules apply -r 3 --dry-run     # Preview what rule #3 would change
    """
    service = RulesService()
    all_rules = service.get_rules()

    if not all_rules:
        console.print("[yellow]No rules defined. Run 'fin rules init' or add rules first.[/yellow]")
        return

    # Filter to specific rules if requested
    rule_indices = None
    if rule:
        rule_indices = []
        for r in rule:
            # Try as number first
            try:
                idx = int(r)
                if 1 <= idx <= len(all_rules):
                    rule_indices.append(idx - 1)  # Convert to 0-based
                else:
                    console.print(f"[yellow]Warning: Rule #{idx} doesn't exist (max: {len(all_rules)})[/yellow]")
            except ValueError:
                # Try as pattern
                found = False
                for i, existing_rule in enumerate(all_rules):
                    if existing_rule.pattern.lower() == r.lower():
                        rule_indices.append(i)
                        found = True
                        break
                if not found:
                    console.print(f"[yellow]Warning: Rule with pattern '{r}' not found[/yellow]")

        if not rule_indices:
            console.print("[red]No valid rules specified[/red]")
            return

        rules_to_apply = [all_rules[i] for i in rule_indices]
        console.print(f"[bold]Applying {len(rules_to_apply)} selected rule(s):[/bold]")
        for i in rule_indices:
            console.print(f"  #{i+1}: {fix_rtl(all_rules[i].pattern)}")
    else:
        rules_to_apply = None  # Apply all
        console.print(f"[bold]Applying {len(all_rules)} rules...[/bold]")

    if dry_run:
        console.print("[yellow](Dry run - no changes will be saved)[/yellow]")

    transaction_ids = [transaction_id] if transaction_id else None

    results = service.apply_rules(
        transaction_ids=transaction_ids,
        only_uncategorized=only_uncategorized,
        dry_run=dry_run,
        rule_indices=rule_indices,
    )

    console.print(f"\nProcessed: {results['processed']} transactions")
    console.print(f"Modified: {results['modified']} transactions")

    if results["details"]:
        console.print("\n[bold]Changes:[/bold]")
        table = Table()
        table.add_column("ID", style="dim", width=6)
        table.add_column("Description", max_width=40)
        table.add_column("Category", style="green")
        table.add_column("Added Tags", style="blue")
        table.add_column("Removed Tags", style="red")
        table.add_column("Matched Rules", style="dim")

        for detail in results["details"][:20]:  # Limit to 20 rows
            table.add_row(
                str(detail["id"]),
                fix_rtl(detail["description"][:40]),
                detail["category"] or "-",
                ", ".join(detail["tags"]) if detail["tags"] else "-",
                ", ".join(detail["remove_tags"]) if detail.get("remove_tags") else "-",
                ", ".join(detail["matched_rules"]),
            )

        console.print(table)

        if len(results["details"]) > 20:
            console.print(f"[dim]... and {len(results['details']) - 20} more[/dim]")

    if dry_run and results["modified"] > 0:
        console.print("\n[yellow]Run without --dry-run to apply changes[/yellow]")


@app.command("init")
def init_rules():
    """Create an empty rules file with format documentation"""
    service = RulesService()

    if RULES_FILE.exists():
        console.print(f"[yellow]Rules file already exists:[/yellow] {RULES_FILE}")
        if not typer.confirm("Overwrite with empty rules file?", default=False):
            return

        # Backup existing file
        backup_path = RULES_FILE.with_suffix(".yaml.bak")
        RULES_FILE.rename(backup_path)
        console.print(f"[dim]Backed up to: {backup_path}[/dim]")

    service.create_default_rules_file()
    console.print(f"[green]Created rules file:[/green] {RULES_FILE}")
    console.print("\nThe file contains format documentation and examples (commented out).")
    console.print("\nAdd rules with:")
    console.print("  [bold]fin rules add \"pango\" -c \"Transportation\" -t \"parking,car\"[/bold]")
    console.print("\nOr edit the file directly:")
    console.print(f"  [bold]fin rules edit[/bold]")


@app.command("test")
def test_rule(
    pattern: str = typer.Argument(..., help="Pattern to test"),
    match_type: str = typer.Option("contains", "--match", "-m", help="Match type"),
    limit: int = typer.Option(10, "--limit", "-l", help="Max transactions to show"),
):
    """Test a pattern against existing transactions"""
    from services.rules_service import Rule
    from db.database import get_db
    from db.models import Transaction

    try:
        match_type_enum = MatchType(match_type)
    except ValueError:
        console.print(f"[red]Error: Invalid match type '{match_type}'[/red]")
        raise typer.Exit(1)

    rule = Rule(pattern=pattern, match_type=match_type_enum)

    session = next(get_db())
    transactions = session.query(Transaction).all()

    matches = []
    for txn in transactions:
        if rule.matches(txn.description):
            matches.append(txn)

    console.print(f"\n[bold]Pattern:[/bold] '{pattern}' ({match_type})")
    console.print(f"[bold]Matches:[/bold] {len(matches)} transactions\n")

    if matches:
        table = Table()
        table.add_column("ID", style="dim", width=6)
        table.add_column("Date", width=12)
        table.add_column("Description")
        table.add_column("Current Category", style="dim")

        for txn in matches[:limit]:
            table.add_row(
                str(txn.id),
                txn.transaction_date.strftime("%Y-%m-%d"),
                fix_rtl(txn.description),
                fix_rtl(txn.effective_category) if txn.effective_category else "-",
            )

        console.print(table)

        if len(matches) > limit:
            console.print(f"[dim]... and {len(matches) - limit} more[/dim]")
    else:
        console.print("[yellow]No matching transactions found[/yellow]")


@app.command("edit")
def edit_rules():
    """Open rules file in default editor"""
    import subprocess
    import os

    if not RULES_FILE.exists():
        console.print(f"[yellow]Rules file doesn't exist. Creating...[/yellow]")
        service = RulesService()
        service.create_default_rules_file()

    editor = os.environ.get("EDITOR", "nano")

    try:
        subprocess.run([editor, str(RULES_FILE)])
    except FileNotFoundError:
        console.print(f"[yellow]Editor '{editor}' not found.[/yellow]")
        console.print(f"Edit manually: {RULES_FILE}")
