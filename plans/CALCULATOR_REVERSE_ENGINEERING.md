# Retirement Calculator - Reverse Engineering

Reverse-engineered from 5 simulation CSV exports with varying parameters.

---

## 1. High-Level Architecture

The calculator is a **deterministic monthly simulation** that runs from current age to ~84. It operates as a state machine with two phases:

```
Phase 1: ACCUMULATION (pre-FIRE)
  - Income flows in (salaries + dividends)
  - Expenses + taxes flow out
  - Surplus deposited to portfolio
  - KH and pensions grow via deposits + returns

Phase 2: DRAWDOWN (post-FIRE)
  - Income = dividends only
  - Withdrawals from assets to cover deficit
  - Assets grow via returns, shrink via withdrawals
  - Pensions convert to annuities at age 60
  - Old age pension kicks in at 70/74
```

**FIRE determination**: The calculator binary-searches for the earliest month (up to `base_problem_max_age`) where the full simulation keeps net worth >= 0 for all future months. The `retireRule` parameter (e.g., 99, 90, 80) controls the conservatism of post-FIRE growth rate assumptions on risky assets — higher values mean more conservative assumptions and later FIRE dates. See Section 12 for details.

---

## 2. Input Configuration

### Persons
| Field | Dad | Mom |
|-------|-----|-----|
| DOB | 1988-01-31 | 1992-03-12 |
| Age gap | - | 4.1 years younger |

### Income Streams
| Stream | Amount | Start | End | Rise |
|--------|--------|-------|-----|------|
| Dad salary | ₪23,000/mo | Now | FIRE | 0% |
| Mom salary | ₪16,000/mo | Now | FIRE | 0% |
| Dividends | ₪3,500/mo | 2034-11 | Forever | 5%/yr |

Income values are **net** (after income tax and Bituach Leumi in the pre-FIRE phase). Tax/BL columns are zero pre-FIRE because income is entered as net.

### Expense Categories
| Type | Amount | Period | Notes |
|------|--------|--------|-------|
| Pre-FIRE living | ₪18K/mo (D1) | Now → FIRE | Flat |
| Post-FIRE living | ₪20K/mo | FIRE → Forever | 1% annual rise |
| Mortgage (fixed) | ₪3,792/mo | Now → 2035-11 | Drops first |
| Mortgage (prime) | ₪3,445/mo | Now → 2036-11 | Drops second |
| Annual trip | ₪2,000/mo | Now → FIRE | Stops at FIRE |
| Kid events | ₪100-500K each | Various dates | One-time |
| Kid education | ₪7,000/mo | ~4 year periods | Recurring |

---

## 3. Asset Growth Formulas

### Portfolio (Broker Account)
```
Config: interest=5.0%, fee=0.1%
Observed effective annual rate: ~4.85%
Monthly: portfolio_next = portfolio * (1 + monthly_rate) + deposit
```

The effective rate of ~4.85% is slightly below the expected 4.9% (5.0% - 0.1%). The small discrepancy (~0.05%) may be due to compounding of the fee deduction.

### Keren Hishtalmut (KH 1-5)
```
Formula: net_annual_rate = interest - declared_fee - hidden_fee
Where hidden_fee ≈ 0.65% (consistent across all 5 funds)

KH1: 5.0% - 0.35% - 0.65% = 4.00% → observed 3.93%
KH2: 5.0% - 0.60% - 0.65% = 3.75% → observed 3.71%
KH3: 5.0% - 0.39% - 0.65% = 3.96% → observed 3.98%
KH4: 5.0% - 0.65% - 0.65% = 3.70% → observed 3.63%
KH5: 5.0% - 0.39% - 0.65% = 3.96% → observed 3.89%
```

The ~0.65% "hidden fee" is a consistent internal deduction across all KH funds beyond the declared fee.

### Pension Funds
```
Dad: interest=5.0%, fee1=0.0%, fee2=2.0 → observed ~4.71% effective
Mom: interest=5.0%, fee1=0.13%, fee2=1.3 → observed ~4.66% effective
```

Fee1 is deducted from deposits (Mom: 5000 * 0.13% = ₪6.5/mo). Fee2 relates to balance management fees but the exact formula that produces the ~0.29% effective deduction is internal to the calculator.

### Kaspit (Money Market Fund)
```
Config: interest=1.0%, fee=0.2%
Observed effective: 0.80% annual (exactly interest - fee)
No hidden fee on kaspit (unlike KH)
```

The kaspit fund is designated as `goal` with `portfolio_goal: 120000`. It maintains its balance forever and is never withdrawn - it serves as an emergency/goal reserve.

### Dividend Income
```
Growth: simple interest (not compound)
Formula: base_amount * (1 + annual_rise / 12 * months_elapsed)
3,500 * (1 + 0.05/12 * n)
```

---

## 4. Pre-FIRE Phase

### Monthly Cash Flow
```
income (net) = dad_salary + mom_salary [+ dividends if started]
expenses = living + mortgages + annual_trip
deposit_to_portfolio = income - expenses
```

All surplus goes to the portfolio. There is no allocation to other assets (KH deposits and pension deposits are configured separately and run in parallel).

### Asset Accumulation
Each month:
1. KH funds grow: `value * (1 + net_rate/12) + deposit`
2. Pension funds grow: `value * (1 + effective_rate/12) + deposit * (1 - fee1)`
3. Portfolio grows: `value * (1 + effective_rate/12) + surplus_deposit`
4. Kaspit grows: `value * (1 + 0.008/12)`

---

## 5. FIRE Transition

### What Changes at FIRE
| Parameter | Pre-FIRE | Post-FIRE |
|-----------|----------|-----------|
| Salary income | ₪39K/mo | ₪0 |
| Dividend income | ₪3.5K+ | Continues growing |
| Living expenses | ₪18K | ₪20K + 1%/yr |
| Annual trip | ₪2K/mo | ₪0 |
| KH deposits | Per config | ₪0 |
| Pension deposits | Per config | ₪0 |
| Portfolio deposits | Surplus | ₪0 |
| Portfolio withdrawals | ₪0 | As needed |

### Expense Transitions After FIRE
The expense drops happen in stages as mortgages end:

```
FIRE (Sep 2035): ₪27,237 = ₪20,000 + ₪3,792 + ₪3,445
Nov 2035 (-2mo):  ₪23,462 = ₪20,017 + ₪3,445 (fixed mortgage ends, 1% growth starts)
Nov 2036 (-14mo): ₪20,233 = ₪20,233 (prime mortgage ends)
Then: ₪20K base growing at ~₪17/month (1% annual = ₪200/yr ÷ 12)
```

---

## 6. Post-FIRE Withdrawal Engine

### Monthly Balance Equation
```
inflows = outflows (every single month, exactly balanced)

inflows:  dividend_income + portfolio_withdrawal + KH_withdrawal + pension_income + old_age
outflows: expenses + one_time_goals + portfolio_tax + income_tax + bituach_leumi
```

The checking account stays at exactly ₪1,000 (the configured `balance_goal`). Withdrawals are calculated to exactly cover the deficit.

### Withdrawal Amount Calculation
```
deficit = expenses + goals + tax + BL - income - pension - old_age
withdrawal_needed = deficit / (1 - portfolio_tax_rate)
```

For KH withdrawals (tax-free): withdrawal = deficit directly.

### Withdrawal Priority (Sequential, Not Parallel)
```
1. Portfolio (broker) — first to be drawn, with FIFO capital gains tax
2. KH1 — when portfolio depletes
3. KH2 — when KH1 depletes
4. KH3 — when KH2 depletes
5. KH4, KH5 — when KH3 depletes
```

Each fund is fully depleted before moving to the next. At the transition month, partial withdrawals from two funds may occur (the remainder of the depleting fund + the start of the next).

**Exception**: When pension income kicks in (age 60), the withdrawal rate drops dramatically because pension covers most expenses. At that point, KH withdrawals drop from ~₪30K/mo to ~₪6K/mo.

### `prati_hishtalmut_order: prati`
"Prati" (private) determines the KH withdrawal priority. KH funds are withdrawn in index order (1→2→3→4→5).

---

## 7. Capital Gains Tax (Portfolio Withdrawals)

### Configuration
```
portfolio_fifo_lifo: 'fifo'
portfolioProfitFraction: 25.0  (25% of initial balance is profit)
Tax rate: 25% on realized gains (standard Israeli rate)
```

### FIFO Mechanics
The oldest shares (with the highest profit ratio) are sold first:

| Age | Effective Tax Rate | Notes |
|-----|-------------------|-------|
| 47.7 (FIRE) | 15.78% | Selling oldest, most appreciated shares |
| 49.3 | 14.18% | Profit fraction declining |
| 51.0 | 12.28% | - |
| 54.3 | 9.57% | - |
| 57.7 | 6.94% | Newer deposits with lower profit |
| 59.3 | 5.33% | Portfolio nearly depleted |

The effective tax rate declines over time because FIFO exhausts the high-profit original shares first, leaving newer deposits with lower profit ratios.

### Tax Formula
```
portfolio_tax = withdrawal * effective_profit_fraction * 0.25
```

The effective profit fraction is tracked internally using FIFO lot accounting. The initial cost basis is `initial_balance * (1 - profitFraction/100)` = ₪645,290 for the original ₪860,386 investment.

---

## 8. Pension System

### Accumulation Phase
Both pension funds grow at their effective rate until the person reaches age 60 (configured via `pension_tactics: 60`).

### Conversion to Annuity (Age 60)
At the pension_tactics age, the fund balance is converted to a lifetime annuity:

```
Dad pension converts: age 60.1 (fund balance: ₪4,658,838)
Mom pension converts: age 60.1 (mom's age, when dad is ~64.2)

Conversion factor: ~224-227 months (varies slightly)
Monthly annuity = fund_balance / conversion_factor
Split: 30% mukeret (tax-exempt) + 70% mazkia (taxable)
```

| Person | Fund at Conversion | Monthly Annuity | Mukeret (30%) | Mazkia (70%) |
|--------|-------------------|-----------------|---------------|--------------|
| Dad | ₪4,658,838 | ₪20,760 | ₪6,228 | ₪14,532 |
| Mom | ₪3,168,676 | ₪13,938 | ₪4,181 | ₪9,756 |

The `percentage_mukeret: 30.0` from config exactly matches the observed 30/70 split.

### Post-Conversion
- Fund balance drops to ₪0
- Monthly pension payments begin (fixed, not inflation-adjusted)
- The annuity payments are permanent

---

## 9. Taxes on Pension Income

Income tax and Bituach Leumi are **zero pre-FIRE** (because income is entered as net). They only appear at age 60.1 when pension income begins:

### Tax Rates on Pension (Mazkia Portion Only)
Mukeret (recognized) pension is tax-exempt. Only mazkia (qualifying) is taxed:

| Age Range | Income Tax Rate | Bituach Leumi Rate | Notes |
|-----------|----------------|-------------------|-------|
| 60.1-67 | ~11.3% of mazkia | ~14.4% of mazkia | Full rates |
| 67+ (both pensions) | ~4.4% of mazkia | ~5.2% of mazkia | Elderly exemptions |
| 70+ (with old age) | ~1.7% of mazkia | 0% | BL exempt after 70 |

The rates decrease at milestones (age 67 partial exemptions, age 70 BL exemption) reflecting Israeli tax benefits for elderly.

---

## 10. Old Age Pension (Bituach Leumi)

```
Dad: starts age 70.1, ₪2,300/month (fixed)
Mom: starts age 74.2, ₪2,300/month (fixed)
```

Mom's old age pension starts ~4 years later, reflecting the age gap. The amount is constant (no inflation adjustment in this model).

---

## 11. Net Worth Computation

```
NW = portfolio + KH1 + KH2 + KH3 + KH4 + KH5 + pension_dad + pension_mom + kaspit + checking
```

Verified: computed NW matches actual NW within ±1 across all 553 months (rounding only).

Post-pension-conversion: pension fund balances drop to zero but pension income begins, which is NOT reflected in NW. This causes the NW "crash" at age 60/64 — it's an accounting artifact, not a real loss.

---

## 12. FIRE Determination Logic

### Algorithm
```
mode: retire_asap
max_search_age: 50
method: binary search (or linear scan) over candidate FIRE months

For each candidate FIRE month M:
  1. Simulate entire timeline (M → age 84)
  2. Check: is NW >= 0 for ALL months?
  3. Pick earliest M where this holds
```

### Evidence
| Dataset | retireRule | FIRE Age | Min NW Post-FIRE | Min NW Age |
|---------|-----------|----------|-----------------|------------|
| D1 (baseline) | 99 | 47.70 (Sep 2035) | ₪184,229 | 66.3 |
| D2 (16K pre, 50K apt2) | 99 | 47.10 | ₪180,137 | 64.3 |
| D3 (18K post, 50K apt2) | 99 | 46.80 | ₪162,410 | 64.3 |
| D4 (= D1, rule 90) | 90 | 47.30 (May 2035) | ₪207,855 | 64.3 |
| D5 (= D1, rule 80) | 80 | 47.10 (Feb 2035) | ₪188,009 | 64.3 |

The NW bottleneck is always just above zero, occurring at the largest one-time expense. If FIRE were ~2 months earlier in D1, estimated NW at the bottleneck would go negative (~₪-53K), confirming the constraint is NW >= 0.

### `retireRule` — Post-FIRE Growth Rate Conservatism

The `retireRule` parameter is **actively used** in `retire_asap` mode. It reduces post-FIRE growth rates on **risky assets only** (portfolio, KH), while leaving **safe assets** (pension, kaspit) unchanged.

**Key observations**:
- Pre-FIRE data is **identical** across all retireRule values (same deposits, same growth rates, same accumulation)
- The difference kicks in only at the post-FIRE phase
- Higher retireRule = more conservative = lower post-FIRE growth = later FIRE date

**FIRE timing impact**:
| retireRule | FIRE Age | Delta from 99 |
|-----------|----------|---------------|
| 99 | 47.70 | baseline |
| 90 | 47.30 | 4 months earlier |
| 80 | 47.10 | 7 months earlier |

**Observed post-FIRE growth rates** (approximate, measured from clean months without one-time goals):

| Asset | Pre-FIRE | rule=99 | rule=90 | rule=80 |
|-------|----------|---------|---------|---------|
| Portfolio | ~4.85% | ~3.5% | ~4.0% | ~4.6% |
| KH1 | ~3.93% | ~1.8% | ~2.2% | ~2.7% |
| Pension | ~4.89% | ~4.89% | ~4.89% | ~4.89% |
| Kaspit | 0.80% | 0.80% | 0.80% | 0.80% |

The haircut is larger on KH than on portfolio (KH drops by ~55% at rule=99, portfolio drops by ~28%), which may reflect different internal risk classifications.

**Exact formula unknown**: The relationship between retireRule values and the growth rate reduction does not follow a simple normal distribution z-score model (the implied volatility differs across rule values). The rates also appear to vary slightly over time within a simulation, suggesting a more complex internal model. The observed rates above are averages and should be treated as approximations.

---

## 13. One-Time Expenses (Goals)

Large one-time expenses appear in the `goals` column:

| Age | Date | Amount | Description |
|-----|------|--------|-------------|
| 47.9 | 2035-12 | ₪100K | Bar mitzvah kid 1 + trip |
| 50.3 | 2038-05 | ₪100K | Bar mitzvah kid 2 + trip |
| 52.0 | 2040-01 | ₪120K | Car kid 1 |
| 55.3 | 2043-05 | ₪120K | Car kid 2 |
| 56-60 | 2044-2048 | ₪7K/mo | Education kid 1 |
| 59-63 | 2047-2051 | ₪7K/mo | Education kid 2 |
| 62.0 | 2050-01 | ₪100K | Wedding kid 1 |
| 64.3 | 2052-05 | ₪100K | Wedding kid 2 |
| 64.3 | 2052-05 | ₪500K | Apartment kid 1 |
| 66.3 | 2054-05 | ₪500K/50K | Apartment kid 2 (varies by scenario) |

The kid education expenses (₪7K/mo) appear as recurring expenses, not one-time goals.

---

## 14. Complete State Machine

```
Each month, in order:

1. INCOME DETERMINATION
   - Pre-FIRE: sum all active income streams
   - Post-FIRE: dividend income only (growing at configured rate)

2. EXPENSE DETERMINATION
   - Sum all active expense streams
   - Apply annual growth (1% on post-FIRE base)
   - Add any one-time goals due this month

3. TAX DETERMINATION (post-FIRE only)
   - If pension income active: calculate income tax + BL on mazkia portion
   - Apply age-based exemptions (67+, 70+)

4. WITHDRAWAL CALCULATION (post-FIRE only)
   - deficit = expenses + goals + tax + BL - income - pension - old_age
   - If deficit > 0: withdraw from current priority asset
   - Portfolio withdrawal includes capital gains tax (FIFO)
   - If current asset insufficient: deplete and move to next

5. ASSET GROWTH (all months)
   - Portfolio: value * (1 + effective_rate/12) - withdrawal - tax
   - KH: value * (1 + net_rate/12) + deposit - withdrawal
   - Pension: value * (1 + effective_rate/12) + deposit (or 0 if converted)
   - Kaspit: value * (1 + 0.008/12)

6. PENSION EVENTS (triggered by age)
   - Age 60 (each person): convert fund → annuity
   - Age 70/74: old age pension begins

7. RECORD STATE
   - Record all flows and balances for this month
   - NW = sum of all asset balances
```

---

## 15. Key Behavioral Patterns

### The NW "Crash" at Age 60-67
Net worth drops sharply around ages 60-67. This is caused by:
1. **Age 60**: Dad's pension fund (₪4.7M) converts to annuity → fund balance goes to zero
2. **Age 64**: Mom's pension fund (₪3.2M) converts → fund balance goes to zero
3. **Age 64-66**: Large one-time expenses (weddings, apartments) hit

These are accounting transitions, not real wealth destruction. The pension annuity provides ongoing income equivalent to the fund's value over the person's lifetime.

### The NW Recovery After Age 67
After the bottleneck:
- All one-time expenses are done
- Both pensions are paying out (~₪34K/month combined)
- Old age pension kicks in (₪4,600/month combined)
- Total income (dividends + pensions + old age) exceeds expenses
- Net worth rebuilds, ending at ~₪6.6M at age 84

### Sensitivity to Parameters
From comparing the 5 datasets:

| Change | FIRE Impact | Mechanism |
|--------|------------|-----------|
| Pre-FIRE expenses ₪18K→16K | ~7 months earlier | More monthly deposits |
| Post-FIRE expenses ₪20K→18K | ~10 months earlier | Lower withdrawal rate, compounds over decades |
| Kid apartment ₪500K→50K | ~5 months earlier | Less withdrawal needed at bottleneck |
| retireRule 99→90 | ~4 months earlier | Higher assumed post-FIRE growth on risky assets |
| retireRule 99→80 | ~7 months earlier | Even higher post-FIRE growth assumptions |

Post-FIRE expense reduction has the largest impact because it compounds: ₪2K/mo less withdrawal over 37 years of retirement = ₪888K less spending + all the preserved growth.

Lowering retireRule has a significant impact (~3-4 months per 10-point decrease) because higher post-FIRE growth rates mean assets last longer, allowing earlier retirement. However, lower retireRule values represent more optimistic assumptions about market returns in retirement — a risk/reward tradeoff.

---

## 16. Summary of Formulas

| Component | Formula |
|-----------|---------|
| Portfolio growth | `value * ~4.85%/12` |
| KH growth | `value * (interest - fee - 0.65%) / 12` |
| Pension growth | `value * ~4.7%/12` |
| Kaspit growth | `value * (interest - fee) / 12 = 0.80%/12` |
| Dividend growth | `base * (1 + rise/12 * months)` (simple) |
| Post-FIRE expenses | `base * (1 + rise/12 * months)` (1% annual) |
| Portfolio withdrawal | `deficit / (1 - FIFO_tax_rate)` |
| FIFO tax | `withdrawal * profit_fraction * 25%` (declining over time) |
| Pension annuity | `fund_balance / ~224 months`, split 30% mukeret / 70% mazkia |
| Old age pension | `₪2,300/month per person`, fixed |
| NW | `sum(all asset balances)` |
| retireRule effect | Post-FIRE growth on risky assets reduced (exact formula unknown) |
| FIRE constraint | `min(NW over all months) >= 0` |
