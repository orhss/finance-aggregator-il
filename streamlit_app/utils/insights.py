"""
Insight generation utilities for financial data
Provides human-readable summaries and contextual information
"""

from typing import Optional, Dict, Any
from datetime import datetime, date


def generate_spending_insight(stats: Dict[str, Any]) -> Optional[str]:
    """
    Generate human-readable spending insight based on statistics.

    Args:
        stats: Dictionary containing financial statistics with keys:
            - monthly_spending: Current month's total spending
            - monthly_avg_spending: Average monthly spending
            - top_category_this_month: Most-spent category this month
            - transaction_count: Number of transactions

    Returns:
        Human-readable insight string, or None if insufficient data
    """
    monthly_spending = stats.get('monthly_spending', 0)
    monthly_avg = stats.get('monthly_avg_spending')
    top_category = stats.get('top_category_this_month')
    transaction_count = stats.get('transaction_count', 0)

    if not monthly_avg or monthly_avg == 0:
        if transaction_count > 0:
            return f"You have {transaction_count:,} transactions. Keep tracking to see spending insights!"
        return None

    diff_pct = ((monthly_spending - monthly_avg) / monthly_avg) * 100

    if abs(diff_pct) < 5:
        return "Your spending this month is on track with your average. Keep it up!"
    elif diff_pct > 30:
        category_note = f", mostly on {top_category}" if top_category else ""
        return f"You've spent {diff_pct:.0f}% more than usual this month{category_note}. Consider reviewing recent purchases."
    elif diff_pct > 15:
        return f"Spending is {diff_pct:.0f}% higher than your monthly average. You're still within a reasonable range."
    elif diff_pct < -30:
        return f"Great job! You've spent {abs(diff_pct):.0f}% less than your monthly average."
    elif diff_pct < -15:
        return f"Good progress! Spending is {abs(diff_pct):.0f}% below your typical month."
    else:
        direction = "more" if diff_pct > 0 else "less"
        return f"Spending is {abs(diff_pct):.0f}% {direction} than your monthly average."


def generate_balance_insight(stats: Dict[str, Any]) -> Optional[str]:
    """
    Generate insight about account balances.

    Args:
        stats: Dictionary containing:
            - total_balance: Current total balance
            - previous_balance: Balance from previous period
            - account_count: Number of accounts

    Returns:
        Human-readable insight string, or None if insufficient data
    """
    total_balance = stats.get('total_balance', 0)
    previous_balance = stats.get('previous_balance')
    account_count = stats.get('account_count', 0)

    if account_count == 0:
        return None

    if previous_balance is None:
        return f"You're tracking {account_count} account{'s' if account_count > 1 else ''} with a total value of ₪{total_balance:,.2f}."

    change = total_balance - previous_balance
    if previous_balance != 0:
        change_pct = (change / abs(previous_balance)) * 100
    else:
        change_pct = 0

    if abs(change_pct) < 1:
        return "Your portfolio value has remained stable."
    elif change > 0:
        return f"Your portfolio has grown by {change_pct:.1f}% (+₪{change:,.2f})."
    else:
        return f"Your portfolio has decreased by {abs(change_pct):.1f}% (₪{abs(change):,.2f})."


def generate_pending_insight(stats: Dict[str, Any]) -> Optional[str]:
    """
    Generate insight about pending transactions.

    Args:
        stats: Dictionary containing:
            - pending_count: Number of pending transactions
            - pending_amount: Total amount of pending transactions

    Returns:
        Human-readable insight string, or None if no pending transactions
    """
    pending_count = stats.get('pending_count', 0)
    pending_amount = stats.get('pending_amount', 0)

    if pending_count == 0:
        return None

    return f"You have {pending_count} pending transaction{'s' if pending_count > 1 else ''} totaling ₪{abs(pending_amount):,.2f}."


def generate_category_insight(category_data: Dict[str, float], top_n: int = 3) -> Optional[str]:
    """
    Generate insight about spending categories.

    Args:
        category_data: Dictionary mapping category names to amounts
        top_n: Number of top categories to mention

    Returns:
        Human-readable insight string, or None if no data
    """
    if not category_data:
        return None

    # Sort by amount (descending)
    sorted_cats = sorted(category_data.items(), key=lambda x: abs(x[1]), reverse=True)
    total = sum(abs(v) for v in category_data.values())

    if total == 0:
        return None

    top_cats = sorted_cats[:top_n]

    if len(top_cats) == 1:
        cat, amount = top_cats[0]
        pct = (abs(amount) / total) * 100
        return f"Most of your spending ({pct:.0f}%) is on {cat}."

    parts = []
    for cat, amount in top_cats:
        pct = (abs(amount) / total) * 100
        parts.append(f"{cat} ({pct:.0f}%)")

    return f"Top spending categories: {', '.join(parts)}."


def get_time_greeting() -> str:
    """
    Get a time-appropriate greeting.

    Returns:
        Greeting string based on current time
    """
    hour = datetime.now().hour

    if hour < 12:
        return "Good morning"
    elif hour < 17:
        return "Good afternoon"
    else:
        return "Good evening"


def format_period_description(start_date: date, end_date: date) -> str:
    """
    Format a human-readable description of a date range.

    Args:
        start_date: Start of the period
        end_date: End of the period

    Returns:
        Human-readable period description
    """
    today = date.today()

    # Check for common periods
    if start_date.year == end_date.year == today.year:
        if start_date.month == end_date.month == today.month:
            return "This month"
        elif start_date.day == 1 and (end_date - start_date).days < 32:
            return f"{start_date.strftime('%B %Y')}"

    # Calculate days
    days = (end_date - start_date).days

    if days <= 7:
        return "Last week"
    elif days <= 31:
        return "Last month"
    elif days <= 93:
        return "Last 3 months"
    elif days <= 186:
        return "Last 6 months"
    elif days <= 366:
        return "Last year"
    else:
        return f"{start_date.strftime('%b %Y')} - {end_date.strftime('%b %Y')}"


def generate_hub_insight(stats: Dict[str, Any], monthly_trend: Optional[list] = None) -> Optional[Dict[str, str]]:
    """
    Generate a contextual insight for the hub landing page.

    Compares current spending patterns to historical averages and
    provides actionable, positive-focused insights.

    Args:
        stats: Dictionary containing financial statistics with keys:
            - monthly_spending: Current month's total spending
            - transaction_count: Number of transactions
            - pending_count: Number of pending transactions
        monthly_trend: Optional list of monthly data from get_monthly_trend_cached()
            Each item has 'amount' key with that month's spending

    Returns:
        Dictionary with 'message', 'type' (positive/neutral/warning), and 'icon',
        or None if no meaningful insight can be generated
    """
    monthly_spending = stats.get('monthly_spending', 0)
    transaction_count = stats.get('transaction_count', 0)
    pending_count = stats.get('pending_count', 0)

    # Not enough data for insights
    if transaction_count < 10:
        return None

    # Calculate average from monthly trend if available
    monthly_avg = None
    if monthly_trend and len(monthly_trend) >= 2:
        # Exclude current month (last item) from average
        past_months = monthly_trend[:-1] if len(monthly_trend) > 1 else monthly_trend
        if past_months:
            monthly_avg = sum(m.get('amount', 0) for m in past_months) / len(past_months)

    # Monthly comparison
    if monthly_avg and monthly_avg > 0:
        month_diff_pct = ((monthly_spending - monthly_avg) / monthly_avg) * 100

        # Only show meaningful insights past the first week
        day_of_month = datetime.now().day
        if day_of_month >= 7:
            if month_diff_pct <= -15:
                return {
                    'message': f"Spending is {abs(month_diff_pct):.0f}% below your monthly average. Nice!",
                    'type': 'positive',
                    'icon': '💡'
                }
            elif month_diff_pct >= 30 and day_of_month >= 15:
                return {
                    'message': f"Spending is {month_diff_pct:.0f}% above your monthly average.",
                    'type': 'warning',
                    'icon': '📊'
                }

    # Pending transactions insight
    if pending_count >= 5:
        return {
            'message': f"You have {pending_count} pending transactions awaiting clearance.",
            'type': 'neutral',
            'icon': '⏳'
        }

    # No significant insight to show
    return None
