"""
Formatting utilities for display
Currency, dates, numbers, etc.
"""

from datetime import datetime, date
from typing import Optional, Union


def format_currency(amount: Optional[float], currency: str = "₪") -> str:
    """
    Format amount as currency with proper symbol and thousands separator

    Args:
        amount: Amount to format
        currency: Currency symbol (default: ₪ for Israeli Shekel)

    Returns:
        Formatted currency string
    """
    if amount is None:
        return "N/A"

    # Format with thousands separator and 2 decimal places
    formatted = f"{abs(amount):,.2f}"

    # Add currency symbol and sign
    if amount < 0:
        return f"-{currency}{formatted}"
    else:
        return f"{currency}{formatted}"


def format_date(dt: Optional[Union[datetime, date, str]], format_str: str = "%Y-%m-%d") -> str:
    """
    Format date/datetime for display

    Args:
        dt: Date/datetime object or string
        format_str: strftime format string

    Returns:
        Formatted date string
    """
    if dt is None:
        return "N/A"

    if isinstance(dt, str):
        # Try to parse string to datetime
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except:
            return dt

    if isinstance(dt, datetime):
        return dt.strftime(format_str)
    elif isinstance(dt, date):
        return dt.strftime(format_str)

    return str(dt)


def format_datetime(dt: Optional[Union[datetime, str]], format_str: str = "%Y-%m-%d %H:%M") -> str:
    """
    Format datetime for display with time

    Args:
        dt: Datetime object or string
        format_str: strftime format string

    Returns:
        Formatted datetime string
    """
    return format_date(dt, format_str)


def format_number(num: Optional[Union[int, float]], decimals: int = 0) -> str:
    """
    Format number with thousands separator

    Args:
        num: Number to format
        decimals: Number of decimal places

    Returns:
        Formatted number string
    """
    if num is None:
        return "N/A"

    if decimals > 0:
        return f"{num:,.{decimals}f}"
    else:
        return f"{int(num):,}"


def format_percentage(value: Optional[float], decimals: int = 1) -> str:
    """
    Format value as percentage

    Args:
        value: Value to format (0.15 = 15%)
        decimals: Number of decimal places

    Returns:
        Formatted percentage string
    """
    if value is None:
        return "N/A"

    return f"{value * 100:.{decimals}f}%"


def format_duration(seconds: Optional[float]) -> str:
    """
    Format duration in seconds to human-readable format

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string (e.g., "2m 30s")
    """
    if seconds is None:
        return "N/A"

    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:.0f}m {secs:.0f}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours:.0f}h {minutes:.0f}m"


def format_account_number(account_num: Optional[str]) -> str:
    """
    Format account number with masking for security

    Args:
        account_num: Account number

    Returns:
        Masked account number (e.g., "****1234")
    """
    if not account_num:
        return "N/A"

    # Show only last 4 digits
    if len(account_num) > 4:
        return f"****{account_num[-4:]}"
    else:
        return account_num


def format_status(status: str) -> str:
    """
    Format status with emoji indicator

    Args:
        status: Status string

    Returns:
        Status with emoji
    """
    status_map = {
        'completed': '✅ Completed',
        'pending': '⏳ Pending',
        'failed': '❌ Failed',
        'success': '✅ Success',
        'error': '❌ Error',
        'running': '🔄 Running',
        'active': '✅ Active',
        'inactive': '⭕ Inactive',
    }

    return status_map.get(status.lower(), status)


def format_institution_name(institution: str) -> str:
    """
    Format institution name with proper capitalization

    Args:
        institution: Institution identifier

    Returns:
        Formatted institution name
    """
    institution_map = {
        'cal': 'CAL',
        'max': 'Max',
        'isracard': 'Isracard',
        'excellence': 'Excellence',
        'meitav': 'Meitav',
        'migdal': 'Migdal',
        'phoenix': 'Phoenix',
    }

    return institution_map.get(institution.lower(), institution.title())


def truncate_text(text: Optional[str], max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate text to max length with suffix

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncated

    Returns:
        Truncated text
    """
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def color_for_amount(amount: float) -> str:
    """
    Get color code for amount (negative=red, positive=green)

    Args:
        amount: Amount value

    Returns:
        Color code
    """
    if amount < 0:
        return "#e74c3c"  # Red for expenses
    elif amount > 0:
        return "#27ae60"  # Green for income
    else:
        return "#95a5a6"  # Gray for zero
