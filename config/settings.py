"""
Configuration and credential management with encryption
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
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
    user_id: Optional[str] = None
    email: Optional[str] = None


class CreditCardCredentials(BaseModel):
    """Credit card credentials"""
    username: Optional[str] = None
    password: Optional[str] = None


class EmailCredentials(BaseModel):
    """Email credentials for MFA"""
    address: Optional[str] = None
    password: Optional[str] = None
    imap_server: str = "imap.gmail.com"


class Credentials(BaseModel):
    """All credentials for different institutions"""
    excellence: BrokerCredentials = Field(default_factory=BrokerCredentials)
    migdal: PensionCredentials = Field(default_factory=PensionCredentials)
    phoenix: PensionCredentials = Field(default_factory=PensionCredentials)
    cal: CreditCardCredentials = Field(default_factory=CreditCardCredentials)
    email: EmailCredentials = Field(default_factory=EmailCredentials)


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

    Returns:
        Credentials object
    """
    # Try loading from encrypted file first
    if CREDENTIALS_FILE.exists():
        try:
            with open(CREDENTIALS_FILE, 'rb') as f:
                encrypted_data = f.read()
            return decrypt_credentials(encrypted_data)
        except Exception as e:
            print(f"Warning: Could not decrypt credentials file: {e}")

    # Fallback to environment variables
    return Credentials(
        excellence=BrokerCredentials(
            username=os.getenv("EXCELLENCE_USERNAME"),
            password=os.getenv("EXCELLENCE_PASSWORD"),
        ),
        migdal=PensionCredentials(
            user_id=os.getenv("MIGDAL_USER_ID"),
            email=os.getenv("USER_EMAIL"),
        ),
        phoenix=PensionCredentials(
            user_id=os.getenv("PHOENIX_USER_ID"),
            email=os.getenv("USER_EMAIL"),
        ),
        cal=CreditCardCredentials(
            username=os.getenv("CAL_USERNAME"),
            password=os.getenv("CAL_PASSWORD"),
        ),
        email=EmailCredentials(
            address=os.getenv("USER_EMAIL"),
            password=os.getenv("USER_EMAIL_APP_PASSWORD"),
        ),
    )


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