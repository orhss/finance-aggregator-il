"""
RTL (Right-to-Left) text handling utilities
Primarily for Hebrew text in transaction descriptions
"""

import re
from typing import Optional


def has_hebrew(text: str) -> bool:
    """
    Check if text contains Hebrew characters

    Args:
        text: Text to check

    Returns:
        True if text contains Hebrew characters
    """
    if not text:
        return False
    return any('\u0590' <= c <= '\u05FF' for c in text)


def fix_rtl(text: str) -> str:
    """
    Fix RTL text display for Hebrew by adding RTL markers

    Args:
        text: Text to fix

    Returns:
        Text with RTL markers if Hebrew detected
    """
    if not text:
        return ""

    if has_hebrew(text):
        # Add RTL markers to ensure proper display
        # U+200F is Right-to-Left Mark
        return f'\u200F{text}\u200F'

    return text


def format_description(desc: Optional[str], max_length: Optional[int] = None) -> str:
    """
    Format transaction description with RTL support

    Args:
        desc: Description text
        max_length: Maximum length (truncate if longer)

    Returns:
        Formatted description
    """
    if not desc:
        return ""

    # Clean up description
    desc = desc.strip()

    # Truncate if needed
    if max_length and len(desc) > max_length:
        desc = desc[:max_length - 3] + "..."

    # Apply RTL fix if Hebrew detected
    return fix_rtl(desc)


def mixed_rtl_ltr(text: str) -> str:
    """
    Handle mixed RTL/LTR text (e.g., Hebrew with English/numbers)

    Args:
        text: Mixed text

    Returns:
        Properly formatted mixed text
    """
    if not text:
        return ""

    # If contains Hebrew, treat as RTL
    if has_hebrew(text):
        return fix_rtl(text)

    return text


def clean_merchant_name(merchant: Optional[str]) -> str:
    """
    Clean and format merchant name with RTL support

    Args:
        merchant: Merchant name

    Returns:
        Cleaned merchant name
    """
    if not merchant:
        return "Unknown"

    # Clean up common artifacts
    merchant = merchant.strip()
    merchant = re.sub(r'\s+', ' ', merchant)  # Normalize whitespace

    # Apply RTL fix
    return fix_rtl(merchant)


def rtl_aware_sort_key(text: str) -> str:
    """
    Generate sort key for RTL-aware sorting

    Args:
        text: Text to generate key for

    Returns:
        Sort key
    """
    if not text:
        return ""

    # For Hebrew text, reverse for proper alphabetical sorting
    if has_hebrew(text):
        return text[::-1]

    return text.lower()


def format_mixed_content(text: str) -> str:
    """
    Format content that may contain both Hebrew and English/numbers

    Args:
        text: Mixed content

    Returns:
        Properly formatted content
    """
    if not text:
        return ""

    # Split by common delimiters while preserving them
    parts = re.split(r'(\s+|[-/,.])', text)

    # Process each part
    formatted_parts = []
    for part in parts:
        if part.strip():  # Skip empty parts
            if has_hebrew(part):
                formatted_parts.append(fix_rtl(part))
            else:
                formatted_parts.append(part)
        else:
            formatted_parts.append(part)  # Preserve delimiters

    return ''.join(formatted_parts)


def wrap_in_rtl_div(text: str) -> str:
    """
    Wrap text in HTML div with RTL direction

    Args:
        text: Text to wrap

    Returns:
        HTML div with RTL text
    """
    if not text:
        return ""

    if has_hebrew(text):
        return f'<div style="direction: rtl; text-align: right;">{text}</div>'

    return text
