# Streamlit UI Plan

## Overview

This plan outlines the implementation of a comprehensive Streamlit-based web UI for the Financial Data Aggregator. The UI will provide visual data exploration, sync management, and analytics capabilities that complement the existing CLI.

## Architecture

### Technology Stack
- **Streamlit**: Main UI framework
- **Plotly**: Interactive charts and graphs
- **Pandas**: Data manipulation and display
- **SQLAlchemy**: Database access (via existing services)

### Integration Points
- Reuse existing service layer (`AnalyticsService`, `TagService`, `RulesService`, etc.)
- Reuse existing database models
- Reuse credential management from `config/settings.py`

### File Structure
```
streamlit_app/
├── __init__.py
├── app.py                    # Main entry point
├── config.py                 # Streamlit configuration
├── pages/
│   ├── __init__.py
│   ├── 1_📊_Dashboard.py     # Main dashboard
│   ├── 2_🔄_Sync.py          # Sync management
│   ├── 3_💳_Transactions.py  # Transaction browser
│   ├── 4_📈_Analytics.py     # Charts and analysis
│   ├── 5_🏷️_Tags.py          # Tag management
│   ├── 6_📋_Rules.py         # Rules management
│   ├── 7_💰_Accounts.py      # Account management
│   └── 8_⚙️_Settings.py      # Configuration
├── components/
│   ├── __init__.py
│   ├── sidebar.py            # Shared sidebar components
│   ├── filters.py            # Reusable filter components
│   ├── charts.py             # Chart components
│   ├── tables.py             # Table display components
│   └── forms.py              # Input form components
├── utils/
│   ├── __init__.py
│   ├── session.py            # Session state management
│   ├── formatters.py         # Display formatters (currency, dates)
│   └── rtl.py                # RTL text handling for Hebrew
└── styles/
    └── custom.css            # Custom styling
```

---

## Pages Specification

### 1. Dashboard (Home) 📊

**Purpose**: High-level overview of financial status

**Components**:

#### Summary Cards Row
- Total Portfolio Value (sum of all account balances)
- Monthly Spending (current month total)
- Pending Transactions (count and amount)
- Last Sync Status (timestamp + success/failure indicator)

#### Quick Charts
- **Spending by Category** (donut chart - top 10 categories)
- **Monthly Spending Trend** (line chart - last 6 months)
- **Balance Distribution** (pie chart - by account type)
- **Recent Spending by Day** (bar chart - last 14 days)

#### Recent Activity
- Last 10 transactions (compact table)
- Recent sync history (last 5 syncs with status)

#### Quick Actions
- "Sync All" button
- "View Transactions" button
- "View Reports" button

---

### 2. Sync Management 🔄

**Purpose**: Trigger and monitor data synchronization

**Components**:

#### Sync Status Overview
- Status cards for each institution showing:
  - Last sync time
  - Records synced
  - Status (success/failed/never synced)
  - "Sync Now" button per institution

#### Sync Options
- **Institution Selector** (multi-select or individual buttons)
  - Brokers: Excellence, Meitav
  - Pensions: Migdal, Phoenix
  - Credit Cards: CAL, Max, Isracard
- **Account Selector** (for multi-account institutions)
- **Options**:
  - Headless mode toggle
  - Months back slider (1-24 months, default 3)
  - Months forward slider (0-6 months, default 1)

#### Sync Actions
- "Sync Selected" button
- "Sync All" button
- Progress indicator during sync (spinner + status messages)

#### Sync History Table
- Columns: Timestamp, Institution, Status, Records Added, Records Updated, Duration, Error Message
- Filters: Institution, Status, Date Range
- Pagination

**Implementation Notes**:
- Sync operations run in subprocess to avoid blocking UI
- Use `st.status()` or `st.progress()` for real-time feedback
- Store sync output in session state for display

---

### 3. Transactions Browser 💳

**Purpose**: View, filter, search, and manage transactions

**Components**:

#### Filter Panel (Sidebar or Expander)
- **Date Range**: Start/End date pickers (default: last 3 months)
- **Account**: Multi-select dropdown (grouped by type)
- **Institution**: Multi-select (CAL, Max, Isracard, etc.)
- **Status**: Radio (All / Pending / Completed)
- **Category**: Multi-select dropdown
- **Tags**: Multi-select with AND logic
- **Untagged Only**: Checkbox
- **Search**: Text input (filters description)
- "Apply Filters" and "Clear Filters" buttons

#### Transaction Table
- Columns: Date, Description, Amount, Category, Tags, Status, Account, Actions
- Features:
  - Sortable columns (click header)
  - Color coding (negative=red, positive=green)
  - Expand row to see full details
  - Pagination (25/50/100 per page)
  - RTL text handling for Hebrew descriptions

#### Row Actions
- **View Details**: Modal/expander with all transaction fields
- **Edit Category**: Inline dropdown or modal
- **Manage Tags**: Modal to add/remove tags
- **View Installment Info**: For installment transactions

#### Bulk Actions
- Select multiple transactions (checkboxes)
- "Bulk Tag" button → opens tag selector
- "Bulk Categorize" button → opens category selector
- "Export Selected" button → CSV/JSON download

#### Summary Footer
- Total transactions shown
- Sum of amounts (income vs expense)
- Average transaction amount

---

### 4. Analytics & Reports 📈

**Purpose**: Visual analysis and insights

**Components**:

#### Time Range Selector (Global)
- Quick buttons: This Month, Last Month, Last 3 Months, Last 6 Months, This Year, Custom
- Custom date picker

#### Tab Layout:

**Tab 1: Spending Analysis**
- **Category Breakdown** (interactive donut chart)
  - Click category to see transactions
- **Top Merchants** (horizontal bar chart - top 15)
- **Spending by Day of Week** (bar chart)
- **Spending Heatmap** (calendar view - optional)

**Tab 2: Trends**
- **Monthly Spending Over Time** (line chart with area fill)
- **Category Trends** (stacked area chart)
- **Month-over-Month Comparison** (grouped bar chart)
- **Year-over-Year Comparison** (line chart overlay)

**Tab 3: Balance & Portfolio**
- **Portfolio Composition** (pie chart by account type)
- **Balance History** (line chart per account)
- **Profit/Loss Tracking** (for broker accounts)
- **Available vs Used Credit** (for credit cards)

**Tab 4: Tags Analysis**
- **Spending by Tag** (bar chart)
- **Tag Distribution** (treemap)
- **Tag Trends Over Time** (multi-line chart)
- **Untagged Transactions Summary**

**Tab 5: Comparisons**
- **Month vs Month** comparison selector
- **Account vs Account** comparison
- **Category Deep Dive** (select category, see detailed breakdown)

#### Export Options
- Download charts as PNG
- Export underlying data as CSV

---

### 5. Tags Management 🏷️

**Purpose**: Create, edit, and manage transaction tags

**Components**:

#### Tags Overview
- **Tag Cloud/List**: All tags with usage count and total amount
- Sort by: Name, Usage Count, Total Amount
- Search/filter tags

#### Tag Table
- Columns: Tag Name, Transaction Count, Total Amount, % of Total, Actions
- Actions: Rename, Delete, View Transactions

#### Create Tag
- Text input for new tag name
- "Create Tag" button

#### Bulk Tagging Tools
- **By Merchant Pattern**:
  - Pattern input (text)
  - Tag selector (multi-select)
  - Preview matches before applying
  - "Apply" button
- **By Category**:
  - Category selector
  - Tag selector
  - Preview matches before applying
  - "Apply" button
- **Migrate Categories to Tags**:
  - Dry run option
  - Preview migration
  - "Execute Migration" button

#### Tag Editor Modal
- Rename tag (with merge warning if new name exists)
- Delete tag (with confirmation)
- View all transactions with this tag

---

### 6. Rules Management 📋

**Purpose**: Manage auto-categorization rules

**Components**:

#### Rules Table
- Columns: Pattern, Match Type, Category, Tags to Add, Tags to Remove, Description, Actions
- Actions: Edit, Delete, Test

#### Add/Edit Rule Form
- **Pattern**: Text input
- **Match Type**: Dropdown (contains, exact, regex, starts_with, ends_with)
- **Category**: Dropdown (existing categories + custom input)
- **Tags to Add**: Multi-select tag picker
- **Tags to Remove**: Multi-select tag picker
- **Description**: Optional text input
- "Save Rule" / "Update Rule" button

#### Rule Testing
- Text input for test description
- Show which rules would match
- Show resulting category and tags

#### Apply Rules
- Scope selector: All transactions / Uncategorized only
- Dry run option (preview changes)
- Preview table showing affected transactions
- "Apply Rules" button
- Results summary

#### Import/Export
- Export rules to YAML
- Import rules from YAML
- Reset to defaults button

---

### 7. Accounts Management 💰

**Purpose**: View and manage financial accounts

**Components**:

#### Accounts Overview
- Cards grouped by type (Broker, Pension, Credit Card)
- Each card shows:
  - Institution logo/icon
  - Account name/number
  - Latest balance
  - Last synced
  - Active/Inactive status

#### Account Details (Click to expand or modal)
- Full account information
- Balance history chart (line chart)
- Transaction count
- Recent transactions (last 10)
- Profit/Loss (for brokers)

#### Account Table View (Alternative)
- Sortable/filterable table
- Columns: Type, Institution, Account Number, Name, Balance, Last Synced, Status

#### Account Actions
- Toggle active/inactive
- View balance history
- View all transactions

---

### 8. Settings ⚙️

**Purpose**: Application configuration

**Components**:

#### Credentials Management
- Show configured institutions (masked)
- Status indicator per institution (configured/not configured)
- "Edit Credentials" button per institution (opens modal)
- Note: Actual credential editing via CLI recommended for security

#### Multi-Account Configuration
- Show accounts per institution
- Add/remove accounts
- Set account labels

#### Database
- Database path display
- "Backup Database" button
- "Initialize/Reset Database" button (with confirmation)

#### Export Settings
- Default export format (CSV/JSON)
- Default date range

#### Display Settings
- Default rows per page
- Default chart colors theme
- Currency display format
- Date format preferences

#### About
- Version information
- Links to documentation
- Links to report issues

---

## Shared Components

### Sidebar (All Pages)
- Navigation menu (automatically handled by Streamlit multipage)
- Quick stats (optional):
  - Total balance
  - Pending transactions
  - Last sync time
- Dark/Light mode toggle (optional)

### Filter Components (Reusable)
```python
# filters.py
def date_range_filter(key_prefix: str) -> tuple[date, date]
def account_filter(key_prefix: str) -> list[int]
def institution_filter(key_prefix: str) -> list[str]
def status_filter(key_prefix: str) -> str
def category_filter(key_prefix: str) -> list[str]
def tag_filter(key_prefix: str) -> list[str]
```

### Chart Components (Reusable)
```python
# charts.py
def spending_donut(data: pd.DataFrame) -> go.Figure
def trend_line(data: pd.DataFrame) -> go.Figure
def category_bar(data: pd.DataFrame) -> go.Figure
def balance_history(data: pd.DataFrame) -> go.Figure
def calendar_heatmap(data: pd.DataFrame) -> go.Figure
```

### Table Components (Reusable)
```python
# tables.py
def transaction_table(transactions: list, show_actions: bool) -> None
def account_table(accounts: list) -> None
def sync_history_table(history: list) -> None
```

---

## Implementation Phases

### Phase 1: Foundation ✅ COMPLETED
1. ✅ Set up Streamlit project structure
2. ✅ Create app.py entry point with basic configuration
3. ✅ Implement service integration layer (session management)
4. ✅ Create shared components (sidebar, filters)
5. ✅ Implement basic Dashboard page

**Deliverables**:
- ✅ Working app skeleton
- ✅ Dashboard with summary cards and basic charts
- ✅ Service integration working

**Files Created**:
- `streamlit_app/app.py` - Main entry point with welcome page
- `streamlit_app/pages/1_📊_Dashboard.py` - Dashboard with metrics and charts
- `streamlit_app/pages/2_🔄_Sync.py` - Placeholder for Phase 2
- `streamlit_app/pages/3_💳_Transactions.py` - Placeholder for Phase 2
- `streamlit_app/pages/4_📈_Analytics.py` - Placeholder for Phase 3
- `streamlit_app/utils/session.py` - Session state management
- `streamlit_app/utils/formatters.py` - Display formatting utilities
- `streamlit_app/utils/rtl.py` - RTL/Hebrew text handling
- `streamlit_app/components/sidebar.py` - Shared sidebar components
- `streamlit_app/components/filters.py` - Reusable filter components
- `streamlit_app/components/charts.py` - Plotly chart components

**How to Run**:
```bash
# Install dependencies (if not already done)
pip install streamlit plotly pandas

# Run the app
streamlit run streamlit_app/app.py

# Or with custom port
streamlit run streamlit_app/app.py --server.port 8502
```

### Phase 2: Core Features
1. Transactions Browser page
   - Filter panel
   - Transaction table with pagination
   - Basic actions (view details)
2. Accounts page
   - Account listing
   - Balance display
3. Sync page (read-only first)
   - Sync history display
   - Status overview

**Deliverables**:
- Transaction browsing functional
- Account viewing functional
- Sync history visible

### Phase 3: Analytics ✅ COMPLETED
1. ✅ Analytics page with all tabs
   - ✅ Spending analysis charts (category breakdown, top merchants, day of week)
   - ✅ Trend charts (monthly, category trends, MoM, YoY)
   - ✅ Balance/portfolio charts (composition, history, account summary)
   - ✅ Tags analysis (spending by tag, treemap, trends, untagged summary)
   - ✅ Comparisons (month vs month, account vs account, category deep dive)
2. ✅ Interactive chart features
   - ✅ Time range selector (quick buttons + custom date picker)
   - ✅ Hover tooltips on all charts
   - ✅ Export options (CSV export for transactions and summary)
   - ✅ Interactive tabs with rich visualizations

**Deliverables**:
- ✅ Full analytics suite with 5 comprehensive tabs
- ✅ Interactive visualizations using Plotly
- ✅ Time-based filtering and comparisons
- ✅ Export functionality

**Files Created/Updated**:
- `streamlit_app/pages/4_📈_Analytics.py` - Complete analytics implementation with 5 tabs

### Phase 4: Management Features
1. Tags management page
   - CRUD operations
   - Bulk tagging
2. Rules management page
   - CRUD operations
   - Rule testing
   - Apply rules
3. Transaction editing
   - Edit category
   - Manage tags

**Deliverables**:
- Full tag management
- Full rules management
- Transaction editing

### Phase 5: Sync & Settings
1. Sync execution
   - Trigger sync from UI
   - Progress tracking
   - Error display
2. Settings page
   - Display settings
   - Database management
   - Export options

**Deliverables**:
- Working sync from UI
- Settings management

### Phase 6: Polish & Advanced Features
1. Performance optimization
   - Caching
   - Lazy loading
2. UI/UX improvements
   - Loading states
   - Error handling
   - Responsive design
3. Advanced features
   - Calendar heatmap
   - Custom dashboards
   - Saved filters/views

**Deliverables**:
- Production-ready application

---

## Technical Considerations

### Session State Management
```python
# utils/session.py
def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        'analytics_service': None,
        'tag_service': None,
        'current_filters': {},
        'selected_transactions': [],
        'sync_in_progress': False,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

def get_analytics_service() -> AnalyticsService:
    """Get or create AnalyticsService instance"""
    if st.session_state.analytics_service is None:
        st.session_state.analytics_service = AnalyticsService()
    return st.session_state.analytics_service
```

### Caching Strategy
```python
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_transaction_data(filters: dict) -> pd.DataFrame:
    """Fetch and cache transaction data"""
    pass

@st.cache_data(ttl=60)  # Cache for 1 minute
def get_dashboard_stats() -> dict:
    """Fetch and cache dashboard statistics"""
    pass

# Clear cache when sync completes
def on_sync_complete():
    st.cache_data.clear()
```

### Error Handling
```python
def safe_service_call(func, *args, **kwargs):
    """Wrapper for service calls with error handling"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None
```

### RTL Text Handling
```python
# utils/rtl.py
import unicodedata

def fix_rtl(text: str) -> str:
    """Fix RTL text display for Hebrew"""
    if any('\u0590' <= c <= '\u05FF' for c in text):
        return f'\u200F{text}\u200F'
    return text

def format_description(desc: str) -> str:
    """Format transaction description with RTL support"""
    return fix_rtl(desc) if desc else ''
```

### Running Sync in Background
```python
import subprocess
import threading

def run_sync_background(institution: str, options: dict):
    """Run sync in background thread"""
    st.session_state.sync_in_progress = True
    st.session_state.sync_output = []

    cmd = ['fin-cli', 'sync', institution]
    if options.get('headless'):
        cmd.append('--headless')
    if options.get('months_back'):
        cmd.extend(['--months-back', str(options['months_back'])])

    def run():
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        for line in process.stdout:
            st.session_state.sync_output.append(line)
        process.wait()
        st.session_state.sync_in_progress = False
        st.cache_data.clear()

    thread = threading.Thread(target=run)
    thread.start()
```

---

## Dependencies

Add to `requirements.txt`:
```
streamlit>=1.28.0
plotly>=5.17.0
pandas>=2.0.0
streamlit-option-menu>=0.3.6
```

---

## Running the App

### Development
```bash
# From project root
streamlit run streamlit_app/app.py

# With custom port
streamlit run streamlit_app/app.py --server.port 8502
```

### Production
```bash
# Using streamlit config
streamlit run streamlit_app/app.py \
    --server.headless true \
    --server.port 8501 \
    --browser.gatherUsageStats false
```

### Add to CLI (optional)
```bash
fin-cli ui  # Launches Streamlit app
```

---

## Future Enhancements

1. **Mobile Responsive Design**: Optimize for mobile viewing
2. **Real-time Updates**: WebSocket for live sync status
3. **Custom Dashboards**: User-configurable dashboard widgets
4. **Budget Tracking**: Set and track budgets per category
5. **Alerts & Notifications**: Unusual spending alerts
6. **Multi-User Support**: Authentication and user profiles
7. **API Backend**: REST API for external integrations
8. **Data Export Scheduling**: Automated exports
9. **OCR Receipt Scanning**: Match receipts to transactions
10. **AI-Powered Categorization**: ML-based auto-categorization suggestions