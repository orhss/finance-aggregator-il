"""
Email MFA code retrieval
Separated from Selenium to allow independent testing and reuse
"""

import imaplib
import email
import re
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    """Configuration for email access"""
    email_address: str
    password: str
    imap_server: str = "imap.gmail.com"
    imap_port: int = 993


@dataclass
class MFAConfig:
    """Configuration for MFA automation"""
    sender_email: str
    sender_name: Optional[str] = None
    code_pattern: str = r'\b\d{6}\b'
    max_wait_time: int = 60
    check_interval: int = 5
    email_delay: int = 30
    login_processing_delay: int = 10
    post_login_delay: int = 5
    mfa_submission_delay: int = 5


class EmailRetrievalError(Exception):
    """Raised when email retrieval fails"""
    pass


class EmailMFARetriever(ABC):
    """
    Base class for retrieving MFA codes from email

    Handles IMAP connection, email searching, and code extraction.
    Subclasses only need to implement institution-specific extraction logic.
    """

    def __init__(self, email_config: EmailConfig, mfa_config: MFAConfig):
        self.email_config = email_config
        self.mfa_config = mfa_config
        self.connection: Optional[imaplib.IMAP4_SSL] = None

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure cleanup"""
        self.disconnect()

    def connect(self) -> bool:
        """
        Connect to email server

        Returns:
            True if connection successful

        Raises:
            EmailRetrievalError: If connection fails
        """
        try:
            logger.info(f"Connecting to {self.email_config.imap_server}:{self.email_config.imap_port}")

            self.connection = imaplib.IMAP4_SSL(
                self.email_config.imap_server,
                self.email_config.imap_port
            )
            self.connection.login(
                self.email_config.email_address,
                self.email_config.password
            )
            self.connection.select('inbox')

            logger.info("Email connection established")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to email: {e}")
            raise EmailRetrievalError(f"Email connection failed: {e}") from e

    def disconnect(self):
        """Disconnect from email server (safe to call multiple times)"""
        if self.connection:
            try:
                logger.debug("Closing email connection")
                self.connection.close()
                self.connection.logout()
                logger.info("Email connection closed")
            except Exception as e:
                logger.warning(f"Error during email disconnect: {e}")
            finally:
                self.connection = None

    def get_recent_mfa_code(self, since_time: Optional[datetime] = None) -> Optional[str]:
        """
        Get MFA code from recent emails

        Args:
            since_time: Only look at emails after this time

        Returns:
            MFA code if found, None otherwise
        """
        if not self.connection:
            self.connect()

        try:
            # Build search criteria
            search_criteria = f'FROM "{self.mfa_config.sender_email}"'
            if since_time:
                date_str = since_time.strftime("%d-%b-%Y")
                search_criteria += f' SINCE "{date_str}"'

            logger.debug(f"Searching emails: {search_criteria}")
            status, messages = self.connection.search(None, search_criteria)

            if status != 'OK' or not messages[0]:
                logger.debug(f"No emails found from {self.mfa_config.sender_email}")
                return None

            message_ids = messages[0].split()
            if not message_ids:
                return None

            logger.info(f"Found {len(message_ids)} emails, checking recent ones")

            # Check last 5 messages (newest first)
            for msg_id in reversed(message_ids[-5:]):
                status, msg_data = self.connection.fetch(msg_id, '(RFC822)')

                if status != 'OK':
                    continue

                email_message = email.message_from_bytes(msg_data[0][1])

                # Check if email is recent enough
                if since_time and self._is_email_too_old(email_message, since_time):
                    logger.debug(f"Email from {email_message['Date']} is too old")
                    continue

                logger.debug(f"Processing email: {email_message['Subject']}")

                # Extract MFA code (institution-specific)
                mfa_code = self.extract_mfa_code(email_message)
                if mfa_code:
                    logger.info(f"MFA code extracted: {mfa_code}")
                    return mfa_code

            logger.warning("No valid MFA codes found in recent emails")
            return None

        except Exception as e:
            logger.error(f"Error retrieving MFA code: {e}")
            return None

    def _is_email_too_old(self, email_message, since_time: datetime) -> bool:
        """Check if email is older than specified time"""
        try:
            email_date = email.utils.parsedate_to_datetime(email_message['Date'])
            return email_date < since_time
        except:
            return False

    def wait_for_mfa_code(
        self,
        since_time: Optional[datetime] = None,
        initial_delay: Optional[int] = None
    ) -> Optional[str]:
        """
        Wait for MFA code to arrive in email

        Args:
            since_time: Only look at emails after this time
            initial_delay: Delay before starting to check (defaults to config)

        Returns:
            MFA code if found within max_wait_time, None otherwise
        """
        if not since_time:
            since_time = datetime.now() - timedelta(minutes=2)

        # Initial delay to allow email to be sent
        delay = initial_delay if initial_delay is not None else self.mfa_config.email_delay
        if delay > 0:
            logger.info(f"Waiting {delay}s before checking for MFA email")
            time.sleep(delay)

        logger.info(f"Waiting for MFA code (max {self.mfa_config.max_wait_time}s)")
        start_time = time.time()
        attempt = 1

        while time.time() - start_time < self.mfa_config.max_wait_time:
            logger.debug(f"Check attempt {attempt}")

            mfa_code = self.get_recent_mfa_code(since_time)
            if mfa_code:
                elapsed = time.time() - start_time
                logger.info(f"MFA code found after {elapsed:.1f}s")
                return mfa_code

            elapsed = time.time() - start_time
            remaining = self.mfa_config.max_wait_time - elapsed
            logger.debug(f"No code yet. Elapsed: {elapsed:.1f}s, Remaining: {remaining:.1f}s")

            time.sleep(self.mfa_config.check_interval)
            attempt += 1

        logger.error(f"Timeout waiting for MFA code after {self.mfa_config.max_wait_time}s")
        return None

    @abstractmethod
    def extract_mfa_code(self, email_message) -> Optional[str]:
        """
        Extract MFA code from email content (institution-specific)

        Args:
            email_message: Email message object

        Returns:
            Extracted MFA code or None
        """
        pass