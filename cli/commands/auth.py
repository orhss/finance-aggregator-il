"""
Authentication management commands for Streamlit UI

Enable/disable authentication and manage users for secure remote access.
"""

import typer
from rich import print as rprint
from rich.table import Table
from cli.utils import print_success, print_error, print_info, print_panel, console
from config.settings import (
    is_auth_enabled,
    set_auth_enabled,
    add_auth_user,
    remove_auth_user,
    list_auth_users,
    get_auth_users_file,
)

app = typer.Typer(help="Manage authentication for Streamlit UI")


@app.command("status")
def status():
    """
    Show current authentication status
    """
    enabled = is_auth_enabled()
    users = list_auth_users()

    rprint("\n[bold blue]Authentication Status[/bold blue]\n")

    if enabled:
        rprint("[green]Authentication is ENABLED[/green]")
    else:
        rprint("[yellow]Authentication is DISABLED[/yellow]")

    rprint(f"\nUsers file: {get_auth_users_file()}")
    rprint(f"Configured users: {len(users)}")

    if users:
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Username", width=20)
        table.add_column("Display Name", width=30)

        for user in users:
            table.add_row(user["username"], user["name"])

        console.print(table)


@app.command("enable")
def enable():
    """
    Enable authentication for Streamlit UI

    When enabled, users must log in to access the Streamlit app.
    """
    users = list_auth_users()

    if not users:
        print_error("No users configured. Add a user first with:")
        print_info("  fin-cli auth add-user <username>")
        raise typer.Exit(code=1)

    set_auth_enabled(True)
    print_success("Authentication enabled")
    print_info("Users must now log in to access the Streamlit app")


@app.command("disable")
def disable():
    """
    Disable authentication for Streamlit UI

    When disabled, the app is accessible without login.
    """
    set_auth_enabled(False)
    print_success("Authentication disabled")
    print_info("Streamlit app is now accessible without login")


@app.command("add-user")
def add_user_cmd(
    username: str = typer.Argument(..., help="Unique username for login"),
    name: str = typer.Option(None, "--name", "-n", help="Display name (defaults to username)"),
):
    """
    Add a new user for authentication

    Prompts for password interactively.

    Example:
        fin-cli auth add-user admin
        fin-cli auth add-user john --name "John Doe"
    """
    import getpass

    try:
        import bcrypt
    except ImportError:
        print_error("bcrypt is required for password hashing")
        print_info("Install it with: pip install bcrypt")
        raise typer.Exit(code=1)

    # Use username as name if not provided
    if not name:
        name = username

    # Check if user already exists
    existing = list_auth_users()
    if any(u["username"] == username for u in existing):
        print_error(f"User '{username}' already exists")
        raise typer.Exit(code=1)

    # Prompt for password
    rprint(f"\n[bold]Creating user: {username}[/bold]")
    password = getpass.getpass("Enter password: ")
    confirm = getpass.getpass("Confirm password: ")

    if password != confirm:
        print_error("Passwords do not match")
        raise typer.Exit(code=1)

    if len(password) < 4:
        print_error("Password must be at least 4 characters")
        raise typer.Exit(code=1)

    # Hash password with bcrypt
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    # Add user
    success = add_auth_user(username, name, hashed)

    if success:
        print_success(f"User '{username}' created successfully")

        # If auth not enabled and this is the first user, suggest enabling
        if not is_auth_enabled():
            print_info("\nTo enable authentication, run:")
            print_info("  fin-cli auth enable")
    else:
        print_error(f"Failed to create user '{username}'")
        raise typer.Exit(code=1)


@app.command("remove-user")
def remove_user_cmd(
    username: str = typer.Argument(..., help="Username to remove"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """
    Remove a user from authentication

    Example:
        fin-cli auth remove-user john
        fin-cli auth remove-user john --force
    """
    # Check if user exists
    existing = list_auth_users()
    if not any(u["username"] == username for u in existing):
        print_error(f"User '{username}' not found")
        raise typer.Exit(code=1)

    # Confirm removal
    if not force:
        confirm = typer.confirm(f"Remove user '{username}'?")
        if not confirm:
            print_info("Cancelled")
            raise typer.Exit()

    # Remove user
    success = remove_auth_user(username)

    if success:
        print_success(f"User '{username}' removed")

        # Check if any users remain
        remaining = list_auth_users()
        if not remaining and is_auth_enabled():
            print_info("\nNo users remaining. Disabling authentication.")
            set_auth_enabled(False)
    else:
        print_error(f"Failed to remove user '{username}'")
        raise typer.Exit(code=1)


@app.command("list-users")
def list_users_cmd():
    """
    List all configured users
    """
    users = list_auth_users()

    if not users:
        print_info("No users configured")
        print_info("Add a user with: fin-cli auth add-user <username>")
        return

    table = Table(
        title="Configured Users",
        show_header=True,
        header_style="bold cyan"
    )
    table.add_column("Username", width=20)
    table.add_column("Display Name", width=30)

    for user in users:
        table.add_row(user["username"], user["name"])

    console.print(table)
    rprint(f"\n[dim]Total: {len(users)} user(s)[/dim]")


@app.command("change-password")
def change_password_cmd(
    username: str = typer.Argument(..., help="Username to update"),
):
    """
    Change password for an existing user

    Example:
        fin-cli auth change-password admin
    """
    import getpass

    try:
        import bcrypt
    except ImportError:
        print_error("bcrypt is required for password hashing")
        print_info("Install it with: pip install bcrypt")
        raise typer.Exit(code=1)

    # Check if user exists
    existing = list_auth_users()
    user_data = next((u for u in existing if u["username"] == username), None)

    if not user_data:
        print_error(f"User '{username}' not found")
        raise typer.Exit(code=1)

    # Prompt for new password
    rprint(f"\n[bold]Changing password for: {username}[/bold]")
    password = getpass.getpass("Enter new password: ")
    confirm = getpass.getpass("Confirm new password: ")

    if password != confirm:
        print_error("Passwords do not match")
        raise typer.Exit(code=1)

    if len(password) < 4:
        print_error("Password must be at least 4 characters")
        raise typer.Exit(code=1)

    # Hash new password
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    # Remove and re-add user with new password
    remove_auth_user(username)
    add_auth_user(username, user_data["name"], hashed)

    print_success(f"Password updated for '{username}'")


if __name__ == "__main__":
    app()
