"""
Scraper exception hierarchy
Enables granular error handling and recovery
"""

from typing import Optional


class ScraperError(Exception):
    """Base exception for all scraper errors"""
    def __init__(self, message: str, institution: Optional[str] = None):
        self.institution = institution
        super().__init__(message)


# Authentication Errors
class AuthenticationError(ScraperError):
    """Base for authentication failures"""
    pass


class LoginFailedError(AuthenticationError):
    """Login credentials rejected"""
    pass


class MFAFailedError(AuthenticationError):
    """MFA code invalid or expired"""
    pass


class SessionExpiredError(AuthenticationError):
    """Session expired during operation"""
    pass


# Data Extraction Errors
class DataExtractionError(ScraperError):
    """Base for data extraction failures"""
    pass


class ElementNotFoundError(DataExtractionError):
    """Required page element not found"""
    def __init__(self, selector: str, institution: Optional[str] = None):
        self.selector = selector
        super().__init__(f"Element not found: {selector}", institution)


class DataParsingError(DataExtractionError):
    """Failed to parse scraped data"""
    pass


# Network Errors
class NetworkError(ScraperError):
    """Base for network-related failures"""
    pass


class APIError(NetworkError):
    """API request failed"""
    pass


class ConnectionError(NetworkError):
    """Network connection failed"""
    pass


# Validation Errors
class ValidationError(ScraperError):
    """Base for validation failures"""
    pass


class InvalidCredentialsError(ValidationError):
    """Credentials format invalid"""
    pass


class InvalidDataError(ValidationError):
    """Scraped data failed validation"""
    pass


# Recovery strategies
class RecoverableError(ScraperError):
    """Error that can potentially be retried"""
    pass


class FatalError(ScraperError):
    """Error that cannot be recovered from"""
    pass