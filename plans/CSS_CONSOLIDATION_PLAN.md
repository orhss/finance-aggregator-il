# CSS Consolidation & Card Usage Plan

**Goal**: Extend Hub's card-based design to other pages for visual consistency before implementing mobile.

**Status**: Pending

---

## Current State

| Page | Loads CSS | Uses Card Classes | Issues |
|------|-----------|-------------------|--------|
| Hub (app.py) | ✅ `load_shared_css()` | ✅ Full usage | None - reference implementation |
| Transactions | ✅ `apply_theme()` | ❌ Plain DataFrames | Has inline `TABLE_STYLE_CSS` |
| Analytics | ✅ `apply_theme()` | ❌ Plain `st.metric()` | No visual cards |
| Accounts | ✅ `apply_theme()` | ❌ Plain columns | No `.account-card` usage |
| Organize | ✅ `apply_theme()` | ❌ Plain `st.metric()` | No visual cards |
| Settings | ✅ `apply_theme()` | ❌ Plain forms | Low priority |

---

## What We Have

### In `styles/main.css` (available but unused outside Hub):
- `.hero-balance` - gradient hero card
- `.metric-card` - small metric displays
- `.section-card` - content section containers
- `.alert-card` - color-coded alerts
- `.account-card` - account display cards
- `.transaction-row` - transaction list items
- `.category-badge`, `.tag-badge` - badges

### In `components/cards.py`:
- `render_card()` - generic card with HTML content
- `render_transaction_card()` - transactions grouped by date
- `render_summary_card()` - summary items (used for accounts in Hub)

---

## Implementation Tasks

### Task 1: Move Transactions Inline CSS to main.css

**File**: `streamlit_app/pages/1_💳_Transactions.py`

**Current** (lines 56-91):
```python
TABLE_STYLE_CSS = """
<style>
/* Zebra striping, hover, headers... */
</style>
"""
st.markdown(TABLE_STYLE_CSS, unsafe_allow_html=True)
```

**Change**:
1. Move CSS rules to `styles/main.css` under `/* ===== DATA TABLE STYLING ===== */`
2. Remove inline CSS from Transactions page
3. Table already gets CSS via `apply_theme()` - just consolidate

**Updated main.css addition**:
```css
/* ===== DATA TABLE STYLING ===== */
[data-testid="stDataFrame"] {
    border-radius: 8px;
}

[data-testid="stDataFrame"] tbody tr:nth-child(even) {
    background-color: #f8f9fa;
}

[data-testid="stDataFrame"] tbody tr:hover {
    background-color: #e3f2fd;
    cursor: pointer;
    transition: background-color 0.15s ease;
}

[data-testid="stDataFrame"] thead th {
    background-color: #667eea;
    color: white;
    font-weight: 600;
    text-align: left;
}

[data-testid="stDataFrame"] td:nth-child(3) {
    font-family: 'SF Mono', 'Roboto Mono', Consolas, monospace;
    font-weight: 500;
}
```

---

### Task 2: Add Metric Cards to Accounts Page

**File**: `streamlit_app/pages/3_🏦_Accounts.py`

**Current** (lines 249-256):
```python
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Accounts", format_number(total_accounts))
with col2:
    st.metric("Total Balance", format_amount_private(total_balance))
with col3:
    st.metric("Active Accounts", format_number(active))
```

**Change**: Use `.metric-card` HTML wrapper

```python
def render_metric_cards(metrics: list):
    """Render metrics using card styling from main.css"""
    cols = st.columns(len(metrics))
    for col, metric in zip(cols, metrics):
        with col:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="value">{metric["value"]}</div>'
                f'<div class="label">{metric["label"]}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

# Usage
render_metric_cards([
    {"value": format_number(total_accounts), "label": "Total Accounts"},
    {"value": format_amount_private(total_balance), "label": "Total Balance"},
    {"value": format_number(active), "label": "Active Accounts"},
])
```

**Also**: Use `.account-card` for individual accounts (lines 315-342)

```python
# Current: plain st.markdown and st.metric
# Change to:
st.markdown(
    f'<div class="account-card">'
    f'<div class="icon">🏦</div>'
    f'<div class="info">'
    f'<div class="name">{status_icon} {account.institution}</div>'
    f'<div class="subtitle">{txn_count} transactions</div>'
    f'</div>'
    f'<div class="balance">{format_amount_private(balance)}</div>'
    f'</div>',
    unsafe_allow_html=True
)
```

---

### Task 3: Add Metric Cards to Analytics Page

**File**: `streamlit_app/pages/2_📈_Analytics.py`

**Current**: Uses plain `st.metric()` scattered throughout

**Change**: Add a summary row at the top using `.metric-card`

After line 66 (after the title), add:
```python
def render_analytics_summary(stats: dict):
    """Render key metrics summary using card styling"""
    metrics = [
        {"value": format_amount_private(stats['total_spending']), "label": "Total Spending"},
        {"value": str(stats['transaction_count']), "label": "Transactions"},
        {"value": stats['top_category'] or "—", "label": "Top Category"},
        {"value": format_amount_private(stats['avg_transaction']), "label": "Avg Transaction"},
    ]

    cols = st.columns(4)
    for col, metric in zip(cols, metrics):
        with col:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="value">{metric["value"]}</div>'
                f'<div class="label">{metric["label"]}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
```

---

### Task 4: Add Metric Cards to Organize Page

**File**: `streamlit_app/pages/4_🏷️_Organize.py`

**Current** (lines 87-101):
```python
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Transactions", f"{coverage['total']:,}")
# ... etc
```

**Change**: Same pattern as above - wrap in `.metric-card`

```python
metrics = [
    {"value": f"{coverage['total']:,}", "label": "Total Transactions"},
    {"value": f"{coverage['with_unified_category']:,}", "label": "Categorized", "sublabel": f"{categorized_pct}%"},
    {"value": f"{coverage['with_provider_category']:,}", "label": "From Provider"},
    {"value": f"{coverage['needs_attention']:,}", "label": "Needs Attention"},
]

cols = st.columns(4)
for col, metric in zip(cols, metrics):
    with col:
        sublabel_html = f'<div class="sublabel">{metric.get("sublabel", "")}</div>' if metric.get("sublabel") else ""
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="value">{metric["value"]}</div>'
            f'<div class="label">{metric["label"]}</div>'
            f'{sublabel_html}'
            f'</div>',
            unsafe_allow_html=True
        )
```

---

### Task 5: Create Reusable Metric Card Helper

**File**: `streamlit_app/components/cards.py`

Add a simple helper function so we don't repeat the HTML everywhere:

```python
def render_metric_row(metrics: List[Dict[str, str]]) -> None:
    """
    Render a row of metric cards using shared CSS.

    Args:
        metrics: List of dicts with keys:
            - value: The metric value (string)
            - label: The metric label
            - sublabel: Optional sublabel text
    """
    cols = st.columns(len(metrics))
    for col, metric in zip(cols, metrics):
        with col:
            sublabel = metric.get('sublabel', '')
            sublabel_html = f'<div class="sublabel">{sublabel}</div>' if sublabel else ''
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="value">{metric["value"]}</div>'
                f'<div class="label">{metric["label"]}</div>'
                f'{sublabel_html}'
                f'</div>',
                unsafe_allow_html=True
            )
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `streamlit_app/styles/main.css` | Add table styling from Transactions |
| `streamlit_app/components/cards.py` | Add `render_metric_row()` helper |
| `streamlit_app/pages/1_💳_Transactions.py` | Remove inline CSS |
| `streamlit_app/pages/2_📈_Analytics.py` | Add metric cards row |
| `streamlit_app/pages/3_🏦_Accounts.py` | Use metric cards + account cards |
| `streamlit_app/pages/4_🏷️_Organize.py` | Use metric cards |

---

## What NOT to Change

- **DataFrames/tables** - Keep as-is, they're appropriate for data grids
- **Forms/inputs** - Keep plain Streamlit components
- **Charts** - Keep Plotly charts as-is
- **Settings page** - Low priority, forms are fine

---

## Implementation Order

1. **Task 5 first** - Create `render_metric_row()` helper
2. **Task 1** - Consolidate Transactions CSS (quick win)
3. **Task 2** - Accounts page (most visible improvement)
4. **Task 3** - Analytics page
5. **Task 4** - Organize page

---

## Verification Checklist

After implementation:
- [ ] All pages load without CSS errors
- [ ] Metric cards render consistently across all pages
- [ ] Account cards in Accounts page match Hub style
- [ ] No duplicate CSS (TABLE_STYLE_CSS removed from Transactions)
- [ ] Privacy mode still works (amounts masked)
- [ ] Dark mode still works (theme-aware)

---

## Relationship to Mobile Plan

Once this is done:
1. All pages use the same CSS classes
2. Mobile can add `@media` queries to `main.css`
3. No need for separate `.mobile-*` classes
4. `render_metric_row()` can be reused in mobile views

This consolidation makes the MOBILE_FIRST_PLAN simpler - just add responsive overrides instead of a parallel CSS system.