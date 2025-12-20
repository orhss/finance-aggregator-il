import os
import re
import time
from datetime import datetime
from typing import Optional, Dict, Any
import logging

import dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# New modular imports
from scrapers.base.email_retriever import (
    EmailMFARetriever,
    EmailConfig,
    MFAConfig
)
from scrapers.base.pension_base import (
    SeleniumMFAAutomatorBase,
)

logger = logging.getLogger(__name__)
dotenv.load_dotenv()


class MigdalEmailMFARetriever(EmailMFARetriever):
    """Handles retrieving MFA codes from email for Migdal pension site"""

    def __init__(self, email_config: EmailConfig, mfa_config: MFAConfig):
        super().__init__(email_config, mfa_config)

    def extract_mfa_code(self, email_message) -> Optional[str]:
        """Extract MFA code from email content - specifically for Migdal format"""
        try:
            # Get email content (both HTML and plain text)
            html_content = ""
            plain_content = ""

            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/html":
                        html_content += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    elif part.get_content_type() == "text/plain":
                        plain_content += part.get_payload(decode=True).decode('utf-8', errors='ignore')
            else:
                if email_message.get_content_type() == "text/html":
                    html_content = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
                else:
                    plain_content = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')

            # First, try to extract from HTML content (Migdal format)
            if html_content:
                # Look for h2 elements containing the code
                h2_pattern = r'<h2[^>]*>.*?(\d{6}).*?</h2>'
                h2_matches = re.findall(h2_pattern, html_content, re.DOTALL | re.IGNORECASE)

                if h2_matches:
                    logger.info(f"Found MFA code in h2 element: {h2_matches[0]}")
                    return h2_matches[0]

                # If no h2 match, try general HTML content
                html_matches = re.findall(self.mfa_config.code_pattern, html_content)
                if html_matches:
                    logger.info(f"Found MFA code in HTML content: {html_matches[0]}")
                    return html_matches[0]

            # Fallback to plain text content
            if plain_content:
                plain_matches = re.findall(self.mfa_config.code_pattern, plain_content)
                if plain_matches:
                    logger.info(f"Found MFA code in plain text: {plain_matches[0]}")
                    return plain_matches[0]

            logger.warning("No MFA code found in email content")
            return None

        except Exception as e:
            logger.error(f"Error extracting MFA code: {e}", exc_info=True)
            return None


class MigdalSeleniumMFAAutomator(SeleniumMFAAutomatorBase):
    """Handles Selenium automation with MFA for Migdal pension site"""

    def __init__(self, email_retriever: MigdalEmailMFARetriever, headless: bool = True):
        super().__init__(email_retriever, headless)

    def login(self, site_url: str, credentials: Dict[str, str], selectors: Dict[str, str]) -> bool:
        """Implement the abstract login method for Migdal site
        
        Args:
            site_url: URL of the login page
            credentials: Dictionary containing login credentials (e.g., {'id': '123456789'})
            selectors: Dictionary containing CSS selectors for form elements
            
        Returns:
            True if login successful, False otherwise
        """
        id_number = credentials.get('id')
        if not id_number:
            logger.error("ID number not provided in credentials")
            return False
            
        return self.login_with_id_and_mfa(
            site_url=site_url,
            id_number=id_number,
            id_selector=selectors.get('id_selector', "input#username[type='number']"),
            login_button_selector=selectors.get('login_button_selector', 'button[type="submit"]'),
            email_label_selector=selectors.get('email_label_selector', 'label[for="otpToEmail"]'),
            continue_button_selector=selectors.get('continue_button_selector', 'button.form-btn'),
            success_indicator=selectors.get('success_indicator', '.dashboard')
        )

    def login_with_id_and_mfa(self,
                              site_url: str,
                              id_number: str,
                              id_selector: str,
                              login_button_selector: str,
                              email_label_selector: str,
                              continue_button_selector: str,
                              success_indicator: str) -> bool:
        """
        Perform login with ID and MFA automation for Migdal site
        
        Args:
            site_url: URL to login page
            id_number: Israeli ID number (9 digits including check digit)
            id_selector: CSS selector for ID input field
            login_button_selector: CSS selector for login button
            email_label_selector: CSS selector for email MFA option label
            continue_button_selector: CSS selector for continue button after MFA selection
            success_indicator: Selector to confirm successful login
        """
        try:
            # Define OTP selectors for individual digit fields (Migdal pattern)
            otp_selectors = [
                "input[name='otp']",
                "input[name='otp2']",
                "input[name='otp3']",
                "input[name='otp4']",
                "input[name='otp5']",
                "input[name='otp6']"
            ]
            
            # Define fallback selectors for various elements
            fallback_selectors = {
                'email_label': [
                    "//label[contains(text(), 'מייל') or contains(text(), 'Email')]"
                ],
                'login_button': [
                    "//button[contains(text(), 'כניסה') or contains(text(), 'Login')]"
                ],
                'continue_button': [
                    "//button[contains(., 'המשך') or contains(., 'Continue')]"
                ],
                'submit_button': [
                    "//button[contains(text(), 'כניסה') or contains(text(), 'Login')]"
                ]
            }
            
            # Use the comprehensive base method for login flow
            return self.login_with_id_and_mfa_flow(
                site_url=site_url,
                id_number=id_number,
                id_selector=id_selector,
                login_button_selector=login_button_selector,
                email_label_selector=email_label_selector,
                continue_button_selector=continue_button_selector,
                otp_selectors=otp_selectors,
                fallback_selectors=fallback_selectors
            )

        except Exception as e:
            logger.error(f"Error during Migdal login: {e}", exc_info=True)
            return False

    def extract_financial_data(self) -> Dict[str, Any]:
        """Extract financial data from Migdal pension site after successful login"""
        data = {}

        try:
            logger.info("Extracting financial data from Migdal site...")

            # Wait for the financial data to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.carusel-cube"))
            )

            # Extract pension balance (קרנות פנסיה)
            try:
                pension_cube = self.driver.find_element(By.XPATH,
                                                        "//div[contains(@class, 'carusel-cube')]//label[contains(text(), 'קרנות פנסיה')]/..//span[contains(@class, 'value')]")
                pension_balance = pension_cube.text.strip()
                data['pension_balance'] = pension_balance
                logger.info(f"Pension balance: {pension_balance}")
            except NoSuchElementException:
                logger.debug("Pension balance not found")
                data['pension_balance'] = None
            except Exception as e:
                logger.warning(f"Error extracting pension balance: {e}")
                data['pension_balance'] = None

            # Extract keren histalmut balance (קרנות השתלמות) - this might not exist for all users
            try:
                keren_cube = self.driver.find_element(By.XPATH,
                                                      "//div[contains(@class, 'carusel-cube')]//label[contains(text(), 'קרנות השתלמות')]/..//span[contains(@class, 'value')]")
                keren_balance = keren_cube.text.strip()
                data['keren_histalmut_balance'] = keren_balance
                logger.info(f"Keren Histalmut balance: {keren_balance}")
            except NoSuchElementException:
                logger.debug("Keren Histalmut balance not found (may not exist for this user)")
                data['keren_histalmut_balance'] = None
            except Exception as e:
                logger.warning(f"Error extracting keren histalmut balance: {e}")
                data['keren_histalmut_balance'] = None

            # Alternative method: try to find all value spans in carusel-cube divs
            if not data.get('pension_balance') or not data.get('keren_histalmut_balance'):
                logger.debug("Trying alternative extraction method...")
                try:
                    value_spans = self.driver.find_elements(By.CSS_SELECTOR, "div.carusel-cube span.value")
                    cube_titles = self.driver.find_elements(By.CSS_SELECTOR, "div.carusel-cube label.cube-title")

                    for i, (title, value) in enumerate(zip(cube_titles, value_spans)):
                        title_text = title.text.strip()
                        value_text = value.text.strip()
                        logger.debug(f"Found cube {i + 1}: {title_text} = {value_text}")

                        if 'קרנות פנסיה' in title_text and not data.get('pension_balance'):
                            data['pension_balance'] = value_text
                        elif 'קרנות השתלמות' in title_text and not data.get('keren_histalmut_balance'):
                            data['keren_histalmut_balance'] = value_text

                except Exception as e:
                    logger.warning(f"Error in alternative extraction method: {e}")

            return data

        except Exception as e:
            logger.error(f"Error extracting financial data: {e}", exc_info=True)
            return {}

    def execute(self, site_url: str, credentials: Dict[str, str], selectors: Dict[str, str]) -> Dict[str, Any]:
        """Execute the complete Migdal automation flow (login + data extraction)

        Args:
            site_url: URL of the login page
            credentials: Dictionary containing login credentials (e.g., {'id': '123456789'})
            selectors: Dictionary containing CSS selectors for form elements

        Returns:
            Dictionary containing extracted Migdal financial data, or empty dict if failed
        """
        try:
            logger.info("=== Starting Migdal Pension Automation ===")
            logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Perform login
            logger.info("1. Attempting login...")
            login_success = self.login(site_url, credentials, selectors)

            if not login_success:
                logger.error("Login failed, cannot extract data")
                return {}

            logger.info("2. Login successful! Extracting financial data...")

            # Extract financial data
            financial_data = self.extract_financial_data()

            logger.info("3. Data extraction completed")
            logger.info("=== Migdal Automation Completed Successfully ===")

            return financial_data

        except Exception as e:
            logger.error(f"Error during Migdal automation execution: {e}", exc_info=True)
            return {}


# Usage Example
def main():
    """Example usage of the MFA automation system for Israeli pension site"""

    # IMPORTANT: Configure logging FIRST!
    logging.basicConfig(
        level=logging.INFO,  # Change to DEBUG for more details
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=== Starting Migdal Pension Automation ===")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Configure email access (use app password for Gmail)
    print("\n1. Configuring email access...")
    email_config = EmailConfig(
        email_address=os.getenv("USER_EMAIL"),
        password=USER_EMAIL_APP_PASSWORD,  # Gmail app password
        imap_server="imap.gmail.com"
    )
    print(f"Email configured for: {email_config.email_address}")

    # Configure MFA settings for Israeli pension provider
    print("\n2. Configuring MFA settings...")
    mfa_config = MFAConfig(
        sender_email="noreply@migdal.co.il",  # Migdal MFA sender email
        code_pattern=r'\b\d{6}\b',  # 6-digit codes (Migdal format)
        max_wait_time=60,
        check_interval=5
    )
    print(f"MFA configured for sender: {mfa_config.sender_email}")

    # Create email retriever
    print("\n3. Creating email retriever...")
    email_retriever = MigdalEmailMFARetriever(email_config, mfa_config)

    # Create automation handler
    print("\n4. Creating automation handler...")
    automator = MigdalSeleniumMFAAutomator(email_retriever, headless=False)  # Set True for headless

    try:
        # Perform login with ID and MFA
        print("\n5. Starting login process...")
        success = automator.login(
            site_url="https://my.migdal.co.il/mymigdal/process/login",
            credentials={'id': os.getenv("USER_ID")},  # Replace with your actual Israeli ID number (9 digits)
            selectors={
                'id_selector': '#username',
                'login_button_selector': 'button[type="submit"]',
                'email_label_selector': 'label[for="otpToEmail"]',
                'continue_button_selector': 'button.form-btn',
                'success_indicator': '.dashboard'
            }
        )

        if success:
            print("\n6. Login successful! Extracting financial data...")
            # Extract financial data directly since we're already logged in
            financial_data = automator.extract_financial_data()

            print("\n=== Financial Data from Migdal ===")
            if financial_data.get('pension_balance'):
                print(f"Pension Balance (קרנות פנסיה): {financial_data['pension_balance']}")
            else:
                print("Pension Balance: Not found")

            if financial_data.get('keren_histalmut_balance'):
                print(f"Keren Histalmut Balance (קרנות השתלמות): {financial_data['keren_histalmut_balance']}")
            else:
                print("Keren Histalmut Balance: Not available for this account")

            print("================================\n")
        else:
            print("\n6. Login failed!")

    except Exception as e:
        print(f"\nERROR during main process: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n7. Cleaning up resources...")
        automator.cleanup()
        print("=== Automation completed ===")


if __name__ == "__main__":
    main()
