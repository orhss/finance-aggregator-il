# Analytics Page Expansion Plan

## Status: ✅ Complete

Agreed scope for expanding `web/src/pages/Analytics.tsx` — 4 items only.

---

## What to Build

### 1. Balance & Portfolio tab (new 4th tab)
- Portfolio composition donut: accounts by type (use `useAccountSummary`)
- Balance over time: `BalanceHistory` chart component (already exists) grouped by institution
- May need to check if a balance history API endpoint exists or needs adding

### 2. MoM comparison in Trends tab
- Two `MetricCard`s side by side: current month total vs last month total + % delta
- Use existing `useMonthlySummary(year, month)` hook for both months
- Simple inline calculation: `((current - previous) / previous * 100)`

### 3. Category Stacked Area in Trends tab
- `useCategoryTrends` hook already exists in `web/src/api/analytics.ts` but is unused
- Add stacked area/line chart for top 5 categories over time
- `CategoryTrends` type already defined in `web/src/types/analytics.ts`
- API endpoint: `GET /analytics/category-trends?months=6&top_n=5`

### 4. Tags tab → proper bar chart
- Replace plain `<Box>` list with `CategoryBars` chart component
- `TagBreakdownItem` has `tag`, `count`, `total_amount`, `percentage`
- `CategoryBars` expects `category` + `total_amount` — needs a simple field-rename adapter

---

## What We're NOT Building
- Calendar heatmap (low value)
- Year-over-Year comparison (not enough historical data yet)
- Tag treemap (visual vanity)
- Untagged transaction stats (already visible in Organize)
- Top Merchants chart (already available via Transactions page filters)
- CSV export (CLI already handles this)
- Category Deep Dive

---

## Files to Touch
- `web/src/pages/Analytics.tsx` — main work
- `api/routers/balances.py` — check if balance history endpoint exists
- `web/src/api/balances.ts` — check if history hook exists
