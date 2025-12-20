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
    CONFIG_DIR
)

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


if __name__ == "__main__":
    app()