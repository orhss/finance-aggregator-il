# Future Reporting Features - High to Low Priority

## Overview

This document catalogs reporting and analytics features that are **not critical** but would enhance the tool's capabilities. These features are ranked by priority and will be implemented after the critical features (Budget Tracking, Net Worth Tracking, Recurring Detection, Goal Tracking) are complete.

**Status:** Backlog
**Last Updated:** 2025-01-03

---

## 🟠 High Priority Features

These features provide significant value and are commonly found in competing tools.

### 1. Cash Flow Forecasting

**What it does:** Predict future account balances based on recurring transactions and historical patterns.

**User Value:**
- See projected balance 3-6 months ahead
- Plan for upcoming expenses
- Avoid overdrafts
- Make informed spending decisions

**Implementation Approach:**
```
1. Use recurring_transactions table (from critical feature #3)
2. Calculate expected income vs expenses
3. Project balance forward month-by-month
4. Show as line chart with confidence bands
```

**Complexity:** Medium
**Estimated Time:** 3-4 days
**Dependencies:** Recurring transaction detection (critical feature)

**CLI Command:**
```bash
fin-cli reports forecast --months 6
```

**Output:**
- Month-by-month projected balance
- Expected income/expenses per month
- Cash flow surplus/deficit
- Warnings if projected balance goes negative

---

### 2. Investment Performance Tracking

**What it does:** Track investment performance (ROI, profit/loss, benchmarks) for broker accounts.

**User Value:**
- See investment returns over time
- Compare performance to benchmarks (S&P 500)
- Track asset allocation
- Identify profitable investments

**Implementation Approach:**
```
1. Use existing balance history for broker accounts
2. Calculate ROI: (current - initial) / initial
3. Fetch benchmark data (external API or manual entry)
4. Calculate profit/loss trends
5. Show asset allocation breakdown
```

**Complexity:** Medium-High
**Estimated Time:** 4-5 days
**Dependencies:** Net worth tracking (critical feature)

**CLI Commands:**
```bash
fin-cli reports portfolio               # Overall performance
fin-cli reports portfolio --account 5   # Specific broker account
fin-cli reports portfolio --benchmark SPY
```

**Output:**
- Total ROI percentage
- Profit/loss in ILS
- Performance vs benchmark
- Asset allocation pie chart (ASCII)
- Top performing periods

---

### 3. Comparative Analysis (Enhanced)

**What it does:** Compare spending/income across custom time periods (not just month-over-month).

**User Value:**
- This month vs same month last year
- Q1 vs Q2 spending
- Custom period comparisons
- Identify seasonal patterns

**Implementation Approach:**
```
1. Extend existing analytics_service
2. Add methods for period-based queries
3. Calculate deltas and percentages
4. Visualize with sparklines
```

**Complexity:** Low-Medium
**Estimated Time:** 2-3 days
**Dependencies:** None (extends existing reports)

**CLI Commands:**
```bash
fin-cli reports compare --period1 "2024-12" --period2 "2023-12"  # YoY
fin-cli reports compare --period1 "Q1-2025" --period2 "Q4-2024"  # Quarterly
fin-cli reports compare --custom "2024-01-01:2024-06-30" "2024-07-01:2024-12-31"
```

**Output:**
- Side-by-side comparison
- Percentage changes
- Category breakdown differences
- Insights on significant changes

---

### 4. Anomaly Detection & Alerts

**What it does:** Automatically detect unusual spending patterns and alert the user.

**User Value:**
- Catch fraud early
- Notice spending spikes
- Identify duplicate charges
- Get alerted to large transactions

**Implementation Approach:**
```
1. Define thresholds:
   - Spending > 2x average for category
   - Large transaction (> ₪X)
   - Duplicate transaction (same merchant, amount, date)
2. Check on each sync
3. Store anomalies in database
4. Show in report + optionally email
```

**Complexity:** Medium
**Estimated Time:** 3-4 days
**Dependencies:** Recurring detection helps baseline "normal" spending

**CLI Commands:**
```bash
fin-cli reports anomalies               # Show all detected anomalies
fin-cli reports anomalies --threshold 2000  # Only transactions > ₪2000
```

**Output:**
- List of anomalous transactions
- Reason for flagging (spike, duplicate, large)
- Recommended action (review, dispute, ignore)

**Types of Anomalies:**
- Spending spike (2x+ average)
- Large transaction (configurable threshold)
- Duplicate transaction
- Unusual merchant for category
- Transaction on inactive account

---

### 5. Bill Tracking & Payment Reminders

**What it does:** Track upcoming bills and send reminders before due dates.

**User Value:**
- Never miss a payment
- Avoid late fees
- Plan cash flow around bills
- Track bill payment history

**Implementation Approach:**
```
1. Extend recurring_transactions with `due_date` field
2. Add `bill_reminders` table for custom bills
3. Check upcoming bills daily
4. Send reminders (CLI output, email, or push)
```

**Complexity:** Medium
**Estimated Time:** 3-4 days
**Dependencies:** Recurring transaction detection

**Database Schema:**
```sql
CREATE TABLE bill_reminders (
    id INTEGER PRIMARY KEY,
    bill_name TEXT NOT NULL,
    amount REAL,
    due_date DATE NOT NULL,
    frequency TEXT,  -- 'monthly', 'quarterly', 'yearly'
    auto_pay BOOLEAN DEFAULT 0,
    notes TEXT
);
```

**CLI Commands:**
```bash
fin-cli bills upcoming --days 7         # Bills due in next 7 days
fin-cli bills add "Rent" 5000 --day 1   # Add monthly bill (1st of month)
fin-cli bills history --bill-id 5       # Payment history for bill
```

**Output:**
- Upcoming bills calendar
- Amount due
- Days until due
- Auto-pay status
- Payment history

---

## 🟡 Medium Priority Features

These features add polish and convenience but are not essential.

### 6. Merchant-Level Analytics

**What it does:** Analyze spending by merchant (top merchants, trends, loyalty tracking).

**User Value:**
- See where money is actually going
- Track favorite merchants
- Identify subscription changes
- Optimize spending patterns

**Implementation:**
```
1. Group transactions by description (merchant)
2. Calculate totals per merchant
3. Track merchant spending trends
4. Identify merchant category patterns
```

**Complexity:** Low-Medium
**Estimated Time:** 2-3 days

**CLI Commands:**
```bash
fin-cli reports merchants --top 10      # Top 10 merchants by spending
fin-cli reports merchants --merchant "Amazon"  # Specific merchant analysis
```

**Output:**
- Top merchants by total spending
- Spending trends per merchant
- Average transaction amount
- Transaction frequency

---

### 7. Tax Categorization

**What it does:** Tag transactions as tax-deductible and generate tax reports.

**User Value:**
- Simplify tax filing
- Track deductible expenses
- Export for accountant
- Annual tax summary

**Implementation:**
```
1. Add `tax_deductible` boolean to transactions
2. Add `tax_category` field (business, medical, charity, etc.)
3. Create tax report showing deductible breakdown
4. Export to CSV for accountant
```

**Complexity:** Low
**Estimated Time:** 2-3 days

**Database Changes:**
```sql
ALTER TABLE transactions ADD COLUMN tax_deductible BOOLEAN DEFAULT 0;
ALTER TABLE transactions ADD COLUMN tax_category TEXT;
```

**CLI Commands:**
```bash
fin-cli transactions mark-tax 12345 --category business
fin-cli reports tax --year 2024
fin-cli export tax-report --year 2024 --format pdf
```

**Output:**
- Total deductible expenses by category
- List of deductible transactions
- Annual tax summary
- Export for tax software

---

### 8. Savings Rate Tracking

**What it does:** Calculate and track savings rate (income - expenses) / income over time.

**User Value:**
- Measure financial health
- Track savings habits
- Set savings rate goals
- Identify improvement opportunities

**Implementation:**
```
1. Require income tracking (currently only expenses)
2. Calculate: (income - expenses) / income
3. Track monthly savings rate
4. Compare to target rate
```

**Complexity:** Low-Medium
**Estimated Time:** 2-3 days
**Blocker:** Need income tracking (currently only track expenses)

**CLI Commands:**
```bash
fin-cli reports savings-rate --months 12
fin-cli reports savings-rate --target 30  # Compare to 30% target
```

**Output:**
- Monthly savings rate percentage
- Trend over time (sparkline)
- Average savings rate
- Months above/below target

**Prerequisites:**
- Add income tracking (positive transactions need classification)
- Distinguish income from refunds

---

### 9. Custom Dashboards

**What it does:** Let users configure their own dashboard with favorite widgets.

**User Value:**
- Personalized view
- Quick access to important metrics
- Drag-and-drop configuration
- Multiple dashboard presets

**Implementation:**
```
1. Create widget system (modular reports)
2. Store dashboard config per user (JSON)
3. Allow widget arrangement
4. Predefined templates (Simple, Detailed, Investment-focused)
```

**Complexity:** Medium-High
**Estimated Time:** 5-6 days

**CLI Commands:**
```bash
fin-cli dashboard show                  # Default dashboard
fin-cli dashboard configure             # Interactive TUI config
fin-cli dashboard add-widget net-worth  # Add widget
fin-cli dashboard templates             # List templates
```

**Available Widgets:**
- Net worth summary
- Budget status
- Upcoming bills
- Recent transactions
- Spending by category
- Goals progress
- Recurring costs
- Anomalies alert

---

### 10. Multi-Currency Reporting

**What it does:** Show reports in multiple currencies with real-time conversion.

**User Value:**
- For users with foreign accounts
- Travel expense tracking
- Multi-currency portfolios
- Cross-border comparisons

**Implementation:**
```
1. Fetch exchange rates (API or manual)
2. Convert all amounts to target currency
3. Store exchange rates with snapshot
4. Allow report in any currency
```

**Complexity:** Medium
**Estimated Time:** 3-4 days

**CLI Commands:**
```bash
fin-cli reports spending --currency USD
fin-cli reports net-worth --currency EUR
fin-cli config set-default-currency ILS
```

**Output:**
- All amounts converted to target currency
- Exchange rate used (with date)
- Multi-currency breakdown available

---

### 11. Advanced Visualizations

**What it does:** Add richer visualizations beyond ASCII (line charts, pie charts, bars).

**User Value:**
- Better data comprehension
- Professional-looking reports
- Exportable charts
- Interactive exploration

**Implementation Options:**

**Option A: Terminal-based (recommended for CLI)**
- Use `plotext` library for terminal charts
- Render in terminal (no external dependencies)
- Export to PNG/SVG

**Option B: Web-based**
- Generate HTML reports with Chart.js
- Open in browser
- Better interactivity

**Complexity:** Medium
**Estimated Time:** 4-5 days

**Example Charts:**
- Line chart: Net worth over time
- Pie chart: Category breakdown
- Stacked bar: Income vs expenses per month
- Area chart: Cumulative spending

---

## 🟢 Low Priority / Nice-to-Have

These features are polish items or edge cases.

### 12. Scheduled Reports

**What it does:** Automatically generate and email reports on a schedule.

**Implementation:**
```
1. Add cron job or scheduler
2. Generate report (PDF/HTML)
3. Email to user
4. Store in report history
```

**Complexity:** Medium
**Estimated Time:** 3-4 days
**Dependencies:** Email configuration, PDF generation

**CLI Commands:**
```bash
fin-cli reports schedule monthly --email user@example.com
fin-cli reports schedule weekly --type spending
```

---

### 13. Debt Payoff Calculator

**What it does:** Calculate debt payoff schedules and track progress.

**Implementation:**
```
1. Enter debt details (principal, interest, minimum payment)
2. Calculate payoff schedule
3. Compare strategies (snowball vs avalanche)
4. Track actual vs projected payoff
```

**Complexity:** Low-Medium
**Estimated Time:** 2-3 days

**CLI Commands:**
```bash
fin-cli debt add "Credit Card" 10000 --rate 18 --min-payment 500
fin-cli debt payoff-schedule 1
fin-cli debt compare-strategies
```

---

### 14. Receipt Scanning (OCR)

**What it does:** Scan receipts and auto-create transactions.

**Implementation:**
```
1. Use OCR library (tesseract)
2. Parse merchant, amount, date
3. Create transaction
4. Attach receipt image
```

**Complexity:** High
**Estimated Time:** 6-7 days
**Dependencies:** OCR library, image storage

---

### 15. Financial Health Score

**What it does:** Calculate overall financial health score (0-100).

**Implementation:**
```
Factors:
- Savings rate (weight: 25%)
- Budget adherence (weight: 20%)
- Net worth growth (weight: 20%)
- Debt-to-income ratio (weight: 20%)
- Emergency fund coverage (weight: 15%)

Calculate weighted average
```

**Complexity:** Medium
**Estimated Time:** 3-4 days

**CLI Commands:**
```bash
fin-cli reports health-score
```

---

### 16. Social Comparison (Anonymous Benchmarks)

**What it does:** Compare spending to anonymized peer groups (age, income level).

**Implementation:**
```
Requires:
- Opt-in anonymous data sharing
- Server/cloud component
- Peer group calculation
- Privacy safeguards
```

**Complexity:** Very High
**Estimated Time:** 10+ days
**Feasibility:** Low (privacy concerns, infrastructure needed)

---

### 17. Mobile App / Companion

**What it does:** Mobile app for on-the-go access, notifications, quick entry.

**Implementation:**
```
Options:
- React Native mobile app
- Progressive Web App (PWA)
- Telegram/WhatsApp bot

Syncs with CLI database
```

**Complexity:** Very High
**Estimated Time:** Several weeks
**Feasibility:** Low for current scope (CLI tool)

---

## Feature Comparison Matrix

| Feature | Priority | Complexity | Time (days) | User Impact | Dependencies |
|---------|----------|------------|-------------|-------------|--------------|
| Cash Flow Forecast | 🟠 High | Medium | 3-4 | High | Recurring detection |
| Investment Performance | 🟠 High | Medium-High | 4-5 | High | Net worth tracking |
| Comparative Analysis | 🟠 High | Low-Medium | 2-3 | Medium | None |
| Anomaly Detection | 🟠 High | Medium | 3-4 | High | None |
| Bill Tracking | 🟠 High | Medium | 3-4 | Medium-High | Recurring detection |
| Merchant Analytics | 🟡 Medium | Low-Medium | 2-3 | Medium | None |
| Tax Categorization | 🟡 Medium | Low | 2-3 | Medium | None |
| Savings Rate | 🟡 Medium | Low-Medium | 2-3 | Medium | Income tracking |
| Custom Dashboards | 🟡 Medium | Medium-High | 5-6 | High | None |
| Multi-Currency | 🟡 Medium | Medium | 3-4 | Low | None |
| Advanced Charts | 🟡 Medium | Medium | 4-5 | Medium | None |
| Scheduled Reports | 🟢 Low | Medium | 3-4 | Low | Email, PDF |
| Debt Payoff | 🟢 Low | Low-Medium | 2-3 | Low | None |
| Receipt OCR | 🟢 Low | High | 6-7 | Medium | OCR library |
| Health Score | 🟢 Low | Medium | 3-4 | Low | Multiple features |
| Social Comparison | 🟢 Low | Very High | 10+ | Low | Cloud infrastructure |
| Mobile App | 🟢 Low | Very High | Weeks | High | Entire rewrite |

---

## Recommended Implementation Order (Post-Critical Features)

### Phase 1: High Priority Quick Wins (1-2 weeks)
1. **Comparative Analysis** (2-3 days) - Easiest high-priority feature
2. **Anomaly Detection** (3-4 days) - High value, moderate complexity
3. **Cash Flow Forecast** (3-4 days) - Uses existing recurring detection

### Phase 2: High Priority Complex Features (2-3 weeks)
4. **Investment Performance** (4-5 days) - Valuable for broker users
5. **Bill Tracking** (3-4 days) - Completes the recurring suite

### Phase 3: Medium Priority Polish (2-3 weeks)
6. **Merchant Analytics** (2-3 days)
7. **Tax Categorization** (2-3 days)
8. **Advanced Visualizations** (4-5 days)

### Phase 4: Medium Priority Advanced (As needed)
9. **Custom Dashboards** (5-6 days) - If user requests personalization
10. **Savings Rate** (2-3 days) - After adding income tracking
11. **Multi-Currency** (3-4 days) - If international users

### Phase 5: Low Priority (If time/interest)
12. **Scheduled Reports** (3-4 days)
13. **Debt Payoff** (2-3 days)
14. **Health Score** (3-4 days)

**Features NOT Recommended:**
- Receipt OCR (complexity not worth it for CLI tool)
- Social Comparison (privacy/infrastructure concerns)
- Mobile App (out of scope for CLI project)

---

## Success Criteria

For each feature to be considered "complete":
- [ ] Fully implemented with tests
- [ ] CLI commands documented
- [ ] Added to CLAUDE.md
- [ ] Migration scripts (if database changes)
- [ ] User testing confirms value
- [ ] No performance regressions

---

## Notes

- **Prioritization is flexible**: User feedback may reprioritize features
- **Dependencies matter**: Some features unlock others (e.g., recurring detection enables forecasting)
- **Complexity estimates**: Based on current codebase; may vary
- **Time estimates**: Assume experienced developer, may take longer
- **User value**: Prioritize features users actually request

---

## References

- `plans/REPORTING_CRITICAL_FEATURES.md` - Critical features (budget, net worth, recurring, goals)
- Competitor research: Mint, YNAB, Personal Capital/Empower, Monarch Money
- User stories and feature requests (track in GitHub issues)

---

## Feedback Loop

As features are implemented, gather user feedback:
1. Which features do users actually use?
2. Which features are confusing?
3. What new features do users request?
4. What performance issues arise?

**Iterate based on real usage data, not assumptions.**
