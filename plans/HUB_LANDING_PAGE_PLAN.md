# Hub Landing Page Implementation Plan

**Status**: All Phases Complete

| Phase | Status |
|-------|--------|
| Phase 1: Foundation | ✅ Complete |
| Phase 2: Hub Page | ✅ Complete |
| Phase 3: Polish & UX Enhancement | ✅ Complete |

---

## Mobile UX Best Practices (2025 Fintech Standards)

Based on current fintech UX research, this plan incorporates:

| Practice | Current State | Enhancement Needed |
|----------|---------------|-------------------|
| **Balance front and center** | ✅ Hero card with gradient | Done |
| **Card-based layouts** | ✅ Section cards, metric cards | Done |
| **Progressive disclosure** | ✅ Summary → details pages | Done |
| **Visual data over numbers** | ⚠️ Numbers only | Add progress bars, sparklines (deferred) |
| **Contextual insights** | ✅ Insight banner | Done |
| **Touch-friendly (44px+)** | ✅ Larger buttons, cards | Done |
| **Bottom navigation (mobile)** | ❌ Missing | Add for mobile view (future) |
| **Color-coded categories** | ✅ Category badges with icons | Done |
| **Microinteractions** | ❌ Missing | Add subtle animations (future) |
| **Accessibility** | ⚠️ Basic | Improve contrast, focus states (future) |

## Overview

Replace the static welcome page with an actionable hub that answers: **"What needs my attention right now?"**

**Goal**: A returning user gets value in 5 seconds without clicking anything.

**Principles**:
- **DRY**: Reuse existing services, cache functions, and components
- **KISS**: No new abstractions - compose existing pieces
- **SIMPLE**: Only show what matters, hide complexity

---

## Design

### Layout (Top to Bottom)

```
┌─────────────────────────────────────────────────────────────────────┐
│ HEADER: Greeting + Quick Action                                     │
├─────────────────────────────────────────────────────────────────────┤
│ METRICS ROW: 4 key numbers                                          │
├─────────────────────────────────────────────────────────────────────┤
│ ALERTS: What needs attention (collapsible if empty)                 │
├─────────────────────────────────────────────────────────────────────┤
│ RECENT ACTIVITY        │  ACCOUNTS OVERVIEW                         │
│ (left column)          │  (right column)                            │
└─────────────────────────────────────────────────────────────────────┘
```

### Sidebar

Use `render_minimal_sidebar()` - same as other pages. Includes:
- Privacy toggle (new)
- Quick stats
- About section

---

## Sections Detail

### 1. Header

```python
col1, col2 = st.columns([4, 1])
with col1:
    st.title(f"{get_time_greeting()}")  # "Good morning" / "Good afternoon" / "Good evening"
with col2:
    if st.button("🔄 Sync Now", use_container_width=True):
        st.switch_page("pages/2_🔄_Sync.py")
```

**Reuses**: `get_time_greeting()` from `streamlit_app/utils/insights.py`

**UX Notes**:
- No name personalization (we don't store user names)
- Single prominent action - sync is the most common need

---

### 2. Metrics Row

Four metrics in equal columns:

| Metric | Source | Format |
|--------|--------|--------|
| Total Balance | `get_dashboard_stats()['total_balance']` | `format_amount_private()` |
| This Month | `get_dashboard_stats()['monthly_spending']` | `format_amount_private()` + "spent" |
| Pending | `get_dashboard_stats()['pending_count']` | Count + amount in delta |
| Last Sync | `get_dashboard_stats()['last_sync']` | Relative time ("2 hrs ago") |

```python
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Balance", format_amount_private(stats['total_balance']))

with col2:
    st.metric("This Month", format_amount_private(stats['monthly_spending']), "spent")

with col3:
    st.metric(
        "Pending",
        stats['pending_count'],
        format_amount_private(stats['pending_amount']) if stats['pending_amount'] else None
    )

with col4:
    st.metric("Last Sync", format_relative_time(stats['last_sync']))
```

**Reuses**:
- `get_dashboard_stats()` from `streamlit_app/utils/cache.py`
- `format_amount_private()` from `streamlit_app/utils/session.py`

**New helper needed**: `format_relative_time()` - simple function, add to `formatters.py`

```python
def format_relative_time(dt: datetime) -> str:
    """Format datetime as relative time (e.g., '2 hrs ago', 'Yesterday')"""
    if not dt:
        return "Never"

    now = datetime.now()
    diff = now - dt

    if diff.days == 0:
        hours = diff.seconds // 3600
        if hours == 0:
            minutes = diff.seconds // 60
            return f"{minutes} min ago" if minutes > 1 else "Just now"
        return f"{hours} hr ago" if hours == 1 else f"{hours} hrs ago"
    elif diff.days == 1:
        return "Yesterday"
    elif diff.days < 7:
        return f"{diff.days} days ago"
    else:
        return dt.strftime("%b %d")
```

---

### 3. Alerts Section ("Needs Attention")

Only show if there are alerts. Each alert has:
- Icon + description
- Action button that navigates to the right page

```python
alerts = get_hub_alerts()  # New function

if alerts:
    st.subheader("⚠️ Needs Attention")

    for alert in alerts:
        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(f"{alert['icon']} {alert['message']}")
        with col2:
            if st.button(alert['action_label'], key=alert['key']):
                st.switch_page(alert['page'])
```

**Alert Types** (priority order):

| Alert | Condition | Message | Action |
|-------|-----------|---------|--------|
| Stale sync | Any account `last_synced_at` > 3 days | "{institution} hasn't synced in {days} days" | "Sync →" → Sync page |
| Unmapped categories | `CategoryService.get_unmapped_categories()` not empty | "{count} unmapped categories from last sync" | "Map →" → Categories page |
| Uncategorized transactions | Transactions where `effective_category` is NULL | "{count} uncategorized transactions ({amount})" | "Categorize →" → Categories page (By Merchant tab) |

**New function** in `streamlit_app/utils/cache.py`:

```python
@st.cache_data(ttl=60)  # Short TTL - alerts should be fresh
def get_hub_alerts() -> list[dict]:
    """Get actionable alerts for the hub page."""
    alerts = []

    # 1. Stale syncs
    stale_accounts = get_stale_accounts(days=3)
    for acc in stale_accounts:
        alerts.append({
            'icon': '🔄',
            'message': f"{acc['institution']} hasn't synced in {acc['days']} days",
            'action_label': 'Sync →',
            'page': 'pages/2_🔄_Sync.py',
            'key': f"alert_sync_{acc['institution']}",
            'priority': 1
        })

    # 2. Unmapped categories
    unmapped = get_unmapped_category_count()
    if unmapped > 0:
        alerts.append({
            'icon': '📂',
            'message': f"{unmapped} unmapped categories from last sync",
            'action_label': 'Map →',
            'page': 'pages/10_📂_Categories.py',
            'key': 'alert_unmapped',
            'priority': 2
        })

    # 3. Uncategorized transactions
    uncategorized = get_uncategorized_transaction_count()
    if uncategorized['count'] > 0:
        alerts.append({
            'icon': '🏷️',
            'message': f"{uncategorized['count']} uncategorized transactions ({format_amount_private(uncategorized['amount'])})",
            'action_label': 'Categorize →',
            'page': 'pages/10_📂_Categories.py',
            'key': 'alert_uncategorized',
            'priority': 3
        })

    return sorted(alerts, key=lambda x: x['priority'])
```

**UX Notes**:
- Max 5 alerts shown (avoid overwhelm)
- If no alerts: show nothing (not "All good!" - that's noise)
- Alerts are actionable - every alert has a clear next step

---

### 4. Recent Activity (Left Column)

Last 7 transactions grouped by date.

```python
with col_left:
    st.subheader("📋 Recent Activity")

    recent = get_recent_transactions(limit=7)

    if recent:
        current_date = None
        for txn in recent:
            # Date header
            txn_date = txn['transaction_date']
            if txn_date != current_date:
                current_date = txn_date
                st.caption(format_date_relative(txn_date))  # "Today", "Yesterday", "Jan 20"

            # Transaction row
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.markdown(f"**{clean_merchant_name(txn['description'])}**")
            with col2:
                st.markdown(txn['effective_category'] or "—")
            with col3:
                st.markdown(format_amount_private(txn['original_amount']))

        if st.button("View all transactions →", use_container_width=True):
            st.switch_page("pages/3_💳_Transactions.py")
    else:
        st.info("No recent transactions. Sync to see activity.")
```

**Reuses**:
- `clean_merchant_name()` from `streamlit_app/utils/rtl.py`
- `format_amount_private()` from `streamlit_app/utils/session.py`

**New cached function**:

```python
@st.cache_data(ttl=300)
def get_recent_transactions(limit: int = 7) -> list[dict]:
    """Get most recent transactions for hub display."""
    # Simple query - just fetch latest N transactions
    # Reuse existing transaction query logic
```

**UX Notes**:
- Group by date for scannability
- Show category to reinforce categorization
- Truncate merchant names if too long
- RTL handling for Hebrew merchants

---

### 5. Accounts Overview (Right Column)

Quick summary of all accounts with balances.

```python
with col_right:
    st.subheader("🏦 Accounts")

    accounts = get_accounts_display()  # Already exists, adds balance_display

    if accounts:
        # Group by institution
        by_institution = {}
        for acc in accounts:
            inst = acc['institution']
            if inst not in by_institution:
                by_institution[inst] = {'accounts': [], 'total': 0}
            by_institution[inst]['accounts'].append(acc)
            by_institution[inst]['total'] += acc['latest_balance'] or 0

        for inst, data in by_institution.items():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{inst.upper()}**")
                st.caption(f"{len(data['accounts'])} account{'s' if len(data['accounts']) > 1 else ''}")
            with col2:
                st.markdown(format_amount_private(data['total']))

        if st.button("View all accounts →", use_container_width=True):
            st.switch_page("pages/7_💰_Accounts.py")
    else:
        st.info("No accounts yet. Sync to add accounts.")
```

**Reuses**: `get_accounts_display()` from `streamlit_app/utils/session.py`

**UX Notes**:
- Group by institution (not individual cards/accounts) to reduce noise
- Show account count per institution
- Privacy mode hides all amounts

---

## Empty State

If no data at all (fresh install):

```python
if not stats or stats['account_count'] == 0:
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 👋 Welcome!")
        st.markdown("""
        Get started by syncing your financial accounts:

        1. **Configure credentials** (one-time setup)
        ```bash
        fin-cli config setup
        ```

        2. **Sync your data**
        """)

        if st.button("🔄 Go to Sync Page", use_container_width=True, type="primary"):
            st.switch_page("pages/2_🔄_Sync.py")

        st.markdown("---")
        st.caption("Supports: CAL, Max, Isracard, Excellence, Migdal, Phoenix")

    return  # Don't render the rest of the hub
```

**UX Notes**:
- Centered, focused onboarding
- One clear action (sync)
- Minimal text - users want to get started, not read

---

## Files to Modify

### Phase 1 & 2 (Complete)
| File | Changes |
|------|---------|
| `streamlit_app/app.py` | Complete rewrite - implement hub layout |
| `streamlit_app/utils/formatters.py` | Add `format_relative_time()` |
| `streamlit_app/utils/cache.py` | Add `get_hub_alerts()`, `get_recent_transactions()`, helper functions |

### Phase 3 (Visual Overhaul)
| File | Changes |
|------|---------|
| `streamlit_app/app.py` | Replace `load_custom_css()`, add hero card, redesign all render functions |
| `streamlit_app/utils/formatters.py` | Add `get_category_icon()`, `CATEGORY_ICONS` mapping |
| `streamlit_app/utils/insights.py` | Add `generate_hub_insight()` for contextual tips |

**No new files needed** - everything builds on existing infrastructure.

---

## Implementation Checklist

### Phase 1: Foundation
- [x] Add `format_relative_time()` to formatters.py
- [x] Add `get_recent_transactions()` to cache.py
- [x] Add alert helper functions to cache.py
- [x] Add `get_hub_alerts()` to cache.py

### Phase 2: Hub Page
- [x] Rewrite app.py with hub layout
- [x] Implement header with greeting + sync button
- [x] Implement metrics row
- [x] Implement alerts section
- [x] Implement recent activity (left column)
- [x] Implement accounts overview (right column)
- [x] Implement empty state

### Phase 3: Visual Overhaul & UX Enhancement

**Problems to Fix:**
- Too plain/boring - needs color, cards, visual hierarchy
- Too cluttered - too much information, needs breathing room
- Layout issues - sections sized incorrectly

#### 3.1 Hero Balance Card (Replace Plain Metrics)
**Current:** 4 equal metrics in a row - boring, no hierarchy
**New:** Large hero card for balance + smaller supporting metrics

```
┌─────────────────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────┐  ┌───────────┐ ┌───────────┐  │
│  │  💰 Net Worth                   │  │ This Month│ │  Pending  │  │
│  │     ₪xxx,xxx                    │  │  ₪4,230   │ │    3      │  │
│  │     ↑ +₪2,340 this month        │  │   spent   │ │  ₪1,240   │  │
│  │     ▓▓▓▓▓▓▓▓▓░ 68% of budget    │  └───────────┘ └───────────┘  │
│  └─────────────────────────────────┘  ┌───────────┐                │
│                                       │ Last Sync │                │
│                                       │  2 hrs ago│                │
│                                       └───────────┘                │
└─────────────────────────────────────────────────────────────────────┘
```

**Changes:**
- Hero card with gradient background (purple/blue like Revolut)
- Balance in 2.5rem font, white text
- Budget progress bar underneath
- Supporting metrics in smaller cards to the right
- Remove "Last Sync" from metrics if stale (show in alerts instead)

#### 3.2 Card-Based Layout
**Current:** Flat sections with just `st.subheader`
**New:** Distinct visual cards with shadows and rounded corners

```python
# New CSS for cards
.hub-card {
    background: white;
    border-radius: 16px;
    padding: 1.5rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    margin-bottom: 1rem;
}

.hub-card-header {
    font-size: 1rem;
    font-weight: 600;
    color: #333;
    margin-bottom: 1rem;
}
```

#### 3.3 Alerts Section Redesign
**Current:** Plain text with buttons - looks like debug output
**New:** Color-coded alert cards with icons

```
┌─────────────────────────────────────────────────────────────────────┐
│  ⚠️ Needs Attention                                                 │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 🔄  CAL hasn't synced in 5 days                    [Sync →]  │  │
│  │     Background: light yellow                                  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 📂  12 transactions need categorizing              [Fix →]   │  │
│  │     Background: light blue                                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

**Alert card colors:**
- Stale sync: `#FEF3C7` (amber-100)
- Unmapped categories: `#DBEAFE` (blue-100)
- Uncategorized transactions: `#E0E7FF` (indigo-100)

#### 3.4 Recent Activity Cleanup
**Current:** Dense 3-column layout, hard to scan
**New:** Clean list with proper spacing and category badges

```
┌─────────────────────────────────────────────────────────────────────┐
│  📋 Recent Activity                                                  │
│  ───────────────────────────────────────────────────────────────    │
│  Today                                                               │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  🛒  Supermarket XYZ        [Groceries]           -₪156.80   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  ⛽  Gas Station             [Fuel]                -₪200.00   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  Yesterday                                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  📺  Netflix                 [Subscriptions]        -₪49.90  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│                      [View all transactions →]                       │
└─────────────────────────────────────────────────────────────────────┘
```

**Changes:**
- Category icons (emoji) based on category name
- Category badges with background color
- More vertical spacing between items
- Amounts right-aligned with monospace font
- Date headers with subtle styling

#### 3.5 Accounts Overview Simplification
**Current:** Institution name + count + total - cluttered
**New:** Clean card per institution with visual hierarchy

```
┌───────────────────────────────────────┐
│  🏦 Accounts                          │
│  ─────────────────────────────────    │
│  ┌─────────────────────────────────┐  │
│  │  CAL              ₪12,345       │  │
│  │  2 cards                        │  │
│  └─────────────────────────────────┘  │
│  ┌─────────────────────────────────┐  │
│  │  EXCELLENCE       ₪45,678       │  │
│  │  1 account                      │  │
│  └─────────────────────────────────┘  │
│                                        │
│        [View all accounts →]           │
└────────────────────────────────────────┘
```

#### 3.6 Contextual Insight Banner
**New feature** - Add an insight below the hero

```
┌─────────────────────────────────────────────────────────────────────┐
│  💡 You spent 18% less than last week. Keep it up!              ✕   │
│     Background: light green                                         │
└─────────────────────────────────────────────────────────────────────┘
```

**Logic:**
- Compare current week spending to last week
- Show positive insight if spending is down
- Show neutral insight if spending is similar
- Hide if no meaningful insight (don't force it)

#### 3.7 CSS Overhaul
**File:** `streamlit_app/app.py` - replace `load_custom_css()`

```css
/* ===== HERO CARD ===== */
.hero-balance {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 2rem;
    border-radius: 20px;
    color: white;
    margin-bottom: 1.5rem;
}
.hero-balance .amount {
    font-size: 2.5rem;
    font-weight: 700;
    margin: 0;
}
.hero-balance .label {
    font-size: 0.9rem;
    opacity: 0.9;
    margin-bottom: 0.5rem;
}
.hero-balance .change {
    font-size: 0.85rem;
    margin-top: 0.5rem;
}
.hero-balance .change.positive { color: #a7f3d0; }
.hero-balance .change.negative { color: #fecaca; }

/* ===== METRIC CARDS ===== */
.metric-card {
    background: white;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    text-align: center;
}
.metric-card .value {
    font-size: 1.5rem;
    font-weight: 600;
    color: #1f2937;
}
.metric-card .label {
    font-size: 0.8rem;
    color: #6b7280;
    margin-top: 0.25rem;
}

/* ===== ALERT CARDS ===== */
.alert-card {
    padding: 0.75rem 1rem;
    border-radius: 10px;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.alert-card.sync { background: #FEF3C7; }
.alert-card.category { background: #DBEAFE; }
.alert-card.uncategorized { background: #E0E7FF; }

/* ===== INSIGHT BANNER ===== */
.insight-banner {
    background: #D1FAE5;
    padding: 0.75rem 1rem;
    border-radius: 10px;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
}
.insight-banner.neutral { background: #F3F4F6; }
.insight-banner.warning { background: #FEF3C7; }

/* ===== SECTION CARDS ===== */
.section-card {
    background: white;
    border-radius: 16px;
    padding: 1.5rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.section-header {
    font-size: 1.1rem;
    font-weight: 600;
    color: #374151;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #f3f4f6;
}

/* ===== TRANSACTION LIST ===== */
.txn-item {
    display: flex;
    align-items: center;
    padding: 0.75rem 0;
    border-bottom: 1px solid #f9fafb;
}
.txn-item:last-child { border-bottom: none; }
.txn-icon {
    font-size: 1.25rem;
    margin-right: 0.75rem;
}
.txn-details { flex: 1; }
.txn-merchant {
    font-weight: 500;
    color: #1f2937;
}
.txn-category {
    display: inline-block;
    font-size: 0.7rem;
    padding: 0.15rem 0.5rem;
    border-radius: 9999px;
    background: #f3f4f6;
    color: #6b7280;
    margin-left: 0.5rem;
}
.txn-amount {
    font-family: 'SF Mono', 'Roboto Mono', monospace;
    font-weight: 500;
    color: #dc2626;
}
.txn-amount.positive { color: #16a34a; }

/* ===== DATE HEADERS ===== */
.date-header {
    font-size: 0.75rem;
    font-weight: 600;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 1rem 0 0.5rem 0;
}

/* ===== BUTTONS ===== */
.view-all-btn {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    background: transparent;
    color: #6b7280;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
}
.view-all-btn:hover {
    background: #f9fafb;
    color: #374151;
}

/* ===== BREATHING ROOM ===== */
.main .block-container {
    padding: 2rem 3rem;
    max-width: 1200px;
}
```

#### 3.8 Category Icons Mapping
**File:** `streamlit_app/utils/formatters.py` - add helper

```python
CATEGORY_ICONS = {
    'groceries': '🛒',
    'restaurants': '🍕',
    'fuel': '⛽',
    'transportation': '🚗',
    'utilities': '💡',
    'healthcare': '🏥',
    'entertainment': '🎬',
    'shopping': '🛍️',
    'travel': '✈️',
    'education': '📚',
    'insurance': '🛡️',
    'subscriptions': '📺',
    'home': '🏠',
    'clothing': '👕',
    'electronics': '📱',
    'gifts': '🎁',
    'fees': '💳',
    'other': '📋',
}

def get_category_icon(category: str) -> str:
    """Get emoji icon for a category"""
    if not category:
        return '📋'
    return CATEGORY_ICONS.get(category.lower(), '📋')
```

---

### Phase 3 Implementation Checklist

#### Visual Components
- [x] Create hero balance card with gradient
- [ ] Add budget progress bar to hero (after Budget feature - deferred)
- [x] Redesign metrics as smaller cards
- [x] Create alert card component with colors
- [x] Add contextual insight banner
- [x] Redesign transaction list with icons and badges
- [x] Redesign accounts overview cards

#### CSS & Styling
- [x] Replace `load_custom_css()` with new CSS
- [x] Add breathing room (max-width, padding)
- [x] Improve typography hierarchy
- [x] Add subtle shadows and rounded corners

#### New Helpers
- [x] Add `get_category_icon()` to formatters.py
- [x] Add `generate_hub_insight()` for contextual insights

#### Testing
- [ ] Test privacy mode (all amounts mask correctly)
- [ ] Test empty states (no data, partial data)
- [ ] Test RTL handling for Hebrew merchants
- [ ] Verify navigation buttons work
- [ ] Test on different screen sizes

---

## What We're NOT Doing

- **No spending chart** - Adds complexity, can go to Analytics for that
- **No week-over-week comparison** - Requires more queries, low value on landing page
- **No customizable layout** - KISS - one layout that works
- **No "dismiss alert" feature** - Alerts clear themselves when resolved
- **No loading skeletons** - Page is fast enough with caching

---

## UX Principles Applied

| Principle | Application |
|-----------|-------------|
| **Progressive disclosure** | Show summary first, details on dedicated pages |
| **Recognition over recall** | Show actual data, not instructions |
| **Visibility of system status** | Last sync time, pending count, alerts |
| **User control** | One-click navigation to fix any issue |
| **Error prevention** | Alerts surface problems before they grow |
| **Aesthetic minimalism** | Only essential info, no decorative elements |

---

## Privacy Mode Behavior

When privacy toggle is ON:
- All amounts show as "••••••"
- Account counts still visible (not sensitive)
- Alert messages show counts but mask amounts
- Recent activity shows merchants but masks amounts

This allows using the hub in public while still seeing what needs attention.