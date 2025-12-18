from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import requests


# Data Transfer Objects (DTOs)
@dataclass
class LoginCredentials:
    user: str
    password: str


@dataclass
class AccountInfo:
    key: str
    name: Optional[str] = None


@dataclass
class BalanceInfo:
    total_amount: float
    profit_loss: float
    profit_loss_percentage: float
    available: Optional[float] = None
    used: Optional[float] = None
    blocked: Optional[float] = None
    is_blocked: Optional[bool] = None
    is_margin: Optional[bool] = None
    is_shorting: Optional[bool] = None
    is_foreign: Optional[bool] = None


# Exceptions
class BrokerAPIError(Exception):
    """Base exception for broker API errors"""
    pass


class AuthenticationError(BrokerAPIError):
    """Raised when authentication fails"""
    pass


class AccountError(BrokerAPIError):
    """Raised when account operations fail"""
    pass


class BalanceError(BrokerAPIError):
    """Raised when balance operations fail"""
    pass


# Abstract Base Classes
class BrokerAPIClient(ABC):
    """Abstract base class for broker API clients"""

    def __init__(self, credentials: LoginCredentials):
        self.credentials = credentials
        self.session_key: Optional[str] = None
        self.accounts: List[AccountInfo] = []

    @abstractmethod
    def login(self) -> str:
        """Authenticate with the broker and return session key"""
        pass

    @abstractmethod
    def get_accounts(self) -> List[AccountInfo]:
        """Retrieve user accounts"""
        pass

    @abstractmethod
    def get_balance(self, account: AccountInfo, currency: str = "ILS") -> BalanceInfo:
        """Get account balance information"""
        pass

    @abstractmethod
    def logout(self) -> bool:
        """Logout and cleanup session"""
        pass


# HTTP Client
class RequestsHTTPClient:
    """HTTP client using requests library"""

    def post(self, url: str, headers: Dict[str, str], data: str) -> Dict[str, Any]:
        try:
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise BrokerAPIError(f"HTTP POST request failed: {e}")

    def get(self, url: str, headers: Dict[str, str], params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise BrokerAPIError(f"HTTP GET request failed: {e}")
