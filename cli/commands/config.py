"""
Configuration and credential management commands
"""

import typer
from typing import Optional
from rich import print as rprint
from rich.table import Table
from cli.utils import print_success, print_error, print_info, print_panel, console
from config.settings import (
    load_credentials,
    save_credentials,
    update_credential,
    Credentials,
    CREDENTIALS_FILE,
    CONFIG_DIR,
    get_card_holders,
    set_card_holder,
    remove_card_holder,
)
from services.tag_service import TagService

app = typer.Typer(help="Manage configuration and credentials")


@app.command()
def show(
    show_secrets: bool = typer.Option(
        False,
        "--show-secrets",
        "-s",
        help="Show actual credential values (default: masked)"
    )
):
    """
    Show current configuration (credentials are masked by default)
    """
    try:
        credentials = load_credentials()

        rprint("\n[bold blue]Current Configuration[/bold blue]\n")
        print_info(f"Config directory: {CONFIG_DIR}")
        if CREDENTIALS_FILE.exists():
            print_info(f"Credentials file: {CREDENTIALS_FILE} (encrypted)")
        else:
            print_info("Credentials file: Not created (using environment variables)")

        # Create table for credentials
        table = Table(title="Credentials", show_header=True, header_style="bold magenta")
        table.add_column("Institution", style="cyan", width=15)
        table.add_column("Field", style="green", width=20)
        table.add_column("Value", style="yellow")

        def mask_value(value: Optional[str]) -> str:
            """Mask credential value"""
            if value is None:
                return "[dim]Not set[/dim]"
            if show_secrets:
                return value
            return "•" * min(len(value), 12)

        # Excellence broker
        table.add_row("Excellence", "Username", mask_value(credentials.excellence.username))
        table.add_row("", "Password", mask_value(credentials.excellence.password))

        # Migdal pension
        table.add_row("Migdal", "User ID", mask_value(credentials.migdal.user_id))
        table.add_row("", "Email", mask_value(credentials.migdal.email))

        # Phoenix pension
        table.add_row("Phoenix", "User ID", mask_value(credentials.phoenix.user_id))
        table.add_row("", "Email", mask_value(credentials.phoenix.email))

        # CAL credit card
        table.add_row("CAL", "Username", mask_value(credentials.cal.username))
        table.add_row("", "Password", mask_value(credentials.cal.password))

        # Email (for MFA)
        table.add_row("Email (MFA)", "Address", mask_value(credentials.email.address))
        table.add_row("", "Password", mask_value(credentials.email.password))
        table.add_row("", "IMAP Server", credentials.email.imap_server)

        console.print(table)

        if not show_secrets:
            rprint("\n[dim]Use --show-secrets to reveal actual values[/dim]")

    except Exception as e:
        print_error(f"Failed to load configuration: {e}")
        raise typer.Exit(code=1)


@app.command()
def set(
    key: str = typer.Argument(..., help="Credential key in format 'institution.field' (e.g., 'cal.username')"),
    value: str = typer.Argument(..., help="Credential value"),
):
    """
    Set a specific credential

    Examples:
        fin-cli config set cal.username "myuser"
        fin-cli config set cal.password "mypass"
        fin-cli config set excellence.username "broker_user"
        fin-cli config set email.address "user@gmail.com"
    """
    try:
        # Parse key (format: institution.field)
        parts = key.split(".", 1)
        if len(parts) != 2:
            print_error("Key must be in format 'institution.field' (e.g., 'cal.username')")
            raise typer.Exit(code=1)

        institution, field = parts

        # Valid institutions
        valid_institutions = ["excellence", "migdal", "phoenix", "cal", "email"]
        if institution not in valid_institutions:
            print_error(f"Invalid institution. Must be one of: {', '.join(valid_institutions)}")
            raise typer.Exit(code=1)

        # Update credential
        update_credential(institution, field, value)
        print_success(f"Updated {institution}.{field}")

    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(code=1)
    except Exception as e:
        print_error(f"Failed to update credential: {e}")
        raise typer.Exit(code=1)


@app.command()
def setup():
    """
    Interactive setup wizard for all credentials
    """
    try:
        rprint("\n[bold blue]Credential Setup Wizard[/bold blue]\n")
        print_info("Enter credentials for each institution (press Enter to skip)\n")

        credentials = load_credentials()

        # Excellence broker
        rprint("[bold cyan]Excellence Broker[/bold cyan]")
        username = typer.prompt("Username", default=credentials.excellence.username or "")
        password = typer.prompt("Password", default=credentials.excellence.password or "", hide_input=True)
        credentials.excellence.username = username if username else None
        credentials.excellence.password = password if password else None

        # Migdal pension
        rprint("\n[bold cyan]Migdal Pension[/bold cyan]")
        user_id = typer.prompt("User ID (Israeli ID)", default=credentials.migdal.user_id or "")
        credentials.migdal.user_id = user_id if user_id else None

        # Phoenix pension
        rprint("\n[bold cyan]Phoenix Pension[/bold cyan]")
        user_id = typer.prompt("User ID (Israeli ID)", default=credentials.phoenix.user_id or "")
        credentials.phoenix.user_id = user_id if user_id else None

        # CAL credit card
        rprint("\n[bold cyan]CAL Credit Card[/bold cyan]")
        username = typer.prompt("Username", default=credentials.cal.username or "")
        password = typer.prompt("Password", default=credentials.cal.password or "", hide_input=True)
        credentials.cal.username = username if username else None
        credentials.cal.password = password if password else None

        # Email (for MFA)
        rprint("\n[bold cyan]Email (for MFA)[/bold cyan]")
        email = typer.prompt("Email address", default="")
        password = typer.prompt("App password (Gmail)", default="", hide_input=True)
        credentials.email.address = email if email else None
        credentials.email.password = password if password else None

        # Save credentials
        save_credentials(credentials)

        print_success("\nCredentials saved successfully!")
        print_info(f"Credentials stored encrypted at: {CREDENTIALS_FILE}")

        # Show summary
        summary = f"""
[bold]Configuration Summary:[/bold]

✓ Excellence: {'Configured' if credentials.excellence.username else 'Not set'}
✓ Migdal: {'Configured' if credentials.migdal.user_id else 'Not set'}
✓ Phoenix: {'Configured' if credentials.phoenix.user_id else 'Not set'}
✓ CAL: {'Configured' if credentials.cal.username else 'Not set'}
✓ Email: {'Configured' if credentials.email.address else 'Not set'}

[bold]Next Steps:[/bold]
  • Sync data: [cyan]fin-cli sync --all[/cyan]
  • View config: [cyan]fin-cli config show[/cyan]
"""
        print_panel(summary, title="✓ Setup Complete", style="green")

    except Exception as e:
        print_error(f"Setup failed: {e}")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)


@app.command("card-holder")
def manage_card_holder(
    last4: str = typer.Argument(..., help="Last 4 digits of the card"),
    name: Optional[str] = typer.Argument(None, help="Card holder name (omit to remove)"),
    apply_to_existing: bool = typer.Option(True, "--apply/--no-apply", help="Apply tag to existing transactions"),
):
    """
    Set or remove card holder name for a card

    The card holder name will be used as an automatic tag for all transactions
    from that card, allowing you to filter spending by card holder.

    By default, the tag is also applied to all existing transactions from this card.
    Use --no-apply to only apply to future transactions.

    Examples:
        fin-cli config card-holder 1234 "Or"
        fin-cli config card-holder 5678 "Wife"
        fin-cli config card-holder 1234 "Or" --no-apply
        fin-cli config card-holder 1234  # Remove mapping
    """
    try:
        if len(last4) != 4 or not last4.isdigit():
            print_error("Card must be exactly 4 digits")
            raise typer.Exit(code=1)

        if name:
            set_card_holder(last4, name)
            print_success(f"Card ****{last4} is now tagged as '{name}'")

            # Apply to existing transactions
            if apply_to_existing:
                tag_service = TagService()
                count = tag_service.bulk_tag_by_card(last4, name)
                if count > 0:
                    print_success(f"Tagged {count} existing transactions with '{name}'")
                else:
                    print_info("No existing transactions to tag (all already tagged or no transactions found)")
        else:
            if remove_card_holder(last4):
                print_success(f"Removed card holder mapping for ****{last4}")
                print_info("Note: Existing tags are not removed. Use 'fin-cli tags delete <name>' to remove them.")
            else:
                print_error(f"No card holder mapping found for ****{last4}")
                raise typer.Exit(code=1)

    except typer.Exit:
        raise
    except Exception as e:
        print_error(f"Failed to update card holder: {e}")
        raise typer.Exit(code=1)


@app.command("card-holders")
def list_card_holders():
    """
    List all configured card holders
    """
    try:
        holders = get_card_holders()

        if not holders:
            print_info("No card holders configured")
            print_info("Use 'fin-cli config card-holder <last4> <name>' to add one")
            return

        table = Table(title="Card Holders", show_header=True, header_style="bold cyan")
        table.add_column("Card", width=10)
        table.add_column("Holder Name", width=20)

        for last4, name in sorted(holders.items()):
            table.add_row(f"****{last4}", name)

        console.print(table)

    except Exception as e:
        print_error(f"Failed to list card holders: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()