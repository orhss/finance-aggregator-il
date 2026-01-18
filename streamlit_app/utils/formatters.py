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


def format_status(status: str, as_badge: bool = True) -> str:
    """
    Format transaction status with icon and color

    Args:
        status: Status string
        as_badge: If True, return HTML badge. If False, return simple emoji + text

    Returns:
        Formatted status (HTML if as_badge=True, plain text otherwise)
    """
    status_config = {
        'completed': {
            'icon': '✅',
            'color': '#00897b',
            'bg': '#e0f2f1',
            'label': 'Completed'
        },
        'pending': {
            'icon': '⏳',
            'color': '#f57c00',
            'bg': '#fff3e0',
            'label': 'Pending'
        },
        'failed': {
            'icon': '❌',
            'color': '#c62828',
            'bg': '#ffebee',
            'label': 'Failed'
        },
        'success': {
            'icon': '✅',
            'color': '#00897b',
            'bg': '#e0f2f1',
            'label': 'Success'
        },
        'error': {
            'icon': '❌',
            'color': '#c62828',
            'bg': '#ffebee',
            'label': 'Error'
        },
        'running': {
            'icon': '🔄',
            'color': '#1976d2',
            'bg': '#e3f2fd',
            'label': 'Running'
        },
        'active': {
            'icon': '✅',
            'color': '#00897b',
            'bg': '#e0f2f1',
            'label': 'Active'
        },
        'inactive': {
            'icon': '⭕',
            'color': '#666',
            'bg': '#f5f5f5',
            'label': 'Inactive'
        }
    }

    config = status_config.get(status.lower(), {
        'icon': '❓',
        'color': '#666',
        'bg': '#f5f5f5',
        'label': status
    })

    if not as_badge:
        # Simple emoji + text format
        return f"{config['icon']} {config['label']}"

    # HTML badge format
    style = f"""
        display: inline-flex;
        align-items: center;
        background-color: {config['bg']};
        color: {config['color']};
        border-radius: 12px;
        padding: 4px 10px;
        font-size: 0.85rem;
        font-weight: 500;
        gap: 4px;
    """

    return f"<span style='{style}'>{config['icon']} {config['label']}</span>"


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


def format_transaction_with_currency(
    charged_amount: Optional[float],
    charged_currency: str,
    original_amount: Optional[float] = None,
    original_currency: Optional[str] = None,
    show_sign: bool = True
) -> str:
    """
    Format transaction amount showing charged amount primarily and original currency
    in parentheses only if different from charged.

    Best practices:
    - Show charged amount (ILS) as primary for budgeting
    - Show original foreign currency in parentheses only if it differs
    - Use proper minus sign (−) not hyphen (-)

    Args:
        charged_amount: Amount charged in local currency (required)
        charged_currency: Currency code/symbol for charged amount (e.g., 'ILS', '₪')
        original_amount: Original transaction amount (optional, defaults to charged_amount)
        original_currency: Original currency code/symbol (optional, defaults to charged_currency)
        show_sign: If True, show +/- sign for clarity

    Returns:
        Formatted string like "−₪18.50 ($5.00)" or just "−₪18.50" if same currency

    Examples:
        >>> format_transaction_with_currency(-18.50, '₪', -5.00, '$')
        "−₪18.50 ($5.00)"

        >>> format_transaction_with_currency(-100.00, '₪', -100.00, '₪')
        "−₪100.00"

        >>> format_transaction_with_currency(-100.00, '₪')
        "−₪100.00"
    """
    # Default values
    if charged_amount is None:
        return "N/A"

    if original_amount is None:
        original_amount = charged_amount

    if original_currency is None:
        original_currency = charged_currency

    # Normalize currency symbols for comparison
    def normalize_currency(curr):
        """Convert currency codes to symbols for display"""
        curr_map = {
            'ILS': '₪',
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
        }
        return curr_map.get(curr, curr)

    charged_curr_symbol = normalize_currency(charged_currency)
    original_curr_symbol = normalize_currency(original_currency)

    # Format the primary (charged) amount
    if charged_amount < 0:
        primary = f"−{charged_curr_symbol}{abs(charged_amount):,.2f}"
    elif charged_amount > 0:
        primary = f"+{charged_curr_symbol}{charged_amount:,.2f}" if show_sign else f"{charged_curr_symbol}{charged_amount:,.2f}"
    else:
        primary = f"{charged_curr_symbol}{charged_amount:,.2f}"

    # Check if we need to show original currency in parentheses
    # Show only if currencies differ OR amounts differ significantly (>0.01 tolerance)
    currencies_differ = charged_curr_symbol != original_curr_symbol
    amounts_differ = abs(abs(charged_amount) - abs(original_amount)) > 0.01

    if currencies_differ or amounts_differ:
        # Format original amount (without sign, just the value)
        original_formatted = f"{original_curr_symbol}{abs(original_amount):,.2f}"
        return f"{primary} ({original_formatted})"
    else:
        # Same currency and amount, just show primary
        return primary


def format_category_badge(category: str, clickable: bool = False) -> str:
    """
    Format category as colored badge/pill

    Args:
        category: Category name
        clickable: If True, style for clickable appearance (reserved for future use)

    Returns:
        HTML string with styled badge
    """
    if not category:
        return "<span style='color:#999; font-size:0.85rem'>Uncategorized</span>"

    # Color scheme for common categories
    category_colors = {
        'Food & Dining': '#ff6b6b',
        'Transportation': '#4ecdc4',
        'Shopping': '#45b7d1',
        'Entertainment': '#f9ca24',
        'Bills & Utilities': '#6c5ce7',
        'Healthcare': '#fd79a8',
        'Groceries': '#00b894',
        'Salary': '#00897b',
        'Investment': '#1976d2',
        'Transfer': '#95a5a6',
    }

    # Get color or use default
    color = category_colors.get(category, '#95a5a6')

    style = f"""
        display: inline-block;
        background-color: {color}20;
        color: {color};
        border: 1px solid {color}40;
        border-radius: 12px;
        padding: 2px 10px;
        font-size: 0.85rem;
        font-weight: 500;
        margin: 2px;
    """

    return f"<span style='{style}'>{category}</span>"


def format_tags(tags: list[str]) -> str:
    """
    Format multiple tags as badges

    Args:
        tags: List of tag names

    Returns:
        HTML string with all tags as styled badges
    """
    if not tags:
        return ""

    badges = []
    for tag in tags:
        style = """
            display: inline-block;
            background-color: #e3f2fd;
            color: #1976d2;
            border-radius: 10px;
            padding: 2px 8px;
            font-size: 0.8rem;
            margin: 2px;
        """
        badges.append(f"<span style='{style}'>🏷️ {tag}</span>")

    return " ".join(badges)


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
