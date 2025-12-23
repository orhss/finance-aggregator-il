"""
Base classes for financial institution scrapers

New modular architecture (recommended):
- PensionAutomatorBase: Base class for pension site automation
- EmailMFARetriever: Email-based MFA code retrieval
- MFAHandler: MFA code entry into web forms
- SeleniumDriver: WebDriver lifecycle management
- WebActions: Common web interaction utilities

Legacy classes (deprecated):
- EmailMFARetrieverBase: Use EmailMFARetriever instead
- SeleniumMFAAutomatorBase: Use PensionAutomatorBase instead
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

# New modular components (recommended)
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

# Legacy classes (deprecated - kept for backwards compatibility)
from .pension_base import (
    EmailMFARetrieverBase,
    SeleniumMFAAutomatorBase,
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
    # New modular components (recommended)
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
    # Legacy classes (deprecated)
    "EmailMFARetrieverBase",
    "SeleniumMFAAutomatorBase",
]