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
    CreditCardCredentials,
    PensionCredentials,
    CREDENTIALS_FILE,
    CONFIG_DIR,
    get_card_holders,
    set_card_holder,
    remove_card_holder,
    manage_cc_account,
    manage_pension_account,
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

        # Migdal pension (multiple accounts)
        if credentials.migdal:
            for idx, account in enumerate(credentials.migdal):
                label = f" ({account.label})" if account.label else ""
                table.add_row(f"Migdal [{idx}]{label}", "User ID", mask_value(account.user_id))
                table.add_row("", "Email (MFA)", mask_value(account.email_address) if account.email_address else "[dim]Use global[/dim]")
                table.add_row("", "Email Password", mask_value(account.email_password) if account.email_password else "[dim]Use global[/dim]")
                if idx < len(credentials.migdal) - 1:  # Add separator between accounts
                    table.add_row("", "", "")
        else:
            table.add_row("Migdal", "User ID", "[dim]Not configured[/dim]")

        # Phoenix pension (multiple accounts)
        if credentials.phoenix:
            for idx, account in enumerate(credentials.phoenix):
                label = f" ({account.label})" if account.label else ""
                table.add_row(f"Phoenix [{idx}]{label}", "User ID", mask_value(account.user_id))
                table.add_row("", "Email (MFA)", mask_value(account.email_address) if account.email_address else "[dim]Use global[/dim]")
                table.add_row("", "Email Password", mask_value(account.email_password) if account.email_password else "[dim]Use global[/dim]")
                if idx < len(credentials.phoenix) - 1:  # Add separator between accounts
                    table.add_row("", "", "")
        else:
            table.add_row("Phoenix", "User ID", "[dim]Not configured[/dim]")

        # CAL credit cards (multiple accounts)
        if credentials.cal:
            for idx, account in enumerate(credentials.cal):
                label = f" ({account.label})" if account.label else ""
                table.add_row(f"CAL [{idx}]{label}", "Username", mask_value(account.username))
                table.add_row("", "Password", mask_value(account.password))
                if idx < len(credentials.cal) - 1:  # Add separator between accounts
                    table.add_row("", "", "")
        else:
            table.add_row("CAL", "Username", "[dim]Not configured[/dim]")
            table.add_row("", "Password", "[dim]Not configured[/dim]")

        # Max credit cards (multiple accounts)
        if credentials.max:
            for idx, account in enumerate(credentials.max):
                label = f" ({account.label})" if account.label else ""
                table.add_row(f"Max [{idx}]{label}", "Username", mask_value(account.username))
                table.add_row("", "Password", mask_value(account.password))
                if idx < len(credentials.max) - 1:  # Add separator between accounts
                    table.add_row("", "", "")
        else:
            table.add_row("Max", "Username", "[dim]Not configured[/dim]")
            table.add_row("", "Password", "[dim]Not configured[/dim]")

        # Isracard credit cards (multiple accounts)
        if credentials.isracard:
            for idx, account in enumerate(credentials.isracard):
                label = f" ({account.label})" if account.label else ""
                table.add_row(f"Isracard [{idx}]{label}", "Username (ID:Card6)", mask_value(account.username))
                table.add_row("", "Password", mask_value(account.password))
                if idx < len(credentials.isracard) - 1:  # Add separator between accounts
                    table.add_row("", "", "")
        else:
            table.add_row("Isracard", "Username (ID:Card6)", "[dim]Not configured[/dim]")
            table.add_row("", "Password", "[dim]Not configured[/dim]")

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
    value: str = typer.Argument(None, help="Credential value (omit for interactive prompt)"),
    prompt: bool = typer.Option(False, "--prompt", "-p", help="Prompt for value interactively (useful for passwords with special characters)"),
):
    """
    Set a specific credential

    Examples:
        fin-cli config set cal.username "myuser"
        fin-cli config set cal.password "mypass"
        fin-cli config set excellence.username "broker_user"
        fin-cli config set email.address "user@gmail.com"

        # Interactive prompt (avoids shell escaping issues with special characters):
        fin-cli config set excellence.password --prompt
        fin-cli config set excellence.password -p
    """
    import getpass

    try:
        # Parse key (format: institution.field)
        parts = key.split(".", 1)
        if len(parts) != 2:
            print_error("Key must be in format 'institution.field' (e.g., 'cal.username')")
            raise typer.Exit(code=1)

        institution, field = parts

        # Valid institutions
        valid_institutions = ["excellence", "migdal", "phoenix", "cal", "max", "email", "meitav", "isracard"]
        if institution not in valid_institutions:
            print_error(f"Invalid institution. Must be one of: {', '.join(valid_institutions)}")
            raise typer.Exit(code=1)

        # Get value interactively if --prompt flag or no value provided
        if prompt or value is None:
            if field == "password":
                value = getpass.getpass(f"Enter {institution}.{field}: ")
            else:
                value = input(f"Enter {institution}.{field}: ")

            if not value:
                print_error("Value cannot be empty")
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
        print_info("Enter credentials for each institution (press Enter to keep current value)\n")

        credentials = load_credentials()

        # Helper to handle optional prompts - only update if user provides a value
        def prompt_optional(prompt_text: str, current_value: Optional[str], hide_input: bool = False) -> Optional[str]:
            """Prompt for optional value, returning None to keep current value unchanged"""
            if current_value:
                default_display = "****" if hide_input else current_value
                prompt_text = f"{prompt_text} [current: {default_display}]"
            else:
                prompt_text = f"{prompt_text} [not set]"

            value = typer.prompt(prompt_text, default="", hide_input=hide_input, show_default=False)
            # Empty string means keep current value
            if value == "":
                return current_value
            return value

        # Excellence broker
        rprint("[bold cyan]Excellence Broker[/bold cyan]")
        credentials.excellence.username = prompt_optional("Username", credentials.excellence.username)
        credentials.excellence.password = prompt_optional("Password", credentials.excellence.password, hide_input=True)

        # Migdal pension (multi-account)
        rprint("\n[bold cyan]Migdal Pension[/bold cyan]")
        if credentials.migdal:
            print_info(f"Currently {len(credentials.migdal)} account(s) configured")
            print_info("Use 'fin-cli config add-account migdal' to manage accounts")
        else:
            print_info("No accounts configured. Add one now? (or use 'fin-cli config add-account migdal')")
            if typer.confirm("Add Migdal account"):
                user_id = typer.prompt("User ID (Israeli ID)")
                label = typer.prompt("Label (optional)", default="") or None
                credentials.migdal.append(PensionCredentials(user_id=user_id, label=label))

        # Phoenix pension (multi-account)
        rprint("\n[bold cyan]Phoenix Pension[/bold cyan]")
        if credentials.phoenix:
            print_info(f"Currently {len(credentials.phoenix)} account(s) configured")
            print_info("Use 'fin-cli config add-account phoenix' to manage accounts")
        else:
            print_info("No accounts configured. Add one now? (or use 'fin-cli config add-account phoenix')")
            if typer.confirm("Add Phoenix account"):
                user_id = typer.prompt("User ID (Israeli ID)")
                label = typer.prompt("Label (optional)", default="") or None
                credentials.phoenix.append(PensionCredentials(user_id=user_id, label=label))

        # CAL credit card (multi-account)
        rprint("\n[bold cyan]CAL Credit Card[/bold cyan]")
        if credentials.cal:
            print_info(f"Currently {len(credentials.cal)} account(s) configured")
            print_info("Use 'fin-cli config add-account cal' to manage accounts")
        else:
            print_info("No accounts configured. Add one now? (or use 'fin-cli config add-account cal')")
            if typer.confirm("Add CAL account"):
                username = typer.prompt("Username")
                password = typer.prompt("Password", hide_input=True)
                label = typer.prompt("Label (optional)", default="") or None
                credentials.cal.append(CreditCardCredentials(username=username, password=password, label=label))

        # Max credit card (multi-account)
        rprint("\n[bold cyan]Max Credit Card[/bold cyan]")
        if credentials.max:
            print_info(f"Currently {len(credentials.max)} account(s) configured")
            print_info("Use 'fin-cli config add-account max' to manage accounts")
        else:
            print_info("No accounts configured. Add one now? (or use 'fin-cli config add-account max')")
            if typer.confirm("Add Max account"):
                username = typer.prompt("Username")
                password = typer.prompt("Password", hide_input=True)
                label = typer.prompt("Label (optional)", default="") or None
                credentials.max.append(CreditCardCredentials(username=username, password=password, label=label))

        # Isracard credit card (multi-account)
        rprint("\n[bold cyan]Isracard Credit Card[/bold cyan]")
        if credentials.isracard:
            print_info(f"Currently {len(credentials.isracard)} account(s) configured")
            print_info("Use 'fin-cli config add-account isracard' to manage accounts")
        else:
            print_info("No accounts configured. Add one now? (or use 'fin-cli config add-account isracard')")
            if typer.confirm("Add Isracard account"):
                print_info("Username format: 'user_id:card_6_digits' (e.g., '123456789:123456')")
                username = typer.prompt("Username (ID:Card6)")
                password = typer.prompt("Password", hide_input=True)
                label = typer.prompt("Label (optional)", default="") or None
                credentials.isracard.append(CreditCardCredentials(username=username, password=password, label=label))

        # Email (for MFA)
        rprint("\n[bold cyan]Email (for MFA)[/bold cyan]")
        credentials.email.address = prompt_optional("Email address", credentials.email.address)
        credentials.email.password = prompt_optional("App password (Gmail)", credentials.email.password, hide_input=True)

        # Save credentials
        save_credentials(credentials)

        print_success("\nCredentials saved successfully!")
        print_info(f"Credentials stored encrypted at: {CREDENTIALS_FILE}")

        # Show summary
        migdal_status = f"{len(credentials.migdal)} account(s)" if credentials.migdal else "Not set"
        phoenix_status = f"{len(credentials.phoenix)} account(s)" if credentials.phoenix else "Not set"
        cal_status = f"{len(credentials.cal)} account(s)" if credentials.cal else "Not set"
        max_status = f"{len(credentials.max)} account(s)" if credentials.max else "Not set"
        isracard_status = f"{len(credentials.isracard)} account(s)" if credentials.isracard else "Not set"

        summary = f"""
[bold]Configuration Summary:[/bold]

✓ Excellence: {'Configured' if credentials.excellence.username else 'Not set'}
✓ Migdal: {migdal_status}
✓ Phoenix: {phoenix_status}
✓ CAL: {cal_status}
✓ Max: {max_status}
✓ Isracard: {isracard_status}
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


@app.command("unmapped-cards")
def list_unmapped_cards():
    """
    List cards that have transactions but no card holder assigned

    This helps you identify newly added cards that need to be tagged.
    Use 'fin-cli config card-holder <last4> <name>' to assign them.
    """
    try:
        from services.analytics_service import AnalyticsService

        analytics = AnalyticsService()
        unmapped = analytics.get_unmapped_cards()
        analytics.close()

        if not unmapped:
            print_info("All cards with transactions have been assigned card holders!")
            return

        table = Table(
            title="Cards Without Holder Assignment",
            show_header=True,
            header_style="bold yellow"
        )
        table.add_column("Card", width=10)
        table.add_column("Transactions", justify="right", width=12)
        table.add_column("Total Amount", justify="right", width=15)
        table.add_column("Latest Transaction", width=16)

        for card in unmapped:
            table.add_row(
                f"****{card['last4']}",
                str(card['transaction_count']),
                f"₪{card['total_amount']:,.0f}",
                card['latest_transaction_date'].strftime("%Y-%m-%d") if card['latest_transaction_date'] else "N/A"
            )

        console.print(table)
        console.print(f"\n[dim]Found {len(unmapped)} unmapped card(s)[/dim]")
        console.print("[dim]Use 'fin-cli config card-holder <last4> <name>' to assign a card holder[/dim]")

    except Exception as e:
        print_error(f"Failed to list unmapped cards: {e}")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)


# Multi-Account Credit Card Commands

@app.command("list-accounts")
def list_accounts(
    institution: str = typer.Argument(..., help="Institution: cal, max, isracard, migdal, phoenix")
):
    """List all configured accounts for an institution"""
    try:
        # Determine institution type
        if institution in ['cal', 'max', 'isracard']:
            success, accounts = manage_cc_account(institution, 'list')
            field_name = "Username"
            field_getter = lambda acc: acc.username
        elif institution in ['migdal', 'phoenix']:
            success, accounts = manage_pension_account(institution, 'list')
            field_name = "User ID"
            field_getter = lambda acc: acc.user_id
        else:
            raise ValueError(f"Invalid institution: {institution}")

        if not accounts:
            print_info(f"No {institution.upper()} accounts configured")
            print_info(f"Use 'fin-cli config add-account {institution}' to add one")
            return

        # Display table
        table = Table(title=f"{institution.upper()} Accounts", show_header=True, header_style="bold cyan")
        table.add_column("Index", width=8)
        table.add_column(field_name, width=20)
        table.add_column("Label", width=20)

        for idx, account in enumerate(accounts):
            field_value = field_getter(account)
            masked = field_value[:4] + "****" if len(field_value) > 4 else "****"
            label = account.label or "[dim]No label[/dim]"
            table.add_row(str(idx), masked, label)

        console.print(table)

    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(code=1)


@app.command("add-account")
def add_account(
    institution: str = typer.Argument(..., help="Institution: cal, max, isracard, migdal, phoenix"),
    username: Optional[str] = typer.Option(None, "--username", "-u", help="Username (for CAL/Max)"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Password (for credit cards)"),
    user_id: Optional[str] = typer.Option(None, "--user-id", help="User ID (for Isracard/pensions)"),
    card_6_digits: Optional[str] = typer.Option(None, "--card-6-digits", help="Last 6 digits of card (for Isracard)"),
    label: Optional[str] = typer.Option(None, "--label", "-l"),
    email_address: Optional[str] = typer.Option(None, "--email-address", help="Email for MFA (for pensions)"),
    email_password: Optional[str] = typer.Option(None, "--email-password", help="Email password (for pensions)"),
):
    """Add a new account for an institution

    Examples:
        fin-cli config add-account migdal --user-id 123456789 --label work \\
            --email-address work@gmail.com --email-password app_password
        fin-cli config add-account isracard --user-id 123456789 --card-6-digits 123456 --password mypass --label personal
        fin-cli config add-account cal --username myuser --password mypass --label personal
    """
    try:
        # Credit cards - Isracard (special handling)
        if institution == 'isracard':
            # Prompt for user_id and card_6_digits separately
            if not user_id:
                user_id = typer.prompt("Israeli ID number")
            if not card_6_digits:
                card_6_digits = typer.prompt("Last 6 digits of card")
            if not password:
                password = typer.prompt("Password", hide_input=True)
            if not label:
                label = typer.prompt("Label (optional, press Enter to skip)", default="") or None

            # Validate card_6_digits
            if not card_6_digits.isdigit() or len(card_6_digits) != 6:
                print_error("Card digits must be exactly 6 numeric digits")
                raise typer.Exit(code=1)

            # Combine user_id:card_6_digits into username field
            combined_username = f"{user_id}:{card_6_digits}"
            manage_cc_account(institution, 'add', username=combined_username, password=password, label=label)

        # Credit cards - CAL/Max
        elif institution in ['cal', 'max']:
            if not username:
                username = typer.prompt(f"{institution.upper()} username")
            if not password:
                password = typer.prompt(f"{institution.upper()} password", hide_input=True)
            if not label:
                label = typer.prompt("Label (optional, press Enter to skip)", default="") or None

            manage_cc_account(institution, 'add', username=username, password=password, label=label)

        # Pensions
        elif institution in ['migdal', 'phoenix']:
            if not user_id:
                user_id = typer.prompt(f"{institution.upper()} user ID")
            if not label:
                label = typer.prompt("Label (optional, press Enter to skip)", default="") or None
            if not email_address:
                email_address = typer.prompt("Email for MFA (optional, press Enter to skip)", default="") or None
            if email_address and not email_password:
                email_password = typer.prompt("Email password", hide_input=True)

            manage_pension_account(
                institution, 'add',
                user_id=user_id,
                label=label,
                email_address=email_address,
                email_password=email_password
            )

        else:
            raise ValueError(f"Invalid institution: {institution}")

        label_str = f" ({label})" if label else ""
        print_success(f"Added {institution.upper()} account{label_str}")

        # If pension account without email, remind about global fallback
        if institution in ['migdal', 'phoenix'] and not email_address:
            print_info("No per-account email set - will use global email credentials as fallback")

    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(code=1)


@app.command("remove-account")
def remove_account(
    institution: str = typer.Argument(..., help="Institution: cal, max, isracard, migdal, phoenix"),
    identifier: str = typer.Argument(..., help="Account index or label"),
):
    """Remove an account by index or label"""
    try:
        # Route to appropriate function
        if institution in ['cal', 'max', 'isracard']:
            success, _ = manage_cc_account(institution, 'remove', identifier=identifier)
        elif institution in ['migdal', 'phoenix']:
            success, _ = manage_pension_account(institution, 'remove', identifier=identifier)
        else:
            raise ValueError(f"Invalid institution: {institution}")

        if success:
            print_success(f"Removed {institution.upper()} account: {identifier}")
        else:
            print_error(f"Account not found: {identifier}")
            raise typer.Exit(code=1)

    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(code=1)


@app.command("update-account")
def update_account(
    institution: str = typer.Argument(..., help="Institution: cal, max, isracard, migdal, phoenix"),
    identifier: str = typer.Argument(..., help="Account index or label"),
    username: Optional[str] = typer.Option(None, "--username", "-u", help="New username (CAL/Max only)"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="New password (credit cards only)"),
    user_id: Optional[str] = typer.Option(None, "--user-id", help="New user ID (Isracard/pensions only)"),
    card_6_digits: Optional[str] = typer.Option(None, "--card-6-digits", help="New last 6 digits (Isracard only)"),
    label: Optional[str] = typer.Option(None, "--label", "-l", help="New label"),
    email_address: Optional[str] = typer.Option(None, "--email-address", help="Email for MFA (pensions only)"),
    email_password: Optional[str] = typer.Option(None, "--email-password", help="Email password (pensions only)"),
):
    """Update account credentials or label

    Examples:
        fin-cli config update-account migdal 0 --email-address personal@gmail.com
        fin-cli config update-account phoenix work --email-password new_app_password
        fin-cli config update-account isracard 0 --password new_password
        fin-cli config update-account isracard 0 --user-id 987654321 --card-6-digits 654321
    """
    try:
        # Credit cards - Isracard (special handling)
        if institution == 'isracard':
            if not any([user_id, card_6_digits, password, label]):
                print_error("At least one of --user-id, --card-6-digits, --password, or --label must be provided")
                raise typer.Exit(code=1)

            # If updating user_id or card_6_digits, we need to rebuild the combined username
            if user_id or card_6_digits:
                # Load existing account to get current values
                _, accounts = manage_cc_account(institution, 'list')
                idx = None
                try:
                    idx = int(identifier)
                except ValueError:
                    # Try as label
                    for i, acc in enumerate(accounts):
                        if acc.label == identifier:
                            idx = i
                            break

                if idx is None or idx >= len(accounts):
                    print_error(f"Account not found: {identifier}")
                    raise typer.Exit(code=1)

                current_account = accounts[idx]

                # Parse current username (format: "user_id:card_6_digits")
                current_user_id, current_card_6_digits = current_account.username.split(':', 1)

                # Use new values if provided, otherwise keep current
                new_user_id = user_id if user_id else current_user_id
                new_card_6_digits = card_6_digits if card_6_digits else current_card_6_digits

                # Validate card_6_digits if changed
                if card_6_digits and (not card_6_digits.isdigit() or len(card_6_digits) != 6):
                    print_error("Card digits must be exactly 6 numeric digits")
                    raise typer.Exit(code=1)

                # Combine into new username
                combined_username = f"{new_user_id}:{new_card_6_digits}"
            else:
                combined_username = None

            success, _ = manage_cc_account(
                institution, 'update',
                identifier=identifier,
                username=combined_username,
                password=password,
                label=label
            )

        # Credit cards - CAL/Max
        elif institution in ['cal', 'max']:
            if not any([username, password, label]):
                print_error("At least one of --username, --password, or --label must be provided")
                raise typer.Exit(code=1)

            success, _ = manage_cc_account(
                institution, 'update',
                identifier=identifier,
                username=username,
                password=password,
                label=label
            )

        # Pensions
        elif institution in ['migdal', 'phoenix']:
            if not any([user_id, label, email_address, email_password]):
                print_error("At least one of --user-id, --label, --email-address, or --email-password must be provided")
                raise typer.Exit(code=1)

            success, _ = manage_pension_account(
                institution, 'update',
                identifier=identifier,
                user_id=user_id,
                label=label,
                email_address=email_address,
                email_password=email_password
            )

        else:
            raise ValueError(f"Invalid institution: {institution}")

        if success:
            print_success(f"Updated {institution.upper()} account: {identifier}")
        else:
            print_error(f"Account not found: {identifier}")
            raise typer.Exit(code=1)

    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()