"""
Base classes for financial institution scrapers
"""

from .broker_base import (
    BrokerAPIClient,
    RequestsHTTPClient,
    LoginCredentials,
    AccountInfo,
    BalanceInfo,
    BrokerAPIError,
    AuthenticationError,
    AccountError,
    BalanceError,
)

from .pension_base import (
    EmailMFARetrieverBase,
    SeleniumMFAAutomatorBase,
    EmailConfig,
    MFAConfig,
)

# New modular components
from .email_retriever import (
    EmailMFARetriever,
    EmailRetrievalError
)

from .mfa_handler import (
    MFAHandler,
    MFAEntryError
)

__all__ = [
    # Broker base
    "BrokerAPIClient",
    "RequestsHTTPClient",
    "LoginCredentials",
    "AccountInfo",
    "BalanceInfo",
    "BrokerAPIError",
    "AuthenticationError",
    "AccountError",
    "BalanceError",
    # Pension base (legacy - will be deprecated)
    "EmailMFARetrieverBase",
    "SeleniumMFAAutomatorBase",
    "EmailConfig",
    "MFAConfig",
    # New modular components
    "EmailMFARetriever",
    "EmailRetrievalError",
    "MFAHandler",
    "MFAEntryError",
]