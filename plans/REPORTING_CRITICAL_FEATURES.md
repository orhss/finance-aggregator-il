# Critical Reporting Features Implementation Plan

## Overview

This document outlines the implementation plan for the **4 critical missing reporting features** identified by comparing against industry leaders (Mint, YNAB, Personal Capital/Empower).

**Critical Features:**
1. Budget Tracking
2. Net Worth Tracking Over Time
3. Recurring Transaction Detection
4. Goal Setting & Tracking

**Timeline Estimate:** 2-3 weeks for all 4 features
**Complexity:** Medium (leverages existing infrastructure)

---

## Feature 1: Budget Tracking

### Overview

Enable users to set monthly budgets per tag/category and track actual spending against budgets with alerts when approaching or exceeding limits.

### User Stories

- As a user, I want to set a monthly budget for "groceries" so I can control food spending
- As a user, I want to see how much of my budget I've used so I know when to slow down
- As a user, I want to be alerted when I exceed my budget so I can adjust behavior
- As a user, I want to see all my budgets in one view to manage my finances

### Database Schema

**New Table: `budgets`**

```sql
CREATE TABLE budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_name TEXT NOT NULL,              -- Tag to budget (e.g., "groceries", "dining")
    monthly_limit REAL NOT NULL,         -- Budget amount (e.g., 2000.00)
    month INTEGER NOT NULL,              -- Month (1-12)
    year INTEGER NOT NULL,               -- Year (e.g., 2025)
    rollover_enabled BOOLEAN DEFAULT 0,  -- If unused budget carries over
    notes TEXT,                          -- Optional notes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tag_name, month, year)
);

-- Index for fast lookups
CREATE INDEX idx_budgets_period ON budgets(year, month);
CREATE INDEX idx_budgets_tag ON budgets(tag_name);
```

**Database Model (SQLAlchemy):**

```python
# In db/models.py

class Budget(Base):
    __tablename__ = 'budgets'

    id = Column(Integer, primary_key=True)
    tag_name = Column(String, nullable=False)
    monthly_limit = Column(Float, nullable=False)
    month = Column(Integer, nullable=False)  # 1-12
    year = Column(Integer, nullable=False)
    rollover_enabled = Column(Boolean, default=False)
    notes = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('tag_name', 'month', 'year', name='uix_budget_period'),
    )

    def __repr__(self):
        return f"<Budget(tag={self.tag_name}, limit={self.monthly_limit}, period={self.month}/{self.year})>"
```

### Service Layer

**New Service: `services/budget_service.py`**

```python
"""
Budget service for managing and tracking budgets
"""

from datetime import date
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from db.models import Budget, Transaction, TransactionTag, Tag
from db.database import get_db


class BudgetService:
    """Service for budget management and tracking"""

    def __init__(self, session: Optional[Session] = None):
        self.session = session or next(get_db())

    def create_budget(
        self,
        tag_name: str,
        monthly_limit: float,
        month: int,
        year: int,
        rollover_enabled: bool = False,
        notes: Optional[str] = None
    ) -> Budget:
        """
        Create a new budget for a tag

        Args:
            tag_name: Tag to budget
            monthly_limit: Budget amount
            month: Month (1-12)
            year: Year
            rollover_enabled: If unused budget carries over
            notes: Optional notes

        Returns:
            Created Budget object

        Raises:
            ValueError: If budget already exists or invalid input
        """
        # Validate month
        if month < 1 or month > 12:
            raise ValueError("Month must be between 1 and 12")

        # Validate limit
        if monthly_limit <= 0:
            raise ValueError("Budget limit must be positive")

        # Check if budget already exists
        existing = self.session.query(Budget).filter(
            and_(
                Budget.tag_name == tag_name,
                Budget.month == month,
                Budget.year == year
            )
        ).first()

        if existing:
            raise ValueError(f"Budget already exists for {tag_name} in {month}/{year}")

        # Create budget
        budget = Budget(
            tag_name=tag_name,
            monthly_limit=monthly_limit,
            month=month,
            year=year,
            rollover_enabled=rollover_enabled,
            notes=notes
        )

        self.session.add(budget)
        self.session.commit()

        return budget

    def update_budget(
        self,
        budget_id: int,
        monthly_limit: Optional[float] = None,
        rollover_enabled: Optional[bool] = None,
        notes: Optional[str] = None
    ) -> Budget:
        """Update an existing budget"""
        budget = self.session.query(Budget).filter(Budget.id == budget_id).first()

        if not budget:
            raise ValueError(f"Budget with ID {budget_id} not found")

        if monthly_limit is not None:
            if monthly_limit <= 0:
                raise ValueError("Budget limit must be positive")
            budget.monthly_limit = monthly_limit

        if rollover_enabled is not None:
            budget.rollover_enabled = rollover_enabled

        if notes is not None:
            budget.notes = notes

        self.session.commit()
        return budget

    def delete_budget(self, budget_id: int) -> bool:
        """Delete a budget"""
        budget = self.session.query(Budget).filter(Budget.id == budget_id).first()

        if not budget:
            return False

        self.session.delete(budget)
        self.session.commit()
        return True

    def get_budget(self, tag_name: str, month: int, year: int) -> Optional[Budget]:
        """Get budget for a specific tag and period"""
        return self.session.query(Budget).filter(
            and_(
                Budget.tag_name == tag_name,
                Budget.month == month,
                Budget.year == year
            )
        ).first()

    def get_budgets_for_month(self, month: int, year: int) -> List[Budget]:
        """Get all budgets for a specific month"""
        return self.session.query(Budget).filter(
            and_(Budget.month == month, Budget.year == year)
        ).order_by(Budget.tag_name).all()

    def get_all_budgets(self) -> List[Budget]:
        """Get all budgets"""
        return self.session.query(Budget).order_by(
            Budget.year.desc(),
            Budget.month.desc(),
            Budget.tag_name
        ).all()

    def get_budget_status(self, month: int, year: int) -> List[Dict[str, Any]]:
        """
        Get budget status with actual spending for a month

        Returns:
            List of dicts with budget info and actual spending
        """
        budgets = self.get_budgets_for_month(month, year)

        if not budgets:
            return []

        result = []

        for budget in budgets:
            # Calculate actual spending for this tag
            actual = self._get_actual_spending(budget.tag_name, month, year)

            remaining = budget.monthly_limit - actual
            percentage = (actual / budget.monthly_limit * 100) if budget.monthly_limit > 0 else 0

            # Determine status
            if percentage >= 100:
                status = "over"
            elif percentage >= 80:
                status = "warning"
            else:
                status = "ok"

            result.append({
                'budget_id': budget.id,
                'tag_name': budget.tag_name,
                'monthly_limit': budget.monthly_limit,
                'actual_spending': actual,
                'remaining': remaining,
                'percentage_used': percentage,
                'status': status,
                'month': month,
                'year': year,
                'notes': budget.notes
            })

        return result

    def _get_actual_spending(self, tag_name: str, month: int, year: int) -> float:
        """Calculate actual spending for a tag in a specific month"""
        from sqlalchemy import func, extract
        from services.analytics_service import effective_amount_expr

        # Get transactions for this tag in this month
        query = self.session.query(
            func.sum(effective_amount_expr()).label('total')
        ).select_from(Transaction).join(
            TransactionTag, Transaction.id == TransactionTag.transaction_id
        ).join(
            Tag, TransactionTag.tag_id == Tag.id
        ).filter(
            and_(
                Tag.name == tag_name,
                extract('month', Transaction.transaction_date) == month,
                extract('year', Transaction.transaction_date) == year,
                Transaction.original_amount < 0  # Only expenses (negative amounts)
            )
        )

        result = query.scalar()
        return abs(result) if result else 0.0

    def copy_budgets_to_next_month(self, from_month: int, from_year: int) -> int:
        """
        Copy budgets from one month to the next month

        Returns:
            Number of budgets copied
        """
        # Calculate next month/year
        if from_month == 12:
            to_month = 1
            to_year = from_year + 1
        else:
            to_month = from_month + 1
            to_year = from_year

        # Get source budgets
        source_budgets = self.get_budgets_for_month(from_month, from_year)

        count = 0
        for budget in source_budgets:
            # Check if already exists
            existing = self.get_budget(budget.tag_name, to_month, to_year)
            if existing:
                continue

            # Create new budget
            self.create_budget(
                tag_name=budget.tag_name,
                monthly_limit=budget.monthly_limit,
                month=to_month,
                year=to_year,
                rollover_enabled=budget.rollover_enabled,
                notes=budget.notes
            )
            count += 1

        return count

    def close(self):
        """Close database session"""
        if self.session:
            self.session.close()
```

### CLI Commands

**New Commands: `cli/commands/budgets.py`**

```python
"""
Budget management CLI commands
"""

import typer
from datetime import date
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from typing import Optional

from services.budget_service import BudgetService
from cli.utils import fix_rtl

app = typer.Typer(help="Manage budgets")
console = Console()


@app.command("list")
def list_budgets(
    month: Optional[int] = typer.Option(None, "--month", "-m", help="Month (1-12)"),
    year: Optional[int] = typer.Option(None, "--year", "-y", help="Year"),
    all: bool = typer.Option(False, "--all", "-a", help="Show all budgets")
):
    """
    List budgets

    Examples:
        fin-cli budgets list                  # Current month
        fin-cli budgets list --month 12       # December (current year)
        fin-cli budgets list -m 12 -y 2024    # December 2024
        fin-cli budgets list --all            # All budgets
    """
    try:
        service = BudgetService()

        if all:
            budgets = service.get_all_budgets()

            if not budgets:
                console.print("[yellow]No budgets found[/yellow]")
                return

            # Group by period
            table = Table(title="All Budgets", show_header=True, header_style="bold cyan", box=box.ROUNDED)
            table.add_column("Period", width=12)
            table.add_column("Tag", width=20)
            table.add_column("Limit", justify="right", width=15)
            table.add_column("Rollover", width=10)

            for budget in budgets:
                period = f"{budget.month:02d}/{budget.year}"
                rollover = "✓" if budget.rollover_enabled else ""

                table.add_row(
                    period,
                    fix_rtl(budget.tag_name),
                    f"₪{budget.monthly_limit:,.2f}",
                    rollover
                )

            console.print(table)
            console.print(f"\n[dim]Total: {len(budgets)} budgets[/dim]")

        else:
            # Use current month if not specified
            today = date.today()
            month = month or today.month
            year = year or today.year

            budgets = service.get_budgets_for_month(month, year)

            if not budgets:
                console.print(f"[yellow]No budgets found for {month:02d}/{year}[/yellow]")
                console.print("[dim]Use 'fin-cli budgets create' to create a budget[/dim]")
                return

            # Create table
            month_name = date(year, month, 1).strftime("%B %Y")
            table = Table(title=f"Budgets - {month_name}", show_header=True, header_style="bold cyan", box=box.ROUNDED)
            table.add_column("ID", style="dim", width=6)
            table.add_column("Tag", width=20)
            table.add_column("Limit", justify="right", width=15)
            table.add_column("Rollover", width=10)

            for budget in budgets:
                rollover = "✓" if budget.rollover_enabled else ""

                table.add_row(
                    str(budget.id),
                    fix_rtl(budget.tag_name),
                    f"₪{budget.monthly_limit:,.2f}",
                    rollover
                )

            console.print(table)

        service.close()

    except Exception as e:
        console.print(f"[red]Error listing budgets: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("create")
def create_budget(
    tag: str = typer.Argument(..., help="Tag name to budget"),
    limit: float = typer.Argument(..., help="Monthly budget limit"),
    month: Optional[int] = typer.Option(None, "--month", "-m", help="Month (default: current)"),
    year: Optional[int] = typer.Option(None, "--year", "-y", help="Year (default: current)"),
    rollover: bool = typer.Option(False, "--rollover", help="Enable rollover"),
    notes: Optional[str] = typer.Option(None, "--notes", "-n", help="Notes")
):
    """
    Create a new budget

    Examples:
        fin-cli budgets create groceries 2000           # ₪2000/month for groceries
        fin-cli budgets create dining 1500 --month 12   # December budget
        fin-cli budgets create gas 800 --rollover       # With rollover enabled
    """
    try:
        # Use current month if not specified
        today = date.today()
        month = month or today.month
        year = year or today.year

        service = BudgetService()
        budget = service.create_budget(
            tag_name=tag,
            monthly_limit=limit,
            month=month,
            year=year,
            rollover_enabled=rollover,
            notes=notes
        )

        month_name = date(year, month, 1).strftime("%B %Y")
        console.print(f"[green]✓[/green] Budget created for '{fix_rtl(tag)}' in {month_name}")
        console.print(f"  Limit: ₪{limit:,.2f}/month")
        if rollover:
            console.print(f"  Rollover: Enabled")

        service.close()

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error creating budget: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("update")
def update_budget(
    budget_id: int = typer.Argument(..., help="Budget ID"),
    limit: Optional[float] = typer.Option(None, "--limit", "-l", help="New budget limit"),
    rollover: Optional[bool] = typer.Option(None, "--rollover/--no-rollover", help="Enable/disable rollover"),
    notes: Optional[str] = typer.Option(None, "--notes", "-n", help="Update notes")
):
    """
    Update an existing budget

    Examples:
        fin-cli budgets update 5 --limit 2500      # Update limit
        fin-cli budgets update 5 --rollover        # Enable rollover
        fin-cli budgets update 5 --notes "Reduced for Q1"
    """
    try:
        if limit is None and rollover is None and notes is None:
            console.print("[red]Error: At least one of --limit, --rollover, or --notes must be provided[/red]")
            raise typer.Exit(code=1)

        service = BudgetService()
        budget = service.update_budget(
            budget_id=budget_id,
            monthly_limit=limit,
            rollover_enabled=rollover,
            notes=notes
        )

        console.print(f"[green]✓[/green] Budget updated for '{fix_rtl(budget.tag_name)}'")
        if limit:
            console.print(f"  New limit: ₪{limit:,.2f}/month")
        if rollover is not None:
            console.print(f"  Rollover: {'Enabled' if rollover else 'Disabled'}")

        service.close()

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error updating budget: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("delete")
def delete_budget(
    budget_id: int = typer.Argument(..., help="Budget ID to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation")
):
    """
    Delete a budget

    Example:
        fin-cli budgets delete 5
        fin-cli budgets delete 5 --yes   # Skip confirmation
    """
    try:
        service = BudgetService()

        # Get budget details for confirmation
        budget = service.session.query(service.session.query(Budget).filter(Budget.id == budget_id).first()

        if not budget:
            console.print(f"[red]Budget with ID {budget_id} not found[/red]")
            raise typer.Exit(code=1)

        if not yes:
            console.print(f"Delete budget for '{fix_rtl(budget.tag_name)}' ({budget.month}/{budget.year})?")
            confirm = typer.confirm("Are you sure?")
            if not confirm:
                console.print("Cancelled")
                return

        success = service.delete_budget(budget_id)

        if success:
            console.print(f"[green]✓[/green] Budget deleted")
        else:
            console.print(f"[red]Failed to delete budget[/red]")

        service.close()

    except Exception as e:
        console.print(f"[red]Error deleting budget: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("status")
def budget_status(
    month: Optional[int] = typer.Option(None, "--month", "-m", help="Month (default: current)"),
    year: Optional[int] = typer.Option(None, "--year", "-y", help="Year (default: current)")
):
    """
    Show budget status with actual spending

    Example:
        fin-cli budgets status              # Current month
        fin-cli budgets status --month 12   # December
    """
    try:
        # Use current month if not specified
        today = date.today()
        month = month or today.month
        year = year or today.year

        service = BudgetService()
        status_data = service.get_budget_status(month, year)

        if not status_data:
            month_name = date(year, month, 1).strftime("%B %Y")
            console.print(f"[yellow]No budgets found for {month_name}[/yellow]")
            console.print("[dim]Use 'fin-cli budgets create' to create a budget[/dim]")
            return

        # Create table
        month_name = date(year, month, 1).strftime("%B %Y")
        table = Table(
            title=f"Budget Status - {month_name}",
            show_header=True,
            header_style="bold cyan",
            box=box.ROUNDED
        )
        table.add_column("Tag", width=20)
        table.add_column("Budget", justify="right", width=12)
        table.add_column("Spent", justify="right", width=12)
        table.add_column("Remaining", justify="right", width=12)
        table.add_column("Used", justify="right", width=10)
        table.add_column("Status", width=10)

        total_budget = 0
        total_spent = 0

        for item in status_data:
            # Color coding
            if item['status'] == 'over':
                status_color = "red"
                status_icon = "✗"
            elif item['status'] == 'warning':
                status_color = "yellow"
                status_icon = "⚠"
            else:
                status_color = "green"
                status_icon = "✓"

            remaining_color = "green" if item['remaining'] >= 0 else "red"

            table.add_row(
                fix_rtl(item['tag_name']),
                f"₪{item['monthly_limit']:,.0f}",
                f"₪{item['actual_spending']:,.0f}",
                f"[{remaining_color}]₪{item['remaining']:,.0f}[/{remaining_color}]",
                f"{item['percentage_used']:.0f}%",
                f"[{status_color}]{status_icon}[/{status_color}]"
            )

            total_budget += item['monthly_limit']
            total_spent += item['actual_spending']

        # Add total row
        table.add_section()
        total_remaining = total_budget - total_spent
        total_pct = (total_spent / total_budget * 100) if total_budget > 0 else 0
        remaining_color = "green" if total_remaining >= 0 else "red"

        table.add_row(
            "[bold]TOTAL[/bold]",
            f"[bold]₪{total_budget:,.0f}[/bold]",
            f"[bold]₪{total_spent:,.0f}[/bold]",
            f"[bold {remaining_color}]₪{total_remaining:,.0f}[/bold {remaining_color}]",
            f"[bold]{total_pct:.0f}%[/bold]",
            ""
        )

        console.print(table)

        # Summary alerts
        over_budget = [item for item in status_data if item['status'] == 'over']
        warning = [item for item in status_data if item['status'] == 'warning']

        if over_budget:
            console.print(f"\n[red]⚠ {len(over_budget)} budget(s) exceeded[/red]")
        if warning:
            console.print(f"[yellow]⚠ {len(warning)} budget(s) at 80%+[/yellow]")

        service.close()

    except Exception as e:
        console.print(f"[red]Error getting budget status: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("copy")
def copy_budgets(
    from_month: int = typer.Argument(..., help="Source month (1-12)"),
    from_year: int = typer.Argument(..., help="Source year"),
):
    """
    Copy budgets from one month to the next month

    Example:
        fin-cli budgets copy 12 2024   # Copy Dec 2024 budgets to Jan 2025
    """
    try:
        service = BudgetService()
        count = service.copy_budgets_to_next_month(from_month, from_year)

        # Calculate target month/year
        if from_month == 12:
            to_month = 1
            to_year = from_year + 1
        else:
            to_month = from_month + 1
            to_year = from_year

        from_str = date(from_year, from_month, 1).strftime("%B %Y")
        to_str = date(to_year, to_month, 1).strftime("%B %Y")

        console.print(f"[green]✓[/green] Copied {count} budget(s) from {from_str} to {to_str}")

        service.close()

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error copying budgets: {e}[/red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
```

**Register in main CLI (`cli/main.py`):**

```python
from cli.commands import init, config, sync, accounts, transactions, reports, export, maintenance, tags, rules, budgets

# Add budgets command
app.add_typer(budgets.app, name="budgets")
```

### Integration with Existing Reports

**Update `cli/commands/reports.py`:**

Add budget comparison to monthly report:

```python
# In monthly_report() function, after summary panel:

# Add budget status if budgets exist
from services.budget_service import BudgetService
budget_service = BudgetService()
budget_status = budget_service.get_budget_status(year, month)

if budget_status:
    console.print()
    budget_table = Table(title="Budget vs Actual", show_header=True, header_style="bold cyan", box=box.ROUNDED)
    budget_table.add_column("Tag", width=20)
    budget_table.add_column("Budget", justify="right", width=12)
    budget_table.add_column("Actual", justify="right", width=12)
    budget_table.add_column("Status", width=10)

    for item in budget_status:
        status_color = "red" if item['status'] == 'over' else "yellow" if item['status'] == 'warning' else "green"
        status_icon = "✗" if item['status'] == 'over' else "⚠" if item['status'] == 'warning' else "✓"

        budget_table.add_row(
            fix_rtl(item['tag_name']),
            f"₪{item['monthly_limit']:,.0f}",
            f"₪{item['actual_spending']:,.0f}",
            f"[{status_color}]{status_icon} {item['percentage_used']:.0f}%[/{status_color}]"
        )

    console.print(budget_table)

budget_service.close()
```

### Migration Script

**Create migration: `db/migrations/add_budgets.py`**

```python
"""
Migration: Add budgets table
"""

from sqlalchemy import create_engine, text
from config.settings import Settings

def upgrade():
    """Add budgets table"""
    settings = Settings()
    engine = create_engine(f"sqlite:///{settings.database_path}")

    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tag_name TEXT NOT NULL,
                monthly_limit REAL NOT NULL,
                month INTEGER NOT NULL,
                year INTEGER NOT NULL,
                rollover_enabled BOOLEAN DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(tag_name, month, year)
            )
        """))

        conn.execute(text("""
            CREATE INDEX idx_budgets_period ON budgets(year, month)
        """))

        conn.execute(text("""
            CREATE INDEX idx_budgets_tag ON budgets(tag_name)
        """))

        conn.commit()

    print("✓ Budgets table created")

def downgrade():
    """Remove budgets table"""
    settings = Settings()
    engine = create_engine(f"sqlite:///{settings.database_path}")

    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS budgets"))
        conn.commit()

    print("✓ Budgets table removed")

if __name__ == "__main__":
    upgrade()
```

### Testing Checklist

- [ ] Create budget for current month
- [ ] Create budget for future month
- [ ] List all budgets
- [ ] List budgets for specific month
- [ ] Update budget limit
- [ ] Update budget rollover setting
- [ ] Delete budget
- [ ] View budget status (with spending)
- [ ] Budget status shows correct percentage
- [ ] Budget status color codes (green/yellow/red)
- [ ] Copy budgets to next month
- [ ] Cannot create duplicate budget (same tag, month, year)
- [ ] Monthly report shows budget comparison
- [ ] Spending report integrates with budgets

### Future Enhancements (Post-MVP)

1. **Budget Templates**
   - Save budget presets ("Conservative", "Normal", "Aggressive")
   - Apply template to new month

2. **Rollover Logic**
   - Actually implement rollover (unused budget → next month)
   - Track rollover history

3. **Budget Alerts via Email/Push**
   - Email when approaching 80%
   - Email when exceeding 100%

4. **Multi-Tag Budgets**
   - Budget across multiple tags
   - "Entertainment" budget covers "dining", "movies", "concerts"

5. **Annual Budgets**
   - Set yearly budget, auto-split to monthly
   - Track yearly progress

---

## Feature 2: Net Worth Tracking Over Time

### Overview

Track net worth (assets - liabilities) over time to visualize financial growth and identify trends.

### User Stories

- As a user, I want to see my net worth history to track my financial progress
- As a user, I want to compare my net worth month-over-month to see growth/decline
- As a user, I want to see net worth by account type (broker, pension, credit card)
- As a user, I want to export net worth data for external analysis

### Database Schema

**New Table: `net_worth_snapshots`**

```sql
CREATE TABLE net_worth_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date DATE NOT NULL UNIQUE,
    total_assets REAL NOT NULL,          -- Sum of positive balances (broker, pension, savings)
    total_liabilities REAL NOT NULL,     -- Sum of negative balances (credit card debt)
    net_worth REAL NOT NULL,             -- Assets - Liabilities
    broker_total REAL DEFAULT 0,
    pension_total REAL DEFAULT 0,
    credit_card_balance REAL DEFAULT 0,  -- Negative (debt)
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast date lookups
CREATE INDEX idx_networth_date ON net_worth_snapshots(snapshot_date DESC);
```

**Database Model:**

```python
# In db/models.py

class NetWorthSnapshot(Base):
    __tablename__ = 'net_worth_snapshots'

    id = Column(Integer, primary_key=True)
    snapshot_date = Column(Date, nullable=False, unique=True)
    total_assets = Column(Float, nullable=False)
    total_liabilities = Column(Float, nullable=False)
    net_worth = Column(Float, nullable=False)
    broker_total = Column(Float, default=0)
    pension_total = Column(Float, default=0)
    credit_card_balance = Column(Float, default=0)
    notes = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<NetWorth(date={self.snapshot_date}, worth={self.net_worth})>"
```

### Service Layer

**Add to `services/analytics_service.py`:**

```python
# In AnalyticsService class

def compute_net_worth_snapshot(self, snapshot_date: Optional[date] = None) -> Dict[str, float]:
    """
    Compute net worth for a specific date

    Args:
        snapshot_date: Date to compute net worth (default: today)

    Returns:
        Dict with net worth breakdown
    """
    snapshot_date = snapshot_date or date.today()

    # Get latest balances for each account on or before snapshot_date
    from sqlalchemy import func

    # Subquery to get latest balance per account before snapshot date
    latest_balance_subq = (
        self.session.query(
            Balance.account_id,
            func.max(Balance.balance_date).label('max_date')
        )
        .filter(Balance.balance_date <= snapshot_date)
        .group_by(Balance.account_id)
        .subquery()
    )

    # Join to get actual balances
    balances = (
        self.session.query(Balance, Account)
        .join(latest_balance_subq, and_(
            Balance.account_id == latest_balance_subq.c.account_id,
            Balance.balance_date == latest_balance_subq.c.max_date
        ))
        .join(Account, Balance.account_id == Account.id)
        .all()
    )

    # Calculate totals by account type
    broker_total = 0
    pension_total = 0
    credit_card_balance = 0

    for balance, account in balances:
        if account.account_type == 'broker':
            broker_total += balance.total_amount
        elif account.account_type == 'pension':
            pension_total += balance.total_amount
        elif account.account_type == 'credit_card':
            credit_card_balance += balance.total_amount  # Negative (debt)

    # Assets = Broker + Pension (positive balances)
    total_assets = broker_total + pension_total

    # Liabilities = Credit card debt (negative, so abs value)
    total_liabilities = abs(credit_card_balance)

    # Net worth = Assets - Liabilities
    net_worth = total_assets - total_liabilities

    return {
        'snapshot_date': snapshot_date,
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'net_worth': net_worth,
        'broker_total': broker_total,
        'pension_total': pension_total,
        'credit_card_balance': credit_card_balance
    }

def save_net_worth_snapshot(self, snapshot_date: Optional[date] = None, notes: Optional[str] = None):
    """Save a net worth snapshot"""
    from db.models import NetWorthSnapshot

    snapshot_date = snapshot_date or date.today()

    # Compute net worth
    data = self.compute_net_worth_snapshot(snapshot_date)

    # Check if snapshot already exists for this date
    existing = self.session.query(NetWorthSnapshot).filter(
        NetWorthSnapshot.snapshot_date == snapshot_date
    ).first()

    if existing:
        # Update existing
        existing.total_assets = data['total_assets']
        existing.total_liabilities = data['total_liabilities']
        existing.net_worth = data['net_worth']
        existing.broker_total = data['broker_total']
        existing.pension_total = data['pension_total']
        existing.credit_card_balance = data['credit_card_balance']
        if notes:
            existing.notes = notes
    else:
        # Create new
        snapshot = NetWorthSnapshot(
            snapshot_date=snapshot_date,
            total_assets=data['total_assets'],
            total_liabilities=data['total_liabilities'],
            net_worth=data['net_worth'],
            broker_total=data['broker_total'],
            pension_total=data['pension_total'],
            credit_card_balance=data['credit_card_balance'],
            notes=notes
        )
        self.session.add(snapshot)

    self.session.commit()

def get_net_worth_history(
    self,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    limit: Optional[int] = None
) -> List:
    """Get net worth snapshot history"""
    from db.models import NetWorthSnapshot

    query = self.session.query(NetWorthSnapshot)

    if from_date:
        query = query.filter(NetWorthSnapshot.snapshot_date >= from_date)
    if to_date:
        query = query.filter(NetWorthSnapshot.snapshot_date <= to_date)

    query = query.order_by(NetWorthSnapshot.snapshot_date.desc())

    if limit:
        query = query.limit(limit)

    return query.all()

def get_latest_net_worth(self) -> Optional:
    """Get most recent net worth snapshot"""
    from db.models import NetWorthSnapshot

    return self.session.query(NetWorthSnapshot).order_by(
        NetWorthSnapshot.snapshot_date.desc()
    ).first()
```

### CLI Commands

**Add to `cli/commands/reports.py`:**

```python
@app.command("net-worth")
def net_worth_report(
    months: int = typer.Option(12, "--months", "-m", help="Number of months to show"),
    compute: bool = typer.Option(False, "--compute", "-c", help="Compute and save snapshot for today"),
    show_breakdown: bool = typer.Option(True, "--breakdown/--no-breakdown", help="Show breakdown by account type")
):
    """
    Show net worth history and trends

    Examples:
        fin-cli reports net-worth                # Last 12 months
        fin-cli reports net-worth --months 24    # Last 24 months
        fin-cli reports net-worth --compute      # Compute and save today's snapshot
    """
    try:
        analytics = AnalyticsService()

        # Compute and save snapshot if requested
        if compute:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
                task = progress.add_task("Computing net worth snapshot...", total=None)
                analytics.save_net_worth_snapshot()
                progress.update(task, completed=True)
            console.print("[green]✓[/green] Net worth snapshot saved\n")

        # Get history
        from_date = date.today() - timedelta(days=months * 30)
        history = analytics.get_net_worth_history(from_date=from_date)

        if not history:
            console.print("[yellow]No net worth snapshots found[/yellow]")
            console.print("[dim]Use --compute to create a snapshot[/dim]")
            analytics.close()
            return

        # Reverse to show oldest first
        history = list(reversed(history))

        # Header
        console.print(f"[bold cyan]NET WORTH HISTORY[/bold cyan]")
        console.print(f"[dim]{history[0].snapshot_date} to {history[-1].snapshot_date}[/dim]\n")

        # Main table
        table = Table(title="Net Worth Over Time", show_header=True, header_style="bold cyan", box=box.ROUNDED)
        table.add_column("Date", width=12)
        table.add_column("Net Worth", justify="right", width=15)
        table.add_column("Change", justify="right", width=12)
        table.add_column("Trend", width=8)

        if show_breakdown:
            table.add_column("Assets", justify="right", width=12)
            table.add_column("Debt", justify="right", width=12)

        prev_worth = None
        for snapshot in history:
            # Calculate change
            if prev_worth is not None:
                change = snapshot.net_worth - prev_worth
                change_pct = (change / prev_worth * 100) if prev_worth != 0 else 0

                if change > 0:
                    change_str = f"[green]+₪{change:,.0f}[/green]"
                    trend_str = f"[green]↗ +{change_pct:.1f}%[/green]"
                elif change < 0:
                    change_str = f"[red]-₪{abs(change):,.0f}[/red]"
                    trend_str = f"[red]↘ {change_pct:.1f}%[/red]"
                else:
                    change_str = "[dim]—[/dim]"
                    trend_str = "[dim]→[/dim]"
            else:
                change_str = "[dim]baseline[/dim]"
                trend_str = "[dim]—[/dim]"

            row = [
                snapshot.snapshot_date.strftime("%Y-%m-%d"),
                f"₪{snapshot.net_worth:,.0f}",
                change_str,
                trend_str
            ]

            if show_breakdown:
                row.extend([
                    f"₪{snapshot.total_assets:,.0f}",
                    f"₪{snapshot.total_liabilities:,.0f}"
                ])

            table.add_row(*row)
            prev_worth = snapshot.net_worth

        console.print(table)

        # Summary stats
        first = history[0]
        last = history[-1]
        total_change = last.net_worth - first.net_worth
        total_change_pct = (total_change / first.net_worth * 100) if first.net_worth != 0 else 0

        console.print()
        summary_lines = [
            f"[bold]Total Change:[/bold] ₪{total_change:,.0f} ({total_change_pct:+.1f}%)",
            f"[bold]Period:[/bold] {(last.snapshot_date - first.snapshot_date).days} days ({len(history)} snapshots)"
        ]

        if total_change > 0:
            summary_lines[0] = f"[green]{summary_lines[0]}[/green]"
        elif total_change < 0:
            summary_lines[0] = f"[red]{summary_lines[0]}[/red]"

        console.print(Panel("\n".join(summary_lines), title="Summary", border_style="cyan"))

        analytics.close()

    except Exception as e:
        console.print(f"[red]Error generating net worth report: {e}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)
```

### Automatic Snapshot on Sync

**Update `services/credit_card_service.py`, `broker_service.py`, `pension_service.py`:**

After successful sync, trigger net worth snapshot:

```python
# At end of sync methods:

# Save net worth snapshot after successful sync
from services.analytics_service import AnalyticsService
analytics = AnalyticsService(session=self.session)
try:
    analytics.save_net_worth_snapshot()
    logger.info("Net worth snapshot saved")
except Exception as e:
    logger.warning(f"Failed to save net worth snapshot: {e}")
```

### Migration Script

```python
"""
Migration: Add net_worth_snapshots table
"""

from sqlalchemy import create_engine, text
from config.settings import Settings

def upgrade():
    """Add net_worth_snapshots table"""
    settings = Settings()
    engine = create_engine(f"sqlite:///{settings.database_path}")

    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE net_worth_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_date DATE NOT NULL UNIQUE,
                total_assets REAL NOT NULL,
                total_liabilities REAL NOT NULL,
                net_worth REAL NOT NULL,
                broker_total REAL DEFAULT 0,
                pension_total REAL DEFAULT 0,
                credit_card_balance REAL DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        conn.execute(text("""
            CREATE INDEX idx_networth_date ON net_worth_snapshots(snapshot_date DESC)
        """))

        conn.commit()

    print("✓ Net worth snapshots table created")

def downgrade():
    """Remove net_worth_snapshots table"""
    settings = Settings()
    engine = create_engine(f"sqlite:///{settings.database_path}")

    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS net_worth_snapshots"))
        conn.commit()

    print("✓ Net worth snapshots table removed")

if __name__ == "__main__":
    upgrade()
```

### Testing Checklist

- [ ] Compute net worth snapshot manually
- [ ] Net worth snapshot saves correctly
- [ ] View net worth history
- [ ] Net worth changes calculated correctly
- [ ] Trend indicators show (↗↘→)
- [ ] Breakdown by account type works
- [ ] Automatic snapshot after sync
- [ ] Cannot create duplicate snapshot for same date (updates instead)
- [ ] Historical data shows correctly

### Future Enhancements

1. **Asset Allocation Chart**
   - Pie chart: Broker vs Pension vs Cash
   - Track allocation changes over time

2. **Net Worth Goals**
   - Set target net worth
   - Projected date to reach goal
   - Milestone celebrations

3. **Comparison to Benchmarks**
   - Age-based net worth benchmarks
   - Income multiplier targets

---

## Feature 3: Recurring Transaction Detection

### Overview

Automatically detect recurring transactions (subscriptions, bills, recurring payments) and provide insights on monthly recurring costs.

### User Stories

- As a user, I want to see all my recurring expenses in one view
- As a user, I want to know my total monthly recurring costs
- As a user, I want to be alerted when a new recurring expense is detected
- As a user, I want to track subscription cost changes

### Algorithm

**Heuristic-Based Detection:**

```
For each unique (description, amount):
1. Find all transactions matching this pattern
2. If >= 3 occurrences with monthly cadence (28-32 days apart):
   → Mark as recurring
3. Calculate average interval
4. Predict next occurrence date
```

### Database Schema

**New Table: `recurring_transactions`**

```sql
CREATE TABLE recurring_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description_pattern TEXT NOT NULL,     -- e.g., "Netflix", "Spotify"
    average_amount REAL NOT NULL,
    frequency TEXT NOT NULL,               -- 'monthly', 'weekly', 'yearly'
    average_interval_days INTEGER,         -- e.g., 30 for monthly
    last_occurrence_date DATE,
    next_expected_date DATE,
    occurrence_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    category TEXT,
    notes TEXT,
    first_detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_recurring_active ON recurring_transactions(is_active);
CREATE INDEX idx_recurring_next_date ON recurring_transactions(next_expected_date);
```

**Database Model:**

```python
# In db/models.py

class RecurringTransaction(Base):
    __tablename__ = 'recurring_transactions'

    id = Column(Integer, primary_key=True)
    description_pattern = Column(String, nullable=False)
    average_amount = Column(Float, nullable=False)
    frequency = Column(String, nullable=False)  # 'monthly', 'weekly', 'yearly'
    average_interval_days = Column(Integer)
    last_occurrence_date = Column(Date)
    next_expected_date = Column(Date)
    occurrence_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    category = Column(String)
    notes = Column(String)
    first_detected_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Recurring({self.description_pattern}, {self.frequency}, ₪{self.average_amount})>"
```

### Service Layer

**New Service: `services/recurring_service.py`**

```python
"""
Service for detecting and managing recurring transactions
"""

from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from db.models import Transaction, RecurringTransaction
from db.database import get_db
import logging

logger = logging.getLogger(__name__)


class RecurringService:
    """Service for recurring transaction detection and management"""

    # Detection thresholds
    MIN_OCCURRENCES = 3  # Need at least 3 occurrences
    MONTHLY_TOLERANCE = 4  # ±4 days from 30 days (26-34 days)
    WEEKLY_TOLERANCE = 2   # ±2 days from 7 days
    YEARLY_TOLERANCE = 15  # ±15 days from 365 days

    def __init__(self, session: Optional[Session] = None):
        self.session = session or next(get_db())

    def detect_recurring_transactions(self, min_occurrences: int = 3) -> Dict[str, Any]:
        """
        Detect recurring transactions using heuristic pattern matching

        Returns:
            Dict with detection results
        """
        logger.info("Starting recurring transaction detection...")

        # Group transactions by description and approximate amount
        # (round amount to nearest 10 to handle small variations)

        query = self.session.query(
            Transaction.description,
            func.round(func.abs(Transaction.original_amount / 10)) * 10,
            func.count().label('count'),
            func.avg(func.abs(Transaction.original_amount)).label('avg_amount'),
            func.min(Transaction.transaction_date).label('first_date'),
            func.max(Transaction.transaction_date).label('last_date')
        ).filter(
            Transaction.original_amount < 0  # Only expenses
        ).group_by(
            Transaction.description,
            func.round(func.abs(Transaction.original_amount / 10)) * 10
        ).having(
            func.count() >= min_occurrences
        ).all()

        detected = []
        new_count = 0
        updated_count = 0

        for description, _, count, avg_amount, first_date, last_date in query:
            # Get actual transactions for this pattern
            transactions = self.session.query(Transaction).filter(
                and_(
                    Transaction.description == description,
                    Transaction.original_amount < 0,
                    func.abs(func.abs(Transaction.original_amount) - avg_amount) < 50  # ±50
                )
            ).order_by(Transaction.transaction_date).all()

            if len(transactions) < min_occurrences:
                continue

            # Calculate intervals between transactions
            intervals = []
            for i in range(1, len(transactions)):
                delta = (transactions[i].transaction_date - transactions[i-1].transaction_date).days
                intervals.append(delta)

            if not intervals:
                continue

            avg_interval = sum(intervals) / len(intervals)

            # Classify frequency
            frequency, is_recurring = self._classify_frequency(avg_interval, intervals)

            if not is_recurring:
                continue

            # Check if already exists
            existing = self.session.query(RecurringTransaction).filter(
                RecurringTransaction.description_pattern == description
            ).first()

            next_expected = last_date + timedelta(days=int(avg_interval))

            if existing:
                # Update existing
                existing.average_amount = avg_amount
                existing.average_interval_days = int(avg_interval)
                existing.last_occurrence_date = last_date
                existing.next_expected_date = next_expected
                existing.occurrence_count = len(transactions)
                existing.frequency = frequency
                updated_count += 1
            else:
                # Create new
                recurring = RecurringTransaction(
                    description_pattern=description,
                    average_amount=avg_amount,
                    frequency=frequency,
                    average_interval_days=int(avg_interval),
                    last_occurrence_date=last_date,
                    next_expected_date=next_expected,
                    occurrence_count=len(transactions),
                    category=transactions[0].category  # Use category from first transaction
                )
                self.session.add(recurring)
                new_count += 1

            detected.append({
                'description': description,
                'frequency': frequency,
                'average_amount': avg_amount,
                'occurrences': len(transactions),
                'next_expected': next_expected
            })

        self.session.commit()

        logger.info(f"Detection complete: {new_count} new, {updated_count} updated")

        return {
            'detected_count': len(detected),
            'new_count': new_count,
            'updated_count': updated_count,
            'recurring_transactions': detected
        }

    def _classify_frequency(self, avg_interval: float, intervals: List[int]) -> tuple[str, bool]:
        """
        Classify transaction frequency based on average interval

        Returns:
            (frequency_name, is_recurring)
        """
        # Check consistency (standard deviation)
        if len(intervals) < 2:
            return 'unknown', False

        # Calculate standard deviation
        mean = avg_interval
        variance = sum((x - mean) ** 2 for x in intervals) / len(intervals)
        std_dev = variance ** 0.5

        # Monthly: 28-32 days (30 ± 2)
        if 26 <= avg_interval <= 34:
            if std_dev < self.MONTHLY_TOLERANCE:
                return 'monthly', True

        # Weekly: 5-9 days (7 ± 2)
        if 5 <= avg_interval <= 9:
            if std_dev < self.WEEKLY_TOLERANCE:
                return 'weekly', True

        # Bi-weekly: 12-16 days (14 ± 2)
        if 12 <= avg_interval <= 16:
            if std_dev < self.WEEKLY_TOLERANCE:
                return 'bi-weekly', True

        # Quarterly: 85-95 days (90 ± 5)
        if 85 <= avg_interval <= 95:
            if std_dev < 7:
                return 'quarterly', True

        # Yearly: 350-380 days (365 ± 15)
        if 350 <= avg_interval <= 380:
            if std_dev < self.YEARLY_TOLERANCE:
                return 'yearly', True

        return 'irregular', False

    def get_active_recurring(self) -> List[RecurringTransaction]:
        """Get all active recurring transactions"""
        return self.session.query(RecurringTransaction).filter(
            RecurringTransaction.is_active == True
        ).order_by(RecurringTransaction.average_amount.desc()).all()

    def get_upcoming_recurring(self, days: int = 30) -> List[RecurringTransaction]:
        """Get recurring transactions expected in next N days"""
        cutoff_date = date.today() + timedelta(days=days)

        return self.session.query(RecurringTransaction).filter(
            and_(
                RecurringTransaction.is_active == True,
                RecurringTransaction.next_expected_date <= cutoff_date,
                RecurringTransaction.next_expected_date >= date.today()
            )
        ).order_by(RecurringTransaction.next_expected_date).all()

    def get_monthly_recurring_cost(self) -> float:
        """Calculate total monthly recurring cost"""
        monthly = self.session.query(RecurringTransaction).filter(
            and_(
                RecurringTransaction.is_active == True,
                RecurringTransaction.frequency == 'monthly'
            )
        ).all()

        return sum(r.average_amount for r in monthly)

    def mark_inactive(self, recurring_id: int) -> bool:
        """Mark a recurring transaction as inactive (e.g., cancelled subscription)"""
        recurring = self.session.query(RecurringTransaction).filter(
            RecurringTransaction.id == recurring_id
        ).first()

        if not recurring:
            return False

        recurring.is_active = False
        self.session.commit()
        return True

    def close(self):
        """Close database session"""
        if self.session:
            self.session.close()
```

### CLI Commands

**New Commands: `cli/commands/recurring.py`**

```python
"""
Recurring transaction CLI commands
"""

import typer
from datetime import date, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn

from services.recurring_service import RecurringService
from cli.utils import fix_rtl

app = typer.Typer(help="Manage recurring transactions")
console = Console()


@app.command("detect")
def detect_recurring(
    min_occurrences: int = typer.Option(3, "--min", "-m", help="Minimum occurrences to detect")
):
    """
    Detect recurring transactions (subscriptions, bills)

    Example:
        fin-cli recurring detect           # Detect with default settings
        fin-cli recurring detect --min 4   # Require 4+ occurrences
    """
    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Detecting recurring transactions...", total=None)

            service = RecurringService()
            result = service.detect_recurring_transactions(min_occurrences=min_occurrences)

            progress.update(task, completed=True)

        console.print(f"[green]✓[/green] Detection complete")
        console.print(f"  New recurring patterns: {result['new_count']}")
        console.print(f"  Updated patterns: {result['updated_count']}")
        console.print(f"  Total detected: {result['detected_count']}\n")

        if result['detected_count'] > 0:
            console.print("[dim]Use 'fin-cli recurring list' to view all recurring transactions[/dim]")

        service.close()

    except Exception as e:
        console.print(f"[red]Error detecting recurring transactions: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("list")
def list_recurring(
    active_only: bool = typer.Option(True, "--active-only/--all", help="Show only active recurring transactions")
):
    """
    List all recurring transactions

    Example:
        fin-cli recurring list              # Active only
        fin-cli recurring list --all        # Include inactive
    """
    try:
        service = RecurringService()

        if active_only:
            recurring = service.get_active_recurring()
            title = "Active Recurring Transactions"
        else:
            recurring = service.session.query(service.session.query(RecurringTransaction).all()
            title = "All Recurring Transactions"

        if not recurring:
            console.print("[yellow]No recurring transactions found[/yellow]")
            console.print("[dim]Use 'fin-cli recurring detect' to detect patterns[/dim]")
            return

        # Create table
        table = Table(title=title, show_header=True, header_style="bold cyan", box=box.ROUNDED)
        table.add_column("ID", style="dim", width=6)
        table.add_column("Description", width=30)
        table.add_column("Amount", justify="right", width=12)
        table.add_column("Frequency", width=12)
        table.add_column("Next Due", width=12)
        table.add_column("Count", justify="right", width=8)

        total_monthly = 0

        for r in recurring:
            # Color code by frequency
            freq_color = "cyan" if r.frequency == 'monthly' else "blue" if r.frequency == 'weekly' else "magenta"

            # Calculate days until next
            if r.next_expected_date:
                days_until = (r.next_expected_date - date.today()).days
                if days_until < 0:
                    next_due_str = f"[red]{r.next_expected_date}[/red]"
                elif days_until <= 7:
                    next_due_str = f"[yellow]{r.next_expected_date}[/yellow]"
                else:
                    next_due_str = str(r.next_expected_date)
            else:
                next_due_str = "[dim]—[/dim]"

            table.add_row(
                str(r.id),
                fix_rtl(r.description_pattern)[:30],
                f"₪{r.average_amount:,.0f}",
                f"[{freq_color}]{r.frequency}[/{freq_color}]",
                next_due_str,
                str(r.occurrence_count)
            )

            # Add to monthly total
            if r.frequency == 'monthly':
                total_monthly += r.average_amount

        console.print(table)

        # Summary
        console.print(f"\n[bold]Total Monthly Recurring:[/bold] ₪{total_monthly:,.0f}")
        console.print(f"[dim]({len(recurring)} recurring transactions)[/dim]")

        service.close()

    except Exception as e:
        console.print(f"[red]Error listing recurring transactions: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("upcoming")
def upcoming_recurring(
    days: int = typer.Option(30, "--days", "-d", help="Show upcoming in next N days")
):
    """
    Show upcoming recurring transactions

    Example:
        fin-cli recurring upcoming              # Next 30 days
        fin-cli recurring upcoming --days 7     # Next week
    """
    try:
        service = RecurringService()
        upcoming = service.get_upcoming_recurring(days=days)

        if not upcoming:
            console.print(f"[yellow]No recurring transactions expected in next {days} days[/yellow]")
            return

        # Create table
        table = Table(
            title=f"Upcoming Recurring Transactions ({days} days)",
            show_header=True,
            header_style="bold cyan",
            box=box.ROUNDED
        )
        table.add_column("Expected Date", width=15)
        table.add_column("Description", width=30)
        table.add_column("Amount", justify="right", width=12)
        table.add_column("Frequency", width=12)
        table.add_column("Days Until", justify="right", width=12)

        total = 0

        for r in upcoming:
            days_until = (r.next_expected_date - date.today()).days

            # Color code urgency
            if days_until <= 3:
                date_color = "red"
            elif days_until <= 7:
                date_color = "yellow"
            else:
                date_color = "white"

            table.add_row(
                f"[{date_color}]{r.next_expected_date}[/{date_color}]",
                fix_rtl(r.description_pattern)[:30],
                f"₪{r.average_amount:,.0f}",
                r.frequency,
                f"[{date_color}]{days_until}[/{date_color}]"
            )

            total += r.average_amount

        console.print(table)
        console.print(f"\n[bold]Total Upcoming:[/bold] ₪{total:,.0f}")

        service.close()

    except Exception as e:
        console.print(f"[red]Error showing upcoming recurring: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("deactivate")
def deactivate_recurring(
    recurring_id: int = typer.Argument(..., help="Recurring transaction ID")
):
    """
    Mark recurring transaction as inactive (cancelled)

    Example:
        fin-cli recurring deactivate 5   # Mark ID 5 as inactive
    """
    try:
        service = RecurringService()
        success = service.mark_inactive(recurring_id)

        if success:
            console.print(f"[green]✓[/green] Recurring transaction {recurring_id} marked as inactive")
        else:
            console.print(f"[red]Recurring transaction {recurring_id} not found[/red]")
            raise typer.Exit(code=1)

        service.close()

    except Exception as e:
        console.print(f"[red]Error deactivating recurring transaction: {e}[/red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
```

**Register in main CLI:**

```python
from cli.commands import ..., recurring

app.add_typer(recurring.app, name="recurring")
```

### Automatic Detection on Sync

**Update sync services to trigger detection:**

```python
# After successful credit card sync:

from services.recurring_service import RecurringService
recurring_service = RecurringService(session=self.session)
try:
    result = recurring_service.detect_recurring_transactions()
    logger.info(f"Recurring detection: {result['new_count']} new, {result['updated_count']} updated")
except Exception as e:
    logger.warning(f"Failed to detect recurring transactions: {e}")
```

### Migration Script

```python
"""
Migration: Add recurring_transactions table
"""

from sqlalchemy import create_engine, text
from config.settings import Settings

def upgrade():
    """Add recurring_transactions table"""
    settings = Settings()
    engine = create_engine(f"sqlite:///{settings.database_path}")

    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE recurring_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description_pattern TEXT NOT NULL,
                average_amount REAL NOT NULL,
                frequency TEXT NOT NULL,
                average_interval_days INTEGER,
                last_occurrence_date DATE,
                next_expected_date DATE,
                occurrence_count INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                category TEXT,
                notes TEXT,
                first_detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        conn.execute(text("""
            CREATE INDEX idx_recurring_active ON recurring_transactions(is_active)
        """))

        conn.execute(text("""
            CREATE INDEX idx_recurring_next_date ON recurring_transactions(next_expected_date)
        """))

        conn.commit()

    print("✓ Recurring transactions table created")

def downgrade():
    """Remove recurring_transactions table"""
    settings = Settings()
    engine = create_engine(f"sqlite:///{settings.database_path}")

    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS recurring_transactions"))
        conn.commit()

    print("✓ Recurring transactions table removed")

if __name__ == "__main__":
    upgrade()
```

### Testing Checklist

- [ ] Detect recurring transactions
- [ ] Monthly subscriptions detected correctly
- [ ] Weekly transactions detected
- [ ] Quarterly/yearly transactions detected
- [ ] List active recurring transactions
- [ ] Show upcoming recurring (next 30 days)
- [ ] Calculate total monthly recurring cost
- [ ] Mark recurring as inactive
- [ ] Automatic detection after sync
- [ ] Handle edge cases (irregular patterns excluded)

### Future Enhancements

1. **Manual Recurring Entry**
   - Add recurring transaction manually
   - Set custom frequency

2. **Price Change Alerts**
   - Detect when recurring amount changes
   - Alert user of price increases

3. **Subscription Calendar**
   - Visual calendar of upcoming recurring charges
   - Export to iCal/Google Calendar

4. **Cancellation Reminders**
   - Track trial periods
   - Remind before renewal

---

## Feature 4: Goal Setting & Tracking

### Overview

Enable users to set financial goals (savings targets, debt payoff, purchase goals) and track progress toward those goals.

### User Stories

- As a user, I want to set a savings goal for a vacation so I can track my progress
- As a user, I want to see how much I've saved toward my goal
- As a user, I want to know when I'll reach my goal based on current saving rate
- As a user, I want to allocate transactions to specific goals

### Database Schema

**New Table: `goals`**

```sql
CREATE TABLE goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    goal_type TEXT NOT NULL,             -- 'savings', 'debt', 'purchase', 'emergency_fund'
    target_amount REAL NOT NULL,
    current_amount REAL DEFAULT 0,
    target_date DATE,
    linked_tag TEXT,                     -- Optional tag to auto-track
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_goals_active ON goals(is_active);
CREATE INDEX idx_goals_type ON goals(goal_type);
```

**Database Model:**

```python
# In db/models.py

class Goal(Base):
    __tablename__ = 'goals'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    goal_type = Column(String, nullable=False)  # 'savings', 'debt', 'purchase', 'emergency_fund'
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0)
    target_date = Column(Date)
    linked_tag = Column(String)  # Auto-track transactions with this tag
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)

    def __repr__(self):
        return f"<Goal({self.name}, {self.current_amount}/{self.target_amount})>"

    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage"""
        if self.target_amount <= 0:
            return 0
        return min((self.current_amount / self.target_amount) * 100, 100)

    @property
    def remaining_amount(self) -> float:
        """Calculate remaining amount to reach goal"""
        return max(self.target_amount - self.current_amount, 0)

    @property
    def is_completed(self) -> bool:
        """Check if goal is completed"""
        return self.current_amount >= self.target_amount
```

### Service Layer

**New Service: `services/goal_service.py`**

```python
"""
Service for managing financial goals
"""

from datetime import date, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from db.models import Goal, Transaction, TransactionTag, Tag
from db.database import get_db
import logging

logger = logging.getLogger(__name__)


class GoalService:
    """Service for financial goal management"""

    def __init__(self, session: Optional[Session] = None):
        self.session = session or next(get_db())

    def create_goal(
        self,
        name: str,
        target_amount: float,
        goal_type: str = 'savings',
        description: Optional[str] = None,
        target_date: Optional[date] = None,
        linked_tag: Optional[str] = None,
        initial_amount: float = 0
    ) -> Goal:
        """
        Create a new goal

        Args:
            name: Goal name
            target_amount: Target amount to reach
            goal_type: Type ('savings', 'debt', 'purchase', 'emergency_fund')
            description: Optional description
            target_date: Optional target completion date
            linked_tag: Optional tag to auto-track contributions
            initial_amount: Initial amount toward goal

        Returns:
            Created Goal object
        """
        # Validate goal type
        valid_types = ['savings', 'debt', 'purchase', 'emergency_fund']
        if goal_type not in valid_types:
            raise ValueError(f"Invalid goal type. Must be one of: {', '.join(valid_types)}")

        # Validate amounts
        if target_amount <= 0:
            raise ValueError("Target amount must be positive")

        if initial_amount < 0:
            raise ValueError("Initial amount cannot be negative")

        goal = Goal(
            name=name,
            description=description,
            goal_type=goal_type,
            target_amount=target_amount,
            current_amount=initial_amount,
            target_date=target_date,
            linked_tag=linked_tag
        )

        self.session.add(goal)
        self.session.commit()

        logger.info(f"Goal created: {name} (₪{target_amount})")
        return goal

    def update_goal(
        self,
        goal_id: int,
        name: Optional[str] = None,
        target_amount: Optional[float] = None,
        target_date: Optional[date] = None,
        description: Optional[str] = None,
        linked_tag: Optional[str] = None
    ) -> Goal:
        """Update an existing goal"""
        goal = self.session.query(Goal).filter(Goal.id == goal_id).first()

        if not goal:
            raise ValueError(f"Goal with ID {goal_id} not found")

        if name is not None:
            goal.name = name
        if target_amount is not None:
            if target_amount <= 0:
                raise ValueError("Target amount must be positive")
            goal.target_amount = target_amount
        if target_date is not None:
            goal.target_date = target_date
        if description is not None:
            goal.description = description
        if linked_tag is not None:
            goal.linked_tag = linked_tag

        self.session.commit()
        return goal

    def add_to_goal(self, goal_id: int, amount: float, notes: Optional[str] = None) -> Goal:
        """
        Add amount to a goal

        Args:
            goal_id: Goal ID
            amount: Amount to add
            notes: Optional notes

        Returns:
            Updated Goal object
        """
        goal = self.session.query(Goal).filter(Goal.id == goal_id).first()

        if not goal:
            raise ValueError(f"Goal with ID {goal_id} not found")

        goal.current_amount += amount

        # Check if goal completed
        if goal.current_amount >= goal.target_amount and not goal.completed_at:
            goal.completed_at = datetime.utcnow()
            logger.info(f"Goal completed: {goal.name}")

        self.session.commit()
        return goal

    def get_goal(self, goal_id: int) -> Optional[Goal]:
        """Get goal by ID"""
        return self.session.query(Goal).filter(Goal.id == goal_id).first()

    def get_active_goals(self) -> List[Goal]:
        """Get all active goals"""
        return self.session.query(Goal).filter(
            Goal.is_active == True
        ).order_by(Goal.created_at.desc()).all()

    def get_goals_by_type(self, goal_type: str) -> List[Goal]:
        """Get goals by type"""
        return self.session.query(Goal).filter(
            and_(
                Goal.is_active == True,
                Goal.goal_type == goal_type
            )
        ).order_by(Goal.created_at.desc()).all()

    def calculate_projected_completion(self, goal_id: int, months_lookback: int = 3) -> Optional[date]:
        """
        Calculate projected completion date based on recent saving rate

        Args:
            goal_id: Goal ID
            months_lookback: Number of months to analyze for saving rate

        Returns:
            Projected completion date, or None if cannot calculate
        """
        goal = self.get_goal(goal_id)
        if not goal or not goal.linked_tag:
            return None

        # Calculate average monthly contribution from linked tag
        from sqlalchemy import func, extract
        from services.analytics_service import effective_amount_expr

        cutoff_date = date.today() - timedelta(days=months_lookback * 30)

        # Get total contributions (positive transactions) for linked tag
        total = self.session.query(
            func.sum(effective_amount_expr()).label('total')
        ).select_from(Transaction).join(
            TransactionTag, Transaction.id == TransactionTag.transaction_id
        ).join(
            Tag, TransactionTag.tag_id == Tag.id
        ).filter(
            and_(
                Tag.name == goal.linked_tag,
                Transaction.transaction_date >= cutoff_date,
                Transaction.original_amount > 0  # Only positive (contributions)
            )
        ).scalar()

        if not total or total <= 0:
            return None

        # Calculate monthly rate
        monthly_rate = total / months_lookback

        # Calculate months needed
        remaining = goal.remaining_amount
        if monthly_rate <= 0:
            return None

        months_needed = remaining / monthly_rate

        # Project completion date
        projected_date = date.today() + timedelta(days=int(months_needed * 30))

        return projected_date

    def sync_linked_tag(self, goal_id: int) -> float:
        """
        Sync goal progress from linked tag transactions

        Calculates total positive transactions for linked tag and updates current_amount

        Returns:
            New current amount
        """
        goal = self.get_goal(goal_id)
        if not goal or not goal.linked_tag:
            return goal.current_amount if goal else 0

        from sqlalchemy import func
        from services.analytics_service import effective_amount_expr

        # Get total contributions for linked tag (positive amounts only)
        total = self.session.query(
            func.sum(effective_amount_expr()).label('total')
        ).select_from(Transaction).join(
            TransactionTag, Transaction.id == TransactionTag.transaction_id
        ).join(
            Tag, TransactionTag.tag_id == Tag.id
        ).filter(
            and_(
                Tag.name == goal.linked_tag,
                Transaction.original_amount > 0  # Only contributions
            )
        ).scalar()

        new_amount = total if total else 0
        goal.current_amount = new_amount

        # Check if completed
        if goal.current_amount >= goal.target_amount and not goal.completed_at:
            goal.completed_at = datetime.utcnow()

        self.session.commit()
        return new_amount

    def deactivate_goal(self, goal_id: int) -> bool:
        """Mark goal as inactive"""
        goal = self.get_goal(goal_id)
        if not goal:
            return False

        goal.is_active = False
        self.session.commit()
        return True

    def delete_goal(self, goal_id: int) -> bool:
        """Delete a goal"""
        goal = self.get_goal(goal_id)
        if not goal:
            return False

        self.session.delete(goal)
        self.session.commit()
        return True

    def close(self):
        """Close database session"""
        if self.session:
            self.session.close()
```

### CLI Commands

**New Commands: `cli/commands/goals.py`**

```python
"""
Goal management CLI commands
"""

import typer
from datetime import date, datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress as RichProgress, BarColumn, TextColumn
from rich import box
from typing import Optional

from services.goal_service import GoalService
from cli.utils import fix_rtl

app = typer.Typer(help="Manage financial goals")
console = Console()


@app.command("create")
def create_goal(
    name: str = typer.Argument(..., help="Goal name"),
    target: float = typer.Argument(..., help="Target amount"),
    type: str = typer.Option("savings", "--type", "-t", help="Goal type (savings, debt, purchase, emergency_fund)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Description"),
    target_date: Optional[str] = typer.Option(None, "--date", help="Target date (YYYY-MM-DD)"),
    tag: Optional[str] = typer.Option(None, "--tag", help="Linked tag for auto-tracking"),
    initial: float = typer.Option(0, "--initial", "-i", help="Initial amount toward goal")
):
    """
    Create a new financial goal

    Examples:
        fin-cli goals create "Vacation" 5000                    # Savings goal
        fin-cli goals create "Emergency Fund" 20000 -t emergency_fund
        fin-cli goals create "New Car" 30000 --date 2026-06-01
        fin-cli goals create "Save for House" 100000 --tag savings --initial 5000
    """
    try:
        # Parse target date
        target_date_obj = None
        if target_date:
            try:
                target_date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
            except ValueError:
                console.print("[red]Invalid date format. Use YYYY-MM-DD[/red]")
                raise typer.Exit(code=1)

        service = GoalService()
        goal = service.create_goal(
            name=name,
            target_amount=target,
            goal_type=type,
            description=description,
            target_date=target_date_obj,
            linked_tag=tag,
            initial_amount=initial
        )

        console.print(f"[green]✓[/green] Goal created: {name}")
        console.print(f"  Target: ₪{target:,.0f}")
        if target_date_obj:
            console.print(f"  Target Date: {target_date_obj}")
        if tag:
            console.print(f"  Linked Tag: {tag}")
        if initial > 0:
            console.print(f"  Initial Amount: ₪{initial:,.0f} ({goal.progress_percentage:.1f}%)")

        service.close()

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error creating goal: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("list")
def list_goals(
    type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by type"),
    show_completed: bool = typer.Option(False, "--completed", help="Include completed goals")
):
    """
    List all goals

    Examples:
        fin-cli goals list                   # Active goals
        fin-cli goals list --type savings    # Savings goals only
        fin-cli goals list --completed       # Include completed
    """
    try:
        service = GoalService()

        if type:
            goals = service.get_goals_by_type(type)
        else:
            goals = service.get_active_goals()

        if not show_completed:
            goals = [g for g in goals if not g.completed_at]

        if not goals:
            console.print("[yellow]No goals found[/yellow]")
            console.print("[dim]Use 'fin-cli goals create' to create a goal[/dim]")
            return

        # Create table
        table = Table(title="Financial Goals", show_header=True, header_style="bold cyan", box=box.ROUNDED)
        table.add_column("ID", style="dim", width=6)
        table.add_column("Name", width=25)
        table.add_column("Type", width=15)
        table.add_column("Progress", width=40)
        table.add_column("Target", justify="right", width=12)
        table.add_column("Remaining", justify="right", width=12)

        for goal in goals:
            # Progress bar
            progress_pct = goal.progress_percentage
            bar_width = 20
            filled = int(progress_pct / 100 * bar_width)
            bar = "█" * filled + "░" * (bar_width - filled)

            if progress_pct >= 100:
                bar_color = "green"
                status = "✓ Complete"
            elif progress_pct >= 75:
                bar_color = "yellow"
                status = f"{progress_pct:.0f}%"
            else:
                bar_color = "cyan"
                status = f"{progress_pct:.0f}%"

            progress_str = f"[{bar_color}]{bar}[/{bar_color}] {status}"

            # Remaining amount color
            remaining_color = "green" if goal.remaining_amount == 0 else "white"

            table.add_row(
                str(goal.id),
                fix_rtl(goal.name),
                goal.goal_type,
                progress_str,
                f"₪{goal.target_amount:,.0f}",
                f"[{remaining_color}]₪{goal.remaining_amount:,.0f}[/{remaining_color}]"
            )

        console.print(table)

        # Summary
        total_target = sum(g.target_amount for g in goals)
        total_current = sum(g.current_amount for g in goals)
        total_remaining = total_target - total_current

        console.print(f"\n[bold]Total Target:[/bold] ₪{total_target:,.0f}")
        console.print(f"[bold]Total Saved:[/bold] ₪{total_current:,.0f}")
        console.print(f"[bold]Total Remaining:[/bold] ₪{total_remaining:,.0f}")

        service.close()

    except Exception as e:
        console.print(f"[red]Error listing goals: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("add")
def add_to_goal(
    goal_id: int = typer.Argument(..., help="Goal ID"),
    amount: float = typer.Argument(..., help="Amount to add"),
    notes: Optional[str] = typer.Option(None, "--notes", "-n", help="Notes")
):
    """
    Add amount to a goal

    Example:
        fin-cli goals add 1 500           # Add ₪500 to goal #1
        fin-cli goals add 1 1000 -n "Bonus payment"
    """
    try:
        service = GoalService()
        goal = service.add_to_goal(goal_id, amount, notes)

        console.print(f"[green]✓[/green] Added ₪{amount:,.0f} to '{goal.name}'")
        console.print(f"  Progress: ₪{goal.current_amount:,.0f} / ₪{goal.target_amount:,.0f} ({goal.progress_percentage:.1f}%)")

        if goal.is_completed:
            console.print(f"  [green]🎉 Goal completed![/green]")

        service.close()

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error adding to goal: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("details")
def goal_details(
    goal_id: int = typer.Argument(..., help="Goal ID")
):
    """
    Show detailed information about a goal

    Example:
        fin-cli goals details 1
    """
    try:
        service = GoalService()
        goal = service.get_goal(goal_id)

        if not goal:
            console.print(f"[red]Goal with ID {goal_id} not found[/red]")
            raise typer.Exit(code=1)

        # Build info panel
        info_lines = [
            f"[bold cyan]{goal.name}[/bold cyan]",
            "",
            f"[bold]Type:[/bold] {goal.goal_type}",
            f"[bold]Target Amount:[/bold] ₪{goal.target_amount:,.0f}",
            f"[bold]Current Amount:[/bold] ₪{goal.current_amount:,.0f}",
            f"[bold]Remaining:[/bold] ₪{goal.remaining_amount:,.0f}",
            f"[bold]Progress:[/bold] {goal.progress_percentage:.1f}%",
        ]

        if goal.description:
            info_lines.extend(["", f"[bold]Description:[/bold] {goal.description}"])

        if goal.target_date:
            days_until = (goal.target_date - date.today()).days
            info_lines.extend([
                "",
                f"[bold]Target Date:[/bold] {goal.target_date} ({days_until} days)"
            ])

        if goal.linked_tag:
            info_lines.extend(["", f"[bold]Linked Tag:[/bold] {goal.linked_tag}"])

            # Calculate projected completion
            projected = service.calculate_projected_completion(goal_id, months_lookback=3)
            if projected:
                days_proj = (projected - date.today()).days
                info_lines.append(f"[bold]Projected Completion:[/bold] {projected} ({days_proj} days)")

        if goal.completed_at:
            info_lines.extend([
                "",
                f"[green]✓ Completed: {goal.completed_at.date()}[/green]"
            ])

        info_lines.extend([
            "",
            f"[dim]Created: {goal.created_at.date()}[/dim]"
        ])

        console.print(Panel("\n".join(info_lines), box=box.ROUNDED))

        # Progress bar
        bar_width = 50
        filled = int(goal.progress_percentage / 100 * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        if goal.progress_percentage >= 100:
            bar_color = "green"
        elif goal.progress_percentage >= 75:
            bar_color = "yellow"
        else:
            bar_color = "cyan"

        console.print(f"\n[{bar_color}]{bar}[/{bar_color}] {goal.progress_percentage:.1f}%\n")

        service.close()

    except Exception as e:
        console.print(f"[red]Error showing goal details: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("sync")
def sync_goal(
    goal_id: int = typer.Argument(..., help="Goal ID to sync")
):
    """
    Sync goal progress from linked tag transactions

    Example:
        fin-cli goals sync 1   # Sync goal #1 from linked tag
    """
    try:
        service = GoalService()
        goal = service.get_goal(goal_id)

        if not goal:
            console.print(f"[red]Goal with ID {goal_id} not found[/red]")
            raise typer.Exit(code=1)

        if not goal.linked_tag:
            console.print(f"[yellow]Goal '{goal.name}' has no linked tag[/yellow]")
            return

        old_amount = goal.current_amount
        new_amount = service.sync_linked_tag(goal_id)

        console.print(f"[green]✓[/green] Goal '{goal.name}' synced from tag '{goal.linked_tag}'")
        console.print(f"  Previous: ₪{old_amount:,.0f}")
        console.print(f"  Current: ₪{new_amount:,.0f}")
        console.print(f"  Progress: {goal.progress_percentage:.1f}%")

        if goal.is_completed and old_amount < goal.target_amount:
            console.print(f"  [green]🎉 Goal completed![/green]")

        service.close()

    except Exception as e:
        console.print(f"[red]Error syncing goal: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("delete")
def delete_goal(
    goal_id: int = typer.Argument(..., help="Goal ID to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation")
):
    """
    Delete a goal

    Example:
        fin-cli goals delete 5
        fin-cli goals delete 5 --yes   # Skip confirmation
    """
    try:
        service = GoalService()
        goal = service.get_goal(goal_id)

        if not goal:
            console.print(f"[red]Goal with ID {goal_id} not found[/red]")
            raise typer.Exit(code=1)

        if not yes:
            console.print(f"Delete goal '{goal.name}' (₪{goal.current_amount:,.0f} / ₪{goal.target_amount:,.0f})?")
            confirm = typer.confirm("Are you sure?")
            if not confirm:
                console.print("Cancelled")
                return

        success = service.delete_goal(goal_id)

        if success:
            console.print(f"[green]✓[/green] Goal deleted")
        else:
            console.print(f"[red]Failed to delete goal[/red]")

        service.close()

    except Exception as e:
        console.print(f"[red]Error deleting goal: {e}[/red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
```

**Register in main CLI:**

```python
from cli.commands import ..., goals

app.add_typer(goals.app, name="goals")
```

### Migration Script

```python
"""
Migration: Add goals table
"""

from sqlalchemy import create_engine, text
from config.settings import Settings

def upgrade():
    """Add goals table"""
    settings = Settings()
    engine = create_engine(f"sqlite:///{settings.database_path}")

    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                goal_type TEXT NOT NULL,
                target_amount REAL NOT NULL,
                current_amount REAL DEFAULT 0,
                target_date DATE,
                linked_tag TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """))

        conn.execute(text("""
            CREATE INDEX idx_goals_active ON goals(is_active)
        """))

        conn.execute(text("""
            CREATE INDEX idx_goals_type ON goals(goal_type)
        """))

        conn.commit()

    print("✓ Goals table created")

def downgrade():
    """Remove goals table"""
    settings = Settings()
    engine = create_engine(f"sqlite:///{settings.database_path}")

    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS goals"))
        conn.commit()

    print("✓ Goals table removed")

if __name__ == "__main__":
    upgrade()
```

### Testing Checklist

- [ ] Create savings goal
- [ ] Create goal with target date
- [ ] Create goal with linked tag
- [ ] List all goals
- [ ] Add amount to goal manually
- [ ] Sync goal from linked tag
- [ ] Goal marked complete when target reached
- [ ] Calculate projected completion date
- [ ] View goal details
- [ ] Delete goal
- [ ] Filter goals by type

### Future Enhancements

1. **Goal Milestones**
   - Set intermediate milestones (25%, 50%, 75%)
   - Celebrate milestone achievements

2. **Automatic Contributions**
   - Schedule recurring contributions
   - Auto-allocate percentage of income

3. **Shared Goals**
   - Multi-user goals (household savings)
   - Track individual contributions

4. **Goal Insights**
   - "On track" / "Behind" / "Ahead" status
   - Recommended monthly contribution to stay on track

---

## Implementation Timeline

| Feature | Complexity | Estimated Time | Dependencies |
|---------|------------|----------------|--------------|
| Budget Tracking | Medium | 3-4 days | None |
| Net Worth Tracking | Low | 1-2 days | Existing balance data |
| Recurring Detection | Medium | 2-3 days | None |
| Goal Tracking | Medium | 3-4 days | None |

**Total: 9-13 days (2-3 weeks)**

**Recommended Order:**
1. Net Worth Tracking (quickest win, uses existing data)
2. Budget Tracking (highest user value)
3. Recurring Detection (moderate complexity, high value)
4. Goal Tracking (completes the suite)

---

## Success Metrics

**Post-Implementation:**
- [ ] All 4 features implemented and tested
- [ ] Database migrations run successfully
- [ ] CLI commands documented in README
- [ ] Integration with existing reports working
- [ ] User can create budgets, track net worth, detect recurring, set goals
- [ ] CLAUDE.md updated with new features

**Quality Metrics:**
- All features have unit tests
- No regressions in existing functionality
- Performance acceptable (queries < 1 second)
- Error handling comprehensive
- Logging in place for debugging
