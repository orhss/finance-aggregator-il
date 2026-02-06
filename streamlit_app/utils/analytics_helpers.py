"""
Analytics helper functions.

Pure Python helpers extracted from analytics.py for testability
and to reduce duplication between mobile/desktop views.
"""

from datetime import date, timedelta
from typing import Dict, List, Any, Tuple
from dateutil.relativedelta import relativedelta
import pandas as pd


def get_period_options(today: date) -> Dict[str, Tuple[date, date]]:
    """
    Get standard period options for date range selection.

    Args:
        today: Reference date (usually date.today())

    Returns:
        Dict mapping period name to (start_date, end_date) tuple
    """
    first_of_month = today.replace(day=1)
    last_month_end = first_of_month - timedelta(days=1)
    first_of_last_month = last_month_end.replace(day=1)
    three_months_ago = today - relativedelta(months=3)
    six_months_ago = today - relativedelta(months=6)
    first_of_year = today.replace(month=1, day=1)

    return {
        "This Month": (first_of_month, today),
        "Last Month": (first_of_last_month, last_month_end),
        "Last 3 Months": (three_months_ago, today),
        "Last 6 Months": (six_months_ago, today),
        "This Year": (first_of_year, today),
    }


def transactions_to_dataframe(transactions_list: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Convert transaction list to DataFrame with standard columns.

    Args:
        transactions_list: List of transaction dicts from cache

    Returns:
        DataFrame with columns: id, date, amount, category, description,
        status, account_id, is_expense, day_of_week
    """
    if not transactions_list:
        return pd.DataFrame()

    data = []
    for txn in transactions_list:
        txn_date = txn['transaction_date']
        data.append({
            'id': txn['id'],
            'date': txn_date,
            'amount': txn['original_amount'],
            'category': txn['effective_category'] or 'Uncategorized',
            'description': txn['description'],
            'status': txn['status'],
            'account_id': txn['account_id'],
            'is_expense': txn['original_amount'] < 0,
            'day_of_week': txn_date.strftime('%A') if txn_date else 'Unknown'
        })

    return pd.DataFrame(data)


def calculate_spending_metrics(df_expenses: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate summary spending metrics from expenses DataFrame.

    Args:
        df_expenses: DataFrame of expenses (negative amounts)

    Returns:
        Dict with: total_spending, transaction_count, top_category, avg_transaction
    """
    if df_expenses.empty:
        return {
            'total_spending': 0,
            'transaction_count': 0,
            'top_category': "—",
            'avg_transaction': 0,
        }

    total_spending = abs(df_expenses['amount'].sum())
    transaction_count = len(df_expenses)
    avg_transaction = abs(df_expenses['amount'].mean())

    # Find top category by total spending
    category_totals = df_expenses.groupby('category')['amount'].sum().abs()
    top_category = category_totals.idxmax() if not category_totals.empty else "—"

    return {
        'total_spending': total_spending,
        'transaction_count': transaction_count,
        'top_category': top_category,
        'avg_transaction': avg_transaction,
    }


def get_spending_by_day_of_week(df_expenses: pd.DataFrame) -> pd.Series:
    """
    Get total spending aggregated by day of week.

    Args:
        df_expenses: DataFrame with 'amount' and 'day_of_week' columns

    Returns:
        Series indexed by day name (Monday-Sunday) with spending totals
    """
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    if df_expenses.empty:
        return pd.Series(0, index=day_order)

    day_spending = df_expenses.groupby('day_of_week')['amount'].sum().abs()
    return day_spending.reindex(day_order, fill_value=0)