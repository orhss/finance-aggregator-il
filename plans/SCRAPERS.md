# Credit Card Scrapers Implementation Guide

## Overview

This document consolidates implementation details for all credit card scrapers in the project. All scrapers follow the **Hybrid Selenium + API Pattern**: use Selenium for complex login flows and token/session extraction, then switch to direct API calls for efficient data retrieval.

**Supported Institutions**:
- **CAL** (Visa CAL) - `cal_credit_card_client.py`
- **Max** - `max_credit_card_client.py`
- **Isracard** - `isracard_credit_card_client.py`

**Common Features**:
- Multi-account support (multiple credentials per institution)
- Installment payment handling (splits into monthly records)
- Both pending and completed transactions
- Multiple cards per account
- Standardized `Transaction`, `CardAccount`, `Installments` DTOs

---

## CAL Scraper

### Overview

**File**: `scrapers/credit_cards/cal_credit_card_client.py`
**Class**: `CALCreditCardScraper`
**Institution**: CAL (Visa CAL)

### Architecture

**Login Flow**:
1. Navigate to `https://www.cal-online.co.il/`
2. Click login button (`#ccLoginDesktopBtn`)
3. **Wait for iframe** (login form is in iframe from `connect.cal-online.co.il`)
4. Switch to iframe context
5. Click "Regular Login" tab (`#regular-login`)
6. Enter username (`[formcontrolname='userName']`)
7. Enter password (`[formcontrolname='password']`)
8. Submit form
9. Switch back to main content
10. Handle tutorial popup if present
11. Extract authorization token
12. Extract card information

**Token Extraction Strategy** (dual approach):
1. **Primary**: Session storage
   - Key: `sessionStorage.getItem('auth-module')`
   - Path: `auth.calConnectToken`
   - Format: Token value (prepend with `CALAuthScheme `)

2. **Fallback**: Performance logs (network monitoring)
   - Enabled via: `options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})`
   - Look for: `Network.requestWillBeSent` to SSO endpoint
   - Endpoint: `https://connect.cal-online.co.il/col-rest/calconnect/authentication/SSO`
   - Extract: `Authorization` header from request

**Card Information Extraction**:
- Source: `sessionStorage.getItem('init')`
- Path: `result.cards[]`
- Fields: `cardUniqueId`, `last4Digits`
- Retry logic: 5 attempts with 2-second delay (session storage populated async)

### API Endpoints

**Base URLs**:
```
BASE_URL = "https://www.cal-online.co.il/"
TRANSACTIONS_ENDPOINT = "https://api.cal-online.co.il/Transactions/api/transactionsDetails/getCardTransactionsDetails"
PENDING_ENDPOINT = "https://api.cal-online.co.il/Transactions/api/approvals/getClearanceRequests"
```

**Required Headers**:
```python
{
    'Authorization': 'CALAuthScheme {token}',  # Extracted during login
    'X-Site-Id': '09031987-273E-2311-906C-8AF85B17C8D9'  # Constant
}
```

**Completed Transactions** (`getCardTransactionsDetails`):
- Method: POST
- Request body:
  ```json
  {
    "cardUniqueId": "...",
    "monthView": "2024-12-01T00:00:00.000Z"  // First day of month
  }
  ```
- Returns: Transactions for specified month and card

**Pending Transactions** (`getClearanceRequests`):
- Method: POST
- Request body:
  ```json
  {
    "cardUniqueIds": ["id1", "id2", ...]
  }
  ```
- Returns: All pending transactions across specified cards

### Transaction Processing

**Transaction Types** (determined by `trnTypeCode`):
- `"5"` - Regular transaction
- `"6"` - Credit (refund)
- `"8"` - Installments
- `"9"` - Standing order

**Installment Handling**:
- Field: `trnInstl.trnInstlInd` (installment number)
- Field: `trnInstl.trnInstlTot` (total installments)
- When `trnInstlInd > 0`: Split transaction into monthly records
- Each month charged amount: `charged_amount / total_installments`

**Date Handling**:
- Transaction date: `trnDt` (when purchase occurred)
- Processing date: `trnPrcsDt` (when charged to account)
- Format: ISO date string

### Common Issues & Solutions

#### Issue 1: Iframe Timing
**Symptom**: `CALLoginError: Failed to find login iframe`
**Cause**: Iframe loads asynchronously
**Solution**:
- Wait for iframe with 10-second timeout
- Check `src` attribute contains "connect"
- Retry every 0.5 seconds

#### Issue 2: Token Extraction Fails
**Symptom**: `CALAuthorizationError: Failed to extract authorization token`
**Cause**: Session storage not populated or performance logs disabled
**Solutions**:
- Ensure performance logging enabled: `goog:loggingPrefs`
- Check session storage retry logic (5 attempts)
- Verify user stayed logged in (no redirect back to login)

#### Issue 3: Card Info Extraction Fails
**Symptom**: `CALScraperError: 'init' key not in session storage`
**Cause**: Session storage populated asynchronously after login
**Solution**:
- Implemented retry logic with 5 attempts
- 2-second delay between attempts
- Logs available keys for debugging

#### Issue 4: Invalid Password Error
**Symptom**: Login appears successful but still on login page
**Solution**:
- Check URL contains "connect" (still on login page)
- Switch to iframe and look for `div.general-error > div`
- Extract error message and raise `CALLoginError`

---

## Max Scraper

### Overview

**File**: `scrapers/credit_cards/max_credit_card_client.py`
**Class**: `MaxCreditCardScraper`
**Institution**: Max

### Architecture

**Login Flow**:
1. Navigate to `https://www.max.co.il/homepage/welcome`
2. Click login button
3. Enter username
4. Enter password
5. Submit form
6. Check for error popups:
   - `#popupWrongDetails` (invalid credentials)
   - `#popupCardHoldersLoginError` (general login error)
7. Check for password expiration redirect (`/renew-password`)
8. Verify successful landing at `/homepage/personal`
9. Extract cookies for API authentication

**Authentication Method**: **Cookie-based** (not token-based like CAL)
- After successful Selenium login, extract all browser cookies
- Use cookies in subsequent API requests
- No explicit authorization token needed

**Transaction Plan Types** (Hebrew, stored in `MaxPlanName` enum):
- `"רגילה"` - Normal (regular charge)
- `"חיוב עסקות מיידי"` - Immediate charge
- `"אינטרנט/חו\"ל"` - Internet/International shopping
- `"תשלומים"` - Installments
- `"חיוב חודשי"` - Monthly charge
- `"דחוי חודש"` - One month postponed
- `"דחוי לחיוב החודשי"` - Monthly postponed
- Plus 10+ more specialized plan types (see enum in code)

### API Endpoints

**Base URLs**:
```
BASE_WELCOME_URL = "https://www.max.co.il"
BASE_API_ACTIONS_URL = "https://onlinelcapi.max.co.il"
```

**Categories Endpoint**:
```
GET https://onlinelcapi.max.co.il/api/contents/getCategories
```
- Authentication: Cookies
- Returns: Map of category IDs to Hebrew names
- Called once during initialization

**Transactions Endpoint**:
```
GET https://onlinelcapi.max.co.il/api/registered/transactionDetails/getTransactionsAndGraphs
```
- Parameters:
  - `month`: 1-12
  - `year`: YYYY
  - `requiredDate`: `DD/MM/YYYY` (first day of month)
- Authentication: Cookies
- Returns: All cards and their transactions for the month

### Transaction Processing

**Currency Codes**:
- `376` - ILS (₪)
- `840` - USD ($)
- `978` - EUR (€)

**Installment Detection**:
- Field: `txnIsInstallments` (boolean)
- If true, parse `currentPayment` and `totalPayments` from transaction data
- Split into monthly records like CAL

**Status Detection**:
- Pending: `isFuture` flag or processing date in future
- Completed: Otherwise

### Common Issues & Solutions

#### Issue 1: Password Expired
**Symptom**: Redirect to `/renew-password` after login
**Solution**: Not currently automated - user must manually update password
**Future**: Could implement password change flow

#### Issue 2: Cookie Expiration
**Symptom**: API returns 401/403 after some time
**Cause**: Session cookies expired
**Solution**: Re-login to get fresh cookies (currently handled by recreating scraper instance)

#### Issue 3: Plan Type Not Recognized
**Symptom**: Unknown Hebrew plan name in transaction
**Solution**:
- Check `MaxPlanName` enum for missing plan types
- Add new enum value if needed
- Plan type affects transaction categorization

#### Issue 4: Category Loading Fails
**Symptom**: Categories empty or API call fails
**Cause**: Cookie issue or API endpoint changed
**Solution**:
- Categories are optional (not critical for transaction fetch)
- Set `fetch_categories=False` to skip

---

## Isracard Scraper

### Overview

**File**: `scrapers/credit_cards/isracard_credit_card_client.py`
**Class**: `IsracardCreditCardScraper`
**Institution**: Isracard (and subsidiaries)

**Special Note**: Isracard has multiple subsidiaries (Isracard, Amex, etc.) with different URLs and company codes but same API structure. This scraper is **configurable** via `base_url` and `company_code` parameters.

### Architecture

**Login Flow** (uses last 6 digits of card):
1. Navigate to login page (configurable `base_url`)
2. Enter country code: `212` (constant)
3. Enter ID type: `1` (constant)
4. Enter user ID (Israeli ID number)
5. Enter last 6 digits of card
6. Enter password
7. Submit form
8. **Check for password change prompt** (unique to Isracard)
9. If prompted to change password → Raise `IsracardChangePasswordError`
10. Otherwise verify successful login
11. Extract session cookies for API authentication

**Authentication Method**: **Cookie-based** (like Max)
- Extract browser cookies after login
- Use in API requests via `ProxyRequestHandler.ashx`

**Password Change Detection**:
- Isracard may force password changes periodically
- Detection: Check for password change modal/redirect
- Action: Raise `IsracardChangePasswordError` with clear message
- User must manually change password before continuing

### API Endpoints

**Services Proxy**:
```
POST {base_url}/services/ProxyRequestHandler.ashx
```

All API calls go through this proxy endpoint with different request bodies:

**Fetch Accounts** (cards for a month):
```json
{
  "reqName": "DashboardMonth",
  "infoRequest": {
    "period": "2024-12",
    "companyCode": "{company_code}",
    "cardsNumbers": null  // null = all cards
  }
}
```

**Fetch Transactions**:
```json
{
  "reqName": "DashboardMonthTransaction",
  "infoRequest": {
    "period": "2024-12",
    "companyCode": "{company_code}",
    "cardNumber": "...",
    "accountIndex": 0
  }
}
```

**Fetch Transaction Category** (optional, slower):
```json
{
  "reqName": "CardTransactionDetails",
  "infoRequest": {
    "companyCode": "{company_code}",
    "cardNumber": "...",
    "accountIndex": 0,
    "transactionId": "..."
  }
}
```

### Transaction Processing

**Constants**:
```python
COUNTRY_CODE = '212'
ID_TYPE = '1'
INSTALLMENTS_KEYWORD = 'תשלום'  # Hebrew for "payment"
SHEKEL_CURRENCY_KEYWORD = 'ש"ח'
SHEKEL_CURRENCY = 'ILS'
```

**Installment Detection**:
- Check if description contains `תשלום` (Hebrew "payment")
- Parse pattern: `תשלום X מתוך Y` (Payment X of Y)
- Extract current installment number and total

**Rate Limiting**:
- `SLEEP_BETWEEN_REQUESTS = 1.0` seconds
- Applied between transaction fetches to avoid throttling
- `TRANSACTIONS_BATCH_SIZE = 10` (fetch in batches)

**Currency Conversion**:
- Original amount and currency from transaction
- Charged amount in ILS (after conversion if applicable)
- Keywords: `ש"ח` or `שח` → normalize to `ILS`

### Common Issues & Solutions

#### Issue 1: Password Change Required
**Symptom**: `IsracardChangePasswordError` raised
**Cause**: Isracard forces periodic password changes
**Solution**:
- User must log in manually and change password
- Update credentials in config
- Re-run sync

#### Issue 2: Invalid Card 6 Digits
**Symptom**: Login fails with authentication error
**Cause**: Wrong last 6 digits of card
**Solution**:
- Verify `card_6_digits` in credentials
- Must match the card being queried
- For multiple cards, may need multiple accounts

#### Issue 3: Company Code Wrong
**Symptom**: API returns no data or errors
**Cause**: Wrong `company_code` for subsidiary
**Solution**:
- Isracard: `"11"`
- Amex: Different code (varies by subsidiary)
- Check Isracard variant and use correct code

#### Issue 4: API Request Format Changed
**Symptom**: API returns errors after working previously
**Cause**: Isracard may update API structure
**Solution**:
- Check network tab in browser during manual login
- Compare request format with scraper
- Update `reqName` or `infoRequest` structure

#### Issue 5: Category Fetch Slow
**Symptom**: Scraper takes too long
**Cause**: `fetch_categories=True` makes extra API call per transaction
**Solution**:
- Set `fetch_categories=False` (default)
- Categories are optional metadata, not critical

---

## Common Patterns Across All Scrapers

### 1. Hybrid Selenium + API Approach

**Why?**
- Login flows are too complex for direct API auth (CAPTCHAs, dynamic forms, tokens)
- Selenium handles the complex human-like login
- API calls are fast and efficient for data fetching

**Pattern**:
```python
1. setup_driver()           # Initialize Selenium
2. login()                  # Complex login via Selenium
3. extract_auth_tokens()    # Get tokens/cookies from browser
4. fetch_data_via_api()     # Fast API calls with auth
5. cleanup()                # Close browser
```

### 2. Multi-Account Support

All scrapers support multiple accounts per institution (implemented in `config/settings.py`):
- Credentials stored as `List[CreditCardCredentials]`
- Each account has optional label: "Personal", "Business", etc.
- Services iterate and sync sequentially (one at a time)
- See `plans/MULTI_ACCOUNT_PLAN.md` for details

### 3. Installment Handling

**Common Logic**:
```python
if transaction has installments:
    for month in range(1, total_installments + 1):
        create_transaction(
            amount=total_amount / total_installments,
            installment_number=month,
            installment_total=total_installments,
            processed_date=original_date + month * 30_days
        )
```

**Result**: Single installment purchase → N separate monthly transaction records in database

### 4. Transaction Deduplication

**Database Level** (not scraper level):
- Unique constraint on `(account_id, transaction_id, transaction_date)`
- For pending transactions (no ID): `(account_id, description, date, amount)`
- SQLAlchemy handles INSERT vs UPDATE automatically

### 5. Error Handling Hierarchy

All scrapers use custom exception hierarchy:
```
{Institution}ScraperError (base)
├── {Institution}LoginError
├── {Institution}APIError
└── {Institution}ChangePasswordError (Isracard only)
```

**Recoverable vs Fatal**:
- Login errors → Fatal (stop sync)
- Single transaction parse error → Log warning, continue
- API errors → Fatal (inconsistent state)

### 6. Logging Strategy

All scrapers use Python `logging` module:
```python
logger = logging.getLogger(__name__)

logger.info("High-level flow: Logging in...")
logger.debug("Low-level detail: Username field found")
logger.error("Error occurred", exc_info=True)  # Include stack trace
logger.warning("Non-critical issue: Missing optional field")
```

**Log Levels**:
- `INFO`: Login steps, transaction counts, success/failure
- `DEBUG`: Element selectors, API responses, retry attempts
- `ERROR`: Exceptions with full stack traces
- `WARNING`: Missing optional data, fallback behavior

---

## Troubleshooting Guide

### General Debugging Steps

1. **Enable Visible Mode**:
   ```python
   scraper = CALCreditCardScraper(credentials, headless=False)
   ```
   - Watch browser automation in real-time
   - See what Selenium is doing

2. **Check Logs**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```
   - See all debug messages
   - Trace exact failure point

3. **Verify Credentials**:
   - Test manual login in browser first
   - Ensure no password expiration
   - Check for 2FA or additional security prompts

4. **Check Selectors**:
   - Institutions may update their websites
   - CSS selectors may change
   - Use browser dev tools to verify current selectors

5. **Network Issues**:
   - Check internet connectivity
   - Verify institution website is accessible
   - Some institutions have rate limiting

### Institution-Specific Quick Fixes

**CAL**:
- Iframe not found → Increase timeout in `wait_for_iframe()`
- Token extraction fails → Check if session storage keys changed
- Tutorial popup blocks → Clear browser cache/cookies

**Max**:
- Categories fail to load → Set `fetch_categories=False`
- Cookie expiration → Re-create scraper instance (triggers new login)
- Unknown plan type → Add to `MaxPlanName` enum

**Isracard**:
- Password change required → User must update password manually
- Company code wrong → Verify subsidiary and use correct code
- Slow performance → Disable `fetch_categories`

### Performance Optimization

**Headless Mode**:
```python
scraper = Scraper(credentials, headless=True)  # Default
```
- Faster execution
- Lower memory usage
- No GUI overhead

**Reduce Date Range**:
```python
# Instead of 18 months:
scraper.fetch_transactions(months_back=3)
```
- Fewer API calls
- Faster sync
- Less data to process

**Parallel Accounts** (experimental):
- Current implementation: Sequential sync (safe)
- Future: Parallel sync option for advanced users
- Risk: Rate limiting, browser resource usage

---

## Adding a New Credit Card Scraper

### Step-by-Step Guide

1. **Research the Institution**:
   - Test manual login flow in browser
   - Use browser dev tools (Network tab) to observe:
     - Login request structure
     - Authentication method (token, cookie, header)
     - API endpoints for transaction data
   - Document any unique flows (password change, 2FA, etc.)

2. **Create Scraper File**:
   ```
   scrapers/credit_cards/{institution}_credit_card_client.py
   ```

3. **Define Models** (follow existing pattern):
   ```python
   @dataclass
   class {Institution}Credentials:
       username: str
       password: str
       # Add any institution-specific fields

   class TransactionStatus(Enum):
       PENDING = "pending"
       COMPLETED = "completed"

   class TransactionType(Enum):
       NORMAL = "normal"
       INSTALLMENTS = "installments"
       # Add institution-specific types

   @dataclass
   class Transaction:
       # Standardized model (same across all scrapers)

   @dataclass
   class CardAccount:
       # Standardized model
   ```

4. **Implement Scraper Class**:
   ```python
   class {Institution}CreditCardScraper:
       def __init__(self, credentials, headless=True):
           ...

       def setup_driver(self):
           # Chrome setup with necessary options

       def login(self) -> bool:
           # Selenium login flow

       def extract_auth_tokens(self):
           # Token/cookie extraction

       def fetch_transactions(self, months_back=3):
           # API calls for data

       def cleanup(self):
           # Close browser, cleanup resources
   ```

5. **Add to Service Layer**:
   - Update `services/credit_card_service.py`
   - Add `sync_{institution}()` method
   - Follow existing patterns (see `sync_cal`, `sync_max`)

6. **Add CLI Commands**:
   - Update `cli/commands/sync.py`
   - Add `sync_{institution}` command
   - Support multi-account via `--account` flag

7. **Add Configuration**:
   - Update `config/settings.py`
   - Add to `Credentials` model
   - Support multi-account list format

8. **Document**:
   - Add section to this file (`plans/SCRAPERS.md`)
   - Update `CLAUDE.md` with brief mention
   - Add usage examples to `README.md`

9. **Test**:
   - Test login flow (headless and visible)
   - Test transaction fetching
   - Test multi-account support
   - Test error handling (wrong password, etc.)

### Template Code

See existing scrapers (`cal_credit_card_client.py`, `max_credit_card_client.py`, `isracard_credit_card_client.py`) as reference templates. They follow consistent patterns that should be maintained for new scrapers.

---

## Maintenance Notes

### When Institution Updates Their Website

1. **Check Selectors**:
   - CSS selectors are fragile
   - Use browser dev tools to find new selectors
   - Update in scraper code

2. **Check API Structure**:
   - Request/response format may change
   - Update DTOs and parsing logic
   - Add logging to catch structure changes early

3. **Test After Changes**:
   - Always test with real credentials (safely)
   - Verify both pending and completed transactions
   - Check installment handling

### Version Control

- Each scraper is **independent** (changes to CAL don't affect Max)
- Keep changes **backward compatible** when possible
- Document breaking changes in commit messages
- Consider deprecation warnings before removing features

### Security Considerations

- **Never log passwords or tokens** (use `logger.debug("Token: ****")`)
- **Clear browser cache** between test runs to avoid token leakage
- **Encrypted credential storage** (handled by `config/settings.py`)
- **Rate limiting respect** (don't spam institution APIs)

---

## Future Enhancements

### Planned Improvements

1. **CAPTCHA Handling**:
   - Currently not needed for supported institutions
   - Future: Integrate 2Captcha or manual CAPTCHA solver

2. **2FA Support**:
   - SMS-based MFA (like pension funds)
   - Email-based MFA
   - TOTP (Google Authenticator)

3. **Automatic Retry on Transient Errors**:
   - Network timeouts
   - Temporary API unavailability
   - Exponential backoff strategy

4. **Transaction Categorization**:
   - AI-based merchant categorization
   - Custom category rules
   - Budget tracking integration

5. **Real-Time Sync**:
   - Webhook-based updates (if institutions support)
   - Scheduled background sync
   - Push notifications for new transactions

6. **Performance Optimization**:
   - Connection pooling for API requests
   - Parallel account sync (with care)
   - Incremental sync (only new transactions)

### Known Limitations

- **No offline mode** (requires active internet connection)
- **No mobile app scraping** (desktop websites only)
- **Sequential account sync** (one at a time, slower for many accounts)
- **No transaction modification** (read-only, can't dispute or categorize via scraper)

---

## References

- **CLAUDE.md**: High-level architecture overview
- **plans/MULTI_ACCOUNT_PLAN.md**: Multi-account implementation details
- **plans/CLI_PLAN.md**: CLI commands and database schema
- **services/credit_card_service.py**: Service layer integration
- **cli/commands/sync.py**: CLI sync commands

For questions or issues, check existing code or create an issue in the repository.
