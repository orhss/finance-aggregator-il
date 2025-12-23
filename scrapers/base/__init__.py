"""
Base classes for financial institution scrapers

Modular architecture:
- PensionAutomatorBase: Base class for pension site automation
- EmailMFARetriever: Email-based MFA code retrieval
- MFAHandler: MFA code entry into web forms
- SeleniumDriver: WebDriver lifecycle management
- WebActions: Common web interaction utilities
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

from .email_retriever import (
    EmailMFARetriever,
    EmailRetrievalError,
    EmailConfig,
    MFAConfig,
)

from .mfa_handler import (
    MFAHandler,
    MFAEntryError,
)

from .selenium_driver import (
    SeleniumDriver,
    DriverConfig,
)

from .web_actions import (
    WebActions,
    WebActionError,
    ElementNotFoundError,
)

from .pension_automator import (
    PensionAutomatorBase,
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
    # Modular components
    "PensionAutomatorBase",
    "EmailMFARetriever",
    "EmailRetrievalError",
    "EmailConfig",
    "MFAConfig",
    "MFAHandler",
    "MFAEntryError",
    "SeleniumDriver",
    "DriverConfig",
    "WebActions",
    "WebActionError",
    "ElementNotFoundError",
]