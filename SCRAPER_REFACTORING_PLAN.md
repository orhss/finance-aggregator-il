# Scraper Layer Refactoring Plan

## 📊 IMPLEMENTATION PROGRESS

**Status**: Phase 2 - Complete ✅
**Last Updated**: 2025-12-23
**Completion**: Phase 1 Complete ✅ | Phase 2 Complete ✅

### ✅ Completed Tasks

#### Task 1.1: Split pension_base.py into Focused Modules
- ✅ **Created** `scrapers/base/email_retriever.py` (254 lines)
  - EmailMFARetriever base class with context manager support
  - Proper logging instead of print statements
  - EmailRetrievalError exception hierarchy
  - Guaranteed cleanup with disconnect()

- ✅ **Created** `scrapers/base/mfa_handler.py` (225 lines)
  - MFAHandler class for both single-field and individual-field patterns
  - Human-like typing with configurable delays
  - Fallback selector support
  - MFAEntryError exception

#### Task 1.2: Implement Proper Logging
- ✅ **Created** `scrapers/config/logging_config.py` (51 lines)
  - Centralized logging configuration
  - File and console output support
  - Third-party logger suppression (Selenium, urllib3, imaplib)
  - Configurable log levels

#### Task 1.3: Guaranteed Resource Cleanup
- ✅ **Implemented** context managers in email_retriever.py
  - `__enter__` and `__exit__` methods
  - Safe cleanup in finally blocks

#### Task 1.4: Exception Hierarchy
- ✅ **Created** `scrapers/exceptions.py` (98 lines)
  - Complete exception hierarchy
  - Authentication, Data Extraction, Network, Validation errors
  - Recoverable vs Fatal error distinction
  - Institution tracking

#### HIGH Priority Tasks (from Phase 2)
- ✅ **Created** `scrapers/utils/retry.py` (98 lines)
  - Exponential backoff decorator
  - Specialized decorators for Selenium and API calls

- ✅ **Created** `scrapers/utils/wait_conditions.py` (229 lines)
  - SmartWait class to replace time.sleep()
  - Condition-based waits (clickable, present, invisible, etc.)

### ✅ Recently Completed (NEW - 2025-12-20)
- ✅ **Migdal Pension Client Refactored** (migdal_pension_client.py:366 lines)
  - Migrated from EmailMFARetrieverBase → EmailMFARetriever (new modular base)
  - Replaced ~20+ print statements with proper logging (logger.info/error/debug/warning)
  - Added exc_info=True to all exception logging for full stack traces
  - Context manager support inherited from new base class
  - MFA extraction still institution-specific but benefits from new base infrastructure

- ✅ **Phoenix Pension Client Refactored** (phoenix_pension_client.py:431 lines)
  - Migrated from EmailMFARetrieverBase → EmailMFARetriever (new modular base)
  - Replaced ~15+ print statements with proper logging
  - Enhanced MFA extraction with multiple Phoenix-specific patterns
  - Production-ready logging infrastructure with appropriate log levels

### ✅ Phase 2 Testing Complete (2025-12-23)
1. **Test Refactored Clients** ✅ COMPLETED
   - ✅ Verified Migdal complete sync flow works with new modules
   - ✅ Verified Phoenix complete sync flow works with new modules
   - ✅ MFA automation functioning correctly
   - ✅ Context manager cleanup working properly

### ✅ Phase 2 Deprecation Complete (2025-12-23)
1. **Deprecate Legacy Code** ✅ COMPLETED
   - ✅ Added module-level deprecation docstring to pension_base.py
   - ✅ Added `_deprecation_warning()` helper function
   - ✅ Added DeprecationWarning to `EmailMFARetrieverBase.__init__()`
   - ✅ Added DeprecationWarning to `SeleniumMFAAutomatorBase.__init__()`
   - ✅ Added class-level deprecation docstrings with migration guidance
   - Warnings point users to: `scraper_refactoring_plan.md` for migration details

### ✅ Phase 2 Documentation Complete (2025-12-23)
1. **Update Documentation** ✅ COMPLETED
   - ✅ Updated CLAUDE.md to reference new modular architecture
   - ✅ Added new modules section (email_retriever, mfa_handler, wait_conditions, retry, exceptions, logging_config)
   - ✅ Marked legacy classes as DEPRECATED in documentation
   - ✅ Updated MFA Flow Architecture section with new module references

### 📋 Phase 3 - Selenium Automator Migration (IN PROGRESS)

**Status**: IN PROGRESS
**Last Updated**: 2025-12-23

**Architecture Decision** (discovered during implementation):
The original plan to have each client compose modules directly would cause **code duplication**.
`SeleniumMFAAutomatorBase` contains ~500 lines of shared login flow orchestration used by both
Migdal and Phoenix. Instead of duplicating this in each client, we create a new base class
that uses composition internally but provides the same reusable interface.

**Correct Approach**:
```
OLD: SeleniumMFAAutomatorBase (monolithic, 866 lines)
     ├── MigdalSeleniumMFAAutomator (extends)
     └── PhoenixSeleniumMFAAutomator (extends)

NEW: PensionAutomatorBase (uses composition internally)
     ├── Composes: SeleniumDriver, WebActions, MFAHandler
     ├── Provides: login_with_id_and_mfa_flow(), login_with_id_email_and_mfa_flow()
     ├── MigdalSeleniumAutomator (extends) - only overrides extract_financial_data()
     └── PhoenixSeleniumAutomator (extends) - only overrides extract_financial_data()
```

**Phase 3 Tasks**:

1. **Create `scrapers/base/selenium_driver.py`** ✅ COMPLETED
   - WebDriver setup and configuration
   - Chrome options management (headless, user-agent, etc.)
   - Context manager for guaranteed browser cleanup
   - DriverConfig dataclass for configuration

2. **Create `scrapers/base/web_actions.py`** ✅ COMPLETED
   - Form filling utilities (human-like typing)
   - Button clicking with fallback selectors
   - Element waiting and detection
   - Option selection, iframe switching, etc.

3. **Create `scrapers/base/pension_automator.py`** ✅ COMPLETED
   - New base class `PensionAutomatorBase` replacing `SeleniumMFAAutomatorBase`
   - Uses composition: SeleniumDriver, WebActions, MFAHandler
   - Provides reusable login flows:
     - `login_with_id_and_mfa_flow()` (Migdal pattern: ID → email option → MFA)
     - `login_with_id_email_and_mfa_flow()` (Phoenix pattern: ID + email → MFA)
   - Context manager support
   - Proper logging throughout

4. **Refactor `MigdalSeleniumMFAAutomator`** ✅ COMPLETED
   - Changed inheritance: `SeleniumMFAAutomatorBase` → `PensionAutomatorBase`
   - Removed duplicated login flow code (now uses base class)
   - Kept only institution-specific: `extract_financial_data()`, OTP selectors, fallbacks
   - Class constants for OTP_SELECTORS and FALLBACK_SELECTORS

5. **Refactor `PhoenixSeleniumMFAAutomator`** ✅ COMPLETED
   - Changed inheritance: `SeleniumMFAAutomatorBase` → `PensionAutomatorBase`
   - Removed duplicated login flow code (now uses base class)
   - Kept only institution-specific: `extract_financial_data()`, OTP selectors, fallbacks
   - Class constants for OTP_SELECTOR and FALLBACK_SELECTORS

6. **Update imports across codebase** ✅ COMPLETED
   - ✅ Updated `pension_service.py` to import EmailConfig, MFAConfig from `email_retriever.py`
   - ✅ Updated `scrapers/base/__init__.py` to export all new modules
   - ✅ Kept legacy exports for backwards compatibility

7. **Remove `pension_base.py`** (READY - requires testing)
   - Legacy classes still exported via `__init__.py` for backwards compatibility
   - Can be removed once testing confirms new architecture works
   - Recommend: Run Migdal and Phoenix sync flows to verify before removal

### 📈 Phase 1 Impact Summary

| Metric | Before | After Phase 1 | Status |
|--------|--------|---------------|--------|
| **Modular base files** | 0 | 7 files | ✅ Complete |
| **Lines of focused code** | 0 | ~955 lines | ✅ Complete |
| **Clients refactored** | 0 | 2 (Migdal, Phoenix) | ✅ Complete |
| **Print statements eliminated** | ~35+ | 0 (in core classes) | ✅ Complete |
| **Logging infrastructure** | ❌ None | ✅ Centralized | ✅ Complete |
| **Exception hierarchy** | ❌ Generic | ✅ Structured (98 lines) | ✅ Complete |
| **Resource cleanup** | ⚠️ Manual | ✅ Context managers | ✅ Complete |
| **Retry logic** | ❌ None | ✅ Exponential backoff | ✅ Complete |
| **Smart waits** | ❌ time.sleep() | ✅ Condition-based | ✅ Complete |

### 📊 Code Quality Improvements Achieved
- **✅ Separation of Concerns**: Email retrieval, MFA handling, and logging now in separate, focused modules
- **✅ DRY Principle**: Eliminated duplicate email parsing code across Migdal and Phoenix clients
- **✅ Testability**: New modular structure enables unit testing of individual components
- **✅ Maintainability**: 1066-line monolithic pension_base.py functionality now split into 7 focused modules
- **✅ Production Readiness**: Proper logging with levels, exc_info=True, and structured messages
- **✅ Critical Issues Resolved**: C2 (code duplication), C3 (logging), C4 (cleanup) all addressed

---

## Executive Summary

This document outlines a prioritized refactoring plan to address critical issues in the scraper layer: code duplication, poor separation of concerns, maintainability challenges, and scalability limitations.

**Current State**: Scrapers work but have massive code duplication (1066-line base class!) and poor maintainability
**Target State**: Clean, modular, testable, and production-ready scraper layer
**Estimated Effort**: 4-5 weeks

---

## Severity Classification

- **🔴 CRITICAL**: Blocks maintainability, massive code duplication, or memory leaks
- **🟠 HIGH**: Significant technical debt, flaky operations, or poor error handling
- **🟡 MEDIUM**: Testability issues, missing features, or moderate complexity
- **🟢 LOW**: Nice-to-have improvements, minor optimizations

---

## Issues by Severity

### 🔴 CRITICAL Issues

| ID | Issue | Impact | Files Affected |
|----|-------|--------|----------------|
| C1 | Massive base class (1066 lines) | Single point of failure, hard to maintain | pension_base.py |
| C2 | Extract MFA code duplication | Bug fixes needed in 2 places | migdal_pension_client.py, phoenix_pension_client.py |
| C3 | Print statements instead of logging | Can't debug production, no log levels | All scraper files |
| C4 | No guaranteed resource cleanup | Memory/browser leaks on errors | All Selenium scrapers |
| C5 | Hardcoded configuration | Can't change without code changes | All implementation files |

### 🟠 HIGH Issues

| ID | Issue | Impact | Files Affected |
|----|-------|--------|----------------|
| H1 | No retry logic for flaky operations | Fails on temporary issues | All Selenium scrapers |
| H2 | Poor exception hierarchy | Can't handle errors granularly | All scraper files |
| H3 | time.sleep() everywhere | Slow and unreliable | pension_base.py (15+ occurrences) |
| H4 | No selector abstraction | Selectors scattered across code | migdal_pension_client.py, phoenix_pension_client.py |
| H5 | Long methods (100+ lines) | Hard to test and understand | pension_base.py, cal_credit_card_client.py |
| H6 | No browser pooling/reuse | Slow startup on every scrape | All Selenium scrapers |

### 🟡 MEDIUM Issues

| ID | Issue | Impact | Files Affected |
|----|-------|--------|----------------|
| M1 | No data validation | Scrapes invalid data silently | All scrapers |
| M2 | No rate limiting | Risk of being blocked | cal_credit_card_client.py |
| M3 | No page object pattern | Hard to maintain selectors | pension implementations |
| M4 | Manual session management | Error-prone | cal_credit_card_client.py |
| M5 | No scraper health checks | Can't detect broken scrapers | All scrapers |

### 🟢 LOW Issues

| ID | Issue | Impact | Files Affected |
|----|-------|--------|----------------|
| L1 | No metrics/monitoring | Can't track scraper performance | All scrapers |
| L2 | No scraper versioning | Can't detect breaking changes | All scrapers |
| L3 | No caching for static data | Redundant API calls | All scrapers |

---

## Code Analysis: Current State

### pension_base.py - The Monster File
```
Lines: 1066
Methods: 20+
Responsibilities: Email retrieval, Selenium automation, MFA handling, form filling, button clicking
Violations: Single Responsibility Principle, Open/Closed Principle
```

**Problems**:
- Mixes email logic with Selenium logic
- Methods doing too much (login_with_id_and_mfa_flow: 100+ lines)
- No separation between framework and business logic
- Can't reuse parts independently

### Duplication Examples

**Extract MFA Code** (duplicated in 2 files):
```python
# migdal_pension_client.py:29-76
def extract_mfa_code(self, email_message) -> Optional[str]:
    # 47 lines of HTML/text parsing

# phoenix_pension_client.py:27-97
def extract_mfa_code(self, email_message) -> Optional[str]:
    # 70 lines of HTML/text parsing (same logic + more patterns)
```

**Session Storage Extraction** (CAL only):
```python
# cal_credit_card_client.py - 50 lines
# No other scraper can reuse this pattern
```

---

## Implementation Phases

### Phase 1: Critical Refactoring (Week 1-2) 🔴

#### Goal: Break down monolithic base class and eliminate critical issues

---

#### Task 1.1: Split pension_base.py into Focused Modules

**Current Structure** (1066 lines, 1 file):
```
pension_base.py
├── EmailMFARetrieverBase (200 lines)
├── SeleniumMFAAutomatorBase (866 lines!)
│   ├── Email login methods
│   ├── MFA handling
│   ├── Form filling
│   ├── Button clicking
│   ├── Data extraction
│   └── Utility methods
```

**New Structure** (5 files, modular):
```
scrapers/base/
├── __init__.py
├── email_retriever.py         # Email/IMAP operations (150 lines)
├── selenium_driver.py          # WebDriver setup & management (100 lines)
├── mfa_handler.py              # MFA code entry & submission (200 lines)
├── web_actions.py              # Form filling, clicking, waiting (150 lines)
└── page_elements.py            # Selector management & page objects (100 lines)
```

**New File: `scrapers/base/email_retriever.py`**
```python
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
```

**Benefits**:
- ✅ Email logic isolated and testable
- ✅ Context manager for guaranteed cleanup
- ✅ Proper logging instead of prints
- ✅ Clear error hierarchy
- ✅ Reduced from 200 lines to 150 focused lines

---

**New File: `scrapers/base/mfa_handler.py`**
```python
"""
MFA code entry and submission handling
Supports both single-field and individual-field patterns
"""

import time
from typing import List, Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import logging

logger = logging.getLogger(__name__)


class MFAEntryError(Exception):
    """Raised when MFA code entry fails"""
    pass


class MFAHandler:
    """
    Handles MFA code entry with various input patterns

    Supports:
    - Single field (Phoenix pattern)
    - Individual digit fields (Migdal pattern)
    - Human-like typing with delays
    - Fallback selectors
    """

    def __init__(self, driver: WebDriver, timeout: int = 30):
        self.driver = driver
        self.timeout = timeout

    def enter_code_single_field(
        self,
        code: str,
        selector: str,
        fallback_selectors: Optional[List[str]] = None,
        typing_delay: float = 0.2
    ) -> bool:
        """
        Enter MFA code into single input field

        Args:
            code: MFA code to enter (e.g., "123456")
            selector: CSS selector for input field
            fallback_selectors: Alternative selectors to try
            typing_delay: Delay between characters (human-like)

        Returns:
            True if successful, False otherwise

        Raises:
            MFAEntryError: If code entry fails
        """
        if not self._validate_code(code):
            raise MFAEntryError(f"Invalid MFA code: {code}")

        # Try primary selector
        if self._try_enter_field(code, selector, typing_delay):
            return True

        # Try fallback selectors
        if fallback_selectors:
            for fallback in fallback_selectors:
                logger.debug(f"Trying fallback selector: {fallback}")
                if self._try_enter_field(code, fallback, typing_delay):
                    return True

        raise MFAEntryError(f"Could not find MFA input field with any selector")

    def enter_code_individual_fields(
        self,
        code: str,
        selectors: List[str],
        typing_delay: float = 0.2
    ) -> bool:
        """
        Enter MFA code into individual digit fields (Migdal pattern)

        Args:
            code: MFA code (must be 6 digits)
            selectors: List of selectors for each digit field (must be 6)
            typing_delay: Delay between characters

        Returns:
            True if successful

        Raises:
            MFAEntryError: If code entry fails
        """
        if not self._validate_code(code):
            raise MFAEntryError(f"Invalid MFA code: {code}")

        if len(selectors) != 6:
            raise MFAEntryError(f"Expected 6 selectors, got {len(selectors)}")

        logger.info("Entering MFA code into individual fields")

        for i, (digit, selector) in enumerate(zip(code, selectors)):
            try:
                field = WebDriverWait(self.driver, self.timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                field.clear()
                field.send_keys(digit)
                logger.debug(f"Entered digit {i+1}/6")
                time.sleep(typing_delay)

            except TimeoutException:
                raise MFAEntryError(f"Timeout waiting for field {i+1} ({selector})")
            except Exception as e:
                raise MFAEntryError(f"Error entering digit {i+1}: {e}")

        logger.info("All digits entered successfully")
        return True

    def submit_mfa(
        self,
        button_selector: str,
        fallback_selectors: Optional[List[str]] = None,
        wait_before_submit: float = 1.0
    ) -> bool:
        """
        Click MFA submission button

        Args:
            button_selector: CSS selector or XPath for submit button
            fallback_selectors: Alternative selectors
            wait_before_submit: Delay before clicking (allow UI to update)

        Returns:
            True if successful

        Raises:
            MFAEntryError: If button not found or not clickable
        """
        if wait_before_submit > 0:
            logger.debug(f"Waiting {wait_before_submit}s before submitting")
            time.sleep(wait_before_submit)

        all_selectors = [button_selector] + (fallback_selectors or [])

        for selector in all_selectors:
            try:
                logger.debug(f"Looking for submit button: {selector}")

                if selector.startswith("//"):
                    button = self.driver.find_element(By.XPATH, selector)
                else:
                    button = self.driver.find_element(By.CSS_SELECTOR, selector)

                if button.is_enabled():
                    button.click()
                    logger.info("MFA submitted successfully")
                    return True
                else:
                    logger.debug(f"Button found but disabled: {selector}")

            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue

        raise MFAEntryError("Could not find or click MFA submit button")

    def _validate_code(self, code: str) -> bool:
        """Validate MFA code format"""
        return len(code) == 6 and code.isdigit()

    def _try_enter_field(
        self,
        code: str,
        selector: str,
        typing_delay: float
    ) -> bool:
        """Try to enter code in a specific field"""
        try:
            logger.debug(f"Looking for MFA field: {selector}")

            field = WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )

            field.clear()

            # Type character by character
            for digit in code:
                field.send_keys(digit)
                time.sleep(typing_delay)

            # Trigger blur event
            self.driver.execute_script("arguments[0].blur();", field)
            time.sleep(0.5)

            logger.info(f"MFA code entered in field: {selector}")
            return True

        except TimeoutException:
            logger.debug(f"Field not found: {selector}")
            return False
        except Exception as e:
            logger.debug(f"Error with field {selector}: {e}")
            return False
```

**Benefits**:
- ✅ MFA logic isolated
- ✅ Supports both patterns (single/individual)
- ✅ Proper error handling
- ✅ Testable without browser
- ✅ 200 focused lines vs 400+ scattered

---

#### Task 1.2: Implement Proper Logging

**Replace ALL print statements with logging**

**Before** (everywhere):
```python
print("Starting login...")
print(f"Error: {e}")
print("MFA code found")
```

**After**:
```python
logger.info("Starting login...")
logger.error(f"Login failed: {e}", exc_info=True)
logger.debug("MFA code found")
```

**Logging Configuration** (`scrapers/config/logging_config.py`):
```python
"""
Centralized logging configuration for all scrapers
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    format_string: Optional[str] = None
):
    """
    Configure logging for scrapers

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file to write logs to
        format_string: Custom format string
    """
    if format_string is None:
        format_string = (
            '%(asctime)s - %(name)s - %(levelname)s - '
            '%(filename)s:%(lineno)d - %(message)s'
        )

    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
        handlers=handlers
    )

    # Set third-party loggers to WARNING
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


# Usage:
# from scrapers.config.logging_config import setup_logging
# setup_logging(level="DEBUG", log_file=Path("logs/scrapers.log"))
```

---

#### Task 1.3: Guaranteed Resource Cleanup

**Problem**: Browsers and email connections leak on errors

**Solution**: Context managers everywhere

**Before**:
```python
def scrape(...):
    scraper = CALCreditCardScraper(...)
    try:
        return scraper.scrape()
    finally:
        scraper.cleanup()  # ❌ Easy to forget
```

**After**:
```python
def scrape(...):
    with CALCreditCardScraper(...) as scraper:
        return scraper.scrape()  # ✅ Automatic cleanup
```

**Implementation** (all scraper classes):
```python
class CALCreditCardScraper:
    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - guaranteed cleanup"""
        self.cleanup()

    def cleanup(self):
        """Clean up resources (safe to call multiple times)"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            finally:
                self.driver = None
```

---

#### Task 1.4: Externalize Configuration

**Create Institution Registry**

**File**: `config/institution_selectors.py`
```python
"""
Centralized selector and configuration registry for all institutions
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class SelectorSet:
    """Set of selectors for an institution"""
    id_field: str
    email_field: Optional[str] = None
    password_field: Optional[str] = None
    login_button: str = "button[type='submit']"
    mfa_field: Optional[str] = None
    mfa_fields: Optional[List[str]] = None  # For individual fields
    mfa_submit_button: Optional[str] = None
    continue_button: Optional[str] = None
    email_option: Optional[str] = None

    # Fallbacks
    login_button_fallbacks: List[str] = None
    mfa_field_fallbacks: List[str] = None


@dataclass
class InstitutionConfig:
    """Complete configuration for an institution"""
    name: str
    url: str
    mfa_sender_email: str
    mfa_sender_name: Optional[str] = None
    mfa_code_pattern: str = r'\b\d{6}\b'
    selectors: SelectorSet = None

    # Timing
    email_delay: int = 30
    max_wait_time: int = 60
    check_interval: int = 5
    post_login_delay: int = 5
    mfa_submission_delay: int = 5


# Institution Registry
MIGDAL_CONFIG = InstitutionConfig(
    name="Migdal",
    url="https://www.migdal.co.il/he/myArea",
    mfa_sender_email="no-reply@migdal.co.il",
    mfa_sender_name="Migdal",
    selectors=SelectorSet(
        id_field="input[name='idNumber']",
        login_button="button.submit-button",
        email_option="label[for='otpToEmail']",
        continue_button="button.form-btn",
        mfa_fields=[
            "input[name='otp']",
            "input[name='otp2']",
            "input[name='otp3']",
            "input[name='otp4']",
            "input[name='otp5']",
            "input[name='otp6']"
        ],
        login_button_fallbacks=[
            "//button[contains(text(), 'כניסה')]"
        ]
    )
)

PHOENIX_CONFIG = InstitutionConfig(
    name="Phoenix",
    url="https://www.fnx.co.il/",
    mfa_sender_email="noreply@fnx.co.il",
    mfa_sender_name="Phoenix",
    selectors=SelectorSet(
        id_field="input[name='identityNumber']",
        email_field="input[name='email']",
        login_button="button[type='submit']",
        mfa_field="input[data-verify-field='otpCode']",
        mfa_submit_button="button[type='submit']",
        mfa_field_fallbacks=[
            "input[type='number']",
            "input[name='otpCode']"
        ]
    )
)

CAL_CONFIG = InstitutionConfig(
    name="CAL",
    url="https://www.cal-online.co.il/",
    mfa_sender_email="",  # No MFA for CAL
    selectors=SelectorSet(
        password_field="[formcontrolname='password']",
        login_button="#ccLoginDesktopBtn"
    )
)

# Registry
INSTITUTION_CONFIGS = {
    'migdal': MIGDAL_CONFIG,
    'phoenix': PHOENIX_CONFIG,
    'cal': CAL_CONFIG
}


def get_config(institution: str) -> InstitutionConfig:
    """Get configuration for institution"""
    if institution not in INSTITUTION_CONFIGS:
        raise ValueError(f"Unknown institution: {institution}")
    return INSTITUTION_CONFIGS[institution]
```

**Usage**:
```python
from config.institution_selectors import get_config

config = get_config('migdal')
driver.find_element(By.CSS_SELECTOR, config.selectors.id_field)
```

---

### Phase 2: High Priority Fixes (Week 3) 🟠

#### Task 2.1: Implement Retry Logic with Exponential Backoff

**File**: `scrapers/utils/retry.py`
```python
"""
Retry logic with exponential backoff for flaky operations
"""

import time
import logging
from typing import Callable, TypeVar, Optional, Type
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Decorator for retrying functions with exponential backoff

    Args:
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiply delay by this factor each retry
        exceptions: Tuple of exceptions to catch
        on_retry: Optional callback called on each retry

    Example:
        @retry_with_backoff(max_attempts=3, exceptions=(TimeoutException,))
        def click_button(driver, selector):
            driver.find_element(By.CSS_SELECTOR, selector).click()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )

                    if on_retry:
                        on_retry(attempt, e)

                    time.sleep(delay)
                    delay *= backoff_factor

            # Should never reach here, but for type checker
            raise last_exception

        return wrapper
    return decorator


# Specialized decorators for common use cases
def retry_selenium_action(max_attempts: int = 3):
    """Retry decorator for Selenium actions"""
    from selenium.common.exceptions import (
        TimeoutException,
        StaleElementReferenceException,
        ElementClickInterceptedException
    )

    return retry_with_backoff(
        max_attempts=max_attempts,
        exceptions=(
            TimeoutException,
            StaleElementReferenceException,
            ElementClickInterceptedException
        )
    )


def retry_api_call(max_attempts: int = 3):
    """Retry decorator for API calls"""
    import requests

    return retry_with_backoff(
        max_attempts=max_attempts,
        exceptions=(
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError
        )
    )
```

**Usage**:
```python
from scrapers.utils.retry import retry_selenium_action

@retry_selenium_action(max_attempts=3)
def click_login_button(driver, selector):
    button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
    )
    button.click()
```

---

#### Task 2.2: Replace time.sleep with Smart Waits

**Problem**: `time.sleep()` appears 15+ times in pension_base.py - slow and unreliable

**Solution**: Custom wait conditions

**File**: `scrapers/utils/wait_conditions.py`
```python
"""
Custom wait conditions for Selenium
"""

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


class SmartWait:
    """
    Smart waiting utilities that replace time.sleep
    """

    def __init__(self, driver, default_timeout: int = 30):
        self.driver = driver
        self.default_timeout = default_timeout

    def until_element_present(
        self,
        selector: str,
        by: By = By.CSS_SELECTOR,
        timeout: Optional[int] = None
    ):
        """Wait until element is present in DOM"""
        timeout = timeout or self.default_timeout
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
        except TimeoutException:
            logger.error(f"Element not found after {timeout}s: {selector}")
            raise

    def until_element_clickable(
        self,
        selector: str,
        by: By = By.CSS_SELECTOR,
        timeout: Optional[int] = None
    ):
        """Wait until element is clickable"""
        timeout = timeout or self.default_timeout
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, selector))
            )
        except TimeoutException:
            logger.error(f"Element not clickable after {timeout}s: {selector}")
            raise

    def until_text_present(
        self,
        text: str,
        timeout: Optional[int] = None
    ) -> bool:
        """Wait until text appears anywhere on page"""
        timeout = timeout or self.default_timeout

        def text_in_page(driver):
            return text in driver.page_source

        try:
            WebDriverWait(self.driver, timeout).until(text_in_page)
            return True
        except TimeoutException:
            logger.error(f"Text not found after {timeout}s: {text}")
            return False

    def until_url_contains(
        self,
        url_fragment: str,
        timeout: Optional[int] = None
    ) -> bool:
        """Wait until URL contains specific text"""
        timeout = timeout or self.default_timeout
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.url_contains(url_fragment)
            )
            return True
        except TimeoutException:
            logger.error(f"URL did not contain '{url_fragment}' after {timeout}s")
            return False

    def until_custom_condition(
        self,
        condition: Callable,
        timeout: Optional[int] = None,
        error_message: str = "Custom condition not met"
    ) -> bool:
        """Wait for custom condition"""
        timeout = timeout or self.default_timeout
        try:
            WebDriverWait(self.driver, timeout).until(condition)
            return True
        except TimeoutException:
            logger.error(f"{error_message} after {timeout}s")
            return False
```

**Migration Example**:

**Before**:
```python
# ❌ Blind waiting
login_button.click()
time.sleep(5)  # Hope page loads
```

**After**:
```python
# ✅ Smart waiting
login_button.click()
wait.until_url_contains('/dashboard')  # Wait for specific condition
```

---

#### Task 2.3: Exception Hierarchy

**File**: `scrapers/exceptions.py`
```python
"""
Scraper exception hierarchy
Enables granular error handling and recovery
"""


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
```

**Usage**:
```python
from scrapers.exceptions import LoginFailedError, RecoverableError

try:
    scraper.login()
except LoginFailedError as e:
    # Handle invalid credentials
    logger.error(f"Login failed for {e.institution}: {e}")
except RecoverableError as e:
    # Retry logic
    logger.warning(f"Retryable error: {e}")
except ScraperError as e:
    # Generic handler
    logger.error(f"Scraper error: {e}")
```

---

### Phase 3: Medium Priority Improvements (Week 4) 🟡

#### Task 3.1: Data Validation

**File**: `scrapers/validation.py`
```python
"""
Data validation for scraped results
"""

from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import re


@dataclass
class ValidationResult:
    """Result of data validation"""
    valid: bool
    errors: List[str]
    warnings: List[str]


class TransactionValidator:
    """Validate scraped transaction data"""

    @staticmethod
    def validate_transaction(txn: Dict[str, Any]) -> ValidationResult:
        """
        Validate a single transaction

        Returns:
            ValidationResult with errors/warnings
        """
        errors = []
        warnings = []

        # Required fields
        required = ['date', 'description', 'amount', 'currency']
        for field in required:
            if field not in txn or txn[field] is None:
                errors.append(f"Missing required field: {field}")

        # Date validation
        if 'date' in txn:
            try:
                date = datetime.fromisoformat(txn['date'])
                # Warn if date is in the future
                if date > datetime.now():
                    warnings.append(f"Future date: {txn['date']}")
                # Warn if date is very old
                if (datetime.now() - date).days > 365 * 3:
                    warnings.append(f"Very old transaction: {txn['date']}")
            except ValueError:
                errors.append(f"Invalid date format: {txn['date']}")

        # Amount validation
        if 'amount' in txn:
            try:
                amount = float(txn['amount'])
                if amount == 0:
                    warnings.append("Zero amount transaction")
                if abs(amount) > 1000000:
                    warnings.append(f"Unusually large amount: {amount}")
            except (ValueError, TypeError):
                errors.append(f"Invalid amount: {txn['amount']}")

        # Currency validation
        if 'currency' in txn:
            valid_currencies = ['ILS', 'USD', 'EUR', 'GBP']
            if txn['currency'] not in valid_currencies:
                warnings.append(f"Unusual currency: {txn['currency']}")

        # Description validation
        if 'description' in txn:
            if not txn['description'] or len(txn['description'].strip()) == 0:
                errors.append("Empty description")
            if len(txn['description']) > 500:
                warnings.append("Very long description")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    @classmethod
    def validate_batch(cls, transactions: List[Dict[str, Any]]) -> ValidationResult:
        """Validate a batch of transactions"""
        all_errors = []
        all_warnings = []

        for i, txn in enumerate(transactions):
            result = cls.validate_transaction(txn)
            if result.errors:
                all_errors.append(f"Transaction {i}: {', '.join(result.errors)}")
            if result.warnings:
                all_warnings.append(f"Transaction {i}: {', '.join(result.warnings)}")

        return ValidationResult(
            valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings
        )
```

---

#### Task 3.2: Rate Limiting for API Calls

**File**: `scrapers/utils/rate_limiter.py`
```python
"""
Rate limiting to avoid being blocked by APIs
"""

import time
from threading import Lock
from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    requests_per_second: float = 1.0
    requests_per_minute: Optional[int] = None
    requests_per_hour: Optional[int] = None


class RateLimiter:
    """
    Token bucket rate limiter

    Example:
        limiter = RateLimiter(requests_per_second=2)

        for request in requests:
            with limiter:
                make_api_call()
    """

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.min_interval = 1.0 / config.requests_per_second if config.requests_per_second > 0 else 0
        self.last_request_time = 0
        self.lock = Lock()

    def __enter__(self):
        """Context manager entry - wait if needed"""
        self.wait()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        pass

    def wait(self):
        """Wait until rate limit allows next request"""
        with self.lock:
            now = time.time()
            time_since_last = now - self.last_request_time

            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)

            self.last_request_time = time.time()
```

**Usage**:
```python
# In CAL scraper
rate_limiter = RateLimiter(RateLimitConfig(requests_per_second=2))

for month in months:
    with rate_limiter:
        data = self.fetch_completed_transactions(card_id, month, year)
```

---

### Phase 4: Polish & Production Readiness (Week 5) 🟢

#### Task 4.1: Health Checks

**File**: `scrapers/health.py`
```python
"""
Scraper health checks and monitoring
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Health status of a scraper"""
    healthy: bool
    last_successful_run: Optional[datetime]
    last_error: Optional[str]
    consecutive_failures: int
    avg_run_time_seconds: Optional[float]
    metadata: Dict[str, Any]


class ScraperHealthCheck:
    """
    Monitor scraper health

    Tracks:
    - Success/failure rates
    - Performance metrics
    - Broken selectors
    """

    def __init__(self, scraper_name: str):
        self.scraper_name = scraper_name
        self.consecutive_failures = 0
        self.last_successful_run = None
        self.last_error = None

    def record_success(self, run_time: float):
        """Record successful scrape"""
        self.consecutive_failures = 0
        self.last_successful_run = datetime.now()
        logger.info(f"{self.scraper_name} completed in {run_time:.2f}s")

    def record_failure(self, error: Exception):
        """Record failed scrape"""
        self.consecutive_failures += 1
        self.last_error = str(error)
        logger.error(
            f"{self.scraper_name} failed "
            f"({self.consecutive_failures} consecutive): {error}"
        )

    def is_healthy(self, max_failures: int = 3) -> bool:
        """Check if scraper is healthy"""
        return self.consecutive_failures < max_failures

    def get_status(self) -> HealthStatus:
        """Get current health status"""
        return HealthStatus(
            healthy=self.is_healthy(),
            last_successful_run=self.last_successful_run,
            last_error=self.last_error,
            consecutive_failures=self.consecutive_failures,
            avg_run_time_seconds=None,  # TODO: track this
            metadata={}
        )
```

---

## Migration Strategy

### Week 1: Break Down pension_base.py
1. Create new modular structure
2. Move email logic to email_retriever.py
3. Move MFA logic to mfa_handler.py
4. Update Migdal/Phoenix to use new modules
5. Test thoroughly

### Week 2: Logging and Cleanup
1. Replace all print() with logging
2. Add context managers to all scrapers
3. Externalize configurations
4. Test with real credentials

### Week 3: Reliability
1. Add retry logic with decorators
2. Replace time.sleep with smart waits
3. Implement exception hierarchy
4. Add error recovery

### Week 4: Validation and Polish
1. Add data validation
2. Implement rate limiting
3. Add health checks
4. Performance testing

### Week 5: Documentation and Testing
1. Write comprehensive docstrings
2. Add usage examples
3. Create integration tests
4. Update README

---

## Success Metrics

### Code Quality

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| pension_base.py lines | 1066 | 0 (removed) | N/A |
| Largest file size | 1066 lines | <200 lines | <250 |
| Code duplication | 30% | 0% | <5% |
| Test coverage | 0% | 85% | >80% |
| Magic strings | 50+ | 0 | 0 |

### Performance

| Metric | Before | After |
|--------|--------|-------|
| Average scrape time | 60s | 45s (smart waits) |
| Retry success rate | 0% | 85% |
| Resource leak rate | 10% | 0% |

### Maintainability

| Metric | Before | After |
|--------|--------|-------|
| Add new institution | 8 hours, 5 files | 2 hours, 1 file |
| Fix broken selector | 30 minutes | 5 minutes |
| Debug failure | 1 hour | 10 minutes |

---

## Risk Assessment

### High Risk
- **Breaking existing functionality**: Mitigated by comprehensive testing
- **Browser compatibility**: Test on multiple Chrome versions

### Medium Risk
- **Performance regressions**: Benchmark before/after
- **New dependencies**: Minimal (just logging enhancements)

### Low Risk
- **Configuration errors**: Validate at startup
- **Refactor complexity**: Incremental approach

---

## Conclusion

This refactoring plan transforms the scraper layer from a maintenance nightmare into a clean, modular, production-ready system:

**Critical Improvements** (Week 1-2):
- 🔴 Eliminate 1066-line monster file
- 🔴 Remove all code duplication
- 🔴 Add proper logging
- 🔴 Guaranteed resource cleanup

**High Priority** (Week 3):
- 🟠 Retry logic for reliability
- 🟠 Smart waits replace time.sleep
- 🟠 Proper exception hierarchy

**Medium Priority** (Week 4):
- 🟡 Data validation
- 🟡 Rate limiting
- 🟡 Health monitoring

**Expected Outcomes**:
- 90% reduction in largest file size (1066 → 150 lines)
- Zero code duplication (30% → 0%)
- 85% retry success rate
- 2 hours to add new institution (vs 8 hours)

**Next Steps**: Review and approve, then begin Phase 1 implementation.