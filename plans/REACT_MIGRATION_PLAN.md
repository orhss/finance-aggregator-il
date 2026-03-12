# Streamlit → React Migration Plan

## Context

The Fin project has a Streamlit web UI (`streamlit_app/`) that needs to be replaced with a React SPA using Material UI. The motivation: Streamlit's limitations (no real component model, poor mobile UX, no offline/PWA, can't wrap with Capacitor for native mobile). The services layer is already well-abstracted — the React app just needs a REST API in front of it.

**Key decisions**: Monorepo (`api/` + `web/` alongside existing code), FastAPI for REST, TanStack Query for data fetching, gradual migration (Streamlit stays running).

---

## Architecture

```
Financial Institutions ──→ Scrapers ──→ Services ──→ SQLite
                                                       ↑
                                          ┌────────────┤
                                          │            │
                                     FastAPI (new)   Streamlit (existing)
                                       :8000           :8501
                                          │
                                     React SPA (new)
                                       :3000
```

Two new top-level directories: `api/` (FastAPI) and `web/` (React+Vite). Everything else untouched.

---

## Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| API | FastAPI + Pydantic | Auto OpenAPI docs, type safety, async SSE support |
| Frontend | React 19 + TypeScript + Vite | Modern, fast builds, code splitting |
| UI Kit | MUI 6 | Mobile-first, RTL support, theming built-in |
| Data fetching | TanStack Query v5 | Caching, refetching, pagination — no Redux needed |
| Charts | Recharts | React-native (JSX), responsive, SVG (mobile-friendly) |
| Forms | React Hook Form + Zod | Lightweight, runtime validation matching TS types |
| Routing | React Router v7 | Stable, lazy loading |
| Sync progress | SSE (Server-Sent Events) | One-way stream, HTTP-based, Capacitor-compatible |
| Testing | Vitest + RTL + MSW (frontend), pytest (API) |

Client state (theme, privacy) lives in React Context + localStorage. No Redux.

---

## Phase 0: Foundation

### 0.1 FastAPI App (`api/`)

```
api/
  __init__.py
  main.py                    # App factory, CORS, health check
  deps.py                    # DI: get_db, get_current_user, get_service(...)
  auth.py                    # JWT create/verify, secret key management
  routers/
    __init__.py
    auth_router.py           # POST /auth/login, /auth/refresh
    accounts.py              # GET /accounts, /accounts/:id, /accounts/summary
    transactions.py          # GET /transactions, PATCH /transactions/:id
    balances.py              # GET /balances/latest, /balances/history/:id
    analytics.py             # GET /analytics/stats, /monthly, /trends, /categories
    categories.py            # CRUD mappings, merchant patterns, analysis, bulk ops
    tags.py                  # CRUD tags, bulk tag, stats
    budget.py                # GET/PUT budget, GET progress
    rules.py                 # CRUD rules, apply
    sync.py                  # POST /sync/:institution, GET /sync/stream/:id (SSE)
  schemas/
    __init__.py
    common.py                # PaginatedResponse[T], DateRange, ErrorResponse
    auth.py                  # LoginRequest, TokenResponse
    accounts.py              # AccountResponse, AccountSummary
    transactions.py          # TransactionResponse, TransactionFilters, TransactionUpdate
    balances.py              # BalanceResponse
    analytics.py             # StatsResponse, TrendData, CategoryBreakdown
    categories.py            # MappingResponse, MerchantMappingResponse, AnalysisResponse
    tags.py                  # TagResponse, BulkTagRequest
    budget.py                # BudgetResponse, BudgetProgress
    rules.py                 # RuleResponse, RuleCreate, ApplyResult
    sync.py                  # SyncRequest, SyncProgress, SyncHistoryResponse
```

**New Python deps**: `fastapi>=0.115.0`, `uvicorn[standard]>=0.30.0`, `python-jose[cryptography]>=3.3.0`

**Key patterns**:
- `api/deps.py` reuses existing service constructors (e.g., `AnalyticsService(session)`)
- Sync routes run `fin-cli sync` as subprocess, stream stdout via SSE
- SQLite concurrency: use sync `def` handlers (not `async def`) for DB routes
- JWT secret auto-generated in `~/.fin/jwt_secret.key`

### 0.2 React App (`web/`)

```
web/
  package.json
  tsconfig.json
  vite.config.ts
  index.html
  .env.development              # VITE_API_URL=http://localhost:8000
  .env.production               # VITE_API_URL=/api
  src/
    main.tsx                    # Providers: Query, Theme, Auth, Router
    App.tsx                     # Route definitions, lazy loading
    api/
      client.ts                 # Axios instance, JWT interceptor
      accounts.ts               # useAccounts, useAccountSummary
      transactions.ts           # useTransactions, useUpdateTransaction
      analytics.ts              # useStats, useMonthlyTrends, useCategoryBreakdown
      categories.ts             # useCategoryMappings, useMerchantMappings, mutations
      tags.ts                   # useTags, tag/untag mutations
      budget.ts                 # useBudget, useBudgetProgress
      rules.ts                  # useRules, useApplyRules
      sync.ts                   # useSyncHistory, useSyncStream (SSE hook)
      auth.ts                   # useLogin, useLogout
    types/
      account.ts, transaction.ts, balance.ts, analytics.ts,
      category.ts, tag.ts, budget.ts, rule.ts, sync.ts,
      auth.ts, common.ts
    contexts/
      AuthContext.tsx            # JWT storage, auto-refresh, login/logout
      PrivacyContext.tsx         # mask_balances toggle → localStorage
      ThemeContext.tsx           # light/dark mode → localStorage
    hooks/
      useDebounce.ts, useDateRange.ts, useLocalStorage.ts,
      useMediaQuery.ts, useRtl.ts, useCurrency.ts
    theme/
      index.ts                  # createAppTheme(mode) → MUI theme
      palette.ts                # Port from streamlit_app/config/theme.py
      typography.ts, components.ts
    components/
      layout/
        AppShell.tsx            # Top bar + bottom nav (mobile) / sidebar (desktop)
        TopBar.tsx              # Title, sync button, privacy toggle
        BottomNav.tsx           # 5-tab mobile nav
        Sidebar.tsx             # Desktop drawer
        PageHeader.tsx
      common/
        AmountDisplay.tsx       # Currency + privacy masking + pos/neg color
        DateRangePicker.tsx     # Presets + custom range
        EmptyState.tsx          # Icon + message + CTA
        LoadingSkeleton.tsx     # MUI Skeleton screens
        SearchInput.tsx         # Debounced search
        ChipFilter.tsx          # Horizontal scroll chips
        StatusBadge.tsx, CategoryBadge.tsx, RtlText.tsx
        ErrorBoundary.tsx
      charts/
        SpendingDonut.tsx       # Recharts PieChart
        MonthlyTrend.tsx        # BarChart/LineChart
        CategoryBars.tsx        # Horizontal bars
        BalanceHistory.tsx      # Line chart
        CalendarHeatmap.tsx     # Day-level heatmap
        DayOfWeekChart.tsx
      cards/
        MetricCard.tsx, HeroCard.tsx, AccountCard.tsx,
        TransactionItem.tsx, BudgetProgress.tsx, AlertCard.tsx
    pages/
      Dashboard.tsx, Transactions.tsx, Analytics.tsx,
      Accounts.tsx, Organize.tsx, Settings.tsx,
      Login.tsx, NotFound.tsx
    utils/
      format.ts                 # formatCurrency, formatDate, formatNumber
      rtl.ts                    # hasHebrew, fixRtl (port from Python)
      dates.ts                  # Presets, relative time
      constants.ts              # Enums mirroring config/constants.py
```

### 0.3 Docker Multi-Service

Update `docker-compose.yml` to three services:
- `api` — FastAPI on :8000 (shares existing Dockerfile + volume)
- `web` — React nginx on :3000 (new Dockerfile with node build + nginx serve)
- `streamlit` — Existing Streamlit on :8501 (kept during migration)

Add `web/Dockerfile` (multi-stage: node build → nginx static serve).

---

## Phase 1: API Layer

### Implementation order (driven by UI page dependencies):

**Round 1 — Dashboard deps** (~20 endpoints):
- `auth_router.py`: login, refresh
- `accounts.py`: list, detail, summary
- `balances.py`: latest, history
- `transactions.py`: list (paginated + filtered), detail
- `analytics.py`: stats, monthly summary, monthly trends
- `budget.py`: current progress, get/set

**Round 2 — Transactions/Organize** (~25 endpoints):
- `transactions.py`: update (user_category, memo), count
- `tags.py`: CRUD, tag/untag transactions, bulk by merchant, stats
- `categories.py`: mappings CRUD, unmapped, analysis, merchants, bulk assign/apply
- `rules.py`: CRUD, apply with dry-run

**Round 3 — Sync + Deep analytics** (~15 endpoints):
- `sync.py`: start sync, SSE stream, history
- `analytics.py`: category breakdown, category trends, tag breakdown, spending by card

### API testing (`tests/api/`):
- Reuse existing `tests/conftest.py` factories
- FastAPI `TestClient` with in-memory SQLite
- ~50 tests covering auth, CRUD, filters, pagination, error cases

---

## Phase 2: React Core

### Theme
Port colors from `streamlit_app/config/theme.py` (indigo/violet gradient primary). MUI `createTheme()` with light/dark palettes. Financial-specific tokens: `income` (green), `expense` (red).

### RTL Strategy
App stays `ltr` globally. `RtlText` component detects Hebrew via regex and applies `dir="rtl"` per-element. No full RTL mode needed (app is LTR with Hebrew data).

### Layout (Mobile-First)
- **Mobile** (< 768px): `BottomNav` with 5 tabs, top bar with title + actions
- **Desktop** (>= 768px): Permanent `Sidebar` drawer, wider content area
- All pages stack on mobile, use grid on desktop

### Auth Flow
JWT tokens in localStorage (Capacitor-compatible). Axios interceptor attaches token. Auto-refresh before expiry. 401 → attempt refresh → redirect to login.

---

## Phase 3: Pages

### Priority order:

| # | Page | Complexity | Key Components |
|---|------|-----------|----------------|
| 1 | Dashboard | Medium | HeroCard, MetricCard(x3), BudgetProgress, AlertCard, TransactionItem(x7), AccountCard |
| 2 | Transactions | High | TransactionFilters, TransactionTable/CardList, TransactionEditDrawer, BulkActions |
| 3 | Analytics | Medium | SpendingDonut, CategoryBars, MonthlyTrend, DayOfWeekChart, BalanceHistory |
| 4 | Accounts | Medium | AccountsList, SyncPanel, SyncProgress (SSE) |
| 5 | Organize | Medium | CategoriesTab, RulesTab, TagsTab |
| 6 | Settings | Low | Theme toggle, privacy toggle, budget input |

### Mobile adaptations per page:
- **Dashboard**: Stacked cards, 2-col metrics, 5 recent txns (not 7)
- **Transactions**: Card list replaces table, filters collapse to bottom sheet
- **Analytics**: Full-width charts, horizontal scroll tab selector, top 5 only
- **Accounts**: Simplified sync controls, minimal account cards

---

## UX Improvements Over Streamlit

React + MUI unlocks UX patterns that Streamlit simply can't do. These are not just "nice to have" — they fundamentally change how the app feels.

### Interaction Model (No More Full-Page Rerenders)

Streamlit reloads the entire page on every click, filter change, or form submit. React updates only what changed.

| Streamlit Problem | React Solution |
|-------------------|---------------|
| Filter change → full page reload | Instant filter with only table re-render |
| Tag a transaction → reload page | Optimistic update — show change instantly, sync in background |
| Edit category → open separate panel | Inline editing — click cell, type, done |
| Search → wait for server round-trip | Search-as-you-type with 300ms debounce |
| Bulk action → reload to see result | Animated row updates + snackbar confirmation |

**Key components**:
- `TransactionItem.tsx`: inline edit mode with `<ClickAwayListener>`
- `useOptimisticUpdate` hook: wrap TanStack Query mutations for instant feedback
- `SearchInput.tsx`: debounced input with `useDebounce` hook

### Mobile Gestures (Capacitor-Ready)

| Gesture | Action | Component |
|---------|--------|-----------|
| Pull-to-refresh | Reload current page data | `PullToRefresh.tsx` wrapping page content |
| Swipe left on transaction | Quick tag | `SwipeableTransactionItem.tsx` |
| Swipe right on transaction | Quick categorize | Same component, opposite direction |
| Swipe between tabs | Navigate pages | React Router + touch event handler |
| Long press on transaction | Context menu (edit, tag, copy) | MUI `Menu` with touch trigger |
| Bottom sheet drag | Expand/collapse filters | MUI `SwipeableDrawer` anchored bottom |

**Key components**:
- `SwipeableTransactionItem.tsx`: MUI `SwipeableDrawer`-inspired swipe actions
- `BottomSheet.tsx`: reusable bottom sheet for filters, actions, details
- `PullToRefresh.tsx`: pull-down gesture → `queryClient.invalidateQueries()`

### Loading & Feedback

Replace Streamlit's blocking spinners with non-blocking patterns:

| Instead of... | Use... |
|---------------|--------|
| `st.spinner("Loading...")` blocking page | `LoadingSkeleton.tsx` — content-shaped placeholders |
| `st.success("Done!")` pushing content down | `useSnackbar()` — toast notification, auto-dismiss |
| `st.progress(0.5)` full-width bar | `SyncProgress.tsx` — inline progress in the sync card |
| `st.error("Failed")` breaking layout | `ErrorBoundary.tsx` — retry button, keeps layout intact |

**Key components**:
- `LoadingSkeleton.tsx`: Skeleton variants for cards, tables, charts
- Snackbar context with undo support: "Tagged 12 transactions" [Undo]
- `ErrorBoundary.tsx`: catches render errors, shows retry UI

### Data Display Upgrades

| Feature | How | Component |
|---------|-----|-----------|
| Virtual scrolling | Only render visible transaction rows (handles 10k+ rows) | `@tanstack/react-virtual` in `TransactionTable.tsx` |
| Sticky headers | Table headers stay visible while scrolling | CSS `position: sticky` |
| Infinite scroll | Auto-load next page when scrolling near bottom | `useInfiniteQuery` from TanStack Query |
| Column sorting | Click header to sort by date, amount, category | State in `TransactionTable.tsx` + API `sort_by` param |
| Expandable rows | Tap transaction → expand inline to show full detail | MUI `Collapse` component |
| Grouped by date | Date separator headers between transaction groups | Virtual list with sticky group headers |

### Navigation & Power User Features

| Feature | Description | Component |
|---------|-------------|-----------|
| URL filter state | Filters persist in URL params — shareable links, browser back works | `useSearchParams` from React Router |
| Drill-down navigation | Analytics → Click category → Filtered transactions for that category | Router `navigate` with filter params |
| Command palette (Ctrl+K) | Search transactions, navigate pages, trigger actions from keyboard | `CommandPalette.tsx` with `cmdk` library |
| Undo actions | Snackbar with "Undo" after destructive actions (bulk tag, categorize) | `useUndoMutation` hook wrapping TanStack mutations |
| Keyboard shortcuts | `j/k` navigate transactions, `e` edit, `t` tag, `?` show shortcuts | `useHotkeys` hook |

### Onboarding & Empty States

| State | What Shows | Action |
|-------|-----------|--------|
| First visit, no data | Welcome wizard: set budget → connect institution → first sync | `OnboardingWizard.tsx` (stepper) |
| No transactions | Empty state with illustration + "Sync your first card" CTA | `EmptyState.tsx` |
| No categories mapped | Banner: "15 unmapped categories" + "Set up now" button | `AlertCard.tsx` |
| No budget set | Dashboard card: "Set a monthly budget to track spending" | Inline CTA in `BudgetProgress.tsx` |

### Chart Interactions (vs Static Streamlit Plotly)

| Feature | Streamlit | React + Recharts |
|---------|-----------|------------------|
| Hover tooltip | Basic Plotly tooltip | Custom tooltip with transaction breakdown |
| Click category slice | Nothing | Drill down to transactions in that category |
| Time range selection | Separate date picker | Brush/zoom directly on the chart |
| Animation | None | Smooth transitions on data change |
| Responsive | Fixed width | `ResponsiveContainer` fills parent |

### Additional Components for UX Improvements

```
web/src/components/
  interaction/
    SwipeableTransactionItem.tsx  # Swipe left/right for quick actions
    PullToRefresh.tsx             # Pull-down gesture wrapper
    BottomSheet.tsx               # Reusable bottom sheet (filters, details)
    CommandPalette.tsx            # Ctrl+K command palette
    InlineEdit.tsx                # Click-to-edit wrapper component
  feedback/
    SnackbarProvider.tsx          # Global snackbar with undo support
    UndoSnackbar.tsx              # "Action completed" [Undo] toast
```

### Additional Dependencies for UX

```json
{
  "@tanstack/react-virtual": "^3.11.0",  // Virtual scrolling
  "cmdk": "^1.0.0",                       // Command palette
  "framer-motion": "^11.15.0"             // Animations (page transitions, list reorder)
}
```

---

## Phase 4: Capacitor Prep

### Already Capacitor-compatible:
- JWT in localStorage (not cookies)
- No `window.open()`, `alert()`, `confirm()` — use MUI Dialog
- SSE works in WebView
- All formatting through utility functions

### PWA first:
- `vite-plugin-pwa` for service worker + manifest
- Installable on mobile home screen
- Static asset caching

### Future Capacitor additions:
- `@capacitor/preferences` for sensitive storage
- `@capacitor/haptics` for pull-to-refresh
- `@capacitor/push-notifications` for sync alerts
- Deep links: `fin://transactions/:id`

---

## File Size Discipline

Target: **< 150 lines per component file**. Split strategy:
- Pages compose sub-components (Dashboard = HeroCard + MetricCards + Alerts + ...)
- Complex pages split into sections: `TransactionFilters.tsx`, `TransactionTable.tsx`, `TransactionEditDrawer.tsx`
- Hooks extract data logic from components
- Types in separate files from components
- Utils in `utils/` not inline

---

## Testing Strategy

### Frontend (Vitest + React Testing Library + MSW)
- MSW intercepts HTTP at network level — realistic mocking
- Test each component in isolation with mock data
- Test pages with mocked API responses
- Test hooks independently
- ~100 tests target for initial launch

### Backend (pytest)
- `tests/api/` with TestClient + in-memory SQLite
- Reuse existing factory functions
- Test auth, CRUD, filters, pagination, error handling
- ~50 tests

---

## Implementation Sequence (What Can Parallelize)

```
Week 1:  api/main.py + deps + auth ──────────┐
         web/ scaffold + theme + layout ──────┤ (parallel)
                                              │
Week 2:  api/routers (accounts, transactions, ┤
         analytics, budget)                   │
         React: Login + AuthContext + client ──┘

Week 3:  React: Dashboard (all sub-components)
         api/ Round 2 (tags, categories, rules)

Week 4:  React: Transactions page
         React: chart components

Week 5:  React: Analytics + Accounts
         api/routers/sync.py (SSE)

Week 6:  React: Organize + Settings
         Docker multi-service
         PWA setup
```

---

## Risks

| Risk | Mitigation |
|------|-----------|
| SQLite concurrent access | Sync `def` handlers (not async), `check_same_thread=False` |
| SSE through nginx | `proxy_buffering off`, `X-Accel-Buffering: no` |
| Chart perf on mobile | Server-side aggregation, limit data points |
| Hebrew in MUI | `RtlText` wrapper, test with real bank descriptions |

---

## Critical Files to Reference

| File | Why |
|------|-----|
| `services/analytics_service.py` | All query methods → API endpoints |
| `db/models.py` | Source of truth for Pydantic schemas + TS types |
| `streamlit_app/config/theme.py` | Color palettes to port to MUI |
| `services/category_service.py` | Most complex service (27+ methods) |
| `streamlit_app/views/transactions.py` | Most feature-rich page to replicate |
| `streamlit_app/utils/rtl.py` | Hebrew detection logic to port |
| `streamlit_app/utils/formatters.py` | Currency/date formatting to port |
| `config/constants.py` | Enums to mirror in TypeScript |

---

## Verification

After each phase:
1. **API**: `pytest tests/api/ -v` — all endpoints return correct data
2. **React**: `npm test` in `web/` — components render, hooks return data
3. **Integration**: Start all 3 Docker services, verify React app loads dashboard with real data
4. **Mobile**: Chrome DevTools device emulation — responsive layout, touch targets, bottom nav
5. **Feature parity**: Compare Streamlit page vs React page side-by-side for each view
