"""
Shared SQLAlchemy query expressions for transaction queries.

These expressions provide consistent calculations across all services.
"""

from sqlalchemy import func
from db.models import Transaction


def effective_amount_expr():
    """
    SQLAlchemy expression for effective amount.

    Uses charged_amount (actual payment per installment) if available,
    otherwise falls back to original_amount (total purchase price).

    Returns:
        SQLAlchemy COALESCE expression
    """
    return func.coalesce(Transaction.charged_amount, Transaction.original_amount)


def effective_category_expr():
    """
    SQLAlchemy expression for effective category.

    Priority order:
    1. user_category - manual user override
    2. category - normalized from mapping
    3. raw_category - original from provider

    Returns:
        SQLAlchemy COALESCE expression
    """
    return func.coalesce(
        Transaction.user_category,
        Transaction.category,
        Transaction.raw_category
    )


def get_effective_amount(txn: Transaction) -> float:
    """
    Get the effective amount for a transaction object (Python-side).

    Uses charged_amount if available, otherwise original_amount.

    Args:
        txn: Transaction object

    Returns:
        Effective amount as float
    """
    if txn.charged_amount is not None:
        return txn.charged_amount
    return txn.original_amount or 0