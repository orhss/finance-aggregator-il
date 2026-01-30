"""
Budget service for managing monthly budgets.

Simple year/month/amount model - no category budgets (KISS principle).
"""

import logging
from datetime import date
from typing import Optional, Dict, Any
from sqlalchemy import func
from sqlalchemy.orm import Session
from db.models import Budget, Transaction
from db.database import get_db
from services.analytics_service import effective_amount_expr

logger = logging.getLogger(__name__)


class BudgetService:
    """
    Service for managing monthly budgets.
    """

    def __init__(self, session: Optional[Session] = None):
        """
        Initialize budget service.

        Args:
            session: SQLAlchemy session (if None, creates a new one)
        """
        self._session = session
        self._owns_session = session is None

    @property
    def session(self) -> Session:
        """Get or create session"""
        if self._session is None:
            self._session = next(get_db())
        return self._session

    def close(self):
        """Close session if owned"""
        if self._owns_session and self._session:
            self._session.close()

    # ==================== Budget CRUD ====================

    def get_budget(self, year: int, month: int) -> Optional[Budget]:
        """
        Get budget for a specific month.

        Args:
            year: Year
            month: Month (1-12)

        Returns:
            Budget object or None if not set
        """
        return self.session.query(Budget).filter(
            Budget.year == year,
            Budget.month == month
        ).first()

    def get_current_budget(self) -> Optional[Budget]:
        """
        Get budget for current month.

        Returns:
            Budget object or None if not set
        """
        today = date.today()
        return self.get_budget(today.year, today.month)

    def set_budget(self, year: int, month: int, amount: float) -> Budget:
        """
        Set or update budget for a specific month.

        Args:
            year: Year
            month: Month (1-12)
            amount: Budget amount

        Returns:
            Budget object (created or updated)
        """
        existing = self.get_budget(year, month)

        if existing:
            existing.amount = amount
            self.session.commit()
            logger.info(f"Updated budget for {year}-{month:02d} to {amount}")
            return existing

        budget = Budget(year=year, month=month, amount=amount)
        self.session.add(budget)
        self.session.commit()
        logger.info(f"Created budget for {year}-{month:02d}: {amount}")
        return budget

    def set_current_budget(self, amount: float) -> Budget:
        """
        Set budget for current month.

        Args:
            amount: Budget amount

        Returns:
            Budget object
        """
        today = date.today()
        return self.set_budget(today.year, today.month, amount)

    def delete_budget(self, year: int, month: int) -> bool:
        """
        Delete budget for a specific month.

        Args:
            year: Year
            month: Month (1-12)

        Returns:
            True if deleted, False if not found
        """
        budget = self.get_budget(year, month)
        if budget:
            self.session.delete(budget)
            self.session.commit()
            logger.info(f"Deleted budget for {year}-{month:02d}")
            return True
        return False

    # ==================== Budget Progress ====================

    def get_monthly_spending(self, year: int, month: int) -> float:
        """
        Get total spending for a specific month.
        Only counts completed expenses (negative amounts).
        Uses effective_amount (charged_amount if available, else original_amount).

        Args:
            year: Year
            month: Month (1-12)

        Returns:
            Total spending (as positive number)
        """
        from sqlalchemy import extract, and_

        result = self.session.query(
            func.sum(effective_amount_expr())
        ).filter(
            and_(
                extract('year', Transaction.transaction_date) == year,
                extract('month', Transaction.transaction_date) == month,
                effective_amount_expr() < 0,
                Transaction.status == 'completed'
            )
        ).scalar()

        return abs(float(result or 0))

    def get_budget_progress(self, year: Optional[int] = None, month: Optional[int] = None) -> Dict[str, Any]:
        """
        Get budget progress for a specific month.

        Args:
            year: Year (default: current)
            month: Month (default: current)

        Returns:
            Dict with: budget, spent, remaining, percent, is_over_budget
            Returns None values if no budget is set
        """
        if year is None or month is None:
            today = date.today()
            year = year or today.year
            month = month or today.month

        budget = self.get_budget(year, month)
        spent = self.get_monthly_spending(year, month)

        if budget is None:
            return {
                'year': year,
                'month': month,
                'budget': None,
                'spent': spent,
                'remaining': None,
                'percent': None,
                'is_over_budget': None
            }

        remaining = budget.amount - spent
        percent = (spent / budget.amount * 100) if budget.amount > 0 else 0

        return {
            'year': year,
            'month': month,
            'budget': budget.amount,
            'spent': spent,
            'remaining': remaining,
            'percent': min(percent, 100),  # Cap at 100 for progress bar
            'percent_actual': percent,  # Actual percentage (can be > 100)
            'is_over_budget': spent > budget.amount
        }

    def get_current_progress(self) -> Dict[str, Any]:
        """
        Get budget progress for current month.

        Returns:
            Dict with budget progress info
        """
        today = date.today()
        return self.get_budget_progress(today.year, today.month)
