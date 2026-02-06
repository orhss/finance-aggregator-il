"""
Shared models for credit card scrapers.

This module contains common enums, dataclasses, and exceptions
used across CAL, Max, and Isracard scrapers.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List


# ==================== Transaction Enums ====================

class TransactionStatus(Enum):
    """Transaction status."""
    PENDING = "pending"
    COMPLETED = "completed"


class TransactionType(Enum):
    """Transaction type."""
    NORMAL = "normal"  # Regular charge
    INSTALLMENTS = "installments"  # Payment plan
    CREDIT = "credit"  # Refund (CAL-specific, but harmless to include)


# ==================== Data Classes ====================

@dataclass
class Installments:
    """Installment information."""
    number: int  # Current installment number
    total: int  # Total number of installments


@dataclass
class Transaction:
    """
    Standardized transaction model.

    Used across all credit card scrapers with consistent field names.
    """
    date: str  # ISO format transaction date
    processed_date: str  # ISO format processing/debit date
    original_amount: float  # Original transaction amount
    original_currency: str  # Original currency
    charged_amount: float  # Amount charged in account currency
    charged_currency: Optional[str]  # Account currency (None for pending)
    description: str  # Merchant name
    status: TransactionStatus
    transaction_type: TransactionType
    identifier: Optional[str] = None  # Transaction ID
    memo: Optional[str] = None
    category: Optional[str] = None
    installments: Optional[Installments] = None


# ==================== Base Exceptions ====================

class CreditCardScraperError(Exception):
    """Base exception for all credit card scraper errors."""
    pass


class CreditCardLoginError(CreditCardScraperError):
    """Login failed."""
    pass


class CreditCardAPIError(CreditCardScraperError):
    """API request failed."""
    pass


# ==================== Institution-Specific Exceptions ====================
# These inherit from the base classes for backwards compatibility

# CAL
class CALScraperError(CreditCardScraperError):
    """Base exception for CAL scraper errors."""
    pass


class CALLoginError(CALScraperError, CreditCardLoginError):
    """CAL login failed."""
    pass


class CALAuthorizationError(CALScraperError):
    """CAL authorization token extraction failed."""
    pass


class CALAPIError(CALScraperError, CreditCardAPIError):
    """CAL API request failed."""
    pass


# Max
class MaxScraperError(CreditCardScraperError):
    """Base exception for Max scraper errors."""
    pass


class MaxLoginError(MaxScraperError, CreditCardLoginError):
    """Max login failed."""
    pass


class MaxAPIError(MaxScraperError, CreditCardAPIError):
    """Max API request failed."""
    pass


# Isracard
class IsracardScraperError(CreditCardScraperError):
    """Base exception for Isracard scraper errors."""
    pass


class IsracardLoginError(IsracardScraperError, CreditCardLoginError):
    """Isracard login failed."""
    pass


class IsracardAPIError(IsracardScraperError, CreditCardAPIError):
    """Isracard API request failed."""
    pass


class IsracardChangePasswordError(IsracardScraperError):
    """Isracard password change required."""
    pass
