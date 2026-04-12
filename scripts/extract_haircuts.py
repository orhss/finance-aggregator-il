"""
Extract post-FIRE growth rates from retirement calculator CSV exports
to determine the correct haircut values for different retireRule settings.

Haircut = pre_fire_annual_rate - post_fire_annual_rate

This tells us how much the external calculator reduces growth rates post-FIRE.
"""
import sys
from datetime import datetime
from typing import List, Dict, Tuple, Optional


# ============================================================
# Reuse the CSV parser from retirement_analysis.py
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
    'deposit_portfolio': 'הפקדה לתיק בברוקר בארץ',
    'portfolio_tax': 'מס על רווחי תיק בברוקר בארץ',
    'portfolio_value': 'שווי תיק בברוקר בארץ',
    'kaspit_value': 'שווי קרן כספית',
    'kh5_value': 'שווי קרן השתלמות 5',
    'kh4_value': 'שווי קרן השתלמות 4',
    'kh3_value': 'שווי קרן השתלמות 3',
    'kh2_value': 'שווי קרן השתלמות 2',
    'kh1_value': 'שווי קרן השתלמות 1',
    'pension_dad': 'קרן פנסיה של אבא',
    'pension_mom': 'קרן פנסיה של אמא',
}


def get(row: dict, key: str) -> float:
    hebrew = COL.get(key, key)
    return row.get(hebrew, row.get(key, 0.0))


def parse_csv(filepath: str) -> Tuple[float, List[dict]]:
    """Parse CSV, return (retireRule, data_rows)."""
    retire_rule = None
    data = []
    header = None

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line == '""':
                continue

            if line.startswith('retireRule:'):
                retire_rule = float(line.split(':')[1].strip())
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
                data.append(row)

    return retire_rule, data


def find_fire_idx(data: List[dict]) -> int:
    """Find FIRE month: where deposit_portfolio drops to 0, OR where withdrawals begin."""
    # Strategy 1: deposit stops
    for i, row in enumerate(data):
        if i > 0 and get(row, 'deposit_portfolio') == 0 and get(data[i-1], 'deposit_portfolio') > 0:
            return i

    # Strategy 2: any withdrawal starts
    for i, row in enumerate(data):
        total_wd = (get(row, 'withdraw_portfolio') + get(row, 'withdraw_kh1') +
                    get(row, 'withdraw_kh2') + get(row, 'withdraw_kh3') +
                    get(row, 'withdraw_kh4') + get(row, 'withdraw_kh5'))
        if total_wd > 0:
            return i

    return -1


def monthly_to_annual(r: float) -> float:
    return (1 + r) ** 12 - 1


def extract_rates(data: List[dict], start_idx: int, num_months: int = 12) -> dict:
    """
    Extract monthly growth rates for portfolio and KH funds.

    For portfolio:
      next_val = curr_val * (1+r) - withdrawal + deposit - tax
      r = (next_val + withdrawal - deposit + tax) / curr_val - 1

    For KH funds:
      next_val = curr_val * (1+r) - withdrawal   (no deposits post-FIRE)
      r = (next_val + withdrawal) / curr_val - 1
      Pre-FIRE with deposits: next_val = (curr_val + deposit) * (1+r) - withdrawal
      But deposits are folded into value, so for funds with no deposits (KH1, KH4, KH5 with deposit=0):
        r = (next_val + withdrawal) / curr_val - 1  (same formula works)
      For funds WITH deposits pre-FIRE (KH2, KH3 with deposit=1571):
        next_val = curr_val * (1+r) + deposit * (1+r) - withdrawal  approximately
        But we don't know exactly when the deposit happens in the month.
        Better to use funds with deposit=0 for pre-FIRE rate extraction.
    """
    results = {
        'portfolio': [],
        'kh1': [], 'kh2': [], 'kh3': [], 'kh4': [], 'kh5': [],
        'pension_d': [], 'pension_m': [],
    }

    end_idx = min(start_idx + num_months, len(data) - 1)

    for i in range(start_idx, end_idx):
        curr = data[i]
        nxt = data[i + 1]

        # Portfolio
        v1 = get(curr, 'portfolio_value')
        v2 = get(nxt, 'portfolio_value')
        wd = get(nxt, 'withdraw_portfolio')
        dep = get(nxt, 'deposit_portfolio')
        tax = get(nxt, 'portfolio_tax')
        if v1 > 0:
            r = (v2 + wd - dep + tax) / v1 - 1
            results['portfolio'].append(r)

        # KH funds
        for kh in ['kh1', 'kh2', 'kh3', 'kh4', 'kh5']:
            v1 = get(curr, f'{kh}_value')
            v2 = get(nxt, f'{kh}_value')
            wd = get(nxt, f'withdraw_{kh}')
            if v1 > 0:
                r = (v2 + wd) / v1 - 1
                results[kh].append(r)

        # Pensions (no withdrawals in early post-FIRE)
        for p_key, r_key in [('pension_dad', 'pension_d'), ('pension_mom', 'pension_m')]:
            v1 = get(curr, p_key)
            v2 = get(nxt, p_key)
            if v1 > 0 and v2 > 0:
                results[r_key].append(v2 / v1 - 1)

    return results


def avg_rate(rates: list) -> Optional[float]:
    if not rates:
        return None
    return sum(rates) / len(rates)


def analyze_file(filepath: str, expected_rule: float) -> dict:
    """Analyze one CSV file and return haircut results."""
    retire_rule, data = parse_csv(filepath)

    if retire_rule != expected_rule:
        print(f"  WARNING: Expected retireRule={expected_rule}, got {retire_rule}")

    fire_idx = find_fire_idx(data)
    if fire_idx < 0:
        print(f"  ERROR: Could not find FIRE transition!")
        return {}

    fire_age = get(data[fire_idx], 'age')
    fire_date = data[fire_idx]['date']

    print(f"\n{'='*80}")
    print(f"retireRule = {retire_rule:.0f}")
    print(f"File: {filepath}")
    print(f"FIRE: age {fire_age:.1f}, {fire_date.strftime('%Y-%m')}, row index {fire_idx}")

    # ---- Pre-FIRE rates (6 months before FIRE, using no-deposit funds) ----
    pre_start = max(0, fire_idx - 7)
    pre_rates = extract_rates(data, pre_start, fire_idx - pre_start - 1)

    # ---- Post-FIRE rates (first 12 months) ----
    post_rates = extract_rates(data, fire_idx, 12)

    # ---- Show raw per-month post-FIRE data for debugging ----
    print(f"\n  Post-FIRE row-by-row (first 6 months):")
    print(f"  {'Idx':>4} {'Age':>5} {'PortVal':>12} {'PortWD':>10} {'PortDep':>10} {'PortTax':>10} "
          f"{'KH1Val':>10} {'KH1WD':>8} {'KH5Val':>10} {'KH5WD':>8}")
    for offset in range(min(7, len(data) - fire_idx)):
        idx = fire_idx + offset
        r = data[idx]
        print(f"  {idx:>4} {get(r,'age'):>5.1f} {get(r,'portfolio_value'):>12.0f} "
              f"{get(r,'withdraw_portfolio'):>10.0f} {get(r,'deposit_portfolio'):>10.0f} "
              f"{get(r,'portfolio_tax'):>10.0f} "
              f"{get(r,'kh1_value'):>10.0f} {get(r,'withdraw_kh1'):>8.0f} "
              f"{get(r,'kh5_value'):>10.0f} {get(r,'withdraw_kh5'):>8.0f}")

    # ---- Compute averages ----
    print(f"\n  Monthly Rates:")
    print(f"  {'Fund':>12} {'Pre-FIRE mo%':>14} {'Post-FIRE mo%':>14} {'Pre Annual%':>12} {'Post Annual%':>12} {'Haircut%':>10}")
    print(f"  {'-'*76}")

    result = {
        'retire_rule': retire_rule,
        'fire_age': fire_age,
        'fire_date': fire_date.strftime('%Y-%m'),
    }

    for fund_key, fund_label in [
        ('portfolio', 'Portfolio'),
        ('kh1', 'KH1 (fee=0.35)'),
        ('kh2', 'KH2 (fee=0.60)'),
        ('kh3', 'KH3 (fee=0.39)'),
        ('kh4', 'KH4 (fee=0.65)'),
        ('kh5', 'KH5 (fee=0.39)'),
    ]:
        pre_avg = avg_rate(pre_rates.get(fund_key, []))
        post_avg = avg_rate(post_rates.get(fund_key, []))

        if pre_avg is not None and post_avg is not None:
            pre_ann = monthly_to_annual(pre_avg)
            post_ann = monthly_to_annual(post_avg)
            haircut = (pre_ann - post_ann) * 100
            print(f"  {fund_label:>12} {pre_avg*100:>13.6f}% {post_avg*100:>13.6f}% "
                  f"{pre_ann*100:>11.4f}% {post_ann*100:>11.4f}% {haircut:>9.4f}%")
            result[f'{fund_key}_pre_monthly'] = pre_avg
            result[f'{fund_key}_post_monthly'] = post_avg
            result[f'{fund_key}_pre_annual'] = pre_ann
            result[f'{fund_key}_post_annual'] = post_ann
            result[f'{fund_key}_haircut'] = haircut
        elif post_avg is not None:
            post_ann = monthly_to_annual(post_avg)
            print(f"  {fund_label:>12} {'N/A':>14} {post_avg*100:>13.6f}% "
                  f"{'N/A':>12} {post_ann*100:>11.4f}% {'N/A':>10}")
        else:
            print(f"  {fund_label:>12} {'N/A':>14} {'N/A':>14}")

    # Pensions
    for p_key, p_label in [('pension_d', 'Pension Dad'), ('pension_m', 'Pension Mom')]:
        pre_avg = avg_rate(pre_rates.get(p_key, []))
        post_avg = avg_rate(post_rates.get(p_key, []))
        if pre_avg is not None and post_avg is not None:
            pre_ann = monthly_to_annual(pre_avg)
            post_ann = monthly_to_annual(post_avg)
            haircut = (pre_ann - post_ann) * 100
            print(f"  {p_label:>12} {pre_avg*100:>13.6f}% {post_avg*100:>13.6f}% "
                  f"{pre_ann*100:>11.4f}% {post_ann*100:>11.4f}% {haircut:>9.4f}%")

    return result


def main():
    files = [
        ("/Users/orhasson/Downloads/retire_calculator (8).csv", 99),
        ("/Users/orhasson/Downloads/retire_calculator (9).csv", 95),
        ("/Users/orhasson/Downloads/retire_calculator (10).csv", 90),
        ("/Users/orhasson/Downloads/retire_calculator (11).csv", 85),
    ]

    all_results = []
    for filepath, expected_rule in files:
        try:
            result = analyze_file(filepath, expected_rule)
            if result:
                all_results.append(result)
        except Exception as e:
            print(f"\nERROR: {filepath}: {e}")
            import traceback
            traceback.print_exc()

    # ============================================================
    # SUMMARY
    # ============================================================
    print(f"\n\n{'='*100}")
    print("FINAL SUMMARY: HAIRCUT VALUES BY retireRule")
    print(f"{'='*100}")

    # Theoretical pre-FIRE rates
    print(f"\nTheoretical pre-FIRE rates:")
    print(f"  Portfolio: interest=5.0%, fee=0.1% -> net annual = 4.9000%")
    port_theoretical_monthly = (1.049) ** (1/12) - 1
    print(f"             compound monthly = {port_theoretical_monthly*100:.6f}%")

    kh_configs = [
        ("KH1", 0.35, 0.65, 0),     # no deposit
        ("KH2", 0.60, 0.65, 1571),   # has deposit
        ("KH3", 0.39, 0.65, 1571),   # has deposit
        ("KH4", 0.65, 0.65, 0),      # no deposit
        ("KH5", 0.39, 0.65, 0),      # no deposit
    ]
    for name, fee, hidden_fee, deposit in kh_configs:
        net_annual = 5.0 - fee - hidden_fee
        monthly = (1 + net_annual/100) ** (1/12) - 1
        dep_note = f" (deposit={deposit})" if deposit > 0 else " (no deposit - clean rate)"
        print(f"  {name}: interest=5.0%, fee={fee}%, hidden_fee={hidden_fee}% -> "
              f"net annual = {net_annual:.2f}%, monthly = {monthly*100:.6f}%{dep_note}")

    # Summary table
    print(f"\n{'Portfolio Haircut Summary':}")
    print(f"{'retireRule':>10} | {'FIRE Age':>8} | {'Pre Annual%':>12} | {'Post Annual%':>12} | {'Haircut%':>10}")
    print(f"{'-'*60}")
    for r in all_results:
        if 'portfolio_haircut' in r:
            print(f"{r['retire_rule']:>10.0f} | {r['fire_age']:>8.1f} | "
                  f"{r['portfolio_pre_annual']*100:>11.4f}% | {r['portfolio_post_annual']*100:>11.4f}% | "
                  f"{r['portfolio_haircut']:>9.4f}%")

    # KH summary - use KH1 and KH5 (no deposits, cleaner rates)
    for kh_key, kh_label in [('kh1', 'KH1 (fee=0.35, no deposit)'),
                              ('kh5', 'KH5 (fee=0.39, no deposit)'),
                              ('kh4', 'KH4 (fee=0.65, no deposit)')]:
        print(f"\n{kh_label} Haircut Summary:")
        print(f"{'retireRule':>10} | {'Pre Annual%':>12} | {'Post Annual%':>12} | {'Haircut%':>10}")
        print(f"{'-'*50}")
        for r in all_results:
            key_pre = f'{kh_key}_pre_annual'
            key_post = f'{kh_key}_post_annual'
            key_hair = f'{kh_key}_haircut'
            if key_hair in r:
                print(f"{r['retire_rule']:>10.0f} | {r[key_pre]*100:>11.4f}% | "
                      f"{r[key_post]*100:>11.4f}% | {r[key_hair]:>9.4f}%")

    # Final mapping
    print(f"\n\n{'='*60}")
    print("RETIRE RULE -> HAIRCUT MAPPING (for use in calculator)")
    print(f"{'='*60}")
    for r in all_results:
        rule = r['retire_rule']
        port_hair = r.get('portfolio_haircut')
        # For KH, prefer KH1 (no deposit, clean), fall back to KH5, KH4
        kh_hair = r.get('kh1_haircut') or r.get('kh5_haircut') or r.get('kh4_haircut')

        print(f"\n  retireRule = {rule:.0f}:")
        if port_hair is not None:
            print(f"    portfolio_haircut = {port_hair:.4f}%")
        if kh_hair is not None:
            print(f"    kh_haircut        = {kh_hair:.4f}%")

        # Also show: are portfolio and KH haircuts the same?
        if port_hair is not None and kh_hair is not None:
            if abs(port_hair - kh_hair) < 0.01:
                print(f"    -> Portfolio and KH haircuts are IDENTICAL ({port_hair:.4f}%)")
            else:
                print(f"    -> Portfolio and KH haircuts DIFFER by {abs(port_hair - kh_hair):.4f}%")


if __name__ == '__main__':
    main()
