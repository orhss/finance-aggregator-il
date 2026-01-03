"""
Configuration and credential management with encryption
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Default configuration directory
CONFIG_DIR = Path.home() / ".fin"
CONFIG_FILE = CONFIG_DIR / "config.json"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.enc"
KEY_FILE = CONFIG_DIR / ".key"


class BrokerCredentials(BaseModel):
    """Broker credentials"""
    username: Optional[str] = None
    password: Optional[str] = None


class PensionCredentials(BaseModel):
    """Pension fund credentials"""
    user_id: str  # Required for account
    label: Optional[str] = None  # Optional label like "Personal", "Work"


class CreditCardCredentials(BaseModel):
    """Credit card credentials"""
    username: str  # Required for account
    password: str  # Required for account
    label: Optional[str] = None  # Optional label like "Personal", "Business"


class EmailCredentials(BaseModel):
    """Email credentials for MFA"""
    address: Optional[str] = None
    password: Optional[str] = None
    imap_server: str = "imap.gmail.com"


class Credentials(BaseModel):
    """All credentials for different institutions"""
    excellence: BrokerCredentials = Field(default_factory=BrokerCredentials)
    migdal: List[PensionCredentials] = Field(default_factory=list)  # Multi-account support
    phoenix: List[PensionCredentials] = Field(default_factory=list)  # Multi-account support
    cal: List[CreditCardCredentials] = Field(default_factory=list)  # Multi-account support
    max: List[CreditCardCredentials] = Field(default_factory=list)  # Multi-account support
    email: EmailCredentials = Field(default_factory=EmailCredentials)

    def get_cc_accounts(self, institution: str) -> List[CreditCardCredentials]:
        """Get credit card accounts by institution (DRY helper)"""
        return getattr(self, institution.lower())

    def get_pension_accounts(self, institution: str) -> List[PensionCredentials]:
        """Get pension accounts by institution (DRY helper)"""
        return getattr(self, institution.lower())


class Settings(BaseSettings):
    """
    Application settings
    """
    # Database settings
    database_path: Path = CONFIG_DIR / "financial_data.db"

    # Scraper settings
    headless: bool = True
    timeout: int = 30
    max_retries: int = 3

    # Sync settings
    default_months_back: int = 3
    default_months_forward: int = 1

    class Config:
        env_prefix = "FIN_"
        case_sensitive = False


def get_encryption_key() -> bytes:
    """
    Get or create encryption key for credentials

    Returns:
        Encryption key as bytes
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if KEY_FILE.exists():
        with open(KEY_FILE, 'rb') as f:
            return f.read()
    else:
        # Generate new key
        key = Fernet.generate_key()
        with open(KEY_FILE, 'wb') as f:
            f.write(key)
        # Set restrictive permissions (readable only by owner)
        os.chmod(KEY_FILE, 0o600)
        return key


def encrypt_credentials(credentials: Credentials) -> bytes:
    """
    Encrypt credentials

    Args:
        credentials: Credentials object

    Returns:
        Encrypted credentials as bytes
    """
    key = get_encryption_key()
    fernet = Fernet(key)
    credentials_json = credentials.model_dump_json()
    return fernet.encrypt(credentials_json.encode())


def decrypt_credentials(encrypted_data: bytes) -> Credentials:
    """
    Decrypt credentials

    Args:
        encrypted_data: Encrypted credentials

    Returns:
        Credentials object
    """
    key = get_encryption_key()
    fernet = Fernet(key)
    decrypted_data = fernet.decrypt(encrypted_data)
    credentials_dict = json.loads(decrypted_data.decode())
    return Credentials(**credentials_dict)


def save_credentials(credentials: Credentials):
    """
    Save encrypted credentials to file

    Args:
        credentials: Credentials object
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    encrypted = encrypt_credentials(credentials)

    with open(CREDENTIALS_FILE, 'wb') as f:
        f.write(encrypted)

    # Set restrictive permissions
    os.chmod(CREDENTIALS_FILE, 0o600)


def load_credentials() -> Credentials:
    """
    Load credentials from file or environment variables

    Handles migration from old single-account format to new multi-account format.

    Returns:
        Credentials object
    """
    # Try loading from encrypted file first
    if CREDENTIALS_FILE.exists():
        try:
            with open(CREDENTIALS_FILE, 'rb') as f:
                encrypted_data = f.read()

            # Decrypt and parse
            key = get_encryption_key()
            fernet = Fernet(key)
            decrypted_data = fernet.decrypt(encrypted_data)
            raw_data = json.loads(decrypted_data.decode())

            # MIGRATION: Convert old single-account format to list
            for institution in ['cal', 'max', 'migdal', 'phoenix']:
                if institution in raw_data:
                    value = raw_data[institution]

                    # Old format: single dict with credentials
                    if isinstance(value, dict):
                        # Credit cards have username/password
                        if 'username' in value:
                            if value.get('username') and value.get('password'):
                                raw_data[institution] = [value]  # Wrap in list
                            else:
                                raw_data[institution] = []  # Empty list if no credentials
                        # Pensions have user_id
                        elif 'user_id' in value and value.get('user_id'):
                            raw_data[institution] = [value]  # Wrap in list
                        # Empty dict
                        else:
                            raw_data[institution] = []

                    # Already new format: list of dicts
                    elif isinstance(value, list):
                        pass  # No migration needed

                    # Empty or null
                    else:
                        raw_data[institution] = []

            return Credentials(**raw_data)

        except Exception as e:
            print(f"Warning: Could not decrypt credentials file: {e}")

    # Fallback to environment variables
    return _load_from_environment()


def _load_from_environment() -> Credentials:
    """Load credentials from environment variables"""

    # Load single-account broker
    excellence = BrokerCredentials(
        username=os.getenv("EXCELLENCE_USERNAME"),
        password=os.getenv("EXCELLENCE_PASSWORD"),
    )

    # Load multi-account pensions
    migdal_accounts = _load_numbered_pension_accounts('MIGDAL')
    phoenix_accounts = _load_numbered_pension_accounts('PHOENIX')

    # Load multi-account credit cards
    cal_accounts = _load_numbered_accounts('CAL')
    max_accounts = _load_numbered_accounts('MAX')

    email = EmailCredentials(
        address=os.getenv("USER_EMAIL"),
        password=os.getenv("USER_EMAIL_APP_PASSWORD"),
    )

    return Credentials(
        excellence=excellence,
        migdal=migdal_accounts,
        phoenix=phoenix_accounts,
        cal=cal_accounts,
        max=max_accounts,
        email=email,
    )


def _load_numbered_accounts(prefix: str) -> List[CreditCardCredentials]:
    """
    Load numbered accounts from environment variables

    Supports both:
    - Old format: CAL_USERNAME, CAL_PASSWORD (single account)
    - New format: CAL_1_USERNAME, CAL_1_PASSWORD, CAL_2_USERNAME, etc.

    Args:
        prefix: 'CAL' or 'MAX'

    Returns:
        List of CreditCardCredentials
    """
    accounts = []

    # Try old single-account format first
    username = os.getenv(f"{prefix}_USERNAME")
    password = os.getenv(f"{prefix}_PASSWORD")

    if username and password:
        accounts.append(CreditCardCredentials(
            username=username,
            password=password,
            label=None
        ))
        return accounts

    # Try numbered accounts (CAL_1_*, CAL_2_*, etc.)
    idx = 1
    while True:
        username = os.getenv(f"{prefix}_{idx}_USERNAME")
        password = os.getenv(f"{prefix}_{idx}_PASSWORD")
        label = os.getenv(f"{prefix}_{idx}_LABEL")

        if not username or not password:
            break  # No more accounts

        accounts.append(CreditCardCredentials(
            username=username,
            password=password,
            label=label
        ))
        idx += 1

    return accounts


def _load_numbered_pension_accounts(prefix: str) -> List[PensionCredentials]:
    """
    Load numbered pension accounts from environment variables

    Supports both:
    - Old format: MIGDAL_USER_ID (single account)
    - New format: MIGDAL_1_USER_ID, MIGDAL_2_USER_ID, etc.

    Args:
        prefix: 'MIGDAL' or 'PHOENIX'

    Returns:
        List of PensionCredentials
    """
    accounts = []

    # Try old single-account format first
    user_id = os.getenv(f"{prefix}_USER_ID")

    if user_id:
        accounts.append(PensionCredentials(
            user_id=user_id,
            label=None
        ))
        return accounts

    # Try numbered accounts (MIGDAL_1_*, MIGDAL_2_*, etc.)
    idx = 1
    while True:
        user_id = os.getenv(f"{prefix}_{idx}_USER_ID")
        label = os.getenv(f"{prefix}_{idx}_LABEL")

        if not user_id:
            break  # No more accounts

        accounts.append(PensionCredentials(
            user_id=user_id,
            label=label
        ))
        idx += 1

    return accounts


def update_credential(institution: str, field: str, value: str):
    """
    Update a specific credential field

    Args:
        institution: Institution name (e.g., 'cal', 'excellence', 'email')
        field: Field name (e.g., 'username', 'password')
        value: New value
    """
    credentials = load_credentials()

    # Update the specific field
    if hasattr(credentials, institution):
        inst_creds = getattr(credentials, institution)
        if hasattr(inst_creds, field):
            setattr(inst_creds, field, value)
            save_credentials(credentials)
        else:
            raise ValueError(f"Field '{field}' not found for institution '{institution}'")
    else:
        raise ValueError(f"Institution '{institution}' not found")


def get_settings() -> Settings:
    """
    Get application settings

    Returns:
        Settings object
    """
    return Settings()


def save_config(config: Dict[str, Any]):
    """
    Save general configuration (non-sensitive)

    Args:
        config: Configuration dictionary
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def load_config() -> Dict[str, Any]:
    """
    Load general configuration

    Returns:
        Configuration dictionary
    """
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}


def get_card_holders() -> Dict[str, str]:
    """
    Get card holder mappings (last 4 digits -> name)

    Returns:
        Dictionary mapping card last 4 digits to holder name
    """
    config = load_config()
    return config.get("card_holders", {})


def set_card_holder(last4: str, name: str):
    """
    Set card holder name for a card

    Args:
        last4: Last 4 digits of the card
        name: Name/label for the card holder (e.g., "Husband", "Wife", "Or")
    """
    config = load_config()
    if "card_holders" not in config:
        config["card_holders"] = {}
    config["card_holders"][last4] = name
    save_config(config)


def remove_card_holder(last4: str) -> bool:
    """
    Remove card holder mapping

    Args:
        last4: Last 4 digits of the card

    Returns:
        True if removed, False if not found
    """
    config = load_config()
    if "card_holders" in config and last4 in config["card_holders"]:
        del config["card_holders"][last4]
        save_config(config)
        return True
    return False


def get_card_holder_name(last4: str) -> Optional[str]:
    """
    Get card holder name for a specific card

    Args:
        last4: Last 4 digits of the card

    Returns:
        Card holder name or None if not configured
    """
    return get_card_holders().get(last4)


# Multi-Account Credit Card Management (DRY)

def _find_account_index(accounts: List[CreditCardCredentials], identifier: str) -> Optional[int]:
    """
    Find account index by identifier (index number or label) - DRY helper

    Args:
        accounts: List of credit card accounts
        identifier: Index number (as string) or label name

    Returns:
        Index if found, None otherwise
    """
    # Try as index
    try:
        idx = int(identifier)
        return idx if 0 <= idx < len(accounts) else None
    except ValueError:
        pass

    # Try as label
    for idx, account in enumerate(accounts):
        if account.label == identifier:
            return idx

    return None


def manage_cc_account(
    institution: str,
    operation: str,
    identifier: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    label: Optional[str] = None
) -> Tuple[bool, Optional[List[CreditCardCredentials]]]:
    """
    Generic function for all credit card account operations (DRY)

    Args:
        institution: 'cal' or 'max'
        operation: 'list', 'add', 'remove', 'update'
        identifier: Account index or label (for remove/update)
        username, password, label: Account credentials (for add/update)

    Returns:
        (success, accounts_list) - accounts_list only for 'list' operation
    """
    if institution not in ['cal', 'max']:
        raise ValueError(f"Invalid institution: {institution}")

    credentials = load_credentials()
    accounts = credentials.get_cc_accounts(institution)

    if operation == 'list':
        return True, accounts

    elif operation == 'add':
        accounts.append(CreditCardCredentials(
            username=username,
            password=password,
            label=label
        ))
        save_credentials(credentials)
        return True, None

    elif operation in ['remove', 'update']:
        idx = _find_account_index(accounts, identifier)
        if idx is None:
            return False, None

        if operation == 'remove':
            accounts.pop(idx)
        else:  # update
            if username is not None:
                accounts[idx].username = username
            if password is not None:
                accounts[idx].password = password
            if label is not None:
                accounts[idx].label = label

        save_credentials(credentials)
        return True, None

    raise ValueError(f"Invalid operation: {operation}")


def select_accounts_to_sync(
    institution: str,
    filters: Optional[List[str]] = None
) -> List[Tuple[int, CreditCardCredentials]]:
    """
    Select accounts to sync (DRY helper)

    Args:
        institution: 'cal' or 'max'
        filters: List of indices or labels (None = all)

    Returns:
        List of (index, account) tuples
    """
    _, accounts = manage_cc_account(institution, 'list')

    if not accounts:
        raise ValueError(f"No {institution.upper()} accounts configured")

    # No filter = all accounts
    if not filters:
        return list(enumerate(accounts))

    # Build selected list
    selected = []
    for filter_str in filters:
        idx = _find_account_index(accounts, filter_str)
        if idx is None:
            raise ValueError(f"Account not found: {filter_str}")
        selected.append((idx, accounts[idx]))

    return selected


# Multi-Account Pension Management (DRY - reuses patterns from credit cards)

def manage_pension_account(
    institution: str,
    operation: str,
    identifier: Optional[str] = None,
    user_id: Optional[str] = None,
    label: Optional[str] = None
) -> Tuple[bool, Optional[List[PensionCredentials]]]:
    """
    Generic function for all pension account operations (DRY - mirrors manage_cc_account)

    Args:
        institution: 'migdal' or 'phoenix'
        operation: 'list', 'add', 'remove', 'update'
        identifier: Account index or label (for remove/update)
        user_id: User ID for account (for add/update)
        label: Optional label (for add/update)

    Returns:
        (success, accounts_list) - accounts_list only for 'list' operation
    """
    if institution not in ['migdal', 'phoenix']:
        raise ValueError(f"Invalid institution: {institution}")

    credentials = load_credentials()
    accounts = credentials.get_pension_accounts(institution)

    if operation == 'list':
        return True, accounts

    elif operation == 'add':
        accounts.append(PensionCredentials(
            user_id=user_id,
            label=label
        ))
        save_credentials(credentials)
        return True, None

    elif operation in ['remove', 'update']:
        idx = _find_account_index(accounts, identifier)  # Reuses credit card helper!
        if idx is None:
            return False, None

        if operation == 'remove':
            accounts.pop(idx)
        else:  # update
            if user_id is not None:
                accounts[idx].user_id = user_id
            if label is not None:
                accounts[idx].label = label

        save_credentials(credentials)
        return True, None

    raise ValueError(f"Invalid operation: {operation}")


def select_pension_accounts_to_sync(
    institution: str,
    filters: Optional[List[str]] = None
) -> List[Tuple[int, PensionCredentials]]:
    """
    Select pension accounts to sync (DRY - mirrors select_accounts_to_sync)

    Args:
        institution: 'migdal' or 'phoenix'
        filters: List of indices or labels (None = all)

    Returns:
        List of (index, account) tuples
    """
    _, accounts = manage_pension_account(institution, 'list')

    if not accounts:
        raise ValueError(f"No {institution.upper()} accounts configured")

    # No filter = all accounts
    if not filters:
        return list(enumerate(accounts))

    # Build selected list
    selected = []
    for filter_str in filters:
        idx = _find_account_index(accounts, filter_str)  # Reuses credit card helper!
        if idx is None:
            raise ValueError(f"Account not found: {filter_str}")
        selected.append((idx, accounts[idx]))

    return selected