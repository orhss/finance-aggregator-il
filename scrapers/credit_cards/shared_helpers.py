"""
Shared helper functions for credit card scrapers.

This module contains utility functions used across CAL, Max, and Isracard scrapers.
"""

import re
from datetime import date, timedelta
from typing import Optional, Generator, Dict, List, Any

from scrapers.credit_cards.shared_models import Installments, Transaction


def iterate_months(start_date: date, end_date: date) -> Generator[tuple[int, int], None, None]:
    """
    Generate (year, month) tuples from end_date backwards to start_date.

    Args:
        start_date: Start of date range (inclusive)
        end_date: End of date range (inclusive)

    Yields:
        Tuples of (year, month) in reverse chronological order
    """
    current = end_date
    while current >= start_date:
        yield current.year, current.month
        if current.month == 1:
            current = current.replace(year=current.year - 1, month=12, day=1)
        else:
            current = current.replace(month=current.month - 1, day=1)


def calculate_date_range(months_back: int, months_forward: int = 1) -> tuple[date, date]:
    """
    Calculate start and end dates for transaction fetching.

    Args:
        months_back: Number of months to look back
        months_forward: Number of months to look forward (default 1)

    Returns:
        Tuple of (start_date, end_date)
    """
    today = date.today()
    start = today - timedelta(days=months_back * 30)
    end = today + timedelta(days=months_forward * 30)
    return start, end


def filter_transactions_by_date(
    transactions: List[Transaction],
    start_date: date,
    end_date: date
) -> List[Transaction]:
    """
    Filter transactions to those within date range (inclusive).

    Args:
        transactions: List of Transaction objects
        start_date: Start of date range (inclusive)
        end_date: End of date range (inclusive)

    Returns:
        Filtered list of transactions
    """
    return [
        t for t in transactions
        if start_date <= date.fromisoformat(t.date) <= end_date
    ]


def extract_installments(raw_string: Optional[str]) -> Optional[Installments]:
    """
    Extract installment info from a string like "3/12" or "תשלום 2 מתוך 10".

    Args:
        raw_string: String containing installment numbers

    Returns:
        Installments object if found, None otherwise
    """
    if not raw_string:
        return None
    matches = re.findall(r'\d+', raw_string)
    if len(matches) >= 2:
        return Installments(number=int(matches[0]), total=int(matches[1]))
    return None


def get_cookies(driver: Any) -> Dict[str, str]:
    """
    Extract cookies from Selenium WebDriver as dictionary.

    Args:
        driver: Selenium WebDriver instance

    Returns:
        Dictionary mapping cookie names to values
    """
    cookies = {}
    for cookie in driver.get_cookies():
        cookies[cookie['name']] = cookie['value']
    return cookies


def parse_amount(amount_str: Optional[str]) -> Optional[float]:
    """
    Parse amount string to float, handling commas.

    Args:
        amount_str: String like "1,234.56" or "100.00"

    Returns:
        Float value or None if invalid
    """
    if not amount_str:
        return None
    try:
        # Remove commas and parse
        cleaned = amount_str.replace(",", "")
        return float(cleaned)
    except (ValueError, AttributeError):
        return None