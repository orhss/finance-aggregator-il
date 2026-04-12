"""Retirement calculator endpoint."""

import logging
from datetime import date
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Response, status

from api.deps import CurrentUser, get_retirement_scenario_service
from api.schemas.retirement import (
    Milestone,
    MonthlyRow,
    ScenarioCreate,
    ScenarioResponse,
    ScenarioUpdate,
    SimulationResponse,
    SimulationSummary,
)
from services.retirement_scenario_service import RetirementScenarioService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/retirement", tags=["retirement"])


def _build_monthly_rows(
    records: list, config_obj: Any
) -> List[MonthlyRow]:
    """Convert MonthRecord list to API MonthlyRow list."""
    rows = []
    for rec in records:
        rows.append(
            MonthlyRow(
                month=rec.month_idx,
                age=round(rec.age, 2),
                date=rec.current_date.strftime("%Y-%m"),
                net_worth=round(rec.net_worth, 0),
                portfolio=round(rec.portfolio_value, 0),
                kh_values=[round(v, 0) for v in rec.kh_values],
                pension_values=[round(v, 0) for v in rec.pension_values],
                kaspit=round(rec.kaspit_value, 0),
                checking=round(rec.checking, 0),
                income=round(rec.income, 0),
                expenses=round(rec.expenses, 0),
                goals=round(rec.goals, 0),
                deposit=round(rec.deposit_portfolio, 0),
                withdrawal_portfolio=round(rec.portfolio_withdrawal, 0),
                withdrawal_kh=[round(v, 0) for v in rec.kh_withdrawals],
                pension_mukeret=[round(v, 0) for v in rec.pension_mukeret],
                pension_mazka=[round(v, 0) for v in rec.pension_mazka],
                old_age=[round(v, 0) for v in rec.old_age],
                income_tax=[round(v, 0) for v in rec.tax_per_person],
                bituach_leumi=[round(v, 0) for v in rec.bl_per_person],
                portfolio_tax=round(rec.portfolio_tax, 0),
            )
        )
    return rows


def _build_milestones(
    records: list, config_obj: Any, fire_month: int
) -> List[Milestone]:
    """Extract milestones from simulation records."""
    milestones: List[Milestone] = []
    sim_start = config_obj.start_date or date.today().replace(day=1)
    primary = config_obj.persons[0]
    start_age = primary.age_at(sim_start)

    # FIRE point
    if fire_month >= 0 and fire_month < len(records):
        rec = records[fire_month]
        milestones.append(
            Milestone(
                age=round(rec.age, 1),
                date=rec.current_date.strftime("%Y-%m"),
                type="fire",
                label="FIRE",
            )
        )

    # Pension conversions
    pension_started = set()
    for rec in records:
        for pi, person in enumerate(config_obj.persons):
            muk = rec.pension_mukeret[pi] if pi < len(rec.pension_mukeret) else 0
            maz = rec.pension_mazka[pi] if pi < len(rec.pension_mazka) else 0
            if (muk > 0 or maz > 0) and pi not in pension_started:
                pension_started.add(pi)
                person_age = person.age_at(rec.current_date)
                milestones.append(
                    Milestone(
                        age=round(person_age, 1),
                        chart_age=round(rec.age, 1),
                        date=rec.current_date.strftime("%Y-%m"),
                        type="pension_conversion",
                        label=f"Pension starts ({person.name})",
                        person=person.name,
                    )
                )

    # Old age pension
    old_age_started = set()
    for rec in records:
        for pi, person in enumerate(config_obj.persons):
            oa = rec.old_age[pi] if pi < len(rec.old_age) else 0
            if oa > 0 and pi not in old_age_started:
                old_age_started.add(pi)
                person_age = person.age_at(rec.current_date)
                milestones.append(
                    Milestone(
                        age=round(person_age, 1),
                        chart_age=round(rec.age, 1),
                        date=rec.current_date.strftime("%Y-%m"),
                        type="old_age_start",
                        label=f"Social Security ({person.name})",
                        person=person.name,
                    )
                )

    # Portfolio depletion
    if fire_month >= 0:
        for rec in records[fire_month:]:
            if rec.portfolio_value <= 0:
                milestones.append(
                    Milestone(
                        age=round(rec.age, 1),
                        date=rec.current_date.strftime("%Y-%m"),
                        type="portfolio_depleted",
                        label="Portfolio depleted",
                    )
                )
                break

    # KH depletion (per fund) — only for funds that were ever positive
    if fire_month >= 0:
        kh_ever_positive: set = set()
        for rec in records:
            for ki, v in enumerate(rec.kh_values):
                if v > 0:
                    kh_ever_positive.add(ki)

        kh_depleted: set = set()
        for rec in records[fire_month:]:
            for ki, v in enumerate(rec.kh_values):
                if v <= 0 and ki not in kh_depleted and ki in kh_ever_positive:
                    kh_depleted.add(ki)
                    milestones.append(
                        Milestone(
                            age=round(rec.age, 1),
                            date=rec.current_date.strftime("%Y-%m"),
                            type="kh_depleted",
                            label=f"KH {ki + 1} depleted",
                        )
                    )

    # One-time expenses (goals)
    for rec in records:
        if rec.goals > 0:
            milestones.append(
                Milestone(
                    age=round(rec.age, 1),
                    date=rec.current_date.strftime("%Y-%m"),
                    type="one_time_expense",
                    label="One-time expense",
                    amount=round(rec.goals, 0),
                )
            )

    milestones.sort(key=lambda m: m.age)
    return milestones


def _build_summary(
    records: list,
    config_obj: Any,
    fire_month: int,
) -> SimulationSummary:
    """Build summary from simulation records."""
    sim_start = config_obj.start_date or date.today().replace(day=1)
    primary = config_obj.persons[0]
    start_age = primary.age_at(sim_start)

    clamped = min(fire_month, len(records) - 1)
    fire_rec = records[clamped]
    fire_age = start_age + fire_month / 12
    fire_date = fire_rec.current_date.strftime("%Y-%m")

    post_fire = records[clamped:]
    min_nw = min(r.net_worth for r in post_fire)
    min_nw_rec = next(r for r in post_fire if r.net_worth == min_nw)
    end_rec = records[-1]

    # Portfolio depletion age
    portfolio_depletion_age = None
    for r in post_fire:
        if r.portfolio_value <= 0:
            portfolio_depletion_age = round(r.age, 1)
            break

    # Pension start ages (per person — each person's own age)
    pension_start_ages = []
    for pi, person in enumerate(config_obj.persons):
        found = False
        for r in records:
            muk = r.pension_mukeret[pi] if pi < len(r.pension_mukeret) else 0
            maz = r.pension_mazka[pi] if pi < len(r.pension_mazka) else 0
            if muk > 0 or maz > 0:
                pension_start_ages.append(round(person.age_at(r.current_date), 1))
                found = True
                break
        if not found:
            pension_start_ages.append(0)

    # Old age start ages (per person — each person's own age)
    old_age_start_ages = []
    for pi, person in enumerate(config_obj.persons):
        found = False
        for r in records:
            oa = r.old_age[pi] if pi < len(r.old_age) else 0
            if oa > 0:
                old_age_start_ages.append(round(person.age_at(r.current_date), 1))
                found = True
                break
        if not found:
            old_age_start_ages.append(0)

    # Withdrawal rate at FIRE
    if fire_rec.net_worth > 0 and fire_rec.expenses > 0:
        withdrawal_rate = (fire_rec.expenses * 12) / fire_rec.net_worth * 100
    else:
        withdrawal_rate = 0

    return SimulationSummary(
        fire_age=round(fire_age, 1),
        fire_date=fire_date,
        fire_month_index=fire_month,
        years_to_fire=round(fire_age - start_age, 1),
        min_nw=round(min_nw, 0),
        min_nw_age=round(min_nw_rec.age, 1),
        end_nw=round(end_rec.net_worth, 0),
        end_age=round(end_rec.age, 1),
        portfolio_depletion_age=portfolio_depletion_age,
        pension_start_ages=pension_start_ages,
        old_age_start_ages=old_age_start_ages,
        withdrawal_rate_at_fire=round(withdrawal_rate, 1),
    )


@router.post("/simulate", response_model=SimulationResponse)
def simulate(
    config: Dict[str, Any],
    _: str = CurrentUser,
):
    """Run the retirement simulation with the given config."""
    from services.retirement_calculator import find_fire_month, parse_config, simulate as run_sim

    config_obj = parse_config(config)

    # Find FIRE month
    fire_month, records = find_fire_month(config_obj, verbose=False)

    if fire_month < 0:
        # Impossible — run with forced retirement at max age
        primary = config_obj.persons[0]
        sim_start = config_obj.start_date or date.today().replace(day=1)
        start_age = primary.age_at(sim_start)
        max_months = int((config_obj.max_retire_age - start_age) * 12)
        records = run_sim(config_obj, fire_month=max_months)
        fire_month = max_months
        sim_status = "impossible"
    else:
        sim_status = "success"

    persons = [p.name for p in config_obj.persons]
    monthly = _build_monthly_rows(records, config_obj)
    milestones = _build_milestones(records, config_obj, fire_month)
    summary = _build_summary(records, config_obj, fire_month)

    return SimulationResponse(
        status=sim_status,
        summary=summary,
        monthly=monthly,
        milestones=milestones,
        persons=persons,
    )


# ==================== Scenario CRUD ====================

def _to_response(scenario) -> ScenarioResponse:
    return ScenarioResponse(
        id=scenario.id,
        name=scenario.name,
        config=scenario.config,
        created_at=scenario.created_at.isoformat() if scenario.created_at else "",
        updated_at=scenario.updated_at.isoformat() if scenario.updated_at else None,
    )


@router.get("/scenarios", response_model=List[ScenarioResponse])
def list_scenarios(
    _: str = CurrentUser,
    svc: RetirementScenarioService = Depends(get_retirement_scenario_service),
):
    """List all retirement scenarios."""
    return [_to_response(s) for s in svc.list_scenarios()]


@router.post(
    "/scenarios",
    response_model=ScenarioResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_scenario(
    body: ScenarioCreate,
    _: str = CurrentUser,
    svc: RetirementScenarioService = Depends(get_retirement_scenario_service),
):
    """Create a new retirement scenario."""
    scenario = svc.create_scenario(name=body.name, config=body.config)
    return _to_response(scenario)


@router.patch("/scenarios/{scenario_id}", response_model=ScenarioResponse)
def update_scenario(
    scenario_id: int,
    body: ScenarioUpdate,
    _: str = CurrentUser,
    svc: RetirementScenarioService = Depends(get_retirement_scenario_service),
):
    """Partially update a retirement scenario (name and/or config)."""
    scenario = svc.update_scenario(
        scenario_id,
        name=body.name,
        config=body.config,
    )
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return _to_response(scenario)


@router.delete(
    "/scenarios/{scenario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_scenario(
    scenario_id: int,
    _: str = CurrentUser,
    svc: RetirementScenarioService = Depends(get_retirement_scenario_service),
):
    """Delete a retirement scenario."""
    if not svc.delete_scenario(scenario_id):
        raise HTTPException(status_code=404, detail="Scenario not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
