"""
Unit tests for retirement_calculator.py

Tests the complex standalone modules where bugs would be hardest to diagnose
from CSV diffs: FIFO tracker, pension converter, tax calculator, growth engine,
cash flow resolution, and withdrawal engine.
"""

import pytest
from datetime import date

from services.retirement_calculator import (
    # Tax module
    calc_annual_income_tax,
    calc_monthly_income_tax,
    calc_pension_income_tax,
    calc_bituach_leumi,
    calc_mukeret_bl,
    # Growth engine
    annual_to_monthly,
    get_portfolio_pre_fire_rate,
    get_kh_pre_fire_rate,
    get_pension_effective_rate,
    get_kaspit_rate,
    interpolate_haircut,
    get_post_fire_rate,
    PORTFOLIO_HAIRCUTS,
    KH_HAIRCUTS,
    # FIFO tracker
    FIFOTracker,
    # Pension converter
    get_conversion_factor,
    get_conversion_age,
    # Cash flow resolution
    CashFlow,
    Person,
    is_cashflow_active,
    calc_cashflow_amount,
    resolve_date,
    # Config
    load_config,
    SimConfig,
    PortfolioConfig,
    PensionConfig,
    KerenConfig,
    # Simulation
    simulate,
    find_fire_month,
    add_month,
)


# ==================== FIFO Tracker ====================

class TestFIFOTracker:
    def test_initial_lot(self):
        """Initial balance creates one lot with correct cost basis."""
        tracker = FIFOTracker(1000, profit_fraction_pct=25)
        assert tracker.total_value == 1000
        assert tracker.total_cost_basis == 750  # 75% is cost basis
        assert len(tracker.lots) == 1

    def test_profit_fraction(self):
        """Profit fraction matches configured value."""
        tracker = FIFOTracker(1000, profit_fraction_pct=25)
        assert abs(tracker.profit_fraction - 0.25) < 0.001

    def test_add_lot_no_profit(self):
        """New deposits have cost basis = full amount (no profit)."""
        tracker = FIFOTracker(1000, profit_fraction_pct=25)
        tracker.add_lot(500)
        assert tracker.total_value == 1500
        assert tracker.total_cost_basis == 1250  # 750 + 500
        assert len(tracker.lots) == 2

    def test_sell_oldest_first(self):
        """FIFO: oldest (most profitable) lot is sold first."""
        tracker = FIFOTracker(1000, profit_fraction_pct=50)  # 50% profit
        tracker.add_lot(1000)  # new lot, 0% profit

        # Sell 500 from the old lot (50% profit)
        proceeds, tax = tracker.sell(500)
        assert proceeds == 500
        # Gain = 500 - 250 (cost basis) = 250, tax = 250 * 0.25 = 62.5
        assert abs(tax - 62.5) < 0.01

    def test_sell_crosses_lots(self):
        """Selling more than one lot depletes first, moves to next."""
        tracker = FIFOTracker(100, profit_fraction_pct=50)  # lot 1: 100, cost 50
        tracker.add_lot(200)  # lot 2: 200, cost 200

        # Sell 150: all of lot 1 (100) + 50 from lot 2
        proceeds, tax = tracker.sell(150)
        assert abs(proceeds - 150) < 0.01
        # Lot 1: gain = 100 - 50 = 50, tax = 12.5
        # Lot 2: gain = 50 - 50 = 0, tax = 0
        assert abs(tax - 12.5) < 0.01
        assert abs(tracker.total_value - 150) < 0.01  # 300 - 150

    def test_sell_depletes_all(self):
        """Selling entire balance leaves zero."""
        tracker = FIFOTracker(1000, profit_fraction_pct=25)
        proceeds, tax = tracker.sell(1000)
        assert abs(proceeds - 1000) < 0.01
        assert abs(tax - 62.5) < 0.01  # 250 gain * 25%
        assert abs(tracker.total_value) < 0.01
        assert len(tracker.lots) == 0

    def test_grow_preserves_cost_basis(self):
        """Growth increases value but not cost basis."""
        tracker = FIFOTracker(1000, profit_fraction_pct=0)  # all cost basis
        tracker.grow(0.01)  # 1% monthly growth
        assert abs(tracker.total_value - 1010) < 0.01
        assert abs(tracker.total_cost_basis - 1000) < 0.01
        assert tracker.profit_fraction > 0

    def test_declining_profit_fraction_over_time(self):
        """Profit fraction declines as high-profit lots are sold first."""
        tracker = FIFOTracker(1000, profit_fraction_pct=50)  # initial: 50% profit
        # Add deposits (0% profit)
        for _ in range(10):
            tracker.add_lot(100)

        initial_pf = tracker.profit_fraction
        tracker.sell(500)  # Sell from oldest (highest profit)
        after_pf = tracker.profit_fraction
        assert after_pf < initial_pf

    def test_zero_balance(self):
        """Tracker with zero balance works correctly."""
        tracker = FIFOTracker(0, profit_fraction_pct=0)
        assert tracker.total_value == 0
        assert tracker.profit_fraction == 0
        proceeds, tax = tracker.sell(100)
        assert proceeds == 0
        assert tax == 0


# ==================== Pension Converter ====================

class TestPensionConverter:
    @pytest.mark.parametrize("age,expected_factor", [
        pytest.param(60, 228, id="age_60"),
        pytest.param(65, 210, id="age_65"),
        pytest.param(67, 199, id="age_67"),
    ])
    def test_conversion_factor_exact(self, age, expected_factor):
        """Conversion factors match observed data at exact ages."""
        assert get_conversion_factor(age) == expected_factor

    def test_conversion_factor_interpolation(self):
        """Conversion factor interpolates between known ages."""
        factor = get_conversion_factor(63)
        assert 210 < factor < 228  # Between 60 and 65

    def test_conversion_factor_clamped(self):
        """Below 60 returns 60's factor, above 67 returns 67's factor."""
        assert get_conversion_factor(55) == 228
        assert get_conversion_factor(70) == 199

    def test_tactics_60(self):
        """Tactics '60': full conversion at 60."""
        person = Person("test", date(1988, 1, 1), "male")
        mukeret_age, mazka_age = get_conversion_age("60", person)
        assert mukeret_age == 60
        assert mazka_age is None

    def test_tactics_67_male(self):
        """Tactics '67': conversion at statutory retirement (67 for male)."""
        person = Person("test", date(1988, 1, 1), "male")
        mukeret_age, mazka_age = get_conversion_age("67", person)
        assert mukeret_age is None
        assert mazka_age == 67

    def test_tactics_67_female(self):
        """Tactics '67': conversion at statutory retirement (65 for female)."""
        person = Person("test", date(1992, 1, 1), "female")
        mukeret_age, mazka_age = get_conversion_age("67", person)
        assert mukeret_age is None
        assert mazka_age == 65

    def test_tactics_60_67_split(self):
        """Tactics '60-67': mukeret at 60, mazka at retirement age."""
        person = Person("test", date(1992, 1, 1), "female")
        mukeret_age, mazka_age = get_conversion_age("60-67", person)
        assert mukeret_age == 60
        assert mazka_age == 65  # Female retirement age


# ==================== Tax Calculator ====================

class TestTaxCalculator:
    def test_zero_income(self):
        """Zero income produces zero tax."""
        assert calc_annual_income_tax(0) == 0

    def test_first_bracket(self):
        """Income within first bracket taxed at 10%."""
        tax = calc_annual_income_tax(50_000)
        assert abs(tax - 5_000) < 1

    def test_multiple_brackets(self):
        """Income spanning multiple brackets taxed progressively."""
        tax = calc_annual_income_tax(150_000)
        # 84K * 10% + 36K * 14% + 30K * 20% = 8400 + 5040 + 6000 = 19440
        assert abs(tax - 19_440) < 1

    def test_high_income(self):
        """High income hits top bracket."""
        tax = calc_annual_income_tax(1_000_000)
        assert tax > 300_000  # Significant tax at high income

    def test_monthly_matches_annual(self):
        """Monthly tax is 1/12 of annual tax."""
        monthly = calc_monthly_income_tax(10_000)
        annual = calc_annual_income_tax(120_000)
        assert abs(monthly * 12 - annual) < 1

    def test_pension_tax_with_retirement_credit(self):
        """Retirees get tax credit reducing effective rate."""
        # Before retirement (age 60, male)
        tax_young = calc_pension_income_tax(15000, 60, "male")
        # After retirement (age 67, male)
        tax_old = calc_pension_income_tax(15000, 67, "male")
        # Retiree should pay less
        assert tax_old < tax_young

    def test_pension_tax_age_70_reduction(self):
        """Age 70+ gets additional tax reduction."""
        tax_67 = calc_pension_income_tax(15000, 67, "male")
        tax_70 = calc_pension_income_tax(15000, 70, "male")
        assert tax_70 < tax_67

    def test_bl_exempt_at_70(self):
        """Bituach Leumi is exempt at age 70+."""
        bl = calc_bituach_leumi(15000, 70, "male")
        assert bl == 0

    def test_bl_reduced_at_retirement(self):
        """BL rate is lower at retirement age."""
        bl_young = calc_bituach_leumi(15000, 60, "male")
        bl_old = calc_bituach_leumi(15000, 67, "male")
        assert bl_old < bl_young

    def test_mukeret_bl_before_retirement(self):
        """Mukeret has BL of ~3.7% before retirement age."""
        bl = calc_mukeret_bl(10000, 60, "male")  # Before 67
        assert abs(bl - 370) < 1  # 3.7%

    def test_mukeret_bl_after_retirement(self):
        """Mukeret BL is exempt after retirement age."""
        bl = calc_mukeret_bl(10000, 67, "male")
        assert bl == 0


# ==================== Growth Engine ====================

class TestGrowthEngine:
    def test_portfolio_pre_fire_rate(self):
        """Portfolio: compound monthly from (interest - fee) annual."""
        rate = get_portfolio_pre_fire_rate(5.0, 0.1)
        expected = (1 + 0.049) ** (1/12) - 1  # ~0.003994
        assert abs(rate - expected) < 1e-8
        # Verify compounding 12 times gives the annual rate
        assert abs((1 + rate) ** 12 - 1 - 0.049) < 1e-8

    def test_kh_pre_fire_rate(self):
        """KH: compound monthly from (interest - fee - hidden_fee) annual."""
        rate = get_kh_pre_fire_rate(5.0, 0.35)
        expected = (1 + 0.04) ** (1/12) - 1  # net 4.0%
        assert abs(rate - expected) < 1e-8
        assert abs((1 + rate) ** 12 - 1 - 0.04) < 1e-8

    def test_kaspit_rate_no_hidden_fee(self):
        """Kaspit: compound monthly from (interest - fee), no hidden fee."""
        rate = get_kaspit_rate(1.0, 0.2)
        expected = (1 + 0.008) ** (1/12) - 1  # net 0.8%
        assert abs(rate - expected) < 1e-8

    def test_pension_effective_rate(self):
        """Pension effective rate: (1+interest)*(1-mgmt_fee)-1."""
        # Mom's pension: interest=5%, management_fee=0.13%
        rate = get_pension_effective_rate(5.0, 0.13)
        expected = (1 + 5.0 / 100) * (1 - 0.13 / 100) - 1  # 4.8635%
        assert abs(rate - expected) < 1e-6
        # No management fee → full interest rate
        assert get_pension_effective_rate(5.0, 0) == 0.05

    @pytest.mark.parametrize("rule,expected_haircut", [
        pytest.param(85, 2.17, id="rule_85"),
        pytest.param(90, 2.44, id="rule_90"),
        pytest.param(95, 2.69, id="rule_95"),
        pytest.param(99, 2.87, id="rule_99"),
    ])
    def test_portfolio_haircut_exact(self, rule, expected_haircut):
        """Portfolio haircuts match observed data at exact retireRule values."""
        haircut = interpolate_haircut(rule, PORTFOLIO_HAIRCUTS)
        assert abs(haircut - expected_haircut) < 0.01

    def test_haircut_interpolation(self):
        """Haircuts interpolate between known retireRule values."""
        haircut = interpolate_haircut(87, PORTFOLIO_HAIRCUTS)
        assert PORTFOLIO_HAIRCUTS[85] < haircut < PORTFOLIO_HAIRCUTS[90]

    def test_haircut_clamping(self):
        """retireRule outside [80,99] is clamped."""
        haircut_low = interpolate_haircut(70, PORTFOLIO_HAIRCUTS)
        assert haircut_low == PORTFOLIO_HAIRCUTS[80]

        haircut_high = interpolate_haircut(100, PORTFOLIO_HAIRCUTS)
        assert haircut_high == PORTFOLIO_HAIRCUTS[99]

    def test_post_fire_rate_portfolio(self):
        """Post-FIRE portfolio rate is reduced by retireRule haircut."""
        pre_rate = (5.0 - 0.1) / 100  # 4.9%
        monthly = get_post_fire_rate("portfolio", pre_rate, 99)
        # haircut = 2.87%, so annual = 4.9% - 2.87% = 2.03%
        expected = annual_to_monthly(pre_rate - 0.0287)
        assert abs(monthly - expected) < 1e-8

    def test_post_fire_rate_pension_unchanged(self):
        """Pension rate is unchanged post-FIRE (no haircut)."""
        rate = 0.047
        monthly = get_post_fire_rate("pension", rate, 99)
        expected = annual_to_monthly(rate)
        assert abs(monthly - expected) < 1e-8

    def test_post_fire_rate_kaspit_unchanged(self):
        """Kaspit rate is unchanged post-FIRE."""
        rate = 0.008
        monthly = get_post_fire_rate("kaspit", rate, 99)
        expected = annual_to_monthly(rate)
        assert abs(monthly - expected) < 1e-8


# ==================== Cash Flow Resolution ====================

class TestCashFlowResolution:
    @pytest.fixture
    def persons(self):
        return [Person("Dad", date(1988, 1, 31), "male")]

    def test_now_resolves_to_sim_start(self, persons):
        cf = CashFlow(amount=1000, start="now", end="fire")
        start = resolve_date("now", date(2026, 3, 1), date(2030, 1, 1),
                             date(2070, 1, 1), None, persons, None, date(2026, 3, 1))
        assert start == date(2026, 3, 1)

    def test_fire_resolves_to_fire_date(self, persons):
        d = resolve_date("fire", date(2026, 3, 1), date(2035, 9, 1),
                         date(2070, 1, 1), None, persons, None, date(2026, 3, 1))
        assert d == date(2035, 9, 1)

    def test_forever_resolves_to_end(self, persons):
        d = resolve_date("forever", date(2026, 3, 1), date(2035, 9, 1),
                         date(2070, 1, 1), None, persons, None, date(2026, 3, 1))
        assert d == date(2070, 1, 1)

    def test_from_date_resolves_to_explicit(self, persons):
        d = resolve_date("from_date", date(2026, 3, 1), date(2035, 9, 1),
                         date(2070, 1, 1), date(2040, 6, 15), persons, None, date(2026, 3, 1))
        assert d == date(2040, 6, 15)

    def test_one_time_active_only_in_month(self, persons):
        cf = CashFlow(
            amount=100000, flow_type="one_time",
            start="from_date", end="from_date",
            start_date=date(2035, 12, 1)
        )
        # Active in December 2035
        assert is_cashflow_active(cf, date(2035, 12, 1), date(2026, 3, 1),
                                  date(2035, 9, 1), date(2070, 1, 1), persons)
        # Not active in January 2036
        assert not is_cashflow_active(cf, date(2036, 1, 1), date(2026, 3, 1),
                                      date(2035, 9, 1), date(2070, 1, 1), persons)

    def test_fire_dependent_changes_with_search(self, persons):
        """Cash flows ending at 'fire' should change active status when fire_date changes."""
        cf = CashFlow(amount=23000, start="now", end="fire")

        # With FIRE at Sep 2035: active in Aug 2035
        assert is_cashflow_active(cf, date(2035, 8, 1), date(2026, 3, 1),
                                  date(2035, 9, 1), date(2070, 1, 1), persons)
        # With FIRE at Sep 2035: inactive in Oct 2035
        assert not is_cashflow_active(cf, date(2035, 10, 1), date(2026, 3, 1),
                                      date(2035, 9, 1), date(2070, 1, 1), persons)

    def test_compound_interest_growth(self):
        """Amount grows with compound interest."""
        cf = CashFlow(amount=20000, rise=1.0)  # 1% annual rise
        # After 12 months: 20000 * (1 + 1/100/12)^12 ≈ 20000 * 1.01005 ≈ 20200.83
        amount = calc_cashflow_amount(cf, 12)
        assert abs(amount - 20000 * (1 + 0.01 / 12) ** 12) < 1

    def test_zero_rise(self):
        """Zero rise means constant amount."""
        cf = CashFlow(amount=18000, rise=0)
        assert calc_cashflow_amount(cf, 100) == 18000


# ==================== Add Month Utility ====================

class TestAddMonth:
    def test_basic_add(self):
        assert add_month(date(2026, 3, 1), 1) == date(2026, 4, 1)

    def test_year_wrap(self):
        assert add_month(date(2026, 11, 1), 3) == date(2027, 2, 1)

    def test_zero_months(self):
        assert add_month(date(2026, 3, 1), 0) == date(2026, 3, 1)

    def test_many_months(self):
        assert add_month(date(2026, 1, 1), 24) == date(2028, 1, 1)


# ==================== Config Loading ====================

class TestConfigLoading:
    def test_load_baseline(self):
        """Baseline config loads without errors."""
        config = load_config("scenarios/baseline.json")
        assert config.mode == "retire_asap"
        assert config.retire_rule == 99
        assert config.withdrawal_order == "prati"
        assert len(config.persons) == 2
        assert len(config.pensions) == 2
        assert len(config.kerens) == 5

    def test_load_d5(self):
        """D5 config loads without errors."""
        config = load_config("scenarios/d5_config.json")
        assert config.retire_rule == 80
        assert config.withdrawal_order == "hishtalmut"


# ==================== Integration: Simulation ====================

class TestSimulation:
    @pytest.fixture
    def baseline_config(self):
        return load_config("scenarios/baseline.json")

    def test_fire_search_finds_result(self, baseline_config):
        """FIRE search finds a valid retirement month."""
        fire_month, records = find_fire_month(baseline_config)
        assert fire_month > 0
        assert len(records) > 0

    def test_fire_month_nw_positive(self, baseline_config):
        """At the found FIRE month, all NW values are >= 0."""
        fire_month, records = find_fire_month(baseline_config)
        assert all(r.net_worth >= 0 for r in records)

    def test_earlier_fire_would_fail(self, baseline_config):
        """One month earlier should produce negative NW somewhere."""
        fire_month, _ = find_fire_month(baseline_config)
        if fire_month > 0:
            records = simulate(baseline_config, fire_month=fire_month - 1)
            min_nw = min(r.net_worth for r in records)
            assert min_nw < 0

    def test_pension_conversion_happens(self, baseline_config):
        """Pension converts to annuity at the expected age."""
        fire_month, records = find_fire_month(baseline_config)
        # Find first month with pension income
        pension_months = [r for r in records if r.pension_mukeret_total > 0]
        assert len(pension_months) > 0
        # Should be around age 60
        first_pension_age = pension_months[0].age
        assert 59.5 < first_pension_age < 61

    def test_old_age_starts_at_70(self, baseline_config):
        """Old age pension starts at age 70."""
        fire_month, records = find_fire_month(baseline_config)
        old_age_months = [r for r in records if r.old_age_total > 0]
        assert len(old_age_months) > 0
        assert 69.5 < old_age_months[0].age < 70.5

    def test_pre_fire_deposits(self, baseline_config):
        """Pre-FIRE months should have portfolio deposits."""
        fire_month, records = find_fire_month(baseline_config)
        pre_fire = [r for r in records if not r.is_post_fire]
        deposits = [r.deposit_portfolio for r in pre_fire]
        assert sum(deposits) > 0

    def test_post_fire_no_deposits(self, baseline_config):
        """Post-FIRE months should have no portfolio deposits."""
        fire_month, records = find_fire_month(baseline_config)
        post_fire = [r for r in records if r.is_post_fire]
        assert all(r.deposit_portfolio == 0 for r in post_fire)

    def test_baseline_fire_age_near_expected(self, baseline_config):
        """Baseline FIRE age should be near 47.9 (within ±3 months)."""
        fire_month, records = find_fire_month(baseline_config)
        fire_age = records[fire_month].age
        assert abs(fire_age - 47.9) < 0.3  # Within ~3 months

    def test_withdrawal_order_prati(self, baseline_config):
        """Prati order: portfolio is withdrawn before KH."""
        fire_month, records = find_fire_month(baseline_config)
        post_fire = [r for r in records if r.is_post_fire]

        # Find first month with portfolio withdrawal
        first_portfolio = next((r for r in post_fire if r.portfolio_withdrawal > 0), None)
        # Find first month with KH withdrawal
        first_kh = next((r for r in post_fire if sum(r.kh_withdrawals) > 0), None)

        if first_portfolio and first_kh:
            assert first_portfolio.month_idx <= first_kh.month_idx

    def test_goals_recorded(self, baseline_config):
        """One-time goals appear in the correct months."""
        fire_month, records = find_fire_month(baseline_config)
        goal_months = [r for r in records if r.goals > 0]
        assert len(goal_months) > 0
        total_goals = sum(r.goals for r in goal_months)
        assert abs(total_goals - 1_640_000) < 1000  # Total goals from config
