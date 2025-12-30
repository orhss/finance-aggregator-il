"""
Credit card scraper implementations
"""

from .cal_credit_card_client import (
    CALCreditCardScraper,
    CALCredentials,
    Transaction,
    CardAccount,
    Installments,
    TransactionStatus,
    TransactionType,
    CALScraperError,
    CALLoginError,
    CALAuthorizationError,
    CALAPIError,
)

from .max_credit_card_client import (
    MaxCreditCardScraper,
    MaxCredentials,
    MaxScraperError,
    MaxLoginError,
    MaxAPIError,
)

__all__ = [
    # CAL
    "CALCreditCardScraper",
    "CALCredentials",
    "Transaction",
    "CardAccount",
    "Installments",
    "TransactionStatus",
    "TransactionType",
    "CALScraperError",
    "CALLoginError",
    "CALAuthorizationError",
    "CALAPIError",
    # Max
    "MaxCreditCardScraper",
    "MaxCredentials",
    "MaxScraperError",
    "MaxLoginError",
    "MaxAPIError",
]