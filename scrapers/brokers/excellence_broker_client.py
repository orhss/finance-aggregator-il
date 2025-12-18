from typing import List
import json
import os
from dotenv import load_dotenv

from scrapers.base.broker_base import AccountInfo, BalanceInfo, LoginCredentials, BrokerAPIClient, RequestsHTTPClient

load_dotenv()

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


# Concrete Implementation for ExtradeProAPI
class ExtraDeProAPIClient(BrokerAPIClient):
    """Concrete implementation for ExtradePro broker API"""

    BASE_URL = "https://extradepro.xnes.co.il/api/v2/json2"

    def __init__(self, credentials: LoginCredentials):
        super().__init__(credentials)
        self.http_client = RequestsHTTPClient()
        self._headers = {
            'accept': 'application/json, text/plain, */*',
            'content-type': 'application/json; charset=UTF-8'
        }

    def login(self) -> str:
        """Authenticate with ExtradePro API"""
        url = f"{self.BASE_URL}/login"
        payload = json.dumps({
            "Login": {
                "User": self.credentials.user,
                "Password": self.credentials.password
            }
        })

        response_data = self.http_client.post(url, self._headers, payload)

        session_key = response_data.get("Login", {}).get("SessionKey")
        if not session_key:
            raise AuthenticationError("Failed to obtain session key")

        self.session_key = session_key
        self._headers["session"] = session_key
        return session_key

    def get_accounts(self) -> List[AccountInfo]:
        """Retrieve user accounts from ExtradePro API"""
        if not self.session_key:
            raise AuthenticationError("Must login first")

        url = f"{self.BASE_URL}/accounts"
        response_data = self.http_client.get(url, self._headers)

        user_accounts = response_data.get("UserAccounts", {}).get("UserAccount", [])
        if not user_accounts:
            raise AccountError("No user accounts found")

        self.accounts = [
            AccountInfo(key=account.get("-key", ""))
            for account in user_accounts
        ]

        return self.accounts

    def get_balance(self, account: AccountInfo, currency: str = "ILS") -> BalanceInfo:
        """Get account balance from ExtradePro API"""
        if not self.session_key:
            raise AuthenticationError("Must login first")

        url = f"{self.BASE_URL}/account/view/balances"
        params = {
            "account": account.key,
            "fields": "Balance,Available,Used,Blocked,IsBlocked,IsMargin,IsShorting,IsForeign",
            "currency": currency
        }

        response_data = self.http_client.get(url, self._headers, params)

        view_data = response_data.get("View", {}).get("Account", {})
        if not view_data:
            raise BalanceError("Failed to retrieve balance information")

        return BalanceInfo(
            total_amount=float(view_data.get('MorningValue', 0)),
            profit_loss=view_data.get('AveragePriceNisProfitLoss'),
            profit_loss_percentage=view_data.get('AveragePriceNisProfitLossPercentage'),
            blocked=view_data.get('Blocked'),
            is_blocked=view_data.get('IsBlocked'),
            is_margin=view_data.get('IsMargin'),
            is_shorting=view_data.get('IsShorting'),
            is_foreign=view_data.get('IsForeign')
        )

    def logout(self) -> bool:
        """Logout from ExtradePro API"""
        # Implementation would depend on API specification
        # For now, just clear session data
        self.session_key = None
        if "session" in self._headers:
            del self._headers["session"]
        self.accounts = []
        return True


# Factory Pattern for creating broker clients
class BrokerClientFactory:
    """Factory for creating broker API clients"""

    _clients = {
        'extradepro': ExtraDeProAPIClient
    }

    @classmethod
    def create_client(cls, broker_name: str, credentials: LoginCredentials) -> BrokerAPIClient:
        """Create a broker client instance"""
        if broker_name.lower() not in cls._clients:
            raise ValueError(f"Unsupported broker: {broker_name}")

        client_class = cls._clients[broker_name.lower()]
        return client_class(credentials)


# Facade Pattern - Simplified interface
class BrokerService:
    """Simplified facade for broker operations"""

    def __init__(self, broker_name: str, credentials: LoginCredentials):
        self.client = BrokerClientFactory.create_client(broker_name, credentials)

    def get_total_balance(self, currency: str = "ILS") -> float:
        """Get total balance with simplified interface"""
        try:
            # Login
            self.client.login()

            # Get accounts
            accounts = self.client.get_accounts()
            if not accounts:
                raise AccountError("No accounts available")

            # Get balance for first account
            balance = self.client.get_balance(accounts[0], currency)

            return balance.total_amount

        finally:
            # Always logout
            self.client.logout()


# Usage Example
def main():
    """Example usage of the broker API client"""
    # Create credentials
    credentials = LoginCredentials(os.getenv("EXELLENCE_USER_NAME"), password=os.getenv("EXELLENCE_PASSWORD"))

    # Method 1: Using the service facade
    broker_service = BrokerService("extradepro", credentials)
    total_amount = broker_service.get_total_balance()
    print(f"Total Amount: {total_amount}")

    # Method 2: Using the client directly
    client = BrokerClientFactory.create_client("extradepro", credentials)
    try:
        client.login()
        accounts = client.get_accounts()
        balance = client.get_balance(accounts[0])
        print(f"Balance Details: {balance}")
    finally:
        client.logout()


if __name__ == "__main__":
    main()
