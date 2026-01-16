# UI/UX Improvements Plan

**Status**: In Progress
**Started**: 2026-01-16
**Goal**: Improve Streamlit UI to follow financial app best practices for trust, security, and usability

---

## Executive Summary

This plan addresses UI/UX improvements identified during review of the Streamlit application. Changes focus on:
- **Security & Privacy**: Protecting sensitive financial data
- **Clarity**: Making financial information easier to understand
- **Trust**: Building confidence through transparency
- **Efficiency**: Reducing cognitive load and improving workflows

All improvements are based on industry best practices from successful financial applications (Mint, YNAB, Personal Capital, Israeli banks).

---

## Progress Overview

- [x] **Critical** (Security & Trust): 2/3 items ✅ (67% complete)
- [ ] **High Priority** (Data Display): 0/6 items
- [ ] **Medium Priority** (UX Polish): 0/5 items
- [ ] **Nice to Have** (Advanced Features): 0/3 items

**Total Progress**: 2/17 items (12%)

---

## Critical Priority - Security & Privacy

### 1. Sensitive Data Masking ✅
**Status**: [x] **COMPLETED** (2026-01-16)
**Impact**: High - Protects user privacy
**Effort**: Low (2-3 hours)

**Problem**: Account numbers and sensitive identifiers displayed in full.

**Solution**: Create masking utility and apply across all pages.

**Implementation**: ✅ Complete
- Added `format_account_number()`, `mask_card_number()`, `format_balance()` to formatters.py
- Added privacy settings to session state (`mask_account_numbers`, `mask_balances`)
- Created Privacy & Security Settings section in Settings page with toggles
- Applied masking to Accounts page (card view, table view, details view)

**Files Updated**:
- [x] `streamlit_app/utils/formatters.py` - Added masking functions ✅
- [x] `streamlit_app/utils/session.py` - Added privacy settings to session state ✅
- [x] `streamlit_app/pages/7_💰_Accounts.py` - Masked account numbers in all views ✅
- [ ] `streamlit_app/pages/3_💳_Transactions.py` - Mask in transaction details (optional)
- [x] `streamlit_app/pages/8_⚙️_Settings.py` - Added Privacy & Security Settings section ✅

**Acceptance Criteria**: ✅ All Met
- [x] Account numbers show as "••••1234" by default
- [x] Card number masking function ready (mask_card_number)
- [x] Settings has toggle to show/hide all balances
- [x] Toggles persist in session state

---

### 2. Sync Page - Security Transparency ✅
**Status**: [x] **COMPLETED** (2026-01-16)
**Impact**: High - Builds user trust
**Effort**: Low (1-2 hours)

**Problem**: Users don't see security measures during sync, may feel unsafe.

**Solution**: Add security indicators and transparent messaging.

**Implementation**: ✅ Complete
- Added prominent security notice at top of Sync page
- Notice explains: encrypted credentials, read-only access, local storage, secure connections
- Page already shows detailed sync output in real-time (existing expander implementation)

**Files Updated**:
- [x] `streamlit_app/pages/2_🔄_Sync.py` - Added security messaging banner ✅

**Acceptance Criteria**: ✅ All Met
- [x] Security notice visible on Sync page (info banner with 4 key points)
- [x] Sync process shows detailed steps (existing output expander)
- [x] Users understand data privacy measures (clear messaging)

---

### 3. Empty States - Onboarding
**Status**: [ ] Not Started
**Impact**: High - First impression for new users
**Effort**: Medium (3-4 hours)

**Problem**: Empty database shows generic warning, not helpful guidance.

**Solution**: Create welcoming empty states with clear next steps.

**Implementation**:
```python
# File: streamlit_app/components/empty_states.py

import streamlit as st

def empty_transactions_state():
    """Welcoming empty state for transactions page"""
    st.markdown("""
    <div style='text-align: center; padding: 3rem 0;'>
        <h2>📭 No Transactions Yet</h2>
        <p style='font-size: 1.1rem; color: #666; margin: 1.5rem 0;'>
            Let's get your financial data synced so you can see your transactions here.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        **Quick Start Guide:**
        1. Configure your credentials: `fin-cli config setup`
        2. Click the button below to sync your accounts
        3. Come back here to see your transactions
        """)

        if st.button("🔄 Start Syncing", type="primary", use_container_width=True):
            st.switch_page("pages/2_🔄_Sync.py")

        st.caption("⏱️ First sync usually takes 2-3 minutes")

def empty_search_state(filter_count: int):
    """Empty state when filters return no results"""
    st.info(f"""
    🔍 No transactions match your {filter_count} active filters.

    **Try:**
    - Expanding your date range
    - Removing some filters
    - Checking for typos in search terms
    """)

    if st.button("Clear All Filters"):
        # Clear filter logic
        st.rerun()
```

**Files to Update**:
- [ ] `streamlit_app/components/empty_states.py` - Create component
- [ ] `streamlit_app/pages/3_💳_Transactions.py` - Use empty states
- [ ] `streamlit_app/pages/1_📊_Dashboard.py` - Use empty states
- [ ] `streamlit_app/pages/4_📈_Analytics.py` - Use empty states
- [ ] `streamlit_app/pages/7_💰_Accounts.py` - Use empty states

**Acceptance Criteria**:
- All pages show helpful empty states (not just warnings)
- Empty states include actionable next steps
- "No results" states suggest how to adjust filters

---

## High Priority - Data Display & Clarity

### 4. Amount Formatting - Visual Clarity
**Status**: [ ] Not Started
**Impact**: High - Core financial data display
**Effort**: Medium (2-3 hours)

**Problem**: Inconsistent amount formatting, hard to distinguish income from expenses.

**Solution**: Standardize with proper typography and color coding.

**Implementation**:
```python
# File: streamlit_app/utils/formatters.py

def format_transaction_amount(
    amount: float,
    show_sign: bool = True,
    colored: bool = True
) -> str:
    """
    Format transaction amount with proper sign and optional color.

    Best practices:
    - Use minus sign (−) not hyphen (-) for negative numbers
    - Always show currency symbol (₪)
    - Color code: red for expenses, green for income, gray for zero
    """
    abs_amount = abs(amount)
    formatted = f"₪{abs_amount:,.2f}"

    if amount == 0:
        return formatted

    # Determine sign and color
    if amount < 0:  # Expense
        sign = "−" if show_sign else ""  # Proper minus sign (U+2212)
        color = "#c62828" if colored else None
    else:  # Income
        sign = "+" if show_sign else ""
        color = "#00897b" if colored else None

    final_text = f"{sign}{formatted}"

    if colored and color:
        return f"<span style='color:{color}; font-weight:500; font-family:monospace'>{final_text}</span>"
    else:
        return final_text

# Add monospace styling for amounts (easier to scan)
AMOUNT_STYLE = """
<style>
.financial-amount {
    font-family: 'SF Mono', 'Roboto Mono', 'Consolas', monospace;
    font-size: 1.1rem;
    font-weight: 500;
    letter-spacing: -0.01em;
}
</style>
"""
```

**Files to Update**:
- [ ] `streamlit_app/utils/formatters.py` - Update `format_currency()` and add `format_transaction_amount()`
- [ ] `streamlit_app/pages/3_💳_Transactions.py` - Use new formatting in table
- [ ] `streamlit_app/pages/1_📊_Dashboard.py` - Color-code metrics
- [ ] `streamlit_app/components/charts.py` - Consistent formatting in chart labels

**Acceptance Criteria**:
- Expenses show in red with proper minus sign (−)
- Income shows in green with plus sign (+)
- All amounts use monospace font
- Consistent formatting across all pages

---

### 5. Transaction Table - Readability
**Status**: [ ] Not Started
**Impact**: High - Most-used feature
**Effort**: Medium (3-4 hours)

**Problem**: Table hard to scan, no visual hierarchy, too many columns.

**Solution**: Add zebra striping, hover effects, column customization.

**Implementation**:
```python
# File: streamlit_app/pages/3_💳_Transactions.py

# Add to page CSS
st.markdown("""
<style>
/* Zebra striping for better readability */
.dataframe tbody tr:nth-child(even) {
    background-color: #f8f9fa;
}

/* Hover effect */
.dataframe tbody tr:hover {
    background-color: #e3f2fd;
    cursor: pointer;
    transition: background-color 0.2s ease;
}

/* Column headers */
.dataframe thead th {
    background-color: #1976d2;
    color: white;
    font-weight: 600;
    padding: 12px 8px;
    text-align: left;
}

/* Amount column - right aligned */
.dataframe td:nth-child(3) {
    text-align: right;
    font-family: monospace;
}

/* Compact table */
.dataframe {
    font-size: 14px;
    line-height: 1.4;
}
</style>
""", unsafe_allow_html=True)

# Add column selector
with st.expander("⚙️ Customize Table View"):
    all_columns = ["Date", "Description", "Amount", "Category", "Status", "Tags", "Account", "Institution"]
    default_columns = ["Date", "Description", "Amount", "Category", "Status"]

    selected_columns = st.multiselect(
        "Select columns to display",
        options=all_columns,
        default=default_columns,
        key="visible_columns"
    )

    # Save to session state for persistence
    st.session_state.table_columns = selected_columns
```

**Files to Update**:
- [ ] `streamlit_app/pages/3_💳_Transactions.py` - Add CSS and column selector
- [ ] Add compact/expanded view toggle
- [ ] Make table sortable by all columns
- [ ] Add row numbers for reference

**Acceptance Criteria**:
- Zebra striping visible on all tables
- Hover effect on transaction rows
- Column customization works and persists
- Table is easier to scan visually

---

### 6. Dashboard - Cognitive Load Reduction
**Status**: [ ] Not Started
**Impact**: High - First page users see
**Effort**: Medium (4-5 hours)

**Problem**: Too much information presented at once, no clear hierarchy.

**Solution**: Progressive disclosure with tabs, hero metrics, and contextual insights.

**Implementation**:
```python
# File: streamlit_app/pages/1_📊_Dashboard.py

# Redesign dashboard with clear hierarchy

# 1. Hero Metrics (Most Important)
st.markdown("## 💰 Your Financial Snapshot")

col1, col2 = st.columns(2)
with col1:
    st.metric(
        label="Net Worth",
        value=format_currency(total_balance),
        delta=f"{balance_change_pct:+.1f}% this month",
        help="Total value of all accounts"
    )

with col2:
    st.metric(
        label="This Month's Spending",
        value=format_currency(abs(monthly_spending)),
        delta=f"{spending_vs_avg:+.0f}% vs average",
        delta_color="inverse",  # Red for higher spending
        help="Total expenses this month"
    )

# 2. Contextual Insight (AI-like summary)
insight = generate_spending_insight(stats)
if insight:
    st.info(f"💡 **Insight:** {insight}")

st.markdown("---")

# 3. Progressive Disclosure - Tabs
tab1, tab2, tab3 = st.tabs(["📊 Overview", "📈 Trends", "🎯 Categories"])

with tab1:
    # Quick overview - 2-3 charts max
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(spending_by_category_chart, use_container_width=True)
    with col2:
        st.plotly_chart(recent_transactions_timeline, use_container_width=True)

with tab2:
    # Detailed trends
    st.plotly_chart(monthly_trend_chart, use_container_width=True)
    st.plotly_chart(spending_by_day_chart, use_container_width=True)

with tab3:
    # Category breakdown
    # ... detailed category analysis
```

**Helper Function**:
```python
def generate_spending_insight(stats: dict) -> str:
    """Generate human-readable spending insight"""
    monthly_avg = stats['monthly_avg_spending']
    current_month = stats['monthly_spending']

    if not monthly_avg or monthly_avg == 0:
        return None

    diff_pct = ((current_month - monthly_avg) / monthly_avg) * 100

    if abs(diff_pct) < 5:
        return "Your spending this month is on track with your average"
    elif diff_pct > 20:
        top_category = stats.get('top_category_this_month', 'various categories')
        return f"You've spent {diff_pct:.0f}% more than usual, mostly on {top_category}"
    elif diff_pct < -20:
        return f"Great job! You've spent {abs(diff_pct):.0f}% less than your monthly average"
    else:
        direction = "more" if diff_pct > 0 else "less"
        return f"Spending is {abs(diff_pct):.0f}% {direction} than your monthly average"
```

**Files to Update**:
- [ ] `streamlit_app/pages/1_📊_Dashboard.py` - Redesign with tabs and insights
- [ ] `streamlit_app/utils/insights.py` - Create insight generation utilities
- [ ] Reduce number of visible metrics from 4 to 2 hero metrics
- [ ] Move detailed charts to tabs

**Acceptance Criteria**:
- Dashboard loads with 2 hero metrics prominently displayed
- Contextual insight appears below metrics
- Tabs organize additional information
- Page feels less overwhelming

---

### 7. Date Range Selector - Financial Context
**Status**: [ ] Not Started
**Impact**: Medium - Used on multiple pages
**Effort**: Low (2 hours)

**Problem**: Users must manually pick dates, unclear what makes sense.

**Solution**: Add quick range buttons with financial context.

**Implementation**:
```python
# File: streamlit_app/components/filters.py

def date_range_filter_with_presets(key_prefix: str = "") -> tuple[date, date]:
    """Date range filter with quick preset buttons"""

    st.markdown("**Quick Ranges:**")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        if st.button("📅 This Month", key=f"{key_prefix}_this_month"):
            st.session_state[f"{key_prefix}_start"] = date.today().replace(day=1)
            st.session_state[f"{key_prefix}_end"] = date.today()
            st.rerun()

    with col2:
        if st.button("📅 Last Month", key=f"{key_prefix}_last_month"):
            last_month = date.today().replace(day=1) - timedelta(days=1)
            st.session_state[f"{key_prefix}_start"] = last_month.replace(day=1)
            st.session_state[f"{key_prefix}_end"] = last_month
            st.rerun()

    with col3:
        if st.button("📅 Last 3 Months", key=f"{key_prefix}_3months"):
            st.session_state[f"{key_prefix}_start"] = date.today() - timedelta(days=90)
            st.session_state[f"{key_prefix}_end"] = date.today()
            st.rerun()

    with col4:
        if st.button("📅 This Year", key=f"{key_prefix}_this_year"):
            st.session_state[f"{key_prefix}_start"] = date.today().replace(month=1, day=1)
            st.session_state[f"{key_prefix}_end"] = date.today()
            st.rerun()

    with col5:
        if st.button("📅 Last Year", key=f"{key_prefix}_last_year"):
            last_year = date.today().year - 1
            st.session_state[f"{key_prefix}_start"] = date(last_year, 1, 1)
            st.session_state[f"{key_prefix}_end"] = date(last_year, 12, 31)
            st.rerun()

    # Manual date pickers
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "From",
            value=st.session_state.get(f"{key_prefix}_start", date.today() - timedelta(days=90)),
            key=f"{key_prefix}_date_start"
        )
    with col2:
        end_date = st.date_input(
            "To",
            value=st.session_state.get(f"{key_prefix}_end", date.today()),
            key=f"{key_prefix}_date_end"
        )

    return start_date, end_date
```

**Files to Update**:
- [ ] `streamlit_app/components/filters.py` - Add preset function
- [ ] `streamlit_app/pages/3_💳_Transactions.py` - Replace date picker
- [ ] `streamlit_app/pages/4_📈_Analytics.py` - Replace date picker
- [ ] Show data coverage info: "You have data from Jan 2024 to Jan 2026"

**Acceptance Criteria**:
- Quick range buttons work and update filters
- Selected range persists when navigating tabs
- Data coverage info visible

---

### 8. Category & Tag Display
**Status**: [ ] Not Started
**Impact**: Medium - Visual clarity
**Effort**: Low (1-2 hours)

**Problem**: Categories and tags display as plain text, hard to distinguish.

**Solution**: Add badge/pill styling with colors.

**Implementation**:
```python
# File: streamlit_app/utils/formatters.py

def format_category_badge(category: str, clickable: bool = False) -> str:
    """Format category as colored badge"""
    if not category:
        return "<span style='color:#999'>Uncategorized</span>"

    # Color scheme for common categories
    category_colors = {
        'Food & Dining': '#ff6b6b',
        'Transportation': '#4ecdc4',
        'Shopping': '#45b7d1',
        'Entertainment': '#f9ca24',
        'Bills & Utilities': '#6c5ce7',
        'Healthcare': '#fd79a8',
        'Groceries': '#00b894',
    }

    color = category_colors.get(category, '#95a5a6')

    style = f"""
        display: inline-block;
        background-color: {color}20;
        color: {color};
        border: 1px solid {color}40;
        border-radius: 12px;
        padding: 2px 10px;
        font-size: 0.85rem;
        font-weight: 500;
        margin: 2px;
    """

    return f"<span style='{style}'>{category}</span>"

def format_tags(tags: list[str]) -> str:
    """Format multiple tags as badges"""
    if not tags:
        return ""

    badges = []
    for tag in tags:
        style = """
            display: inline-block;
            background-color: #e3f2fd;
            color: #1976d2;
            border-radius: 10px;
            padding: 2px 8px;
            font-size: 0.8rem;
            margin: 2px;
        """
        badges.append(f"<span style='{style}'>🏷️ {tag}</span>")

    return " ".join(badges)
```

**Files to Update**:
- [ ] `streamlit_app/utils/formatters.py` - Add badge functions
- [ ] `streamlit_app/pages/3_💳_Transactions.py` - Use badges in table
- [ ] `streamlit_app/pages/5_🏷️_Tags.py` - Use badges in tag list

**Acceptance Criteria**:
- Categories display as colored pills
- Tags display as blue badges with emoji
- Badges are visually distinct from regular text

---

### 9. Status Indicators
**Status**: [ ] Not Started
**Impact**: Medium - Transaction clarity
**Effort**: Low (1 hour)

**Problem**: Transaction status (Pending/Completed) not visually clear.

**Solution**: Add colored status badges with icons.

**Implementation**:
```python
# File: streamlit_app/utils/formatters.py

def format_status(status: str) -> str:
    """Format transaction status with icon and color"""
    status_config = {
        'completed': {
            'icon': '✅',
            'color': '#00897b',
            'bg': '#e0f2f1',
            'label': 'Completed'
        },
        'pending': {
            'icon': '⏳',
            'color': '#f57c00',
            'bg': '#fff3e0',
            'label': 'Pending'
        },
        'failed': {
            'icon': '❌',
            'color': '#c62828',
            'bg': '#ffebee',
            'label': 'Failed'
        }
    }

    config = status_config.get(status.lower(), {
        'icon': '❓',
        'color': '#666',
        'bg': '#f5f5f5',
        'label': status
    })

    style = f"""
        display: inline-flex;
        align-items: center;
        background-color: {config['bg']};
        color: {config['color']};
        border-radius: 12px;
        padding: 4px 10px;
        font-size: 0.85rem;
        font-weight: 500;
    """

    return f"<span style='{style}'>{config['icon']} {config['label']}</span>"
```

**Files to Update**:
- [ ] `streamlit_app/utils/formatters.py` - Add status formatter
- [ ] `streamlit_app/pages/3_💳_Transactions.py` - Use in table
- [ ] `streamlit_app/pages/1_📊_Dashboard.py` - Use in recent activity

**Acceptance Criteria**:
- Completed transactions show green badge with ✅
- Pending transactions show amber badge with ⏳
- Status is immediately visually clear

---

## Medium Priority - UX Polish

### 10. Success Feedback & Toasts
**Status**: [ ] Not Started
**Impact**: Medium - User confidence
**Effort**: Low (1-2 hours)

**Problem**: Actions succeed silently, users unsure if operation worked.

**Solution**: Add toast notifications and success animations.

**Implementation**:
```python
# Use Streamlit's built-in st.toast()

# After transaction edit:
st.toast("✅ Transaction updated successfully", icon="✅")

# After tag added:
st.toast(f"Added tag '{tag_name}'", icon="🏷️")

# After successful sync:
st.toast(f"✅ Synced {count} transactions from {institution}", icon="✅")
st.balloons()  # Celebration for major operations

# After rule applied:
st.toast(f"Applied rule to {count} transactions", icon="📋")
```

**Files to Update**:
- [ ] `streamlit_app/pages/3_💳_Transactions.py` - Add toasts after edits
- [ ] `streamlit_app/pages/5_🏷️_Tags.py` - Add toasts after tag operations
- [ ] `streamlit_app/pages/6_📋_Rules.py` - Add toasts after rule operations
- [ ] `streamlit_app/pages/2_🔄_Sync.py` - Add celebration after sync

**Acceptance Criteria**:
- Every user action gets feedback (toast or success message)
- Toasts auto-dismiss after 3 seconds
- Major operations trigger balloons/confetti

---

### 11. Search Improvements
**Status**: [ ] Not Started
**Impact**: Medium - Efficiency
**Effort**: Medium (2-3 hours)

**Problem**: Search only filters descriptions, no fuzzy matching or highlights.

**Solution**: Add search highlighting and "no results" guidance.

**Implementation**:
```python
# File: streamlit_app/pages/3_💳_Transactions.py

# Add search with highlighting
search_term = st.text_input(
    "🔍 Search transactions",
    placeholder="Merchant name, description, amount...",
    key="search_input"
)

if search_term:
    # Highlight matches in results
    def highlight_match(text: str, term: str) -> str:
        if not term or not text:
            return text
        # Case-insensitive highlight
        import re
        pattern = re.compile(f"({re.escape(term)})", re.IGNORECASE)
        return pattern.sub(r"<mark>\1</mark>", text)

    # Apply to description column
    df['description'] = df['description'].apply(
        lambda x: highlight_match(x, search_term)
    )

    # Show search stats
    st.caption(f"Found {len(df)} transactions matching '{search_term}'")

    if len(df) == 0:
        st.info(f"""
        🔍 No transactions found for "{search_term}"

        **Try:**
        - Checking spelling
        - Using fewer keywords
        - Searching by amount or date instead
        """)

        if st.button("Clear Search"):
            st.session_state.search_input = ""
            st.rerun()
```

**Files to Update**:
- [ ] `streamlit_app/pages/3_💳_Transactions.py` - Add search highlighting
- [ ] Show "X results found" counter
- [ ] Add "No results" state with suggestions
- [ ] Support searching amounts (e.g., "100" finds ₪100 transactions)

**Acceptance Criteria**:
- Search highlights matched terms in yellow
- Results counter shows number of matches
- Helpful message when no results
- Can search by amount values

---

### 12. Bulk Actions UX
**Status**: [ ] Not Started
**Impact**: Medium - Power user efficiency
**Effort**: Medium (3 hours)

**Problem**: Bulk operations lack preview and confirmation.

**Solution**: Add preview before apply, show counts, add undo.

**Implementation**:
```python
# File: streamlit_app/pages/5_🏷️_Tags.py

# Bulk tagging with preview
st.subheader("🏷️ Bulk Tag by Pattern")

pattern = st.text_input("Search pattern", placeholder="e.g., 'Starbucks'")
tags_to_add = st.multiselect("Tags to add", options=all_tags)

if pattern and st.button("Preview Matches"):
    # Find matching transactions
    matches = find_transactions_matching(pattern)

    st.info(f"📊 Found {len(matches)} matching transactions")

    # Show preview table
    st.dataframe(matches[['date', 'description', 'amount']].head(10))

    if len(matches) > 10:
        st.caption(f"Showing first 10 of {len(matches)} matches")

    # Confirmation
    st.warning(f"⚠️ This will add {len(tags_to_add)} tag(s) to {len(matches)} transactions")

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("✅ Apply Tags", type="primary"):
            apply_tags_bulk(matches, tags_to_add)
            st.toast(f"✅ Tagged {len(matches)} transactions", icon="✅")
            st.rerun()
    with col2:
        if st.button("❌ Cancel"):
            st.rerun()
```

**Files to Update**:
- [ ] `streamlit_app/pages/5_🏷️_Tags.py` - Add preview to bulk operations
- [ ] `streamlit_app/pages/6_📋_Rules.py` - Add preview before applying rules
- [ ] Show affected count before confirming
- [ ] Add "Undo" for recent bulk operations (session-based)

**Acceptance Criteria**:
- Bulk operations show preview of affected items
- Count is always visible before confirmation
- Two-step confirmation for destructive actions
- Success message shows number of items affected

---

### 13. Loading State Improvements
**Status**: [ ] Not Started
**Impact**: Medium - Perceived performance
**Effort**: Low (1-2 hours)

**Problem**: Spinners don't explain what's happening, no progress indication.

**Solution**: Add descriptive loading messages and skeleton screens.

**Implementation**:
```python
# File: streamlit_app/utils/errors.py

# Enhance existing safe_call_with_spinner
def safe_call_with_progress(
    func,
    spinner_text: str = "Loading...",
    steps: list[str] = None,  # NEW: Show multi-step progress
    **kwargs
):
    """Call function with multi-step progress indicators"""

    if steps:
        # Multi-step progress
        with st.status(spinner_text, expanded=True) as status:
            for step_text in steps:
                st.write(f"⏳ {step_text}")
                time.sleep(0.3)  # Brief pause for visibility

            result = func(**kwargs)
            status.update(label="✅ Complete", state="complete")
            return result
    else:
        # Simple spinner
        with st.spinner(spinner_text):
            return func(**kwargs)

# Usage:
data = safe_call_with_progress(
    fetch_large_dataset,
    spinner_text="Loading transaction data...",
    steps=[
        "Connecting to database...",
        "Applying filters...",
        "Aggregating results...",
        "Formatting data..."
    ]
)
```

**Files to Update**:
- [ ] `streamlit_app/utils/errors.py` - Add multi-step progress
- [ ] `streamlit_app/pages/2_🔄_Sync.py` - Use detailed progress for sync
- [ ] `streamlit_app/pages/4_📈_Analytics.py` - Show progress for heavy charts
- [ ] Add skeleton screens (placeholder UI) while loading

**Acceptance Criteria**:
- Long operations show step-by-step progress
- Users never see blank screen while loading
- Progress text is descriptive ("Fetching transactions from CAL..." not "Loading...")

---

### 14. Responsive Layout Check
**Status**: [ ] Not Started
**Impact**: Low - Mobile usage
**Effort**: Medium (3-4 hours)

**Problem**: Layout not tested on smaller screens (tablets, mobile).

**Solution**: Test and fix layout at common breakpoints.

**Implementation**:
```python
# File: streamlit_app/utils/responsive.py

import streamlit as st

def responsive_columns(mobile: int = 1, tablet: int = 2, desktop: int = 4):
    """
    Create responsive columns based on viewport.
    Note: Streamlit doesn't have native responsive, so use best guess.
    """
    # Streamlit limitation: Can't detect screen size
    # Workaround: Use more conservative column counts

    # For now, use tablet layout (2 columns) as safe default
    # Desktop users get more space, mobile stacks naturally
    return st.columns(tablet)

# Add mobile-friendly CSS
RESPONSIVE_CSS = """
<style>
/* Stack columns on small screens */
@media (max-width: 768px) {
    .element-container {
        width: 100% !important;
    }

    [data-testid="column"] {
        width: 100% !important;
        margin-bottom: 1rem;
    }
}

/* Reduce padding on mobile */
@media (max-width: 768px) {
    .main .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
    }
}
</style>
"""
```

**Testing Checklist**:
- [ ] Dashboard at 768px width (tablet)
- [ ] Dashboard at 375px width (mobile)
- [ ] Transactions page at 768px
- [ ] Charts render correctly on mobile
- [ ] Filter panel accessible on mobile
- [ ] Buttons don't overflow

**Acceptance Criteria**:
- All pages functional at 768px width
- No horizontal scrolling on mobile
- Key features accessible on tablet/mobile

---

## Nice to Have - Advanced Features

### 15. Keyboard Shortcuts
**Status**: [ ] Not Started
**Impact**: Low - Power users
**Effort**: Medium (2-3 hours)

**Problem**: Mouse-only navigation is slow for frequent users.

**Solution**: Add keyboard shortcuts for common actions.

**Implementation**:
```python
# File: streamlit_app/utils/shortcuts.py

import streamlit as st
from streamlit.components.v1 import html

def register_keyboard_shortcuts():
    """Register global keyboard shortcuts"""

    shortcuts_js = """
    <script>
    document.addEventListener('keydown', function(e) {
        // Only trigger if not in input field
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }

        // Alt+1-8: Navigate to pages
        if (e.altKey && e.key >= '1' && e.key <= '8') {
            const pageMap = {
                '1': 'Dashboard',
                '2': 'Sync',
                '3': 'Transactions',
                '4': 'Analytics',
                '5': 'Tags',
                '6': 'Rules',
                '7': 'Accounts',
                '8': 'Settings'
            };
            console.log('Navigate to:', pageMap[e.key]);
            // Streamlit page switching requires custom implementation
        }

        // Ctrl+F: Focus search
        if (e.ctrlKey && e.key === 'f') {
            e.preventDefault();
            const searchInput = document.querySelector('input[placeholder*="Search"]');
            if (searchInput) searchInput.focus();
        }

        // ?: Show shortcuts help
        if (e.key === '?') {
            window.parent.postMessage({type: 'showShortcuts'}, '*');
        }
    });
    </script>
    """

    html(shortcuts_js, height=0)

def show_shortcuts_help():
    """Display keyboard shortcuts reference"""
    with st.expander("⌨️ Keyboard Shortcuts"):
        st.markdown("""
        | Shortcut | Action |
        |----------|--------|
        | `Alt + 1-8` | Navigate to page (1=Dashboard, 2=Sync, etc.) |
        | `Ctrl + F` | Focus search box |
        | `Ctrl + S` | Trigger sync (on Sync page) |
        | `?` | Show this help |
        """)
```

**Files to Update**:
- [ ] `streamlit_app/utils/shortcuts.py` - Create shortcuts system
- [ ] `streamlit_app/app.py` - Register shortcuts globally
- [ ] Add shortcuts help to Settings page

**Acceptance Criteria**:
- Alt+1-8 navigates to pages
- Ctrl+F focuses search
- ? shows shortcuts help

---

### 16. Export Enhancements
**Status**: [ ] Not Started
**Impact**: Low - Data portability
**Effort**: Low (1-2 hours)

**Problem**: CSV export lacks formatting, no Excel option.

**Solution**: Add formatted Excel export with multiple sheets.

**Implementation**:
```python
# File: streamlit_app/utils/export.py

import pandas as pd
from io import BytesIO

def export_to_excel(
    transactions: pd.DataFrame,
    summary_stats: dict = None,
    filename: str = "transactions"
) -> BytesIO:
    """Export data to formatted Excel file with multiple sheets"""

    output = BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Sheet 1: Transactions
        transactions.to_excel(writer, sheet_name='Transactions', index=False)

        # Sheet 2: Summary (if provided)
        if summary_stats:
            summary_df = pd.DataFrame([summary_stats])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)

        # Sheet 3: Charts data (category breakdown)
        if 'category' in transactions.columns:
            category_summary = transactions.groupby('category')['amount'].agg(['sum', 'count'])
            category_summary.to_excel(writer, sheet_name='By Category')

        # Format the workbook
        workbook = writer.book
        worksheet = writer.sheets['Transactions']

        # Add header formatting
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#1976d2',
            'font_color': 'white',
            'border': 1
        })

        # Apply to header row
        for col_num, value in enumerate(transactions.columns.values):
            worksheet.write(0, col_num, value, header_format)

    output.seek(0)
    return output

# Usage:
excel_file = export_to_excel(df_transactions, summary_stats=stats)
st.download_button(
    label="📥 Download Excel",
    data=excel_file,
    file_name=f"transactions_{datetime.now().strftime('%Y%m%d')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
```

**Files to Update**:
- [ ] `streamlit_app/utils/export.py` - Add Excel export
- [ ] `streamlit_app/pages/3_💳_Transactions.py` - Add Excel download option
- [ ] `streamlit_app/pages/4_📈_Analytics.py` - Export chart data

**Acceptance Criteria**:
- Excel export includes multiple sheets
- Headers are formatted (bold, colored)
- Amounts formatted as currency
- Dates formatted correctly

---

### 17. Visual Theme Consistency
**Status**: [ ] Not Started
**Impact**: Low - Polish
**Effort**: Low (1-2 hours)

**Problem**: Mixed visual styles (buttons, cards, spacing).

**Solution**: Standardize spacing, borders, shadows.

**Implementation**:
```python
# File: streamlit_app/app.py

# Add comprehensive CSS theme
THEME_CSS = """
<style>
/* ===== Design System Variables ===== */
:root {
    --primary-color: #0066cc;
    --success-color: #00a86b;
    --danger-color: #d32f2f;
    --warning-color: #f57c00;
    --neutral-color: #546e7a;

    --border-radius: 8px;
    --shadow-sm: 0 2px 4px rgba(0,0,0,0.1);
    --shadow-md: 0 4px 8px rgba(0,0,0,0.12);
    --spacing-sm: 0.5rem;
    --spacing-md: 1rem;
    --spacing-lg: 1.5rem;
}

/* ===== Cards ===== */
.element-container > div {
    border-radius: var(--border-radius);
}

[data-testid="stMetric"] {
    background-color: white;
    padding: var(--spacing-md);
    border-radius: var(--border-radius);
    box-shadow: var(--shadow-sm);
}

/* ===== Buttons ===== */
.stButton > button {
    border-radius: var(--border-radius);
    font-weight: 500;
    transition: all 0.2s ease;
}

.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: var(--shadow-md);
}

/* ===== Consistent Spacing ===== */
.main .block-container {
    padding-top: var(--spacing-lg);
    padding-bottom: var(--spacing-lg);
}

/* ===== Chart Container ===== */
.plotly-graph-div {
    border-radius: var(--border-radius);
    box-shadow: var(--shadow-sm);
    padding: var(--spacing-sm);
    background-color: white;
}
</style>
"""
```

**Files to Update**:
- [ ] `streamlit_app/app.py` - Add comprehensive theme CSS
- [ ] Audit all pages for consistent spacing
- [ ] Ensure all buttons use same styling
- [ ] Standardize card shadows

**Acceptance Criteria**:
- All buttons have same border-radius
- Consistent spacing between sections
- Uniform shadows on cards and charts
- Visual harmony across all pages

---

## Testing Checklist

Before marking improvements as complete, verify:

### Functional Testing
- [ ] All new features work on first try
- [ ] No console errors in browser developer tools
- [ ] Database operations don't cause errors
- [ ] Session state persists correctly

### Visual Testing
- [ ] Test on Chrome, Firefox, Safari
- [ ] Test at 1920px, 1440px, 768px widths
- [ ] Colors meet WCAG contrast requirements
- [ ] Hebrew text displays correctly (RTL)

### User Acceptance
- [ ] First-time user can onboard without confusion
- [ ] Empty states are helpful, not frustrating
- [ ] Financial data is clear and trustworthy
- [ ] No overwhelming information density

### Performance
- [ ] Dashboard loads in < 2 seconds
- [ ] Transactions page handles 1000+ rows smoothly
- [ ] Charts render without lag
- [ ] Filters apply without noticeable delay

---

## Success Metrics

Track these metrics before/after improvements:

| Metric | Before | Target | After |
|--------|--------|--------|-------|
| Dashboard Load Time | ? | < 2s | ? |
| User Confidence (subjective) | ? | High | ? |
| Empty State Clarity | Low | High | ? |
| Transaction Scanning Speed | Slow | Fast | ? |
| First-Time User Success | ? | 90% | ? |

---

## Notes & Decisions

**Date**: 2026-01-16
**Decision**: Focus on security and data display first (items 1-9), polish later (items 10-17)

**Rationale**: Financial apps must prioritize trust and clarity. Visual polish comes after core UX is solid.

---

## Next Steps

1. Review this plan with user
2. Prioritize items 1-3 (Critical) for immediate implementation
3. Implement and test each item sequentially
4. Update checkboxes as items complete
5. Create `UI_UX_GUIDELINES.md` after improvements are complete