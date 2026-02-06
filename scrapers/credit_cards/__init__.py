"""
Credit card scraper implementations
"""

# Base scraper class
from .base_scraper import BaseCreditCardScraper

# Shared models (used by all scrapers)
from .shared_models import (
    TransactionStatus,
    TransactionType,
    Installments,
    Transaction,
    # Base exceptions
    CreditCardScraperError,
    CreditCardLoginError,
    CreditCardAPIError,
    # CAL exceptions
    CALScraperError,
    CALLoginError,
    CALAuthorizationError,
    CALAPIError,
    # Max exceptions
    MaxScraperError,
    MaxLoginError,
    MaxAPIError,
    # Isracard exceptions
    IsracardScraperError,
    IsracardLoginError,
    IsracardAPIError,
    IsracardChangePasswordError,
)

# CAL scraper
from .cal_credit_card_client import (
    CALCreditCardScraper,
    CALCredentials,
    CardAccount as CALCardAccount,
)

# Max scraper
from .max_credit_card_client import (
    MaxCreditCardScraper,
    MaxCredentials,
    CardAccount as MaxCardAccount,
)

# Isracard scraper
from .isracard_credit_card_client import (
    IsracardCreditCardScraper,
    IsracardCredentials,
    CardAccount as IsracardCardAccount,
)

# Backwards compatibility - CardAccount defaults to CAL's version
CardAccount = CALCardAccount

__all__ = [
    # Base scraper
    "BaseCreditCardScraper",
    # Shared models
    "TransactionStatus",
    "TransactionType",
    "Installments",
    "Transaction",
    # Base exceptions
    "CreditCardScraperError",
    "CreditCardLoginError",
    "CreditCardAPIError",
    # CAL
    "CALCreditCardScraper",
    "CALCredentials",
    "CALCardAccount",
    "CALScraperError",
    "CALLoginError",
    "CALAuthorizationError",
    "CALAPIError",
    # Max
    "MaxCreditCardScraper",
    "MaxCredentials",
    "MaxCardAccount",
    "MaxScraperError",
    "MaxLoginError",
    "MaxAPIError",
    # Isracard
    "IsracardCreditCardScraper",
    "IsracardCredentials",
    "IsracardCardAccount",
    "IsracardScraperError",
    "IsracardLoginError",
    "IsracardAPIError",
    "IsracardChangePasswordError",
    # Backwards compatibility
    "CardAccount",
]
