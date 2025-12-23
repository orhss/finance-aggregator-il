"""
Phoenix Pension Client

Handles login and data extraction for Phoenix pension site using:
- Email-based MFA automation
- Selenium web automation
- PensionAutomatorBase for reusable login flows
"""

import os
import re
from datetime import datetime
from typing import Optional, Dict, Any
import logging

import dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

# Modular imports
from scrapers.base.email_retriever import (
    EmailMFARetriever,
    EmailConfig,
    MFAConfig
)
from scrapers.base.pension_automator import PensionAutomatorBase

logger = logging.getLogger(__name__)
dotenv.load_dotenv()


class PhoenixEmailMFARetriever(EmailMFARetriever):
    """Handles retrieving MFA codes from email for Phoenix pension site"""

    def __init__(self, email_config: EmailConfig, mfa_config: MFAConfig):
        super().__init__(email_config, mfa_config)

    def extract_mfa_code(self, email_message) -> Optional[str]:
        """Extract MFA code from email content - specifically for Phoenix format"""
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

            # Phoenix MFA code extraction - try multiple patterns
            if html_content:
                # Pattern 1: Look for 6-digit codes in HTML
                html_matches = re.findall(self.mfa_config.code_pattern, html_content)
                if html_matches:
                    logger.info(f"Found MFA code in HTML content: {html_matches[0]}")
                    return html_matches[0]

                # Pattern 2: Look for codes in specific Phoenix elements
                phoenix_patterns = [
                    r'<strong[^>]*>(\d{6})</strong>',
                    r'<span[^>]*>(\d{6})</span>',
                    r'<div[^>]*>(\d{6})</div>',
                    r'<p[^>]*>(\d{6})</p>',
                    r'<td[^>]*>(\d{6})</td>'
                ]

                for pattern in phoenix_patterns:
                    matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
                    if matches:
                        logger.info(f"Found MFA code with Phoenix pattern {pattern}: {matches[0]}")
                        return matches[0]

            # Fallback to plain text content - Phoenix might send simple text emails
            if plain_content:
                # Look for 6-digit codes in plain text
                plain_matches = re.findall(self.mfa_config.code_pattern, plain_content)
                if plain_matches:
                    logger.info(f"Found MFA code in plain text: {plain_matches[0]}")
                    return plain_matches[0]

                # Look for codes with context (e.g., "קוד האימות שלך לאתר הפניקס הוא: 387367")
                context_patterns = [
                    r'קוד האימות שלך לאתר הפניקס הוא:\s*(\d{6})',  # Exact Phoenix format
                    r'קוד הכניסה[^:]*:\s*(\d{6})',
                    r'קוד[^:]*:\s*(\d{6})',
                    r'code[^:]*:\s*(\d{6})',
                    r'הקוד[^:]*:\s*(\d{6})'
                ]

                for pattern in context_patterns:
                    matches = re.findall(pattern, plain_content, re.IGNORECASE)
                    if matches:
                        logger.info(f"Found MFA code with context pattern: {matches[0]}")
                        return matches[0]

            logger.warning("No MFA code found in Phoenix email content")
            return None

        except Exception as e:
            logger.error(f"Error extracting MFA code: {e}", exc_info=True)
            return None


class PhoenixSeleniumMFAAutomator(PensionAutomatorBase):
    """
    Handles Selenium automation with MFA for Phoenix pension site

    Extends PensionAutomatorBase which provides:
    - Browser lifecycle management via SeleniumDriver
    - Web interactions via WebActions
    - MFA code entry via MFAHandler
    - Reusable login_with_id_email_and_mfa_flow() for Phoenix's login pattern
    """

    # Phoenix-specific OTP selector (single field)
    OTP_SELECTOR = "input[data-verify-field='otpCode']"

    # Fallback selectors for various elements
    FALLBACK_SELECTORS = {
        'login_button': [
            # Text-based selectors (most reliable for distinguishing between buttons)
            "//button[contains(text(), 'שלחו לי קוד כניסה')]",  # "Send me login code"
            "//button[contains(text(), 'שלחו לי קוד')]",          # Partial match
            "//button[contains(text(), 'קוד כניסה')]",            # "Login code"
            "//button[contains(., 'שלחו לי קוד כניסה')]",        # Any descendant text
            # Class-based fallbacks (less specific)
            "button.bg-\\[\\#FF4E31\\]",
            "button.text-white.w-\\[340px\\]",
            "button[type='button'].bg-\\[\\#FF4E31\\]",
            "button[type='button'].text-white",
            "//button[contains(@class, 'bg-[#FF4E31]')]",
            "//button[contains(@class, 'text-white')]",
            "button[type='button']"
        ],
        'otp_field': [
            "input[type='number']",
            "input.input-otp",
            "#otp",
            "input[name='otp']",
            "input[name='otpCode']",
            "input[inputmode='numeric']"
        ],
        'submit_button': [
            "button[type='submit']",
            "//button[contains(text(), 'כניסה')]",
            "button[style*='background-color: rgb(255, 90, 35)']",
            "button.bg-\\[\\#FF4E31\\]",
            "button.text-white"
        ]
    }

    def __init__(self, email_retriever: PhoenixEmailMFARetriever, headless: bool = True):
        super().__init__(email_retriever, headless)

    def login(self, site_url: str, credentials: Dict[str, str], selectors: Dict[str, str]) -> bool:
        """
        Perform login for Phoenix site using ID, email and MFA flow

        Args:
            site_url: URL of the login page
            credentials: Dictionary containing login credentials (e.g., {'id': '123456789', 'email': 'user@example.com'})
            selectors: Dictionary containing CSS selectors for form elements

        Returns:
            True if login successful, False otherwise
        """
        id_number = credentials.get('id')
        email = credentials.get('email')

        if not id_number:
            logger.error("ID number not provided in credentials")
            return False

        if not email:
            logger.error("Email not provided in credentials")
            return False

        # Use the base class login flow with Phoenix-specific selectors
        return self.login_with_id_email_and_mfa_flow(
            site_url=site_url,
            id_number=id_number,
            email_address=email,
            id_selector=selectors.get('id_selector', '#fnx-id'),
            email_selector=selectors.get('email_selector', 'input[inputmode="email"]'),
            login_button_selector=selectors.get('login_button_selector', "//button[contains(text(), 'שלחו לי קוד כניסה')]"),
            otp_selector=self.OTP_SELECTOR,
            submit_button_selector="#login-btn",
            fallback_selectors=self.FALLBACK_SELECTORS
        )

    def extract_financial_data(self) -> Dict[str, Any]:
        """Extract financial data from Phoenix pension site after successful login"""
        data = {}

        try:
            logger.info("Extracting financial data from Phoenix site...")

            # Wait for the financial data to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "app-pie-chart .legend"))
            )

            # Extract individual account values from the pie chart legend
            # Legend structure: .legend-item contains category name (caption-3) and value (body-2-medium)
            try:
                legend_items = self.driver.find_elements(By.CSS_SELECTOR, "app-pie-chart .legend .legend-item")
                logger.info(f"Found {len(legend_items)} legend items in pie chart")

                for item in legend_items:
                    try:
                        # Get category name (e.g., "קרן השתלמות", "קרן פנסיה")
                        category_elem = item.find_element(By.CSS_SELECTOR, ".caption-3")
                        category = category_elem.text.strip()

                        # Get value
                        value_elem = item.find_element(By.CSS_SELECTOR, ".body-2-medium")
                        value = value_elem.text.strip()

                        logger.info(f"Found: {category} = {value}")

                        # Map Hebrew category names to data keys
                        if 'קרן השתלמות' in category:
                            data['keren_histalmut_balance'] = value
                        elif 'קרן פנסיה' in category or 'פנסיה' in category:
                            data['pension_balance'] = value
                        elif 'ביטוח מנהלים' in category:
                            data['managers_insurance_balance'] = value
                        elif 'גמל' in category:
                            data['gemel_balance'] = value
                        else:
                            # Store any other categories with a generic key
                            safe_key = category.replace(' ', '_').replace('"', '')
                            data[f'phoenix_{safe_key}'] = value

                    except NoSuchElementException:
                        continue
                    except Exception as e:
                        logger.debug(f"Error extracting legend item: {e}")
                        continue

            except NoSuchElementException:
                logger.warning("Pie chart legend not found")
            except Exception as e:
                logger.warning(f"Error extracting from pie chart legend: {e}")

            return data

        except Exception as e:
            logger.error(f"Error extracting financial data: {e}", exc_info=True)
            return {}

    def execute(self, site_url: str, credentials: Dict[str, str], selectors: Dict[str, str]) -> Dict[str, Any]:
        """Execute the complete Phoenix automation flow (login + data extraction)

        Args:
            site_url: URL of the login page
            credentials: Dictionary containing login credentials (e.g., {'id': '123456789', 'email': 'user@example.com'})
            selectors: Dictionary containing CSS selectors for form elements

        Returns:
            Dictionary containing extracted Phoenix financial data, or empty dict if failed
        """
        try:
            logger.info("=== Starting Phoenix Pension Automation ===")
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
            logger.info("=== Phoenix Automation Completed Successfully ===")

            return financial_data

        except Exception as e:
            logger.error(f"Error during Phoenix automation execution: {e}", exc_info=True)
            return {}


# Usage Example
def main():
    """Example usage of the MFA automation system for Phoenix pension site"""

    # IMPORTANT: Configure logging FIRST!
    logging.basicConfig(
        level=logging.INFO,  # Change to DEBUG for more details
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=== Starting Phoenix Pension Automation ===")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Configure email access (use app password for Gmail)
    print("\n1. Configuring email access...")
    email_config = EmailConfig(
        email_address=os.getenv("USER_EMAIL"),
        password=os.getenv("USER_EMAIL_APP_PASSWORD"),  # Gmail app password
        imap_server="imap.gmail.com"
    )
    print(f"Email configured for: {email_config.email_address}")

    # Configure MFA settings for Phoenix pension provider
    print("\n2. Configuring MFA settings...")
    mfa_config = MFAConfig(
        sender_email="fnxnoreplay@fnx.co.il",  # Fixed Phoenix MFA sender email (was missing 'n')
        code_pattern=r'\b\d{6}\b',  # 6-digit codes (Phoenix format)
        max_wait_time=120,  # Increased wait time to 2 minutes
        check_interval=3,   # Check more frequently
        email_delay=30,  # Added email_delay
        login_processing_delay=10  # Added login_processing_delay
    )
    print(f"MFA configured for sender: {mfa_config.sender_email}")

    # Create email retriever
    print("\n3. Creating email retriever...")
    email_retriever = PhoenixEmailMFARetriever(email_config, mfa_config)

    # Create automation handler
    print("\n4. Creating automation handler...")
    automator = PhoenixSeleniumMFAAutomator(email_retriever, headless=False)  # Set True for headless

    try:
        # Execute complete automation flow
        print("\n5. Starting complete automation process...")
        financial_data = automator.execute(
            site_url="https://my.fnx.co.il/",
            credentials={
                'id': os.getenv("USER_ID"),  # Replace with your actual Israeli ID number (9 digits)
                'email': 'hassono@gmail.com'  # Replace with your email
            },
            selectors={
                'id_selector': '#fnx-id',
                'email_selector': 'input[inputmode="email"]',
                'login_button_selector': 'button[type="button"]',  # Phoenix uses button type="button"
                'success_indicator': '.dashboard'  # Adjust based on Phoenix site structure
            }
        )

        if financial_data:
            print("\n=== Financial Data from Phoenix ===")
            if financial_data.get('total_investments_savings'):
                print(f"Total Investments and Savings (סה\"כ השקעות וחסכונות): {financial_data['total_investments_savings']}")
            else:
                print("Total Investments and Savings: Not found")

            if financial_data.get('pension_fund'):
                print(f"Pension Fund (קרן פנסיה): {financial_data['pension_fund']}")
            else:
                print("Pension Fund: Not found")

            if financial_data.get('keren_histalmut'):
                print(f"Keren Histalmut (קרן השתלמות): {financial_data['keren_histalmut']}")
            else:
                print("Keren Histalmut: Not found")

            if financial_data.get('managers_insurance'):
                print(f"Managers Insurance (ביטוח מנהלים): {financial_data['managers_insurance']}")
            else:
                print("Managers Insurance: Not found")

            if financial_data.get('savings'):
                print(f"Savings (חסכונות): {financial_data['savings']}")
            else:
                print("Savings: Not found")

            # Display any additional Phoenix-specific data
            additional_data = {k: v for k, v in financial_data.items() if k.startswith('phoenix_')}
            if additional_data:
                print("\nAdditional Phoenix Data:")
                for key, value in additional_data.items():
                    print(f"  {key}: {value}")

            print("================================\n")
        else:
            print("\n6. Automation failed - no data extracted!")

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