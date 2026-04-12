"""
Retirement Calculator Data Analysis

Analyzes exported CSV data from Israeli retirement calculator.

Usage:
    # Analyze a single simulation
    python retirement_analysis.py /path/to/export.csv

    # Compare two simulations
    python retirement_analysis.py /path/to/baseline.csv /path/to/scenario.csv

    # Compare with labels
    python retirement_analysis.py baseline.csv scenario.csv --labels "Original" "2K Less Post-FIRE"
"""

import sys
import argparse
from datetime import datetime
from typing import List, Dict, Tuple, Optional


# ============================================================
# Parse the CSV
# ============================================================

def parse_retirement_csv(filepath: str) -> Tuple[dict, List[dict]]:
    """Parse the retirement calculator CSV into config + time series."""
    config = {}
    timeseries = []
    header = None

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line == '""':
                continue

            if ':' in line and not line[0].isdigit():
                key, _, value = line.partition(':')
                key = key.strip()
                value = value.strip()
                config.setdefault(key, [])
                config[key].append(value)
                continue

            if line.startswith(',,'):
                header = ['age', 'timestamp'] + [h.strip() for h in line.split(',')[2:]]
                continue

            if header and line[0].isdigit():
                parts = line.split(',')
                row = {}
                for i, val in enumerate(parts):
                    col = header[i] if i < len(header) else f"col_{i}"
                    try:
                        row[col] = float(val)
                    except ValueError:
                        row[col] = val
                if 'timestamp' in row:
                    row['date'] = datetime.fromtimestamp(row['timestamp'] / 1000)
                timeseries.append(row)

    return config, timeseries


# ============================================================
# Column name mapping (Hebrew -> English keys)
# ============================================================

COL = {
    'age': 'age',
    'income': 'תזרים מנכסים שאינם תיק השקעות',
    'withdraw_portfolio': 'משיכה מתיק תיק בברוקר בארץ',
    'withdraw_kh1': 'משיכה מקרן השתלמות 1',
    'withdraw_kh2': 'משיכה מקרן השתלמות 2',
    'withdraw_kh3': 'משיכה מקרן השתלמות 3',
    'withdraw_kh4': 'משיכה מקרן השתלמות 4',
    'withdraw_kh5': 'משיכה מקרן השתלמות 5',
    'pension_recognized_dad': 'מוכרת אבא',
    'pension_recognized_mom': 'מוכרת אמא',
    'pension_qualifying_dad': 'מזכה אבא',
    'pension_qualifying_mom': 'מזכה אמא',
    'old_age_dad': 'קיצבת זיקנה אבא',
    'old_age_mom': 'קיצבת זיקנה אמא',
    'expenses': 'הוצאות שוטפות',
    'goals': 'יעדים',
    'deposit_portfolio': 'הפקדה לתיק בברוקר בארץ',
    'tax_dad': 'מס הכנסה אבא',
    'tax_mom': 'מס הכנסה אמא',
    'bituach_dad': 'ביטוח לאומי אבא',
    'bituach_mom': 'ביטוח לאומי אמא',
    'portfolio_tax': 'מס על רווחי תיק בברוקר בארץ',
    'net_worth': 'שווי נקי',
    'checking': 'עובר ושב',
    'kh5_value': 'שווי קרן השתלמות 5',
    'kh4_value': 'שווי קרן השתלמות 4',
    'kh3_value': 'שווי קרן השתלמות 3',
    'kh2_value': 'שווי קרן השתלמות 2',
    'kh1_value': 'שווי קרן השתלמות 1',
    'portfolio_value': 'שווי תיק בברוקר בארץ',
    'kaspit_value': 'שווי קרן כספית',
    'pension_dad': 'קרן פנסיה של אבא',
    'pension_mom': 'קרן פנסיה של אמא',
    'checking_level': 'גובה עובר ושב',
}


def get(row: dict, key: str) -> float:
    """Get value by English key name."""
    hebrew = COL.get(key, key)
    return row.get(hebrew, row.get(key, 0.0))


def format_ils(amount: float) -> str:
    """Format as ILS currency."""
    if abs(amount) >= 1_000_000:
        return f"₪{amount/1_000_000:.2f}M"
    elif abs(amount) >= 1_000:
        return f"₪{amount/1_000:.0f}K"
    return f"₪{amount:.0f}"


# ============================================================
# Core Analysis
# ============================================================

def find_fire_point(data: List[dict]) -> Tuple[int, dict]:
    """Find the month where FIRE happens (deposits to portfolio stop)."""
    for i, row in enumerate(data):
        deposit = get(row, 'deposit_portfolio')
        if i > 0 and deposit == 0 and get(data[i-1], 'deposit_portfolio') > 0:
            return i, row
    return -1, {}


def get_kh_total(row: dict) -> float:
    return (get(row, 'kh1_value') + get(row, 'kh2_value') + get(row, 'kh3_value') +
            get(row, 'kh4_value') + get(row, 'kh5_value'))


def get_pension_total(row: dict) -> float:
    return get(row, 'pension_dad') + get(row, 'pension_mom')


def get_pension_income(row: dict) -> float:
    return (get(row, 'pension_recognized_dad') + get(row, 'pension_qualifying_dad') +
            get(row, 'pension_recognized_mom') + get(row, 'pension_qualifying_mom'))


def get_kh_withdrawals(row: dict) -> float:
    return (get(row, 'withdraw_kh1') + get(row, 'withdraw_kh2') + get(row, 'withdraw_kh3') +
            get(row, 'withdraw_kh4') + get(row, 'withdraw_kh5'))


def find_depletion_age(data: List[dict], fire_idx: int, key: str) -> Optional[float]:
    """Find age when an asset depletes to 0."""
    for row in data[fire_idx:]:
        if get(row, key) <= 0:
            return get(row, 'age')
    return None


def find_pension_start(data: List[dict], fire_idx: int) -> Optional[float]:
    """Find age when pension payments begin."""
    for row in data[fire_idx:]:
        if get_pension_income(row) > 0:
            return get(row, 'age')
    return None


def find_old_age_start(data: List[dict], fire_idx: int) -> Optional[float]:
    """Find age when old age pension begins."""
    for row in data[fire_idx:]:
        if get(row, 'old_age_dad') > 0 or get(row, 'old_age_mom') > 0:
            return get(row, 'age')
    return None


def find_min_net_worth(data: List[dict], fire_idx: int) -> Tuple[float, float]:
    """Find minimum net worth post-FIRE. Returns (age, amount)."""
    post = data[fire_idx:]
    min_nw = min(get(r, 'net_worth') for r in post)
    min_age = next(get(r, 'age') for r in post if get(r, 'net_worth') == min_nw)
    return min_age, min_nw


def find_row_at_age(data: List[dict], target_age: float, tolerance: float = 0.15) -> Optional[dict]:
    """Find the data row closest to a target age."""
    for row in data:
        if abs(get(row, 'age') - target_age) < tolerance:
            return row
    return None


# ============================================================
# Single Simulation Analysis
# ============================================================

def analyze_single(filepath: str, label: str = "Simulation") -> None:
    """Full analysis of a single simulation export."""
    config, data = parse_retirement_csv(filepath)
    if not data:
        print("No data found!")
        return

    fire_idx, _ = find_fire_point(data)
    if fire_idx < 0:
        print("Could not find FIRE transition point!")
        return

    pre = data[:fire_idx]
    post = data[fire_idx:]

    start_age = get(data[0], 'age')
    end_age = get(data[-1], 'age')
    fire_age = get(data[fire_idx], 'age')
    fire_date = data[fire_idx]['date']

    # ---- Header ----
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"  {filepath}")
    print(f"{'='*70}")

    # ---- Timeline ----
    print(f"\n  Timeline: Age {start_age:.0f} -> {end_age:.0f} ({end_age - start_age:.0f} years)")
    print(f"  FIRE:     Age {fire_age:.1f} ({fire_date.strftime('%B %Y')})")
    print(f"            {fire_age - start_age:.1f} years to FIRE, {end_age - fire_age:.1f} years in retirement")

    # ---- Net Worth ----
    start_nw = get(data[0], 'net_worth')
    fire_nw = get(data[fire_idx], 'net_worth')
    end_nw = get(data[-1], 'net_worth')
    peak_nw = max(get(r, 'net_worth') for r in data)
    peak_age = next(get(r, 'age') for r in data if get(r, 'net_worth') == peak_nw)
    min_age, min_nw = find_min_net_worth(data, fire_idx)

    print(f"\n  Net Worth:")
    print(f"    Start:   {format_ils(start_nw)}")
    print(f"    FIRE:    {format_ils(fire_nw)}")
    print(f"    Peak:    {format_ils(peak_nw)} (age {peak_age:.0f})")
    print(f"    Lowest:  {format_ils(min_nw)} (age {min_age:.0f})")
    print(f"    End:     {format_ils(end_nw)}")

    # ---- Pre-FIRE Cash Flow ----
    avg_income = sum(get(r, 'income') for r in pre) / len(pre)
    avg_expenses = sum(get(r, 'expenses') for r in pre) / len(pre)
    avg_deposit = sum(get(r, 'deposit_portfolio') for r in pre) / len(pre)
    savings_rate = avg_deposit / avg_income * 100 if avg_income > 0 else 0

    print(f"\n  Pre-FIRE Monthly:")
    print(f"    Income:   {format_ils(avg_income)}")
    print(f"    Expenses: {format_ils(avg_expenses)}")
    print(f"    Savings:  {format_ils(avg_deposit)} ({savings_rate:.0f}% rate)")

    # ---- Post-FIRE Income Sources ----
    avg_dividends = sum(get(r, 'income') for r in post) / len(post)
    avg_withdraw = sum(get(r, 'withdraw_portfolio') for r in post) / len(post)
    avg_kh = sum(get_kh_withdrawals(r) for r in post) / len(post)
    avg_pension = sum(get_pension_income(r) for r in post) / len(post)
    avg_old_age = sum(get(r, 'old_age_dad') + get(r, 'old_age_mom') for r in post) / len(post)
    avg_exp_post = sum(get(r, 'expenses') for r in post) / len(post)

    print(f"\n  Post-FIRE Monthly Averages:")
    print(f"    Dividends:     {format_ils(avg_dividends)}")
    print(f"    Portfolio:     {format_ils(avg_withdraw)} (withdrawals)")
    print(f"    KH:            {format_ils(avg_kh)} (withdrawals)")
    print(f"    Pension:       {format_ils(avg_pension)}")
    print(f"    Old Age:       {format_ils(avg_old_age)}")
    print(f"    Expenses:      {format_ils(avg_exp_post)}")

    # ---- One-Time Expenses ----
    goals = [(get(r, 'age'), r['date'], get(r, 'goals')) for r in data if get(r, 'goals') > 0]
    if goals:
        total_goals = sum(g[2] for g in goals)
        print(f"\n  One-Time Expenses ({format_ils(total_goals)} total):")
        for age, dt, amount in goals:
            print(f"    Age {age:.0f} ({dt.strftime('%Y-%m')}): {format_ils(amount)}")

    # ---- Asset Composition at Milestones ----
    print(f"\n  Asset Composition:")
    print(f"  {'':>10} {'Portfolio':>11} {'KH':>11} {'Pensions':>11} {'Net Worth':>11}")
    print(f"  {'-'*56}")

    for label_m, age_target in [("Start", start_age), ("FIRE", fire_age),
                                 ("Age 60", 60), ("Age 67", 67), ("End", end_age)]:
        row = find_row_at_age(data, age_target)
        if row:
            print(f"  {label_m:>10} {format_ils(get(row, 'portfolio_value')):>11} "
                  f"{format_ils(get_kh_total(row)):>11} "
                  f"{format_ils(get_pension_total(row)):>11} "
                  f"{format_ils(get(row, 'net_worth')):>11}")

    # ---- Key Dates ----
    portfolio_depletion = find_depletion_age(data, fire_idx, 'portfolio_value')
    pension_start = find_pension_start(data, fire_idx)
    old_age_start = find_old_age_start(data, fire_idx)

    print(f"\n  Key Dates:")
    print(f"    FIRE:                 Age {fire_age:.1f}")
    if portfolio_depletion:
        print(f"    Portfolio depletes:    Age {portfolio_depletion:.1f}")
    else:
        print(f"    Portfolio depletes:    Never")
    if pension_start:
        print(f"    Pension starts:       Age {pension_start:.1f}")
        gap = pension_start - fire_age
        print(f"    FIRE-to-Pension gap:  {gap:.1f} years")
    if old_age_start:
        print(f"    Old age pension:      Age {old_age_start:.1f}")

    # ---- Risk ----
    print(f"\n  Risk:")
    print(f"    Lowest post-FIRE NW:  {format_ils(min_nw)} at age {min_age:.0f}")
    if fire_nw > 0:
        print(f"    Drawdown from FIRE:   {(1 - min_nw/fire_nw)*100:.0f}%")


# ============================================================
# Two-Simulation Comparison
# ============================================================

def compare_simulations(file_a: str, file_b: str,
                        label_a: str = "Baseline", label_b: str = "Scenario") -> None:
    """Compare two simulation exports side by side."""
    _, data_a = parse_retirement_csv(file_a)
    _, data_b = parse_retirement_csv(file_b)

    fire_idx_a, _ = find_fire_point(data_a)
    fire_idx_b, _ = find_fire_point(data_b)

    if fire_idx_a < 0 or fire_idx_b < 0:
        print("Could not find FIRE transition in one or both files.")
        return

    fire_age_a = get(data_a[fire_idx_a], 'age')
    fire_age_b = get(data_b[fire_idx_b], 'age')
    fire_date_a = data_a[fire_idx_a]['date']
    fire_date_b = data_b[fire_idx_b]['date']

    months_diff = fire_idx_a - fire_idx_b

    print(f"\n{'='*70}")
    print(f"  COMPARISON: {label_a} vs {label_b}")
    print(f"{'='*70}")

    # ---- FIRE timing ----
    print(f"\n  FIRE Age:")
    print(f"    {label_a + ':':20} {fire_age_a:.1f} ({fire_date_a.strftime('%B %Y')})")
    print(f"    {label_b + ':':20} {fire_age_b:.1f} ({fire_date_b.strftime('%B %Y')})")
    direction = "earlier" if months_diff > 0 else "later"
    print(f"    {'Delta:':20} {abs(months_diff)} months {direction}")

    # ---- Config diffs ----
    # Parse key expense/income params from the data
    pre_exp_a = sum(get(r, 'expenses') for r in data_a[:fire_idx_a]) / fire_idx_a
    pre_exp_b = sum(get(r, 'expenses') for r in data_b[:fire_idx_b]) / fire_idx_b
    post_exp_a = sum(get(r, 'expenses') for r in data_a[fire_idx_a:]) / len(data_a[fire_idx_a:])
    post_exp_b = sum(get(r, 'expenses') for r in data_b[fire_idx_b:]) / len(data_b[fire_idx_b:])
    savings_a = sum(get(r, 'deposit_portfolio') for r in data_a[:fire_idx_a]) / fire_idx_a
    savings_b = sum(get(r, 'deposit_portfolio') for r in data_b[:fire_idx_b]) / fire_idx_b
    goals_a = sum(get(r, 'goals') for r in data_a)
    goals_b = sum(get(r, 'goals') for r in data_b)

    print(f"\n  Parameter Differences:")
    print(f"  {'':25} {label_a:>14} {label_b:>14} {'Delta':>14}")
    print(f"  {'-'*67}")
    _diff_row("Pre-FIRE expenses/mo", pre_exp_a, pre_exp_b)
    _diff_row("Post-FIRE expenses/mo", post_exp_a, post_exp_b)
    _diff_row("Savings/mo", savings_a, savings_b)
    _diff_row("Total one-time goals", goals_a, goals_b)

    # ---- Net Worth Timeline ----
    print(f"\n  Net Worth Over Time:")
    print(f"  {'Age':>6} {label_a:>14} {label_b:>14} {'Delta':>14}")
    print(f"  {'-'*52}")

    target_ages = sorted(set([
        round(get(data_a[0], 'age')),
        45, round(fire_age_b), round(fire_age_a),
        50, 55, 60, 65, 67, 70, 75, 80,
        round(get(data_a[-1], 'age'))
    ]))

    seen = set()
    for target in target_ages:
        if target in seen:
            continue
        row_a = find_row_at_age(data_a, target)
        row_b = find_row_at_age(data_b, target)
        if row_a and row_b:
            seen.add(target)
            nw_a = get(row_a, 'net_worth')
            nw_b = get(row_b, 'net_worth')
            delta = nw_b - nw_a
            sign = "+" if delta >= 0 else ""
            print(f"  {target:>6} {format_ils(nw_a):>14} {format_ils(nw_b):>14} {sign + format_ils(delta):>14}")

    # ---- Danger zone ----
    min_age_a, min_nw_a = find_min_net_worth(data_a, fire_idx_a)
    min_age_b, min_nw_b = find_min_net_worth(data_b, fire_idx_b)

    print(f"\n  Danger Zone (lowest post-FIRE NW):")
    print(f"    {label_a + ':':20} {format_ils(min_nw_a)} at age {min_age_a:.0f}")
    print(f"    {label_b + ':':20} {format_ils(min_nw_b)} at age {min_age_b:.0f}")

    # ---- Portfolio depletion ----
    depl_a = find_depletion_age(data_a, fire_idx_a, 'portfolio_value')
    depl_b = find_depletion_age(data_b, fire_idx_b, 'portfolio_value')

    print(f"\n  Portfolio Depletion:")
    print(f"    {label_a + ':':20} {'Age ' + f'{depl_a:.1f}' if depl_a else 'Never'}")
    print(f"    {label_b + ':':20} {'Age ' + f'{depl_b:.1f}' if depl_b else 'Never'}")

    # ---- End state ----
    end_nw_a = get(data_a[-1], 'net_worth')
    end_nw_b = get(data_b[-1], 'net_worth')
    delta_end = end_nw_b - end_nw_a

    print(f"\n  End State (age ~{get(data_a[-1], 'age'):.0f}):")
    print(f"    {label_a + ':':20} {format_ils(end_nw_a)}")
    print(f"    {label_b + ':':20} {format_ils(end_nw_b)} ({'+' if delta_end >= 0 else ''}{format_ils(delta_end)})")

    # ---- Cumulative expenses ----
    total_exp_a = sum(get(r, 'expenses') for r in data_a[fire_idx_a:])
    total_exp_b = sum(get(r, 'expenses') for r in data_b[fire_idx_b:])
    if abs(total_exp_a - total_exp_b) > 10000:
        print(f"\n  Cumulative Post-FIRE Expenses:")
        print(f"    {label_a + ':':20} {format_ils(total_exp_a)}")
        print(f"    {label_b + ':':20} {format_ils(total_exp_b)} (save {format_ils(total_exp_a - total_exp_b)})")


def _diff_row(label: str, val_a: float, val_b: float) -> None:
    """Print a comparison row, only if values differ."""
    if abs(val_a - val_b) > 100:
        delta = val_b - val_a
        sign = "+" if delta >= 0 else ""
        print(f"  {label:25} {format_ils(val_a):>14} {format_ils(val_b):>14} {sign + format_ils(delta):>14}")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Analyze retirement calculator CSV exports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python retirement_analysis.py simulation.csv
  python retirement_analysis.py baseline.csv scenario.csv
  python retirement_analysis.py baseline.csv scenario.csv --labels "Original" "2K Less"
        """
    )
    parser.add_argument('files', nargs='+', help='CSV file(s) to analyze (1 or 2)')
    parser.add_argument('--labels', nargs=2, default=None,
                        help='Labels for comparison (e.g. --labels "Original" "Scenario")')

    args = parser.parse_args()

    if len(args.files) == 1:
        analyze_single(args.files[0])
    elif len(args.files) == 2:
        labels = args.labels or ["Baseline", "Scenario"]
        # Run individual analysis for each
        analyze_single(args.files[0], label=labels[0])
        analyze_single(args.files[1], label=labels[1])
        # Then comparison
        compare_simulations(args.files[0], args.files[1], labels[0], labels[1])
    else:
        parser.error("Provide 1 or 2 CSV files")


if __name__ == "__main__":
    main()
