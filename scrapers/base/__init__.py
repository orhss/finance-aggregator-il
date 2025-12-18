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
    # Pension base
    "EmailMFARetrieverBase",
    "SeleniumMFAAutomatorBase",
    "EmailConfig",
    "MFAConfig",
]