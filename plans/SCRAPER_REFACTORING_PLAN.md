# Scraper Layer Refactoring Plan

## Status: Phase 3 Complete ✅

**Last Updated**: 2025-12-23

| Phase | Status |
|-------|--------|
| Phase 1: Modular Base Classes | ✅ Complete |
| Phase 2: Logging, Cleanup, Testing | ✅ Complete |
| Phase 3: Selenium Automator Migration | ✅ Complete |

## Final Architecture

```
OLD: pension_base.py (1066 lines, monolithic) - REMOVED ✅

NEW: Modular structure
scrapers/base/
├── email_retriever.py     # EmailMFARetriever - IMAP/email operations
├── mfa_handler.py         # MFAHandler - code entry (single/individual fields)
├── selenium_driver.py     # SeleniumDriver - WebDriver setup, context manager
├── web_actions.py         # WebActions - form filling, clicking, waits
├── pension_automator.py   # PensionAutomatorBase - login flows, composition
└── broker_base.py         # BrokerAPIClient - REST API base

scrapers/utils/
├── retry.py               # @retry_with_backoff decorator
└── wait_conditions.py     # SmartWait - replaces time.sleep()

scrapers/
├── exceptions.py          # Exception hierarchy
└── config/logging_config.py  # Centralized logging
```

### Pension Automator Hierarchy
```
PensionAutomatorBase (uses composition)
├── Composes: SeleniumDriver, WebActions, MFAHandler
├── Provides: login_with_id_and_mfa_flow(), login_with_id_email_and_mfa_flow()
│
├── MigdalSeleniumAutomator (extends)
│   └── Only overrides: extract_financial_data(), OTP selectors
│
└── PhoenixSeleniumAutomator (extends)
    └── Only overrides: extract_financial_data(), OTP selectors
```

## Completed Tasks

### Phase 1: Module Creation ✅
- [x] `email_retriever.py` - EmailMFARetriever base class, context manager, logging
- [x] `mfa_handler.py` - Single-field and individual-field MFA patterns
- [x] `logging_config.py` - Centralized logging, third-party suppression
- [x] `exceptions.py` - Exception hierarchy (Auth, DataExtraction, Network, Validation)
- [x] `retry.py` - Exponential backoff decorator
- [x] `wait_conditions.py` - SmartWait class

### Phase 2: Client Migration ✅
- [x] Migdal pension client refactored (print → logging, new base class)
- [x] Phoenix pension client refactored (print → logging, new base class)
- [x] Both sync flows verified working
- [x] Context manager cleanup verified

### Phase 2: Deprecation ✅
- [x] Added deprecation warnings to old `EmailMFARetrieverBase`
- [x] Added deprecation warnings to old `SeleniumMFAAutomatorBase`
- [x] Documentation updated

### Phase 3: Selenium Automator ✅
- [x] `selenium_driver.py` - WebDriver setup, Chrome options, context manager
- [x] `web_actions.py` - Form utilities, button clicking, iframe switching
- [x] `pension_automator.py` - PensionAutomatorBase with composition
- [x] Migdal migrated to PensionAutomatorBase
- [x] Phoenix migrated to PensionAutomatorBase
- [x] `pension_base.py` removed
- [x] Imports updated across codebase

## Key Modules Reference

### EmailMFARetriever (`scrapers/base/email_retriever.py`)
```python
@dataclass
class EmailConfig:
    email_address: str
    password: str
    imap_server: str = "imap.gmail.com"

@dataclass
class MFAConfig:
    sender_email: str
    code_pattern: str = r'\b\d{6}\b'
    max_wait_time: int = 60
    email_delay: int = 30

class EmailMFARetriever(ABC):
    # Context manager for IMAP connection
    # wait_for_mfa_code() - polls for MFA email
    # extract_mfa_code() - abstract, institution-specific
```

### MFAHandler (`scrapers/base/mfa_handler.py`)
```python
class MFAHandler:
    enter_code_single_field(code, selector, fallback_selectors)  # Phoenix
    enter_code_individual_fields(code, selectors)  # Migdal (6 fields)
    submit_mfa(button_selector, fallback_selectors)
```

### SmartWait (`scrapers/utils/wait_conditions.py`)
```python
class SmartWait:
    until_element_present(selector)
    until_element_clickable(selector)
    until_text_present(text)
    until_url_contains(url_fragment)
    until_element_invisible(selector)
```

### Retry Decorator (`scrapers/utils/retry.py`)
```python
@retry_with_backoff(max_attempts=3, exceptions=(TimeoutException,))
def click_button(driver, selector):
    ...

# Specialized decorators
@retry_selenium_action(max_attempts=3)
@retry_api_call(max_attempts=3)
```

### Exception Hierarchy (`scrapers/exceptions.py`)
```
ScraperError
├── AuthenticationError
│   ├── LoginFailedError
│   ├── MFAFailedError
│   └── SessionExpiredError
├── DataExtractionError
│   ├── ElementNotFoundError
│   └── DataParsingError
├── NetworkError
│   ├── APIError
│   └── ConnectionError
└── ValidationError
    ├── InvalidCredentialsError
    └── InvalidDataError
```

## Impact Summary

| Metric | Before | After |
|--------|--------|-------|
| pension_base.py | 1066 lines | 0 (removed) |
| Modular base files | 0 | 7 files |
| Print statements | ~35+ | 0 (logging) |
| Resource cleanup | Manual | Context managers |
| Retry logic | None | Exponential backoff |
| Waits | time.sleep() | SmartWait |

## Remaining Issues (Not Addressed)

### Medium Priority 🟡
| ID | Issue | Files |
|----|-------|-------|
| M1 | No data validation | All scrapers |
| M2 | No rate limiting | cal_credit_card_client.py |
| M3 | No page object pattern | pension implementations |

### Low Priority 🟢
| ID | Issue | Files |
|----|-------|-------|
| L1 | No metrics/monitoring | All scrapers |
| L2 | No scraper versioning | All scrapers |
| L3 | No caching for static data | All scrapers |

## Usage Examples

### Using EmailMFARetriever
```python
from scrapers.base.email_retriever import EmailMFARetriever, EmailConfig, MFAConfig

class MigdalMFARetriever(EmailMFARetriever):
    def extract_mfa_code(self, email_message):
        # Institution-specific extraction
        ...

with MigdalMFARetriever(email_config, mfa_config) as retriever:
    code = retriever.wait_for_mfa_code()
```

### Using PensionAutomatorBase
```python
from scrapers.base.pension_automator import PensionAutomatorBase

class MigdalSeleniumAutomator(PensionAutomatorBase):
    OTP_SELECTORS = [...]

    def extract_financial_data(self):
        # Institution-specific data extraction
        ...

with MigdalSeleniumAutomator(...) as automator:
    automator.login_with_id_and_mfa_flow()
    data = automator.extract_financial_data()
```

### Using SmartWait
```python
from scrapers.utils.wait_conditions import SmartWait

wait = SmartWait(driver, default_timeout=30)
wait.until_element_clickable("button.submit")
wait.until_url_contains("/dashboard")
```