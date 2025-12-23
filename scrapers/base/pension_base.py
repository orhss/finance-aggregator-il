"""
DEPRECATED: This module is deprecated and will be removed in a future version.

Use the new modular components instead:
    - scrapers.base.email_retriever.EmailMFARetriever (replaces EmailMFARetrieverBase)
    - scrapers.base.mfa_handler.MFAHandler (replaces MFA handling in SeleniumMFAAutomatorBase)
    - scrapers.utils.wait_conditions.SmartWait (replaces time.sleep patterns)
    - scrapers.utils.retry.retry_with_backoff (for retry logic)
    - scrapers.exceptions (for structured error handling)

See scraper_refactoring_plan.md for migration details.
"""

import imaplib
import email
import re
import time
import warnings
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException


def _deprecation_warning(class_name: str, replacement: str):
    """Issue a deprecation warning for legacy classes."""
    warnings.warn(
        f"{class_name} is deprecated and will be removed in a future version. "
        f"Use {replacement} instead. See scraper_refactoring_plan.md for migration details.",
        DeprecationWarning,
        stacklevel=3
    )


@dataclass
class EmailConfig:
    """Configuration for email access"""
    email_address: str
    password: str  # Use app password for Gmail
    imap_server: str = "imap.gmail.com"
    imap_port: int = 993


@dataclass
class MFAConfig:
    """Configuration for MFA automation"""
    sender_email: str  # Email address that sends MFA codes
    sender_name: Optional[str] = None  # Optional sender name to match
    code_pattern: str = r'\b\d{6}\b'  # Regex pattern for 6-digit MFA codes (Migdal format)
    max_wait_time: int = 60  # Maximum seconds to wait for MFA email
    check_interval: int = 5  # Seconds between email checks
    email_delay: int = 30  # Seconds to wait before starting to check for emails
    login_processing_delay: int = 10  # Seconds to wait after MFA submission for page to process
    post_login_delay: int = 5  # Seconds to wait after clicking login button before clicking continue
    mfa_submission_delay: int = 5  # Seconds to wait after entering MFA code before clicking submission button


class EmailMFARetrieverBase(ABC):
    """
    DEPRECATED: Use scrapers.base.email_retriever.EmailMFARetriever instead.

    This class is maintained for backwards compatibility only and will be
    removed in a future version.
    """

    def __init__(self, email_config: EmailConfig, mfa_config: MFAConfig):
        _deprecation_warning(
            "EmailMFARetrieverBase",
            "scrapers.base.email_retriever.EmailMFARetriever"
        )
        self.email_config = email_config
        self.mfa_config = mfa_config
        self.mail_connection = None

    def connect(self) -> bool:
        """Connect to email server"""
        try:
            print(f"Connecting to email server: {self.email_config.imap_server}:{self.email_config.imap_port}")
            self.mail_connection = imaplib.IMAP4_SSL(
                self.email_config.imap_server,
                self.email_config.imap_port
            )
            self.mail_connection.login(
                self.email_config.email_address,
                self.email_config.password
            )
            self.mail_connection.select('inbox')
            print("Inbox selected successfully")
            return True
        except Exception as e:
            print(f"Failed to connect to email: {e}")
            return False

    def disconnect(self):
        """Disconnect from email server"""
        if self.mail_connection:
            try:
                print("Closing email connection...")
                self.mail_connection.close()
                self.mail_connection.logout()
                print("Email connection closed successfully")
            except:
                print("Error during email disconnect, but continuing...")
                pass
            self.mail_connection = None
        else:
            print("No email connection to disconnect")

    def get_recent_mfa_code(self, since_time: datetime = None) -> Optional[str]:
        """Get MFA code from recent emails from service"""
        if not self.mail_connection:
            if not self.connect():
                return None
        try:
            # Search for emails from service MFA sender
            search_criteria = f'FROM "{self.mfa_config.sender_email}"'

            # Add time filter if specified
            if since_time:
                date_str = since_time.strftime("%d-%b-%Y")
                search_criteria += f' SINCE "{date_str}"'

            print(f"Searching for emails with criteria: {search_criteria}")
            status, messages = self.mail_connection.search(None, search_criteria)

            if status != 'OK' or not messages[0]:
                print("No emails found from Migdal MFA sender")
                return None

            # Get the most recent message
            message_ids = messages[0].split()
            if not message_ids:
                print("No message IDs found")
                return None

            print(f"Found {len(message_ids)} emails from Migdal. Checking most recent ones...")

            # Check messages from newest to oldest
            for msg_id in reversed(message_ids[-5:]):  # Check last 5 messages
                status, msg_data = self.mail_connection.fetch(msg_id, '(RFC822)')

                if status != 'OK':
                    continue

                email_message = email.message_from_bytes(msg_data[0][1])

                # Check if email is recent enough
                if since_time and self._is_email_too_old(email_message, since_time):
                    print(f"Email from {email_message['Date']} is too old, skipping...")
                    continue

                print(f"Processing email from {email_message['Date']} with subject: {email_message['Subject']}")

                # Extract MFA code from email
                mfa_code = self.extract_mfa_code(email_message)
                if mfa_code:
                    print(f"Successfully extracted MFA code: {mfa_code}")
                    return mfa_code

            print("No valid MFA codes found in recent emails")
            return None

        except Exception as e:
            print(f"Error retrieving MFA code: {e}")
            return None

    def _is_email_too_old(self, email_message, since_time: datetime) -> bool:
        """Check if email is older than the specified time"""
        try:
            email_date = email.utils.parsedate_to_datetime(email_message['Date'])
            return email_date < since_time
        except:
            return False

    def wait_for_mfa_code(self, since_time: datetime = None) -> Optional[str]:
        """Wait for MFA code to arrive in email"""
        if not since_time:
            since_time = datetime.now() - timedelta(minutes=2)

        print(f"Starting to wait for MFA code since: {since_time.strftime('%Y-%m-%d %H:%M:%S')}")
        start_time = time.time()

        while time.time() - start_time < self.mfa_config.max_wait_time:
            print(
                f"Checking for MFA code... (attempt {int((time.time() - start_time) / self.mfa_config.check_interval) + 1})")
            mfa_code = self.get_recent_mfa_code(since_time)
            if mfa_code:
                elapsed_time = time.time() - start_time
                print(f"MFA code found after {elapsed_time:.1f} seconds!")
                return mfa_code

            elapsed = time.time() - start_time
            remaining = self.mfa_config.max_wait_time - elapsed
            print(f"Waiting for MFA code... ({elapsed:.1f}s elapsed, {remaining:.1f}s remaining)")
            time.sleep(self.mfa_config.check_interval)

        print(f"Timeout waiting for MFA code after {self.mfa_config.max_wait_time} seconds")
        return None

    def wait_for_mfa_code_with_delay(self, since_time: datetime = None) -> Optional[str]:
        """Wait for MFA code with initial delay to allow email to be sent
        
        Args:
            since_time: Time to start looking for emails from
            
        Returns:
            MFA code if found, None otherwise
        """
        # Add configurable delay before starting to look for emails
        # This allows the service time to process the request and send the email
        email_delay = self.mfa_config.email_delay
        print(f"Waiting {email_delay} seconds before checking for MFA email...")
        time.sleep(email_delay)
        
        # Now wait for the MFA code
        return self.wait_for_mfa_code(since_time)

    @abstractmethod
    def extract_mfa_code(self, email_message):
        """Extract MFA code from email content

        :param email_message: Email message object

        :return: Extracted MFA code or None if not found
        """
        pass


class SeleniumMFAAutomatorBase(ABC):
    """
    DEPRECATED: This class is deprecated and will be removed in a future version.

    Use the new modular components instead:
        - scrapers.base.mfa_handler.MFAHandler for MFA code entry
        - scrapers.utils.wait_conditions.SmartWait for intelligent waiting
        - scrapers.utils.retry.retry_selenium_action for retry logic

    This class is maintained for backwards compatibility only.
    """

    def __init__(self, email_retriever: EmailMFARetrieverBase, headless: bool = True):
        _deprecation_warning(
            "SeleniumMFAAutomatorBase",
            "scrapers.base.mfa_handler.MFAHandler and modular components"
        )
        self.email_retriever = email_retriever
        self.headless = headless
        self.driver = None

    def setup_driver(self):
        """Setup Chrome WebDriver"""
        print("Setting up Chrome WebDriver...")
        options = Options()
        if self.headless:
            print("Running in headless mode")
            options.add_argument('--headless')
        else:
            print("Running in visible mode")
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')

        # Add user agent to avoid detection
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        print("Initializing Chrome driver...")
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(10)
        print("Chrome driver initialized successfully")

    def cleanup(self):
        """Clean up resources"""
        print("Starting cleanup process...")
        if self.driver:
            print("Closing Chrome driver...")
            self.driver.quit()
            print("Chrome driver closed successfully")
        else:
            print("No Chrome driver to close")

        print("Disconnecting email retriever...")
        self.email_retriever.disconnect()
        print("Cleanup completed")

    @abstractmethod
    def login(self, site_url: str, credentials: Dict[str, str], selectors: Dict[str, str]) -> bool:
        """Perform login with the given credentials and selectors
        
        Args:
            site_url: URL of the login page
            credentials: Dictionary containing login credentials (e.g., {'id': '123456789'})
            selectors: Dictionary containing CSS selectors for form elements
            
        Returns:
            True if login successful, False otherwise
        """
        pass

    @abstractmethod
    def execute(self, site_url: str, credentials: Dict[str, str], selectors: Dict[str, str]) -> Dict[str, Any]:
        """Execute the complete automation flow (login + data extraction)
        
        Args:
            site_url: URL of the login page
            credentials: Dictionary containing login credentials (e.g., {'id': '123456789'})
            selectors: Dictionary containing CSS selectors for form elements
            
        Returns:
            Dictionary containing extracted financial data, or empty dict if failed
        """
        pass

    def get_and_enter_mfa(self, mfa_code: str, otp_selectors: list) -> bool:
        """Retrieve and enter MFA code into the input fields

        Args:
            mfa_code: The MFA code to enter
            otp_selectors: List of CSS selectors for OTP input fields
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if len(mfa_code) != 6 or not mfa_code.isdigit():
                print(f"Invalid MFA code format: {mfa_code}")
                return False

            print("Entering MFA code into separate fields...")
            for i, field_selector in enumerate(otp_selectors):
                try:
                    field = WebDriverWait(self.driver, self.email_retriever.mfa_config.max_wait_time).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, field_selector))
                    )
                    # Clear the field and enter the digit
                    field.clear()
                    field.send_keys(mfa_code[i])
                    print(f"Entered digit {mfa_code[i]} in field {i + 1}")

                    # Small delay to make it more human-like
                    time.sleep(0.2)

                except TimeoutException:
                    print(f"Timeout waiting for OTP field {i + 1}")
                    return False
                except Exception as e:
                    print(f"Error entering digit in field {i + 1}: {e}")
                    return False

            return True
        except Exception as e:
            print(f"Error in get_and_enter_mfa: {e}")
            return False

    def wait_for_mfa_prompt(self, otp_selector: str = "input[name='otp']", timeout: int = 15):
        """Wait for MFA prompt to appear on the page
        
        Args:
            otp_selector: CSS selector for the first OTP input field
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if MFA prompt found, False otherwise
        """
        try:
            print("Waiting for MFA prompt...")
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, otp_selector))
            )
            print("MFA prompt found")
            return True
        except TimeoutException:
            print(f"Timeout waiting for MFA prompt after {timeout} seconds")
            return False
        except Exception as e:
            print(f"Error waiting for MFA prompt: {e}")
            return False

    def enter_mfa_code_human_like(self, mfa_code: str, otp_selector: str, delay_between_chars: float = 0.2) -> bool:
        """Enter MFA code character by character with human-like typing behavior
        
        Args:
            mfa_code: The MFA code to enter
            otp_selector: CSS selector for the OTP input field
            delay_between_chars: Delay between each character in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if len(mfa_code) != 6 or not mfa_code.isdigit():
                print(f"Invalid MFA code format: {mfa_code}")
                return False

            print(f"Looking for OTP input field with selector: {otp_selector}")
            otp_field = WebDriverWait(self.driver, self.email_retriever.mfa_config.max_wait_time).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, otp_selector))
            )
            print("Found OTP input field")
            
            # Clear the field first
            otp_field.clear()
            
            # Enter MFA code character by character like human typing
            print(f"Typing MFA code character by character: {mfa_code}")
            for digit in mfa_code:
                otp_field.send_keys(digit)
                time.sleep(delay_between_chars)  # Small delay between each character
            
            print(f"Entered MFA code: {mfa_code}")
            
            # Trigger validation by sending blur event
            self.driver.execute_script("arguments[0].blur();", otp_field)
            time.sleep(0.5)
            
            return True
            
        except TimeoutException:
            print(f"Timeout waiting for OTP field with selector: {otp_selector}")
            return False
        except Exception as e:
            print(f"Error entering MFA code: {e}")
            return False

    def check_for_immediate_mfa_field(self, mfa_input_selectors: list) -> bool:
        """Check if MFA input field is already present on the page
        
        Args:
            mfa_input_selectors: List of CSS selectors to try for MFA input fields
            
        Returns:
            True if MFA field found, False otherwise
        """
        try:
            mfa_field_found = False
            for selector in mfa_input_selectors:
                try:
                    field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if field and field.is_displayed():
                        print(f"MFA input field found immediately with selector: {selector}")
                        mfa_field_found = True
                        break
                except:
                    continue
            
            return mfa_field_found
            
        except Exception as e:
            print(f"Error checking for immediate MFA field: {e}")
            return False

    def click_mfa_submission_button(self, primary_selector: str, fallback_selectors: list) -> bool:
        """Click MFA submission button with fallback selectors
        
        Args:
            primary_selector: Primary CSS selector for the MFA submission button
            fallback_selectors: List of fallback selectors to try if primary fails
            
        Returns:
            True if button clicked successfully, False otherwise
        """
        try:
            print("Looking for MFA submission button...")
            
            # Try primary selector first
            try:
                mfa_submit_button = WebDriverWait(self.driver, self.email_retriever.mfa_config.max_wait_time).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, primary_selector))
                )
                print("Found MFA submission button, clicking...")
                mfa_submit_button.click()
                print("Clicked MFA submission button")
                return True
                
            except TimeoutException:
                print("Primary MFA submission button not found, trying fallback selectors...")
                
                # Try fallback selectors
                for selector in fallback_selectors:
                    try:
                        if selector.startswith("//"):
                            # XPath selector
                            button = self.driver.find_element(By.XPATH, selector)
                        else:
                            # CSS selector
                            button = self.driver.find_element(By.CSS_SELECTOR, selector)
                        
                        if button.is_enabled():
                            button.click()
                            print(f"Clicked MFA submission button using fallback selector: {selector}")
                            return True
                    except:
                        continue
                
                print("Could not find or click MFA submission button")
                return False
                
        except Exception as e:
            print(f"Error clicking MFA submission button: {e}")
            return False

    def wait_for_page_processing(self) -> str:
        """Wait for page to process login and redirect after MFA submission
        
        Returns:
            Final URL after processing
        """
        login_delay = self.email_retriever.mfa_config.login_processing_delay
        print(f"Waiting {login_delay} seconds for page to process login...")
        time.sleep(login_delay)
        
        # Check current URL to see if we've been redirected
        current_url = self.driver.current_url
        print(f"Current URL after MFA submission: {current_url}")
        return current_url

    def handle_mfa_flow(self, mfa_code: str, primary_otp: str, otp_fallbacks: list, 
                       primary_submit: str, submit_fallbacks: list) -> bool:
        """Handle complete MFA flow: enter code and submit
        
        Args:
            mfa_code: The MFA code to enter
            primary_otp: Primary selector for OTP input field
            otp_fallbacks: List of fallback selectors for OTP input field
            primary_submit: Primary selector for MFA submission button
            submit_fallbacks: List of fallback selectors for MFA submission button
            
        Returns:
            True if MFA flow completed successfully, False otherwise
        """
        try:
            print("Entering MFA code...")
            
            # Try primary OTP selector first
            if not self.enter_mfa_code_human_like(mfa_code, primary_otp):
                print("Primary OTP field not found, trying fallback selectors...")
                
                # Try fallback OTP selectors
                mfa_entered = False
                for selector in otp_fallbacks:
                    if self.enter_mfa_code_human_like(mfa_code, selector):
                        print(f"Successfully entered MFA code using fallback selector: {selector}")
                        mfa_entered = True
                        break
                
                if not mfa_entered:
                    print("Could not find or enter MFA code in any OTP field")
                    return False
            
            # Click MFA submission button
            if not self.click_mfa_submission_button(primary_submit, submit_fallbacks):
                return False
            
            # Wait for page processing
            final_url = self.wait_for_page_processing()
            
            # Login successful
            print("Login successful!")
            return True
            
        except Exception as e:
            print(f"Error in MFA flow: {e}")
            return False

    def extract_financial_data(self) -> Dict[str, Any]:
        """Extract financial data from the site after successful login
        
        :return: Dictionary containing extracted financial data
        """
        pass

    def enter_mfa_code_individual_fields(self, mfa_code: str, otp_selectors: list, delay_between_chars: float = 0.2) -> bool:
        """Enter MFA code into individual digit fields (like Migdal's otp1, otp2, etc.)
        
        Args:
            mfa_code: The MFA code to enter
            otp_selectors: List of CSS selectors for individual OTP input fields
            delay_between_chars: Delay between each character in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if len(mfa_code) != 6 or not mfa_code.isdigit():
                print(f"Invalid MFA code format: {mfa_code}")
                return False

            if len(otp_selectors) != 6:
                print(f"Expected 6 OTP selectors, got {len(otp_selectors)}")
                return False

            print("Entering MFA code into individual fields...")
            for i, field_selector in enumerate(otp_selectors):
                try:
                    field = WebDriverWait(self.driver, self.email_retriever.mfa_config.max_wait_time).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, field_selector))
                    )
                    # Clear the field and enter the digit
                    field.clear()
                    field.send_keys(mfa_code[i])
                    print(f"Entered digit {mfa_code[i]} in field {i + 1}")

                    # Small delay to make it more human-like
                    time.sleep(delay_between_chars)

                except TimeoutException:
                    print(f"Timeout waiting for OTP field {i + 1}")
                    return False
                except Exception as e:
                    print(f"Error entering digit in field {i + 1}: {e}")
                    return False

            print(f"Successfully entered MFA code: {mfa_code}")
            return True
            
        except Exception as e:
            print(f"Error in enter_mfa_code_individual_fields: {e}")
            return False

    def handle_mfa_flow_individual_fields(self, mfa_code: str, otp_selectors: list, 
                                        primary_submit_selector: str = None, fallback_submit_selectors: list = None) -> bool:
        """Handle complete MFA flow with individual digit fields: enter code and submit
        
        Args:
            mfa_code: The MFA code to enter
            otp_selectors: List of selectors for individual OTP input fields (should be 6)
            primary_submit_selector: Primary selector for MFA submission button (optional)
            fallback_submit_selectors: Fallback selectors for MFA submission button (optional)
            
        Returns:
            True if MFA flow completed successfully, False otherwise
        """
        try:
            print("Entering MFA code into individual fields...")
            
            # Enter MFA code into individual fields
            if not self.enter_mfa_code_individual_fields(mfa_code, otp_selectors):
                print("Failed to enter MFA code into individual fields")
                return False
            
            # Add a delay to allow loader overlays to disappear after entering MFA code
            mfa_submission_delay = getattr(self.email_retriever.mfa_config, 'mfa_submission_delay', 5)
            print(f"Waiting {mfa_submission_delay} seconds after entering MFA code to allow loader overlays to disappear...")
            time.sleep(mfa_submission_delay)
            
            # Click MFA submission button only if selector is provided
            if primary_submit_selector:
                if not self.click_mfa_submission_button(primary_submit_selector, fallback_submit_selectors or []):
                    return False
            else:
                print("No MFA submission button selector provided, skipping button click...")
            
            # Wait for page processing
            final_url = self.wait_for_page_processing()
            
            # Login successful
            print("Login successful!")
            return True
            
        except Exception as e:
            print(f"Error in MFA flow with individual fields: {e}")
            return False

    def click_continue_button_after_mfa_selection(self, primary_selector: str, fallback_selectors: list, 
                                                wait_for_enabled: bool = True, enabled_timeout: int = 5) -> bool:
        """Click continue button after selecting MFA option (like Migdal's pattern)
        
        Note: If a loader overlay appears after login, add a short delay (e.g., time.sleep(3)) before calling this method.
        
        Args:
            primary_selector: Primary CSS selector for the continue button
            fallback_selectors: List of fallback selectors to try if primary fails
            wait_for_enabled: Whether to wait for button to be enabled
            enabled_timeout: Timeout for waiting for button to be enabled
            
        Returns:
            True if button clicked successfully, False otherwise
        """
        try:
            print("Looking for continue button after MFA selection...")
            
            # Try primary selector first
            try:
                continue_button = WebDriverWait(self.driver, self.email_retriever.mfa_config.max_wait_time).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, primary_selector))
                )
                
                # Wait for button to be enabled if required
                if wait_for_enabled:
                    print("Waiting for continue button to be enabled...")
                    WebDriverWait(self.driver, enabled_timeout).until(
                        lambda driver: not continue_button.get_attribute("disabled")
                    )
                
                print("Continue button is enabled, clicking...")
                continue_button.click()
                print("Successfully clicked continue button")
                return True
                
            except TimeoutException:
                print("Primary continue button not found or not enabled, trying fallback selectors...")
                
                # Try fallback selectors
                for selector in fallback_selectors:
                    try:
                        if selector.startswith("//"):
                            # XPath selector
                            button = self.driver.find_element(By.XPATH, selector)
                        else:
                            # CSS selector
                            button = self.driver.find_element(By.CSS_SELECTOR, selector)
                        
                        # Check if button is enabled
                        if not button.get_attribute("disabled"):
                            button.click()
                            print(f"Clicked continue button using fallback selector: {selector}")
                            return True
                        else:
                            print(f"Continue button found but disabled: {selector}")
                            
                    except:
                        continue
                
                print("Could not find or click enabled continue button")
                return False
                
        except Exception as e:
            print(f"Error clicking continue button: {e}")
            return False

    def select_email_mfa_option(self, primary_selector: str, fallback_selectors: list) -> bool:
        """Select email MFA option before proceeding with login (like Migdal's pattern)
        
        Args:
            primary_selector: Primary CSS selector for the email MFA option
            fallback_selectors: List of fallback selectors to try if primary fails
            
        Returns:
            True if email MFA option selected successfully, False otherwise
        """
        try:
            print("Switching to email MFA mode...")
            
            # Try primary selector first
            try:
                email_label = WebDriverWait(self.driver, 30).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, primary_selector))
                )
                email_label.click()
                print("Successfully switched to email MFA mode")
                return True
                
            except TimeoutException:
                print("Primary email MFA option not found, trying fallback selectors...")
                
                # Try fallback selectors
                for selector in fallback_selectors:
                    try:
                        if selector.startswith("//"):
                            # XPath selector
                            email_label = self.driver.find_element(By.XPATH, selector)
                        else:
                            # CSS selector
                            email_label = self.driver.find_element(By.CSS_SELECTOR, selector)
                        
                        email_label.click()
                        print(f"Successfully switched to email MFA mode using fallback selector: {selector}")
                        return True
                        
                    except:
                        continue
                
                print("Could not find email MFA option")
                return False
                
        except Exception as e:
            print(f"Error switching to email MFA mode: {e}")
            return False

    def enter_id_number_human_like(self, id_number: str, id_selector: str, delay_between_chars: float = 0.1) -> bool:
        """Enter ID number with human-like typing behavior
        
        Args:
            id_number: The ID number to enter
            id_selector: CSS selector for the ID input field
            delay_between_chars: Delay between each character in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"Looking for ID input field with selector: {id_selector}")
            id_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, id_selector))
            )
            print("Found ID input field")
            
            # Clear the field first
            id_field.clear()
            
            # Enter ID number character by character like manual typing
            print(f"Typing ID number: {id_number}")
            for digit in id_number:
                id_field.send_keys(digit)
                time.sleep(delay_between_chars)  # Small delay between each character
            
            # Trigger blur event to ensure form validation
            self.driver.execute_script("arguments[0].blur();", id_field)
            time.sleep(0.5)  # Wait for validation to complete
            
            # Verify the ID was entered correctly
            entered_value = id_field.get_attribute("value")
            if entered_value != id_number:
                print(f"Warning: ID value mismatch. Expected: {id_number}, Got: {entered_value}")
                # Try to clear and re-enter manually
                id_field.clear()
                for digit in id_number:
                    id_field.send_keys(digit)
                    time.sleep(delay_between_chars)
                self.driver.execute_script("arguments[0].blur();", id_field)
                time.sleep(0.5)
            
            print(f"Successfully entered ID number: {id_number}")
            return True
            
        except TimeoutException:
            print(f"Timeout waiting for ID field with selector: {id_selector}")
            return False
        except Exception as e:
            print(f"Error entering ID number: {e}")
            return False

    def click_initial_login_button(self, login_button_selector: str, fallback_selectors: list = None) -> bool:
        """Click the initial login button after entering credentials
        
        Args:
            login_button_selector: CSS selector for the login button
            fallback_selectors: List of fallback selectors to try if primary fails
            
        Returns:
            True if button clicked successfully, False otherwise
        """
        try:
            print("Looking for initial login button...")
            
            # Try primary selector first
            try:
                if login_button_selector:
                    login_button = self.driver.find_element(By.CSS_SELECTOR, login_button_selector)
                    if login_button.is_enabled():
                        print("Found enabled login button, clicking...")
                        login_button.click()
                        print("Successfully clicked initial login button")
                        return True
                    else:
                        print("Login button found but disabled")

            except NoSuchElementException:
                print("Primary login button not found, trying fallback selectors...")
            
            # Try fallback selectors if provided
            if fallback_selectors:
                for selector in fallback_selectors:
                    try:
                        if selector.startswith("//"):
                            # XPath selector
                            button = self.driver.find_element(By.XPATH, selector)
                        else:
                            # CSS selector
                            button = self.driver.find_element(By.CSS_SELECTOR, selector)
                        
                        if button.is_enabled():
                            button.click()
                            print(f"Clicked initial login button using fallback selector: {selector}")
                            return True
                        else:
                            print(f"Login button found but disabled: {selector}")
                            
                    except:
                        continue
            
            print("Could not find or click enabled initial login button")
            return False
            
        except Exception as e:
            print(f"Error clicking initial login button: {e}")
            return False

    def login_with_id_and_mfa_flow(self, 
                                  site_url: str,
                                  id_number: str,
                                  id_selector: str,
                                  login_button_selector: str,
                                  email_label_selector: str = None,
                                  continue_button_selector: str = None,
                                  otp_selectors: list = None,
                                  submit_button_selector: str = None,
                                  fallback_selectors: dict = None) -> bool:
        """Complete login flow with ID and MFA automation
        
        Args:
            site_url: URL to login page
            id_number: ID number to enter
            id_selector: CSS selector for ID input field
            login_button_selector: CSS selector for initial login button
            email_label_selector: CSS selector for email MFA option (optional)
            continue_button_selector: CSS selector for continue button after MFA selection (optional)
            otp_selectors: List of OTP input field selectors (optional)
            submit_button_selector: CSS selector for MFA submission button (optional)
            fallback_selectors: Dictionary of fallback selectors for various elements (optional)
            
        Returns:
            True if login successful, False otherwise
        """
        try:
            if not self.driver:
                self.setup_driver()

            # Navigate to login page
            print("Navigating to login page...")
            self.driver.get(site_url)

            # Enter ID number
            if not self.enter_id_number_human_like(id_number, id_selector):
                print("Failed to enter ID number")
                return False

            # Small delay to allow page to update after ID entry
            time.sleep(2)
            print("Waiting for MFA options to appear...")

            # Select email MFA option if provided
            if email_label_selector:
                email_fallbacks = fallback_selectors.get('email_label', []) if fallback_selectors else []
                if not self.select_email_mfa_option(email_label_selector, email_fallbacks):
                    print("Could not select email MFA option, proceeding anyway...")

                # Small delay after selecting email option before clicking login
                time.sleep(1)
                print("Email option selected, proceeding to login...")

            # Click initial login button
            login_fallbacks = fallback_selectors.get('login_button', []) if fallback_selectors else []
            login_time = datetime.now()
            
            if not self.click_initial_login_button(login_button_selector, login_fallbacks):
                print("Failed to click initial login button")
                return False

            # Add a delay to allow loader overlays to disappear
            post_login_delay = getattr(self.email_retriever.mfa_config, 'post_login_delay', 5)
            print(f"Waiting {post_login_delay} seconds after login button to allow loader overlays to disappear...")
            time.sleep(post_login_delay)

            # Click continue button if provided
            if continue_button_selector:
                continue_fallbacks = fallback_selectors.get('continue_button', []) if fallback_selectors else []
                if not self.click_continue_button_after_mfa_selection(continue_button_selector, continue_fallbacks):
                    print("Failed to click continue button")
                    return False

            # Wait for MFA prompt
            if not self.wait_for_mfa_prompt():
                print("Failed to find MFA prompt")
                return False

            # Wait for MFA code in email
            print("Waiting for MFA code in email...")
            mfa_code = self.email_retriever.wait_for_mfa_code_with_delay(login_time)

            if not mfa_code:
                print("Failed to retrieve MFA code")
                return False

            print(f"Retrieved MFA code: {mfa_code}")

            # Handle MFA flow
            if otp_selectors and len(otp_selectors) == 6:
                # Individual digit fields (like Migdal)
                submit_fallbacks = fallback_selectors.get('submit_button', []) if fallback_selectors else []
                if not self.handle_mfa_flow_individual_fields(mfa_code, otp_selectors, 
                                                            submit_button_selector, submit_fallbacks):
                    print("Failed to complete MFA flow with individual fields")
                    return False
            else:
                # Single field (like Phoenix)
                primary_otp = otp_selectors[0] if otp_selectors else "input[name='otp']"
                otp_fallbacks = fallback_selectors.get('otp_field', []) if fallback_selectors else []
                submit_fallbacks = fallback_selectors.get('submit_button', []) if fallback_selectors else []
                
                if not self.handle_mfa_flow(mfa_code, primary_otp, otp_fallbacks, 
                                          submit_button_selector, submit_fallbacks):
                    print("Failed to complete MFA flow")
                    return False

            return True

        except TimeoutException as e:
            print(f"Timeout during login process: {e}")
            return False
        except Exception as e:
            print(f"Error during login: {e}")
            return False

    def login_with_id_email_and_mfa_flow(self, 
                                        site_url: str,
                                        id_number: str,
                                        email: str,
                                        id_selector: str,
                                        email_selector: str,
                                        login_button_selector: str,
                                        otp_selectors: list = None,
                                        submit_button_selector: str = None,
                                        fallback_selectors: dict = None) -> bool:
        """Complete login flow with ID, email and MFA automation (like Phoenix)
        
        Args:
            site_url: URL to login page
            id_number: ID number to enter
            email: Email address to enter
            id_selector: CSS selector for ID input field
            email_selector: CSS selector for email input field
            login_button_selector: CSS selector for login button
            otp_selectors: List of OTP input field selectors (optional)
            submit_button_selector: CSS selector for MFA submission button (optional)
            fallback_selectors: Dictionary of fallback selectors for various elements (optional)
            
        Returns:
            True if login successful, False otherwise
        """
        try:
            if not self.driver:
                self.setup_driver()

            # Navigate to login page
            print("Navigating to login page...")
            self.driver.get(site_url)

            # Enter ID number
            if not self.enter_id_number_human_like(id_number, id_selector):
                print("Failed to enter ID number")
                return False

            # Enter email address
            print(f"Looking for email input field with selector: {email_selector}")
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, email_selector))
            )
            print("Found email input field")
            
            # Clear the field first
            email_field.clear()
            
            # Enter email address
            print(f"Typing email: {email}")
            email_field.send_keys(email)
            
            # Trigger blur event to ensure form validation
            self.driver.execute_script("arguments[0].blur();", email_field)
            time.sleep(0.5)  # Wait for validation to complete

            # Click login button
            login_fallbacks = fallback_selectors.get('login_button', []) if fallback_selectors else []
            login_time = datetime.now()
            
            if not self.click_initial_login_button(login_button_selector, login_fallbacks):
                print("Failed to click login button")
                return False

            # Wait for MFA prompt or check if MFA field is already present
            mfa_input_selectors = otp_selectors if otp_selectors else [
                "input[data-verify-field='otpCode']",
                "input[type='number']",
                "input.input-otp",
                "#otp",
                "input[name='otp']",
                "input[name='otpCode']",
                "input[inputmode='numeric']"
            ]
            
            mfa_field_found = self.check_for_immediate_mfa_field(mfa_input_selectors)
            
            if not mfa_field_found:
                # Wait for MFA prompt
                if not self.wait_for_mfa_prompt():
                    print("Failed to find MFA prompt")
                    return False

            # Wait for MFA code in email
            print("Waiting for MFA code in email...")
            mfa_code = self.email_retriever.wait_for_mfa_code_with_delay(login_time)

            if not mfa_code:
                print("Failed to retrieve MFA code")
                return False

            print(f"Retrieved MFA code: {mfa_code}")

            # Handle MFA flow
            primary_otp = otp_selectors[0] if otp_selectors else "input[data-verify-field='otpCode']"
            otp_fallbacks = fallback_selectors.get('otp_field', []) if fallback_selectors else []
            submit_fallbacks = fallback_selectors.get('submit_button', []) if fallback_selectors else []
            
            if not self.handle_mfa_flow(mfa_code, primary_otp, otp_fallbacks, 
                                      submit_button_selector, submit_fallbacks):
                print("Failed to complete MFA flow")
                return False

            return True

        except TimeoutException as e:
            print(f"Timeout during login process: {e}")
            return False
        except Exception as e:
            print(f"Error during login: {e}")
            return False
