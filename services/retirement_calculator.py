"""
Israeli FIRE Retirement Calculator

Deterministic monthly simulation for Israeli FIRE planning.
Supports portfolios, keren hishtalmut, pensions, and kaspit funds.
Implements Israeli tax brackets, pension annuity conversion, and FIFO capital gains.

Usage:
    python retirement_calculator.py config.json
    python retirement_calculator.py config.json --csv output.csv
    python retirement_calculator.py config.json --csv output.csv --verbose
"""

import argparse
import csv
import json

import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple


# ============================================================
# Constants
# ============================================================

STATUTORY_RETIREMENT_AGE_M = 67
STATUTORY_RETIREMENT_AGE_F = 65
OLD_AGE_PENSION_AMOUNT = 2300  # NIS/month per person
OLD_AGE_START_AGE = 70  # Both genders in this model
DEFAULT_END_AGE = 84
DEFAULT_CASH_BUFFER = 1000

# Capital gains tax rate on portfolio profits
CAPITAL_GAINS_TAX_RATE = 0.25

# KH hidden fee (consistent across all funds per reverse engineering)
KH_HIDDEN_FEE = 0.65  # percent

# retireRule haircut tables (piecewise linear, observed data points)
# Maps retireRule -> haircut in percentage points subtracted from pre-FIRE rate
PORTFOLIO_HAIRCUTS = {80: 1.94, 85: 2.17, 90: 2.44, 95: 2.69, 99: 2.87}
KH_HAIRCUTS = {80: 1.26, 85: 1.51, 90: 1.77, 95: 2.02, 99: 2.20}

# Pension conversion factors (months) by age
PENSION_CONVERSION_FACTORS = {60: 228, 65: 210, 67: 199}


# ============================================================
# Israeli Tax Brackets (2024)
# ============================================================

# Annual income brackets and marginal rates
TAX_BRACKETS = [
    (84_000, 0.10),
    (120_000, 0.14),
    (193_000, 0.20),
    (269_000, 0.31),
    (560_000, 0.35),
    (float('inf'), 0.47),
]

# Annual Bituach Leumi brackets (simplified, for pension income)
# Below retirement age: ~12% on first ~70K, ~7% above
# At/above retirement age: reduced rates, exempt at 70+
BL_RATE_BELOW_RETIREMENT = 0.12
BL_RATE_ABOVE_RETIREMENT = 0.052
BL_EXEMPT_AGE = 70

# Pension income tax credit for retirees (monthly, approximate)
# This credit reduces effective tax rate for pension income at retirement age
# Calibrated to produce ~10.9% effective rate on ~₪14.5K mazka (observed)
PENSION_TAX_CREDIT_MONTHLY = 700  # NIS/month, approximate


# ============================================================
# Data Classes
# ============================================================

@dataclass
class Person:
    name: str
    dob: date
    gender: str  # "male" or "female"

    @property
    def retirement_age(self) -> int:
        return STATUTORY_RETIREMENT_AGE_M if self.gender == "male" else STATUTORY_RETIREMENT_AGE_F

    def age_at(self, ref_date: date) -> float:
        delta = ref_date - self.dob
        return delta.days / 365.25


@dataclass
class CashFlow:
    amount: float
    rise: float = 0.0  # annual rise percent
    description: str = ""
    # Start/end markers
    start: str = "now"  # "now", "fire", "forever", "from_date", "60", etc.
    end: str = "forever"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    flow_type: str = "recurring"  # "recurring" or "one_time"
    person: Optional[int] = None  # index into persons list, for age-based markers


@dataclass
class PortfolioConfig:
    designation: str  # "goal" or "withdraw"
    portfolio_type: str  # "portfolio" or "kaspit"
    balance: float
    interest: float  # annual percent
    fee: float  # annual percent
    profit_fraction: float  # percent of initial balance that is profit
    withdrawal_method: str = "fifo"  # "fifo" or "flat"
    goal: Optional[float] = None  # for goal-designated portfolios


@dataclass
class PensionConfig:
    balance: float
    deposit: float  # monthly deposit
    fee1: float  # percent management fee (deducted from balance)
    fee2: float  # percent deposit fee (deducted from deposits)
    interest: float  # annual percent
    tactics: str  # "60", "67", "60-67"
    mukeret_pct: float  # percent of annuity that is mukeret (tax-exempt)
    end: str = "fire"  # when deposits stop
    person: int = 0  # index into persons list


@dataclass
class KerenConfig:
    balance: float
    deposit: float  # monthly deposit
    interest: float  # annual percent
    keren_type: str  # "maslulit"
    fee: float  # declared annual fee percent
    end: str = "fire"  # when deposits stop


@dataclass
class SimConfig:
    mode: str  # "retire_asap"
    max_retire_age: int
    retire_rule: int
    withdrawal_order: str  # "prati" or "hishtalmut"
    cash_buffer: float
    balance: float  # starting checking account balance
    persons: List[Person]
    expenses: List[CashFlow]
    incomes: List[CashFlow]
    portfolios: List[PortfolioConfig]
    pensions: List[PensionConfig]
    kerens: List[KerenConfig]
    end_age: int = DEFAULT_END_AGE
    start_date: Optional[date] = None  # defaults to today


# ============================================================
# Config Parsing
# ============================================================

def parse_date_str(s: str) -> date:
    """Parse date string in YYYY-MM-DD format."""
    return datetime.strptime(s, "%Y-%m-%d").date()


def parse_cashflow(data: dict) -> CashFlow:
    """Parse a cash flow entry from JSON config."""
    cf = CashFlow(
        amount=data["amount"],
        rise=data.get("rise", 0.0),
        description=data.get("description", ""),
        person=data.get("person"),
    )

    if data.get("type") == "one_time" or data.get("flow_type") == "one_time":
        cf.flow_type = "one_time"
        cf.start = "from_date"
        cf.end = "from_date"
        if "start_date" in data:
            cf.start_date = parse_date_str(data["start_date"])
    else:
        cf.start = data.get("start", "now")
        cf.end = data.get("end", "forever")
        if "start_date" in data:
            cf.start_date = parse_date_str(data["start_date"])
        if "end_date" in data:
            cf.end_date = parse_date_str(data["end_date"])

    return cf


def parse_config(data: dict) -> SimConfig:
    """Parse a config dict into SimConfig."""
    persons = [
        Person(
            name=p["name"],
            dob=parse_date_str(p["dob"]),
            gender=p["gender"]
        )
        for p in data.get("persons", [])
    ]

    expenses = [parse_cashflow(e) for e in data.get("expenses", [])]
    incomes = [parse_cashflow(i) for i in data.get("incomes", [])]

    portfolios = [
        PortfolioConfig(
            designation=p["designation"],
            portfolio_type=p.get("type", "portfolio"),
            balance=p["balance"],
            interest=p["interest"],
            fee=p["fee"],
            profit_fraction=p.get("profit_fraction", 0),
            withdrawal_method=p.get("withdrawal_method", "fifo"),
            goal=p.get("goal"),
        )
        for p in data.get("portfolios", [])
    ]

    pensions = [
        PensionConfig(
            balance=p["balance"],
            deposit=p["deposit"],
            fee1=p.get("fee1", 0),
            fee2=p.get("fee2", 0),
            interest=p["interest"],
            tactics=p["tactics"],
            mukeret_pct=p.get("mukeret_pct", 30),
            end=p.get("end", "fire"),
            person=p.get("person", 0),
        )
        for p in data.get("pensions", [])
    ]

    kerens = [
        KerenConfig(
            balance=k["balance"],
            deposit=k.get("deposit", 0),
            interest=k["interest"],
            keren_type=k.get("type", "maslulit"),
            fee=k.get("fee", 0),
            end=k.get("end", "fire"),
        )
        for k in data.get("kerens", [])
    ]

    # Validate required fields
    if not persons:
        raise ValueError("Config must have at least one person")
    has_withdraw_portfolio = any(p.designation == "withdraw" for p in portfolios)
    if not has_withdraw_portfolio:
        raise ValueError("Config must have at least one portfolio with designation='withdraw'")

    start_date = None
    if "start_date" in data:
        start_date = parse_date_str(data["start_date"])

    return SimConfig(
        mode=data.get("mode", "retire_asap"),
        max_retire_age=data.get("max_retire_age", 50),
        retire_rule=data.get("retire_rule", 80),
        withdrawal_order=data.get("withdrawal_order", "prati"),
        cash_buffer=data.get("cash_buffer", DEFAULT_CASH_BUFFER),
        balance=data.get("balance", DEFAULT_CASH_BUFFER),
        persons=persons,
        expenses=expenses,
        incomes=incomes,
        portfolios=portfolios,
        pensions=pensions,
        kerens=kerens,
        end_age=data.get("end_age", DEFAULT_END_AGE),
        start_date=start_date,
    )


def load_config(path: str) -> SimConfig:
    """Load simulation config from JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return parse_config(data)


# ============================================================
# Tax Module
# ============================================================

def calc_annual_income_tax(annual_income: float) -> float:
    """Calculate Israeli income tax on annual income using progressive brackets."""
    if annual_income <= 0:
        return 0.0
    tax = 0.0
    prev_limit = 0
    for limit, rate in TAX_BRACKETS:
        taxable = min(annual_income, limit) - prev_limit
        if taxable <= 0:
            break
        tax += taxable * rate
        prev_limit = limit
    return tax


def calc_monthly_income_tax(monthly_income: float) -> float:
    """Calculate monthly income tax from monthly income."""
    annual = monthly_income * 12
    annual_tax = calc_annual_income_tax(annual)
    return annual_tax / 12


def calc_pension_income_tax(mazka_monthly: float, person_age: float, gender: str) -> float:
    """Calculate income tax on mazka (qualifying) pension income.

    Mukeret is exempt. Mazka is taxed as regular income with age-based credits.
    """
    if mazka_monthly <= 0:
        return 0.0

    base_tax = calc_monthly_income_tax(mazka_monthly)

    retirement_age = STATUTORY_RETIREMENT_AGE_M if gender == "male" else STATUTORY_RETIREMENT_AGE_F

    # Apply pension tax credit for retirees
    if person_age >= retirement_age:
        base_tax = max(0, base_tax - PENSION_TAX_CREDIT_MONTHLY)

    # Additional reduction at age 70+
    if person_age >= 70:
        base_tax *= 0.5  # Approximate further elderly reduction

    return base_tax


def calc_bituach_leumi(total_pension_monthly: float, person_age: float, gender: str) -> float:
    """Calculate Bituach Leumi (national insurance) on pension income."""
    if total_pension_monthly <= 0:
        return 0.0

    # Exempt at age 70+
    if person_age >= BL_EXEMPT_AGE:
        return 0.0

    retirement_age = STATUTORY_RETIREMENT_AGE_M if gender == "male" else STATUTORY_RETIREMENT_AGE_F

    if person_age >= retirement_age:
        return total_pension_monthly * BL_RATE_ABOVE_RETIREMENT
    else:
        return total_pension_monthly * BL_RATE_BELOW_RETIREMENT


def calc_mukeret_bl(mukeret_monthly: float, person_age: float, gender: str) -> float:
    """Calculate BL on mukeret pension before retirement age (~3.7% observed)."""
    retirement_age = STATUTORY_RETIREMENT_AGE_M if gender == "male" else STATUTORY_RETIREMENT_AGE_F
    if person_age >= retirement_age:
        return 0.0
    return mukeret_monthly * 0.037


# ============================================================
# Growth Engine
# ============================================================

def annual_to_monthly(annual_rate: float) -> float:
    """Convert annual rate (decimal) to effective monthly compound rate.

    Uses: (1 + annual)^(1/12) - 1
    This produces the true monthly rate such that compounding 12 times
    gives exactly the stated annual rate.
    """
    return (1 + annual_rate) ** (1 / 12) - 1


def get_portfolio_pre_fire_rate(interest: float, fee: float) -> float:
    """Monthly growth rate for portfolio pre-FIRE."""
    return annual_to_monthly((interest - fee) / 100)


def get_kh_pre_fire_rate(interest: float, fee: float) -> float:
    """Monthly growth rate for KH pre-FIRE."""
    return annual_to_monthly((interest - fee - KH_HIDDEN_FEE) / 100)


def get_pension_effective_rate(interest: float, management_fee: float) -> float:
    """Annual effective rate for pension fund.

    Management fee (fee1) is deducted from the balance, not from the return rate.
    Effective annual rate = (1 + interest) * (1 - management_fee) - 1
    """
    if management_fee <= 0:
        return interest / 100
    return (1 + interest / 100) * (1 - management_fee / 100) - 1


def get_kaspit_rate(interest: float, fee: float) -> float:
    """Monthly growth rate for kaspit. No hidden fee."""
    return annual_to_monthly((interest - fee) / 100)


def interpolate_haircut(retire_rule: int, haircut_table: Dict[int, float]) -> float:
    """Piecewise linear interpolation of retireRule haircuts.

    Clamps to [80, 99] range. Returns haircut in percentage points.
    """
    clamped = max(80, min(99, retire_rule))
    points = sorted(haircut_table.items())

    # Exact match
    for rule_val, haircut in points:
        if clamped == rule_val:
            return haircut

    # Interpolate between bracketing points
    for i in range(len(points) - 1):
        r1, h1 = points[i]
        r2, h2 = points[i + 1]
        if r1 <= clamped <= r2:
            frac = (clamped - r1) / (r2 - r1)
            return h1 + frac * (h2 - h1)

    # Should not reach here due to clamping, but return last point
    return points[-1][1]


def get_post_fire_rate(asset_type: str, pre_fire_annual_rate: float,
                       retire_rule: int) -> float:
    """Get monthly post-FIRE growth rate with retireRule haircut.

    Only risky assets (portfolio, kh) get haircuts. Pension and kaspit unchanged.
    """
    if asset_type == "portfolio":
        haircut = interpolate_haircut(retire_rule, PORTFOLIO_HAIRCUTS) / 100
        return annual_to_monthly(pre_fire_annual_rate - haircut)
    elif asset_type == "kh":
        haircut = interpolate_haircut(retire_rule, KH_HAIRCUTS) / 100
        return annual_to_monthly(pre_fire_annual_rate - haircut)
    else:
        # Pension, kaspit: no haircut
        return annual_to_monthly(pre_fire_annual_rate)


# ============================================================
# FIFO Capital Gains Tracker
# ============================================================

@dataclass
class Lot:
    amount: float  # current value of this lot
    cost_basis: float  # original cost basis


class FIFOTracker:
    """Tracks cost basis lots for FIFO capital gains tax calculation."""

    def __init__(self, initial_balance: float, profit_fraction_pct: float):
        self.lots: List[Lot] = []
        if initial_balance > 0:
            cost_basis = initial_balance * (1 - profit_fraction_pct / 100)
            self.lots.append(Lot(amount=initial_balance, cost_basis=cost_basis))

    def add_lot(self, amount: float):
        """Add a new lot (deposit). Cost basis = full amount (no profit yet)."""
        if amount > 0:
            self.lots.append(Lot(amount=amount, cost_basis=amount))

    def grow(self, monthly_rate: float):
        """Grow all lots by the monthly rate. Cost basis stays the same."""
        for lot in self.lots:
            lot.amount *= (1 + monthly_rate)

    @property
    def total_value(self) -> float:
        return sum(lot.amount for lot in self.lots)

    @property
    def total_cost_basis(self) -> float:
        return sum(lot.cost_basis for lot in self.lots)

    @property
    def profit_fraction(self) -> float:
        """Current aggregate profit fraction."""
        total = self.total_value
        if total <= 0:
            return 0.0
        return max(0, (total - self.total_cost_basis) / total)

    def sell(self, amount: float) -> Tuple[float, float]:
        """Sell the given amount using FIFO. Returns (proceeds, tax).

        Sells oldest lots first. Tax = realized_gain * 25%.
        """
        if amount <= 0:
            return 0.0, 0.0

        remaining = amount
        total_proceeds = 0.0
        total_tax = 0.0

        while remaining > 0 and self.lots:
            lot = self.lots[0]
            sell_from_lot = min(remaining, lot.amount)

            # Proportional cost basis for this sale
            if lot.amount > 0:
                cost_fraction = lot.cost_basis / lot.amount
            else:
                cost_fraction = 1.0

            cost_sold = sell_from_lot * cost_fraction
            gain = max(0, sell_from_lot - cost_sold)
            tax = gain * CAPITAL_GAINS_TAX_RATE

            lot.amount -= sell_from_lot
            lot.cost_basis -= cost_sold

            total_proceeds += sell_from_lot
            total_tax += tax
            remaining -= sell_from_lot

            # Remove depleted lots
            if lot.amount <= 0.01:
                self.lots.pop(0)

        return total_proceeds, total_tax


# ============================================================
# Pension Converter
# ============================================================

def get_conversion_factor(age: int) -> float:
    """Get pension-to-annuity conversion factor (months) by conversion age.

    Uses lookup table from observed data. Only 60, 65, 67 are supported.
    """
    if age in PENSION_CONVERSION_FACTORS:
        return PENSION_CONVERSION_FACTORS[age]

    # Interpolate between known points
    points = sorted(PENSION_CONVERSION_FACTORS.items())
    if age < points[0][0]:
        return points[0][1]
    if age > points[-1][0]:
        return points[-1][1]

    for i in range(len(points) - 1):
        a1, f1 = points[i]
        a2, f2 = points[i + 1]
        if a1 <= age <= a2:
            frac = (age - a1) / (a2 - a1)
            return f1 + frac * (f2 - f1)

    return points[-1][1]


def get_conversion_age(tactics: str, person: Person) -> Tuple[Optional[int], Optional[int]]:
    """Get the conversion age(s) based on pension tactics.

    Returns (mukeret_age, mazka_age). None means no conversion at that stage.

    Tactics:
    - "60": full conversion at 60
    - "67": full conversion at statutory retirement age
    - "60-67": 30% mukeret at 60, 70% mazka at retirement age
    """
    retirement_age = person.retirement_age

    if tactics == "60":
        return 60, None  # Full conversion at 60 (both mukeret and mazka from same pot)
    elif tactics == "67":
        return None, retirement_age  # Full conversion at retirement age
    elif tactics == "60-67":
        return 60, retirement_age  # Split: mukeret@60, mazka@retirement
    else:
        # Default to 60
        return 60, None


# ============================================================
# Cash Flow Resolution
# ============================================================

def resolve_date(marker: str, sim_start: date, fire_date: date,
                 end_date: date, explicit_date: Optional[date],
                 persons: List[Person], person_idx: Optional[int],
                 current_date: date) -> date:
    """Resolve a start/end marker to an actual date."""
    if marker == "now":
        return sim_start
    elif marker == "fire":
        return fire_date
    elif marker == "forever":
        return end_date
    elif marker == "from_date" and explicit_date:
        return explicit_date
    elif marker.isdigit() and person_idx is not None and person_idx < len(persons):
        # Age-based marker (e.g., "60")
        target_age = int(marker)
        person = persons[person_idx]
        target_date = date(
            person.dob.year + target_age,
            person.dob.month,
            person.dob.day if person.dob.day <= 28 else 28
        )
        return target_date
    elif explicit_date:
        return explicit_date
    return sim_start


def is_cashflow_active(cf: CashFlow, current_date: date, sim_start: date,
                       fire_date: date, end_date: date,
                       persons: List[Person]) -> bool:
    """Check if a cash flow is active in the given month."""
    start = resolve_date(cf.start, sim_start, fire_date, end_date,
                         cf.start_date, persons, cf.person, current_date)
    end = resolve_date(cf.end, sim_start, fire_date, end_date,
                       cf.end_date, persons, cf.person, current_date)

    if cf.flow_type == "one_time":
        # Active only in the month matching start_date
        return (current_date.year == start.year and current_date.month == start.month)

    return start <= current_date <= end


def calc_cashflow_amount(cf: CashFlow, months_since_active: int) -> float:
    """Calculate cash flow amount with compound growth applied.

    Uses compound interest: base * (1 + rise%/12) ^ months
    """
    if cf.rise == 0 or months_since_active <= 0:
        return cf.amount
    return cf.amount * (1 + cf.rise / 100 / 12) ** months_since_active


# ============================================================
# Simulation State
# ============================================================

@dataclass
class PensionAnnuity:
    """State of a pension after conversion to annuity."""
    mukeret_monthly: float = 0.0
    mazka_monthly: float = 0.0
    is_active: bool = False
    person_idx: int = 0


@dataclass
class MonthRecord:
    """One month's simulation output."""
    month_idx: int = 0
    current_date: date = field(default_factory=lambda: date.today())
    age: float = 0.0
    is_post_fire: bool = False

    # Inflows
    income: float = 0.0
    pension_mukeret_total: float = 0.0
    pension_mazka_total: float = 0.0
    old_age_total: float = 0.0
    portfolio_withdrawal: float = 0.0
    kh_withdrawals: List[float] = field(default_factory=list)

    # Outflows
    expenses: float = 0.0
    goals: float = 0.0
    income_tax: float = 0.0
    bituach_leumi: float = 0.0
    portfolio_tax: float = 0.0

    # Deposits (pre-FIRE)
    deposit_portfolio: float = 0.0

    # Asset values (end of month)
    portfolio_value: float = 0.0
    kaspit_value: float = 0.0
    kh_values: List[float] = field(default_factory=list)
    pension_values: List[float] = field(default_factory=list)
    checking: float = 0.0

    # Per-person breakdowns
    pension_mukeret: List[float] = field(default_factory=list)
    pension_mazka: List[float] = field(default_factory=list)
    old_age: List[float] = field(default_factory=list)
    tax_per_person: List[float] = field(default_factory=list)
    bl_per_person: List[float] = field(default_factory=list)

    @property
    def net_worth(self) -> float:
        return (self.portfolio_value + self.kaspit_value +
                sum(self.kh_values) + sum(self.pension_values) +
                self.checking)


# ============================================================
# Simulation Engine
# ============================================================

@dataclass
class SimState:
    """Mutable simulation state carried month to month."""
    # Assets
    portfolio_fifo: Optional[FIFOTracker] = None
    portfolio_value: float = 0.0
    kaspit_value: float = 0.0
    kh_values: List[float] = field(default_factory=list)
    pension_values: List[float] = field(default_factory=list)
    checking: float = 0.0

    # Pension annuities (one per pension config)
    annuities: List[PensionAnnuity] = field(default_factory=list)

    # Pension conversion tracking: whether mukeret/mazka conversion happened
    pension_mukeret_converted: List[bool] = field(default_factory=list)
    pension_mazka_converted: List[bool] = field(default_factory=list)

    # Current withdrawal source index (for sequential depletion)
    current_withdrawal_idx: int = 0

    # Track which asset is being withdrawn from in prati/hishtalmut order
    # 0 = portfolio, 1..N = kh1..khN (for prati)
    # 0..N-1 = kh1..khN, N = portfolio (for hishtalmut)

    # Cashflow tracking (for growth calculation)
    cashflow_start_months: Dict[int, int] = field(default_factory=dict)


def init_state(config: SimConfig) -> SimState:
    """Initialize simulation state from config."""
    state = SimState()

    # Aggregate all withdraw-designated portfolios
    withdraw_portfolios = [p for p in config.portfolios if p.designation == "withdraw"]
    total_balance = sum(p.balance for p in withdraw_portfolios)

    # Create FIFO tracker with individual lots per portfolio (preserves per-portfolio cost basis)
    state.portfolio_fifo = FIFOTracker(0, 0)
    state.portfolio_fifo.lots.clear()
    for p in withdraw_portfolios:
        if p.balance > 0:
            cost_basis = p.balance * (1 - p.profit_fraction / 100)
            state.portfolio_fifo.lots.append(Lot(amount=p.balance, cost_basis=cost_basis))

    state.portfolio_value = total_balance

    # Kaspit (goal portfolios) — sum all kaspit funds
    state.kaspit_value = sum(
        p.balance for p in config.portfolios
        if p.designation == "goal" and p.portfolio_type == "kaspit"
    )

    # KH funds
    state.kh_values = [k.balance for k in config.kerens]

    # Pension funds
    state.pension_values = [p.balance for p in config.pensions]

    # Annuity state
    state.annuities = [
        PensionAnnuity(person_idx=p.person) for p in config.pensions
    ]
    state.pension_mukeret_converted = [False] * len(config.pensions)
    state.pension_mazka_converted = [False] * len(config.pensions)

    state.checking = config.balance

    return state


def get_withdrawal_order(config: SimConfig) -> List[Tuple[str, int]]:
    """Get ordered list of (asset_type, index) for withdrawal priority.

    Returns list like [("portfolio", 0), ("kh", 0), ("kh", 1), ...]
    or [("kh", 0), ("kh", 1), ..., ("portfolio", 0)] for hishtalmut order.
    """
    kh_entries = [("kh", i) for i in range(len(config.kerens))]

    if config.withdrawal_order == "hishtalmut":
        return kh_entries + [("portfolio", 0)]
    else:  # "prati" (default)
        return [("portfolio", 0)] + kh_entries


def add_month(d: date, months: int) -> date:
    """Add months to a date."""
    month = d.month + months
    year = d.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    day = min(d.day, 28)  # Safe day
    return date(year, month, day)


def simulate(config: SimConfig, fire_month: int, verbose: bool = False) -> List[MonthRecord]:
    """Run the full monthly simulation with FIRE at the given month index.

    fire_month: month index (0-based) when FIRE happens. -1 = never retire.
    Returns list of MonthRecord for each simulated month.

    Follows the original calculator's monthly state machine order:
    1. Income determination
    2. Expense determination
    3. Tax determination (post-FIRE only)
    4. Withdrawal calculation (post-FIRE only)
    5. Asset growth (all months)
    6. Pension conversion events (triggered by age)
    7. Record state
    """
    state = init_state(config)
    records: List[MonthRecord] = []

    sim_start = config.start_date or date.today().replace(day=1)
    primary_person = config.persons[0] if config.persons else Person("default", date(1988, 1, 1), "male")
    start_age = primary_person.age_at(sim_start)

    # Calculate simulation end date
    total_months = int((config.end_age - start_age) * 12)

    fire_date = add_month(sim_start, fire_month) if fire_month >= 0 else add_month(sim_start, total_months + 1)
    end_sim_date = add_month(sim_start, total_months)

    # Pre-compute rates (weighted average across all withdraw portfolios)
    withdraw_portfolios = [p for p in config.portfolios if p.designation == "withdraw"]
    if withdraw_portfolios:
        total_bal = sum(p.balance for p in withdraw_portfolios)
        if total_bal > 0:
            avg_interest = sum(p.balance * p.interest for p in withdraw_portfolios) / total_bal
            avg_fee = sum(p.balance * p.fee for p in withdraw_portfolios) / total_bal
        else:
            avg_interest = sum(p.interest for p in withdraw_portfolios) / len(withdraw_portfolios)
            avg_fee = sum(p.fee for p in withdraw_portfolios) / len(withdraw_portfolios)
        portfolio_pre_rate = get_portfolio_pre_fire_rate(avg_interest, avg_fee)
        portfolio_annual = (avg_interest - avg_fee) / 100
    else:
        portfolio_pre_rate = 0.0
        portfolio_annual = 0.0

    kaspit_portfolios = [p for p in config.portfolios if p.designation == "goal" and p.portfolio_type == "kaspit"]
    if kaspit_portfolios:
        total_kaspit = sum(p.balance for p in kaspit_portfolios)
        if total_kaspit > 0:
            avg_k_interest = sum(p.balance * p.interest for p in kaspit_portfolios) / total_kaspit
            avg_k_fee = sum(p.balance * p.fee for p in kaspit_portfolios) / total_kaspit
        else:
            avg_k_interest = sum(p.interest for p in kaspit_portfolios) / len(kaspit_portfolios)
            avg_k_fee = sum(p.fee for p in kaspit_portfolios) / len(kaspit_portfolios)
        kaspit_rate = get_kaspit_rate(avg_k_interest, avg_k_fee)
    else:
        kaspit_rate = 0.0

    kh_pre_rates = [get_kh_pre_fire_rate(k.interest, k.fee) for k in config.kerens]
    kh_annual_rates = [(k.interest - k.fee - KH_HIDDEN_FEE) / 100 for k in config.kerens]

    pension_annual_rates = [get_pension_effective_rate(p.interest, p.fee1)
                           for p in config.pensions]

    withdrawal_order = get_withdrawal_order(config)

    for month_idx in range(total_months + 1):
        current_date = add_month(sim_start, month_idx)
        is_post_fire = (fire_month >= 0 and month_idx >= fire_month)

        rec = MonthRecord(
            month_idx=month_idx,
            current_date=current_date,
            age=primary_person.age_at(current_date),
            is_post_fire=is_post_fire,
            kh_values=[0.0] * len(config.kerens),
            pension_values=[0.0] * len(config.pensions),
            kh_withdrawals=[0.0] * len(config.kerens),
            pension_mukeret=[0.0] * len(config.persons),
            pension_mazka=[0.0] * len(config.persons),
            old_age=[0.0] * len(config.persons),
            tax_per_person=[0.0] * len(config.persons),
            bl_per_person=[0.0] * len(config.persons),
        )

        # ===== STEP 1: INCOME DETERMINATION =====
        total_income = 0.0
        for i, inc in enumerate(config.incomes):
            if is_cashflow_active(inc, current_date, sim_start, fire_date, end_sim_date, config.persons):
                if i not in state.cashflow_start_months:
                    state.cashflow_start_months[i] = month_idx
                months_active = month_idx - state.cashflow_start_months[i]
                total_income += calc_cashflow_amount(inc, months_active)

        # Pension annuity income (from previous conversions)
        total_mukeret = 0.0
        total_mazka = 0.0
        for pi, annuity in enumerate(state.annuities):
            if annuity.is_active:
                person_idx = annuity.person_idx
                if person_idx < len(rec.pension_mukeret):
                    rec.pension_mukeret[person_idx] += annuity.mukeret_monthly
                if person_idx < len(rec.pension_mazka):
                    rec.pension_mazka[person_idx] += annuity.mazka_monthly
                total_mukeret += annuity.mukeret_monthly
                total_mazka += annuity.mazka_monthly

        # Old age pension
        total_old_age = 0.0
        for pi, person in enumerate(config.persons):
            person_age = person.age_at(current_date)
            if person_age >= OLD_AGE_START_AGE:
                rec.old_age[pi] = OLD_AGE_PENSION_AMOUNT
                total_old_age += OLD_AGE_PENSION_AMOUNT

        rec.income = total_income
        rec.pension_mukeret_total = total_mukeret
        rec.pension_mazka_total = total_mazka
        rec.old_age_total = total_old_age

        # ===== STEP 2: EXPENSE DETERMINATION =====
        total_expenses = 0.0
        total_goals = 0.0
        expense_offset = len(config.incomes)

        for i, exp in enumerate(config.expenses):
            if is_cashflow_active(exp, current_date, sim_start, fire_date, end_sim_date, config.persons):
                cf_key = expense_offset + i
                if cf_key not in state.cashflow_start_months:
                    state.cashflow_start_months[cf_key] = month_idx
                months_active = month_idx - state.cashflow_start_months[cf_key]
                amount = calc_cashflow_amount(exp, months_active)
                if exp.flow_type == "one_time":
                    total_goals += amount
                else:
                    total_expenses += amount

        rec.expenses = total_expenses
        rec.goals = total_goals

        # ===== STEP 3: TAX DETERMINATION =====
        total_tax = 0.0
        total_bl = 0.0

        for pi, person in enumerate(config.persons):
            person_age = person.age_at(current_date)
            mazka = rec.pension_mazka[pi] if pi < len(rec.pension_mazka) else 0
            mukeret = rec.pension_mukeret[pi] if pi < len(rec.pension_mukeret) else 0

            if mazka > 0:
                tax = calc_pension_income_tax(mazka, person_age, person.gender)
                bl = calc_bituach_leumi(mazka, person_age, person.gender)
                if mukeret > 0:
                    bl += calc_mukeret_bl(mukeret, person_age, person.gender)
                rec.tax_per_person[pi] = tax
                rec.bl_per_person[pi] = bl
                total_tax += tax
                total_bl += bl

        rec.income_tax = total_tax
        rec.bituach_leumi = total_bl

        # ===== STEP 4: WITHDRAWAL OR DEPOSIT =====
        if is_post_fire:
            total_outflows = total_expenses + total_goals + total_tax + total_bl
            total_inflows = total_income + total_mukeret + total_mazka + total_old_age
            deficit = total_outflows - total_inflows

            if deficit > 0:
                remaining_deficit = deficit

                for asset_type, asset_idx in withdrawal_order:
                    if remaining_deficit <= 0.01:
                        break

                    if asset_type == "portfolio":
                        available = state.portfolio_value
                        if available <= 0:
                            continue

                        # Gross up for capital gains tax
                        profit_frac = state.portfolio_fifo.profit_fraction if state.portfolio_fifo else 0
                        effective_tax_rate = profit_frac * CAPITAL_GAINS_TAX_RATE

                        if effective_tax_rate < 1.0:
                            gross_withdrawal = remaining_deficit / (1 - effective_tax_rate)
                        else:
                            gross_withdrawal = remaining_deficit

                        gross_withdrawal = min(gross_withdrawal, available)
                        _, tax = state.portfolio_fifo.sell(gross_withdrawal)

                        state.portfolio_value -= gross_withdrawal
                        rec.portfolio_withdrawal += gross_withdrawal
                        rec.portfolio_tax += tax

                        net_after_tax = gross_withdrawal - tax
                        remaining_deficit -= net_after_tax

                    elif asset_type == "kh":
                        if asset_idx >= len(state.kh_values):
                            continue
                        available = state.kh_values[asset_idx]
                        if available <= 0:
                            continue

                        withdrawal = min(remaining_deficit, available)
                        state.kh_values[asset_idx] -= withdrawal
                        rec.kh_withdrawals[asset_idx] = withdrawal
                        remaining_deficit -= withdrawal

                # Uncovered deficit goes to negative checking
                # This makes NW go negative, causing FIRE search to reject this date
                if remaining_deficit > 0.01:
                    state.checking -= remaining_deficit
        else:
            # Pre-FIRE: deposit surplus to portfolio
            surplus = total_income - total_expenses - total_goals
            if surplus > 0:
                state.portfolio_value += surplus
                if state.portfolio_fifo:
                    state.portfolio_fifo.add_lot(surplus)
                rec.deposit_portfolio = surplus
            elif surplus < 0:
                # Deficit pre-FIRE: reduce checking (shouldn't normally happen)
                state.checking += surplus

        # ===== STEP 5: ASSET GROWTH =====
        if is_post_fire:
            p_rate = get_post_fire_rate("portfolio", portfolio_annual, config.retire_rule)
        else:
            p_rate = portfolio_pre_rate

        if state.portfolio_value > 0:
            state.portfolio_value *= (1 + p_rate)
            if state.portfolio_fifo:
                state.portfolio_fifo.grow(p_rate)

        state.kaspit_value *= (1 + kaspit_rate)

        for ki, kcfg in enumerate(config.kerens):
            if is_post_fire:
                rate = get_post_fire_rate("kh", kh_annual_rates[ki], config.retire_rule)
            else:
                rate = kh_pre_rates[ki]

            if state.kh_values[ki] > 0:
                state.kh_values[ki] *= (1 + rate)

            # KH deposits (only pre-FIRE)
            if not is_post_fire and kcfg.deposit > 0:
                state.kh_values[ki] += kcfg.deposit

        for pi, pcfg in enumerate(config.pensions):
            if state.pension_values[pi] > 0:
                annual_rate = pension_annual_rates[pi]
                state.pension_values[pi] *= (1 + annual_rate) ** (1 / 12)

                if not is_post_fire and pcfg.deposit > 0:
                    deposit_after_fee = pcfg.deposit * (1 - pcfg.fee2 / 100)
                    state.pension_values[pi] += deposit_after_fee

        # ===== STEP 6: PENSION CONVERSION EVENTS =====
        for pi, pcfg in enumerate(config.pensions):
            person = config.persons[pcfg.person]
            person_age = person.age_at(current_date)
            annuity = state.annuities[pi]

            mukeret_age, mazka_age = get_conversion_age(pcfg.tactics, person)

            if pcfg.tactics == "60-67":
                if mukeret_age and person_age >= mukeret_age and not state.pension_mukeret_converted[pi]:
                    fund = state.pension_values[pi]
                    mukeret_fund = fund * (pcfg.mukeret_pct / 100)
                    factor = get_conversion_factor(mukeret_age)
                    annuity.mukeret_monthly = mukeret_fund / factor
                    state.pension_values[pi] -= mukeret_fund
                    state.pension_mukeret_converted[pi] = True
                    annuity.is_active = True

                if mazka_age and person_age >= mazka_age and not state.pension_mazka_converted[pi]:
                    fund = state.pension_values[pi]
                    factor = get_conversion_factor(mazka_age)
                    annuity.mazka_monthly = fund / factor
                    state.pension_values[pi] = 0
                    state.pension_mazka_converted[pi] = True
                    annuity.is_active = True
            else:
                conv_age = mukeret_age if mukeret_age else mazka_age
                if conv_age and person_age >= conv_age and not state.pension_mukeret_converted[pi]:
                    fund = state.pension_values[pi]
                    factor = get_conversion_factor(conv_age)
                    total_monthly = fund / factor
                    annuity.mukeret_monthly = total_monthly * (pcfg.mukeret_pct / 100)
                    annuity.mazka_monthly = total_monthly * (1 - pcfg.mukeret_pct / 100)
                    state.pension_values[pi] = 0
                    state.pension_mukeret_converted[pi] = True
                    state.pension_mazka_converted[pi] = True
                    annuity.is_active = True

        # ===== STEP 7: RECORD STATE =====
        rec.portfolio_value = state.portfolio_value
        rec.kaspit_value = state.kaspit_value
        rec.kh_values = list(state.kh_values)
        rec.pension_values = list(state.pension_values)
        rec.checking = state.checking

        records.append(rec)

    return records


# ============================================================
# FIRE Search
# ============================================================

def find_fire_month(config: SimConfig, verbose: bool = False) -> Tuple[int, List[MonthRecord]]:
    """Find the earliest FIRE month where NW stays >= 0 for all months.

    Returns (fire_month_idx, simulation_records) or (-1, []) if impossible.
    Uses linear scan (not binary search) because monotonicity isn't guaranteed.
    """
    primary = config.persons[0] if config.persons else Person("default", date(1988, 1, 1), "male")
    sim_start = config.start_date or date.today().replace(day=1)
    start_age = primary.age_at(sim_start)

    max_months = int((config.max_retire_age - start_age) * 12)

    if verbose:
        print(f"Searching for FIRE month (ages {start_age:.1f} to {config.max_retire_age})...")

    best_month = -1
    best_records: List[MonthRecord] = []

    for candidate in range(max_months + 1):
        records = simulate(config, fire_month=candidate, verbose=False)

        # Check if NW stays >= 0 for all months
        all_positive = all(r.net_worth >= 0 for r in records)

        if all_positive:
            if verbose:
                fire_age = start_age + candidate / 12
                min_nw = min(r.net_worth for r in records)
                print(f"  Month {candidate} (age {fire_age:.1f}): OK, min NW = {format_ils(min_nw)}")
            best_month = candidate
            best_records = records
            break
        elif verbose and candidate % 12 == 0:
            fire_age = start_age + candidate / 12
            min_nw = min(r.net_worth for r in records)
            print(f"  Month {candidate} (age {fire_age:.1f}): FAIL, min NW = {format_ils(min_nw)}")

    return best_month, best_records


# ============================================================
# Output
# ============================================================

def format_ils(amount: float) -> str:
    """Format as ILS currency."""
    if abs(amount) >= 1_000_000:
        return f"₪{amount/1_000_000:.2f}M"
    elif abs(amount) >= 1_000:
        return f"₪{amount/1_000:.0f}K"
    return f"₪{amount:.0f}"



def build_csv_row(rec: MonthRecord, config: SimConfig) -> dict:
    """Build a CSV row dict from a MonthRecord."""
    row = {
        'age': f"{rec.age:.2f}",
        'timestamp': str(int(datetime.combine(rec.current_date, datetime.min.time()).timestamp() * 1000)),
    }

    # Income
    row['תזרים מנכסים שאינם תיק השקעות'] = f"{rec.income:.0f}"

    # Withdrawals
    row['משיכה מתיק תיק בברוקר בארץ'] = f"{rec.portfolio_withdrawal:.0f}"
    for ki in range(len(config.kerens)):
        kh_name = f'משיכה מקרן השתלמות {ki+1}'
        kh_val = rec.kh_withdrawals[ki] if ki < len(rec.kh_withdrawals) else 0
        row[kh_name] = f"{kh_val:.0f}"

    # Pension income
    for pi, person in enumerate(config.persons):
        muk = rec.pension_mukeret[pi] if pi < len(rec.pension_mukeret) else 0
        maz = rec.pension_mazka[pi] if pi < len(rec.pension_mazka) else 0
        row[f'מוכרת {person.name}'] = f"{muk:.0f}"
        row[f'מזכה {person.name}'] = f"{maz:.0f}"

    # Old age pension
    for pi, person in enumerate(config.persons):
        oa = rec.old_age[pi] if pi < len(rec.old_age) else 0
        row[f'קיצבת זיקנה {person.name}'] = f"{oa:.0f}"

    # Expenses
    row['הוצאות שוטפות'] = f"{rec.expenses:.0f}"
    row['יעדים'] = f"{rec.goals:.0f}"

    # Deposits
    row['הפקדה לתיק בברוקר בארץ'] = f"{rec.deposit_portfolio:.0f}"

    # Taxes
    for pi, person in enumerate(config.persons):
        tax = rec.tax_per_person[pi] if pi < len(rec.tax_per_person) else 0
        bl = rec.bl_per_person[pi] if pi < len(rec.bl_per_person) else 0
        row[f'מס הכנסה {person.name}'] = f"{tax:.0f}"
        row[f'ביטוח לאומי {person.name}'] = f"{bl:.0f}"

    row['מס על רווחי תיק בברוקר בארץ'] = f"{rec.portfolio_tax:.0f}"

    # Asset values
    row['שווי תיק בברוקר בארץ'] = f"{rec.portfolio_value:.0f}"
    row['שווי קרן כספית'] = f"{rec.kaspit_value:.0f}"

    for ki in range(len(config.kerens)):
        row[f'שווי קרן השתלמות {ki+1}'] = \
            f"{rec.kh_values[ki]:.0f}" if ki < len(rec.kh_values) else "0"

    for pi, person in enumerate(config.persons):
        pval = rec.pension_values[pi] if pi < len(rec.pension_values) else 0
        row[f'קרן פנסיה של {person.name}'] = f"{pval:.0f}"

    row['עובר ושב'] = f"{rec.checking:.0f}"
    row['גובה עובר ושב'] = f"{rec.checking:.0f}"
    row['שווי נקי'] = f"{rec.net_worth:.0f}"

    return row


def write_csv(records: List[MonthRecord], config: SimConfig, path: str):
    """Write simulation results in the original calculator's CSV format.

    Format: header starts with ',,' (age/timestamp have no column header),
    followed by Hebrew column names. Data lines start with age (digit).
    Compatible with retirement_analysis.py parser.
    """
    if not records:
        return

    rows = [build_csv_row(r, config) for r in records]
    fieldnames = list(rows[0].keys())
    # Hebrew columns (skip 'age' and 'timestamp' in header — they're implicit)
    hebrew_cols = fieldnames[2:]

    with open(path, 'w', encoding='utf-8') as f:
        # Header line: starts with ',,' then column names
        f.write(',,' + ','.join(hebrew_cols) + '\n')

        # Data lines
        for row in rows:
            values = [row[col] for col in fieldnames]
            f.write(','.join(values) + '\n')

    print(f"CSV written to {path} ({len(records)} rows)")


def print_summary(records: List[MonthRecord], config: SimConfig, fire_month: int):
    """Print CLI summary of simulation results."""
    if not records:
        print("No simulation data.")
        return

    primary = config.persons[0]
    sim_start = config.start_date or date.today().replace(day=1)
    start_age = primary.age_at(sim_start)

    print(f"\n{'='*65}")
    print(f"  FIRE Retirement Calculator Results")
    print(f"{'='*65}")

    if fire_month < 0:
        print(f"\n  Cannot retire before age {config.max_retire_age}")
        print(f"  Consider: lower expenses, higher savings, or later retirement age")
        return

    fire_age = start_age + fire_month / 12
    fire_date = add_month(sim_start, fire_month)

    print(f"\n  Config:")
    print(f"    retireRule:        {config.retire_rule}")
    print(f"    Withdrawal order:  {config.withdrawal_order}")
    print(f"    End age:           {config.end_age}")

    print(f"\n  FIRE Date:")
    print(f"    Age {fire_age:.1f} ({fire_date.strftime('%B %Y')})")
    print(f"    {fire_age - start_age:.1f} years from now")

    # Net worth milestones
    fire_rec = records[fire_month]
    min_nw = min(r.net_worth for r in records[fire_month:])
    min_nw_rec = next(r for r in records[fire_month:] if r.net_worth == min_nw)
    end_rec = records[-1]

    print(f"\n  Net Worth:")
    print(f"    At FIRE:   {format_ils(fire_rec.net_worth)} (age {fire_rec.age:.1f})")
    print(f"    Minimum:   {format_ils(min_nw)} (age {min_nw_rec.age:.1f})")
    print(f"    At end:    {format_ils(end_rec.net_worth)} (age {end_rec.age:.1f})")

    # Asset composition at FIRE
    print(f"\n  Assets at FIRE:")
    print(f"    Portfolio:  {format_ils(fire_rec.portfolio_value)}")
    kh_total = sum(fire_rec.kh_values)
    print(f"    KH total:   {format_ils(kh_total)}")
    pension_total = sum(fire_rec.pension_values)
    print(f"    Pensions:   {format_ils(pension_total)}")
    print(f"    Kaspit:     {format_ils(fire_rec.kaspit_value)}")

    # Key events
    print(f"\n  Key Events:")
    print(f"    FIRE:              Age {fire_age:.1f}")

    # Portfolio depletion
    for r in records[fire_month:]:
        if r.portfolio_value <= 0:
            print(f"    Portfolio depletes: Age {r.age:.1f}")
            break
    else:
        print(f"    Portfolio depletes: Never")

    # Pension start
    for r in records[fire_month:]:
        if r.pension_mukeret_total > 0 or r.pension_mazka_total > 0:
            print(f"    Pension starts:    Age {r.age:.1f}")
            total_pension = r.pension_mukeret_total + r.pension_mazka_total
            print(f"      Monthly annuity: {format_ils(total_pension)}")
            break

    # Old age pension
    for r in records[fire_month:]:
        if r.old_age_total > 0:
            print(f"    Old age pension:   Age {r.age:.1f}")
            break

    # Post-FIRE averages
    post_fire = records[fire_month:]
    avg_expenses = sum(r.expenses for r in post_fire) / len(post_fire)
    avg_pension = sum(r.pension_mukeret_total + r.pension_mazka_total for r in post_fire) / len(post_fire)
    avg_withdrawal = sum(r.portfolio_withdrawal + sum(r.kh_withdrawals) for r in post_fire) / len(post_fire)

    print(f"\n  Post-FIRE Monthly Averages:")
    print(f"    Expenses:     {format_ils(avg_expenses)}")
    print(f"    Pension:      {format_ils(avg_pension)}")
    print(f"    Withdrawals:  {format_ils(avg_withdrawal)}")

    # One-time goals
    goals = [(r.age, r.goals) for r in records if r.goals > 0]
    if goals:
        total_goals = sum(g[1] for g in goals)
        print(f"\n  One-Time Goals ({format_ils(total_goals)} total):")
        for age, amount in goals:
            print(f"    Age {age:.0f}: {format_ils(amount)}")

    # Risk assessment
    print(f"\n  Risk:")
    print(f"    Min NW post-FIRE: {format_ils(min_nw)} at age {min_nw_rec.age:.1f}")
    if fire_rec.net_worth > 0:
        drawdown = (1 - min_nw / fire_rec.net_worth) * 100
        print(f"    Max drawdown:     {drawdown:.0f}%")

    print()


# ============================================================
# CLI Entry Point
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Israeli FIRE Retirement Calculator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python retirement_calculator.py config.json
  python retirement_calculator.py config.json --csv output.csv
  python retirement_calculator.py config.json --csv output.csv --verbose

Compare with original calculator:
  python retirement_analysis.py original.csv output.csv --labels "Original" "Ours"
        """
    )
    parser.add_argument('config', help='JSON config file path')
    parser.add_argument('--csv', help='Output CSV file path')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show search progress')
    parser.add_argument('--fire-month', type=int, default=None,
                        help='Force specific FIRE month (skip search)')

    args = parser.parse_args()

    config = load_config(args.config)

    # Validate
    if config.retire_rule < 80 or config.retire_rule > 99:
        print(f"Warning: retireRule={config.retire_rule} is outside observed range [80, 99].")
        print(f"  Results may be inaccurate. Clamping to nearest observed value.")
        if config.retire_rule >= 100:
            print(f"  Using retireRule=99 (most conservative observed).")

    if not config.persons:
        print("Error: At least one person must be defined.")
        sys.exit(1)

    if args.fire_month is not None:
        fire_month = args.fire_month
        records = simulate(config, fire_month=fire_month, verbose=args.verbose)
        print(f"Simulated with forced FIRE month {fire_month}")
    else:
        fire_month, records = find_fire_month(config, verbose=args.verbose)

    print_summary(records, config, fire_month)

    if args.csv and records:
        write_csv(records, config, args.csv)


if __name__ == "__main__":
    main()
