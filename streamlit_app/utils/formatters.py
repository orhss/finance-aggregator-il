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


def format_account_number(account_num: Optional[str], show_last: int = 4, masked: bool = True) -> str:
    """
    Format account number with masking for security

    Args:
        account_num: Account number
        show_last: Number of digits to show at the end
        masked: If True, mask the account number. If False, show full number

    Returns:
        Masked account number (e.g., "••••1234") or full number
    """
    if not account_num:
        return "N/A"

    # If not masked, return full number
    if not masked:
        return account_num

    # Show only last N digits with bullet points
    if len(account_num) > show_last:
        return f"{'•' * (len(account_num) - show_last)}{account_num[-show_last:]}"
    else:
        return account_num


def mask_card_number(card_num: Optional[str], masked: bool = True) -> str:
    """
    Mask credit card number (show last 4 digits only)

    Args:
        card_num: Credit card number
        masked: If True, mask the card number. If False, show full number

    Returns:
        Masked card number (e.g., "•••• •••• •••• 5678") or full number
    """
    if not card_num:
        return "N/A"

    # If not masked, return full number
    if not masked:
        return card_num

    # Remove spaces/dashes for processing
    clean = card_num.replace(' ', '').replace('-', '')

    if len(clean) < 4:
        return clean

    # Format as card number with spaces
    return f"•••• •••• •••• {clean[-4:]}"


def format_balance(amount: Optional[float], masked: bool = False, currency: str = "₪") -> str:
    """
    Format balance with optional masking

    Args:
        amount: Balance amount
        masked: If True, show bullets instead of amount
        currency: Currency symbol

    Returns:
        Formatted balance or masked string
    """
    if amount is None:
        return "N/A"

    if masked:
        return "••••••"

    return format_currency(amount, currency)


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
        return "#c62828"  # Red for expenses
    elif amount > 0:
        return "#00897b"  # Green for income (teal)
    else:
        return "#757575"  # Gray for zero


def format_transaction_amount(
    amount: Optional[float],
    show_sign: bool = True,
    colored: bool = True,
    currency: str = "₪"
) -> str:
    """
    Format transaction amount with proper sign and optional color.

    Best practices:
    - Use minus sign (−) not hyphen (-) for negative numbers
    - Always show currency symbol (₪)
    - Color code: red for expenses, green for income, gray for zero

    Args:
        amount: Amount to format
        show_sign: If True, show +/- sign
        colored: If True, return HTML with color styling
        currency: Currency symbol

    Returns:
        Formatted amount string (HTML if colored=True)
    """
    if amount is None:
        return "N/A"

    abs_amount = abs(amount)
    formatted = f"{currency}{abs_amount:,.2f}"

    if amount == 0:
        if colored:
            return f"<span style='color:#757575; font-family:\"SF Mono\",\"Roboto Mono\",Consolas,monospace; font-weight:500'>{formatted}</span>"
        return formatted

    # Determine sign and color
    if amount < 0:  # Expense
        sign = "−" if show_sign else ""  # Proper minus sign (U+2212)
        color = "#c62828"  # Material Red 800
    else:  # Income
        sign = "+" if show_sign else ""
        color = "#00897b"  # Material Teal 600

    final_text = f"{sign}{formatted}"

    if colored:
        return f"<span style='color:{color}; font-family:\"SF Mono\",\"Roboto Mono\",Consolas,monospace; font-weight:500'>{final_text}</span>"
    else:
        return final_text


def format_amount_delta(
    current: Optional[float],
    previous: Optional[float],
    currency: str = "₪"
) -> tuple[str, str]:
    """
    Format amount change with delta indicator.

    Args:
        current: Current amount
        previous: Previous amount for comparison
        currency: Currency symbol

    Returns:
        Tuple of (formatted_current, delta_text)
    """
    if current is None:
        return "N/A", ""

    formatted_current = format_currency(current, currency)

    if previous is None or previous == 0:
        return formatted_current, ""

    delta = current - previous
    delta_pct = (delta / abs(previous)) * 100

    if abs(delta_pct) < 0.1:
        return formatted_current, "No change"

    direction = "↑" if delta > 0 else "↓"
    return formatted_current, f"{direction} {abs(delta_pct):.1f}%"


# CSS for monospace amount styling (use in Streamlit pages)
AMOUNT_STYLE_CSS = """
<style>
.financial-amount {
    font-family: 'SF Mono', 'Roboto Mono', 'Consolas', monospace;
    font-size: 1rem;
    font-weight: 500;
    letter-spacing: -0.01em;
}
.amount-positive {
    color: #00897b;
}
.amount-negative {
    color: #c62828;
}
.amount-zero {
    color: #757575;
}
</style>
"""
