# Phase 1: Enhanced Streamlit Mobile

## Goal
Create a mobile-first experience for the Streamlit app following modern fintech UX best practices, while keeping the full-featured desktop experience intact.

## Relationship to Hub Landing Page

| Page | Desktop | Mobile |
|------|---------|--------|
| `app.py` (Hub) | Visual overhaul (HUB_LANDING_PAGE_PLAN Phase 3) | Redirect to Mobile Dashboard |
| `0_📱_Mobile.py` | Not shown | Primary mobile experience |

**Flow:**
1. Desktop users → `app.py` (Hub with cards, hero balance, etc.)
2. Mobile users → Auto-redirect to `0_📱_Mobile.py` (simplified, touch-optimized)

The Mobile Dashboard (`0_📱_Mobile.py`) is the **mobile-first version of the Hub**, not a separate page. It shows the same information (balance, spending, recent activity, alerts) but with mobile-optimized UX patterns.

---

## Mobile UX Best Practices (Applied)

Based on 2025 fintech UX research, this plan incorporates:

| Practice | Implementation |
|----------|----------------|
| **Balance front and center** | Hero card with net worth as first element |
| **Card-based layouts** | Each metric/section in distinct visual cards |
| **Bottom navigation** | Sticky bottom bar with 3-4 primary actions |
| **Progressive disclosure** | Show summary first, details on tap |
| **Visual data over numbers** | Mini sparklines, progress bars, color coding |
| **Contextual insights** | AI-style tips ("You spent 20% less this week") |
| **Thumb-friendly zones** | Primary actions in bottom 2/3 of screen |
| **Microinteractions** | Subtle feedback on actions |
| **Color-coded categories** | Consistent category colors across app |
| **Single CTA per section** | Clear primary action, secondary actions hidden |
| **Accessibility** | 44px touch targets, sufficient contrast, clear labels |

---

## Mobile Information Hierarchy

```
┌─────────────────────────────────────────┐
│  HERO ZONE (Most Important)             │
│  ┌─────────────────────────────────────┐│
│  │ 💰 ₪xxx,xxx                         ││
│  │    Net Worth                        ││
│  │    ↑ +₪2,340 this month            ││
│  └─────────────────────────────────────┘│
├─────────────────────────────────────────┤
│  INSIGHT ZONE (Contextual)              │
│  ┌─────────────────────────────────────┐│
│  │ 💡 You spent 18% less than last wk  ││
│  └─────────────────────────────────────┘│
├─────────────────────────────────────────┤
│  ACTION CARDS (Tap to Expand)           │
│  ┌─────────────────────────────────────┐│
│  │ 📉 This Month        -₪4,230   ▼   ││
│  │    ██████████░░░░ 68% of budget    ││
│  └─────────────────────────────────────┘│
│  ┌─────────────────────────────────────┐│
│  │ 🕐 Recent              10 new   ▼   ││
│  │    Last: Supermarket -₪150         ││
│  └─────────────────────────────────────┘│
│  ┌─────────────────────────────────────┐│
│  │ ⏳ Pending              3 items  ▼  ││
│  │    ₪1,240 awaiting                 ││
│  └─────────────────────────────────────┘│
│  ┌─────────────────────────────────────┐│
│  │ 📂 Uncategorized          12    →   ││
│  │    Quick categorize                ││
│  └─────────────────────────────────────┘│
├─────────────────────────────────────────┤
│  BOTTOM NAV (Thumb Zone - Sticky)       │
│  ┌─────────────────────────────────────┐│
│  │  🏠    💳    📊    ⚙️              ││
│  │ Home  Txns  Stats  More            ││
│  └─────────────────────────────────────┘│
└─────────────────────────────────────────┘
```

---

## Implementation Plan

g### Step 0: Basic Monthly Budget System (Both Versions)
**New feature for both mobile and desktop**

#### Database Model
**File:** `db/models.py` (modify)

```python
class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)  # 1-12
    amount = Column(Float, nullable=False)   # Monthly budget limit
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('year', 'month', name='uq_budget_period'),
    )
```

#### Budget Service
**File:** `services/budget_service.py` (new)

```python
class BudgetService:
    def get_current_budget(self) -> Optional[float]:
        """Get budget for current month, or default if not set"""

    def set_monthly_budget(self, year: int, month: int, amount: float) -> Budget:
        """Set/update budget for a specific month"""

    def set_default_budget(self, amount: float) -> None:
        """Set default monthly budget (stored in config)"""

    def get_budget_progress(self) -> dict:
        """Returns: {budget: 5000, spent: 3400, remaining: 1600, percent: 68}"""

    def copy_budget_to_next_month(self) -> Budget:
        """Copy current month's budget to next month"""
```

#### Settings Page Update
**File:** `streamlit_app/pages/8_⚙️_Settings.py` (modify)

Add "Budget" section:
```
┌─────────────────────────────────────────┐
│  💰 Monthly Budget                      │
│  ┌─────────────────────────────────────┐│
│  │ Default monthly budget: ₪ [5000]   ││
│  │ [Save]                              ││
│  └─────────────────────────────────────┘│
│                                         │
│  Current month (January 2026):          │
│  Budget: ₪5,000  |  Spent: ₪3,400      │
│  Progress: ██████████░░░░ 68%          │
└─────────────────────────────────────────┘
```

#### Desktop Dashboard Update
**File:** `streamlit_app/pages/1_📊_Dashboard.py` (modify)

Add budget progress to hero section:
```python
# After monthly spending display
budget_progress = budget_service.get_budget_progress()
if budget_progress:
    st.progress(budget_progress['percent'] / 100)
    st.caption(f"₪{budget_progress['remaining']:,.0f} remaining of ₪{budget_progress['budget']:,.0f} budget")
```

#### CLI Commands
**File:** `cli/commands/budget.py` (new)

```bash
fin-cli budget show           # Show current month budget and progress
fin-cli budget set 5000       # Set this month's budget
fin-cli budget set-default 5000  # Set default for future months
```

---

### Step 1: Mobile Detection & Routing
**File:** `streamlit_app/utils/mobile.py` (new)

```python
def is_mobile() -> bool
    """Detect mobile via JavaScript user-agent injection"""

def get_thumb_zone_position() -> str
    """Return 'bottom' for mobile, 'any' for desktop"""

def mobile_page_config():
    """Set mobile-optimized page config (collapsed sidebar, etc.)"""
```

Uses `st.components.v1.html` to inject JS that checks `navigator.userAgent` and stores result in `st.session_state.is_mobile`.

---

### Step 2: Mobile Component Library
**File:** `streamlit_app/components/mobile_ui.py` (new)

**Hero Card Component:**
```python
def hero_balance_card(
    balance: float,
    change: float,
    change_period: str = "this month"
) -> None:
    """Large, prominent balance display with trend indicator"""
```
- Full-width gradient card
- Balance in large font (2.5rem)
- Change indicator with color (green up, red down)
- Tap to see breakdown by account type

**Insight Banner Component:**
```python
def contextual_insight(insight_text: str, icon: str = "💡") -> None:
    """Dismissible insight banner with actionable tip"""
```
- Generated from analytics (spending trends, unusual activity)
- Dismissible with X button
- Links to relevant action when applicable

**Summary Card Component:**
```python
def summary_card(
    title: str,
    primary_value: str,
    secondary_text: str,
    progress: float = None,  # 0-1 for progress bar
    expandable: bool = True,
    expand_content: callable = None
) -> None:
    """Expandable card with summary + optional progress bar"""
```
- Collapsed: Shows title, value, optional mini progress bar
- Expanded: Shows detailed content (transactions, breakdown)
- Tap anywhere to expand (not just arrow)

**Transaction Card Component:**
```python
def transaction_card(
    txn: dict,
    show_category_badge: bool = True,
    on_categorize: callable = None
) -> None:
    """Touch-friendly transaction display"""
```
- Category color dot on left
- Description (truncated), amount on right
- Relative date ("Today", "Yesterday", "3 days ago")
- Tap to expand: full details + categorize button

**Bottom Navigation Component:**
```python
def bottom_nav(
    items: list[dict],  # {"icon": "🏠", "label": "Home", "page": "..."}
    current: str
) -> str:
    """Sticky bottom navigation bar - returns selected page"""
```
- Fixed to bottom of viewport
- 4 items maximum (Home, Transactions, Stats, More)
- Active state indicator
- 56px height for thumb comfort

---

### Step 3: Mobile Dashboard Page (Mobile Hub)
**File:** `streamlit_app/pages/0_📱_Mobile.py` (new)

This is the **mobile-first version of the Hub** (`app.py`). Same data, mobile-optimized UX.

**Content Mirror from Hub:**
| Hub Section | Mobile Version |
|-------------|----------------|
| Hero Balance (gradient card) | Same gradient card, stacked layout |
| Metrics row (4 metrics) | Collapsed into hero + 2 supporting cards |
| Alerts section | Expandable alert cards |
| Recent Activity | Transaction cards (not table) |
| Accounts Overview | Expandable account cards |
| Contextual Insight | Same insight banner |

**Structure:**
1. **Hero Zone** (always visible, no scroll needed for key info)
   - Balance card with trend (same gradient as desktop Hub)
   - Budget progress bar
   - One-line contextual insight

2. **Action Cards** (scrollable, match Hub sections)
   - Monthly spending card with budget progress
   - Alerts cards (expandable, color-coded like desktop)
   - Recent transactions (last 5, card-based, tap for more)
   - Accounts summary (grouped by institution)
   - Pending items card (if any)
   - Uncategorized card (if any) - links to quick categorize

3. **Bottom Navigation** (fixed)
   - Home (current page)
   - Transactions (goes to mobile transactions)
   - Stats (simplified analytics)
   - More (settings, sync, desktop hub link)

**Key UX Features:**
- Pull-to-refresh gesture (simulated with manual refresh button)
- Last synced timestamp at top
- Skeleton loading states
- Error states with retry button
- Uses same `get_hub_alerts()`, `get_recent_transactions()` from cache.py
- Uses same `generate_hub_insight()` for contextual tips

---

### Step 4: Mobile Transactions View
**File:** `streamlit_app/pages/3_💳_Transactions.py` (modify)

Add mobile-aware rendering at top of file:
```python
if is_mobile():
    render_mobile_transactions()
    st.stop()
# ... existing desktop code
```

**Mobile Transactions Features:**
- **Search bar** - Always visible at top, full width
- **Quick filters** - Horizontal scrollable chips (All, Food, Transport, etc.)
- **Date filter** - Dropdown with presets (Today, This Week, This Month, Custom)
- **Transaction list** - Card-based, infinite scroll pattern
- **Tap to expand** - Shows full details, category assignment, tags

**No DataFrames on mobile** - Only card-based views

---

### Step 5: Quick Categorize Flow
**File:** `streamlit_app/components/mobile_ui.py` (add)

```python
def quick_categorize_flow(uncategorized: list[dict]) -> None:
    """Swipe-through categorization for uncategorized transactions"""
```

**UX Pattern (inspired by Tinder/dating apps):**
```
┌─────────────────────────────────────────┐
│  📂 Quick Categorize          3/12      │
├─────────────────────────────────────────┤
│  ┌─────────────────────────────────────┐│
│  │                                     ││
│  │  🛒 SUPERMARKET XYZ                 ││
│  │                                     ││
│  │  ₪156.80                            ││
│  │  Jan 15, 2026                       ││
│  │                                     ││
│  └─────────────────────────────────────┘│
├─────────────────────────────────────────┤
│  Category:                              │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   │
│  │ 🍕   │ │ 🛒   │ │ ⛽   │ │ 🎬   │   │
│  │ Food │ │Grocer│ │ Fuel │ │ Fun  │   │
│  └──────┘ └──────┘ └──────┘ └──────┘   │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   │
│  │ 🏥   │ │ 🛍️   │ │ 📱   │ │ ••• │   │
│  │Health│ │ Shop │ │ Bills│ │ More │   │
│  └──────┘ └──────┘ └──────┘ └──────┘   │
├─────────────────────────────────────────┤
│         [Skip]      [Create Rule]       │
└─────────────────────────────────────────┘
```

- Large category buttons (easy thumb tap)
- Top 8 most-used categories shown
- "More" expands full category list
- "Skip" moves to next without categorizing
- "Create Rule" saves pattern for future auto-categorization
- Progress indicator shows remaining items

---

### Step 6: Mobile CSS System
**File:** `streamlit_app/components/mobile_ui.py` (add)

```python
MOBILE_CSS = """
<style>
/* ===== BASE MOBILE STYLES ===== */
@media (max-width: 768px) {
    /* Hide sidebar completely */
    [data-testid="stSidebar"] {
        display: none !important;
    }

    /* Remove default padding */
    .main .block-container {
        padding: 0.5rem 1rem 5rem 1rem !important;
    }

    /* Prevent iOS zoom on input focus */
    input, select, textarea {
        font-size: 16px !important;
    }
}

/* ===== HERO CARD ===== */
.mobile-hero {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 1.5rem;
    border-radius: 16px;
    color: white;
    margin-bottom: 1rem;
}
.mobile-hero .balance {
    font-size: 2.5rem;
    font-weight: 700;
    margin: 0;
}
.mobile-hero .label {
    font-size: 0.875rem;
    opacity: 0.9;
}
.mobile-hero .change {
    font-size: 0.875rem;
    margin-top: 0.5rem;
}
.mobile-hero .change.positive { color: #a7f3d0; }
.mobile-hero .change.negative { color: #fecaca; }

/* ===== SUMMARY CARDS ===== */
.mobile-card {
    background: white;
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 0.75rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    cursor: pointer;
    transition: box-shadow 0.2s;
}
.mobile-card:active {
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

/* ===== TRANSACTION CARDS ===== */
.txn-card {
    display: flex;
    align-items: center;
    padding: 0.75rem 0;
    border-bottom: 1px solid #f0f0f0;
}
.txn-card .category-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 0.75rem;
}
.txn-card .description {
    flex: 1;
    font-size: 0.9rem;
}
.txn-card .amount {
    font-weight: 600;
    font-size: 0.9rem;
}
.txn-card .date {
    font-size: 0.75rem;
    color: #888;
    margin-left: 0.5rem;
}

/* ===== BOTTOM NAVIGATION ===== */
.bottom-nav {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: 56px;
    background: white;
    display: flex;
    justify-content: space-around;
    align-items: center;
    box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
    z-index: 1000;
}
.bottom-nav-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 0.5rem 1rem;
    color: #666;
    text-decoration: none;
    font-size: 0.7rem;
}
.bottom-nav-item.active {
    color: #667eea;
}
.bottom-nav-item .icon {
    font-size: 1.25rem;
    margin-bottom: 0.25rem;
}

/* ===== CATEGORY BUTTONS ===== */
.category-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.75rem;
}
.category-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 0.75rem;
    background: #f5f5f5;
    border-radius: 12px;
    min-height: 64px;
}
.category-btn:active {
    background: #e0e0e0;
}
.category-btn .icon {
    font-size: 1.5rem;
    margin-bottom: 0.25rem;
}
.category-btn .label {
    font-size: 0.7rem;
    text-align: center;
}

/* ===== ACCESSIBILITY ===== */
button, a, [role="button"] {
    min-height: 44px;
    min-width: 44px;
}

/* ===== DARK MODE SUPPORT ===== */
@media (prefers-color-scheme: dark) {
    .mobile-card {
        background: #1e1e1e;
    }
    .bottom-nav {
        background: #1e1e1e;
    }
}
</style>
"""
```

---

### Step 7: Simplified Mobile Stats
**File:** `streamlit_app/pages/4_📈_Analytics.py` (modify)

Add mobile view with:
- Spending by category (horizontal bar chart, not pie)
- Monthly trend (simple line, last 6 months)
- Top merchants (list with amounts)

No complex visualizations - those stay desktop-only.

---

## Files Summary

### Budget Feature (Both Versions)
| File | Action | Description |
|------|--------|-------------|
| `db/models.py` | Modify | Add Budget model |
| `services/budget_service.py` | New | Budget CRUD and progress calculation |
| `cli/commands/budget.py` | New | CLI budget commands |
| `cli/main.py` | Modify | Register budget command group |
| `streamlit_app/pages/8_⚙️_Settings.py` | Modify | Add budget settings section |
| `streamlit_app/pages/1_📊_Dashboard.py` | Modify | Add budget progress display |

### Mobile Feature
| File | Action | Description |
|------|--------|-------------|
| `streamlit_app/utils/mobile.py` | New | Mobile detection, routing utilities |
| `streamlit_app/components/mobile_ui.py` | New | All mobile UI components + CSS |
| `streamlit_app/pages/0_📱_Mobile.py` | New | Mobile-optimized dashboard |
| `streamlit_app/pages/3_💳_Transactions.py` | Modify | Add mobile transactions view |
| `streamlit_app/pages/4_📈_Analytics.py` | Modify | Add simplified mobile stats |

---

## Verification Checklist

### Budget Feature
- [ ] `fin-cli budget set 5000` sets monthly budget
- [ ] `fin-cli budget show` displays current progress
- [ ] Settings page shows budget configuration
- [ ] Desktop dashboard shows progress bar
- [ ] Mobile dashboard shows progress bar
- [ ] Budget persists across sessions

### Desktop Experience
- [ ] All existing pages work unchanged
- [ ] No visual regressions

### Mobile Detection
- [ ] Detects mobile browsers correctly
- [ ] Detects tablet as mobile (or configurable)
- [ ] Chrome DevTools mobile emulation works

### Mobile Dashboard
- [ ] Balance visible without scrolling
- [ ] Cards expand/collapse smoothly
- [ ] Bottom nav stays fixed on scroll
- [ ] Touch targets are 44px+ minimum
- [ ] No horizontal scroll

### Mobile Transactions
- [ ] Search works correctly
- [ ] Filter chips scroll horizontally
- [ ] Cards display all necessary info
- [ ] Tap expands card with details

### Quick Categorize
- [ ] Shows one transaction at a time
- [ ] Category buttons are large enough
- [ ] Progress indicator updates
- [ ] "Create Rule" saves mapping

### Accessibility
- [ ] Font size 16px+ on inputs (no iOS zoom)
- [ ] Sufficient color contrast
- [ ] Focus states visible
- [ ] Screen reader labels present

---

## Future Enhancements (Phase 2 - React Hybrid)

If Streamlit mobile proves insufficient:
- PWA manifest for home screen install
- Service worker for offline balance cache
- Push notifications for pending items
- True swipe gestures (requires React/custom component)

---

## References

- [Fintech UX Best Practices 2025](https://www.g-co.agency/insights/the-best-ux-design-practices-for-finance-apps)
- [Fintech UI Examples](https://www.eleken.co/blog-posts/trusted-fintech-ui-examples)
- [Mobile Finance App Design](https://procreator.design/blog/finance-app-design-best-practices/)