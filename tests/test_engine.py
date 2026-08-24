"""Tests for the deterministic financial engine."""

import pytest

from src.profile import FinancialProfile, LoanScenario, SimulationAssumptions
from src.engine import (
    calculate_emi,
    generate_amortization_schedule,
    total_interest_paid,
    calculate_affordability,
    evaluate_scenario,
    compare_scenarios,
)
from src.simulation import simulate_scenario
from src.engine import evaluate_scenario
from src.scoring import (
    borrowing_stress_score,
    score_debt_burden,
    score_liquidity,
    score_interest_load,
    WEIGHTS,
)

def test_emi_standard_loan():
    """8L at 11% over 5 years should produce ~17,394/month.

    Reference value cross-checked against standard EMI calculators.
    """
    emi = calculate_emi(principal=800000, annual_rate=11, tenure_years=5)
    assert emi == pytest.approx(17393.94, abs=0.01)


def test_emi_zero_interest():
    """With no interest, the principal is simply split evenly."""
    emi = calculate_emi(principal=120000, annual_rate=0, tenure_years=1)
    assert emi == pytest.approx(10000.00, abs=0.01)


def test_longer_tenure_lowers_emi():
    """A longer tenure spreads repayment out, so each payment is smaller.

    This is a *property* test -- it doesn't hardcode a value, it asserts
    a relationship that must hold regardless of the exact numbers.
    """
    emi_5yr = calculate_emi(800000, 11, 5)
    emi_7yr = calculate_emi(800000, 11, 7)
    assert emi_7yr < emi_5yr


def test_longer_tenure_raises_total_interest():
    """But a longer tenure means paying interest for longer, so total cost rises.

    This is the core trade-off FinLens exists to make visible to users.
    """
    total_5yr = calculate_emi(800000, 11, 5) * 60
    total_7yr = calculate_emi(800000, 11, 7) * 84
    assert total_7yr > total_5yr


def test_schedule_has_correct_length():
    schedule = generate_amortization_schedule(800000, 11, 5)
    assert len(schedule) == 60


def test_schedule_ends_at_zero_balance():
    """The whole point of the EMI formula: balance hits exactly zero at term end."""
    schedule = generate_amortization_schedule(800000, 11, 5)
    assert schedule[-1]["balance"] == pytest.approx(0.0, abs=0.01)


def test_interest_component_decreases_over_time():
    """Interest shrinks each month because the outstanding balance shrinks."""
    schedule = generate_amortization_schedule(800000, 11, 5)
    assert schedule[0]["interest"] > schedule[30]["interest"] > schedule[-1]["interest"]


def test_principal_component_increases_over_time():
    """The mirror image: more of each fixed EMI goes to principal over time."""
    schedule = generate_amortization_schedule(800000, 11, 5)
    assert schedule[0]["principal"] < schedule[30]["principal"] < schedule[-1]["principal"]


def test_total_interest_matches_emi_shortcut():
    """Cross-check: summing the schedule should match (EMI * n - principal).

    Two independent derivations agreeing is strong evidence both are right.
    """
    schedule = generate_amortization_schedule(800000, 11, 5)
    emi = calculate_emi(800000, 11, 5)
    assert total_interest_paid(schedule) == pytest.approx(emi * 60 - 800000, abs=1.0)


def test_affordability_matches_spec_example():
    profile = FinancialProfile(
        monthly_income=80000,
        monthly_expenses=20000,
        existing_emi=10000,
        savings=300000,
    )

    result = calculate_affordability(profile, new_emi=17393.94)

    assert result["total_emi"] == pytest.approx(27393.94, abs=0.01)
    assert result["debt_to_income"] == pytest.approx(0.3424, abs=0.001)
    assert result["monthly_surplus"] == pytest.approx(32606.06, abs=0.01)
    assert result["emergency_fund_months"] == pytest.approx(6.33, abs=0.01)
    assert result["expense_coverage_months"] == pytest.approx(15.0, abs=0.01)


def test_affordability_handles_zero_income():
    """A degenerate profile shouldn't crash -- ratios should be None, not a ZeroDivisionError."""
    profile = FinancialProfile(
        monthly_income=0,
        monthly_expenses=20000,
        existing_emi=0,
        savings=100000,
    )

    result = calculate_affordability(profile, new_emi=5000)

    assert result["debt_to_income"] is None
    assert result["savings_rate"] is None


def test_evaluate_scenario_merges_loan_and_affordability():
    profile = FinancialProfile(80000, 20000, 10000, 300000)
    scenario = LoanScenario("A", 800000, 11, 5)

    result = evaluate_scenario(profile, scenario)

    assert result["emi"] == pytest.approx(17393.94, abs=0.01)
    assert result["total_interest"] == pytest.approx(243636.30, abs=1.0)
    assert result["debt_to_income"] == pytest.approx(0.3424, abs=0.001)


def test_baseline_is_excluded_from_comparisons():
    """Comparisons hold only non-baseline scenarios, since a baseline
    has no meaningful delta against itself."""
    profile = FinancialProfile(80000, 20000, 10000, 300000)
    scenarios = [LoanScenario("A", 800000, 11, 5), LoanScenario("B", 600000, 11, 5)]

    out = compare_scenarios(profile, scenarios)

    assert out["baseline"] == "A"
    assert len(out["scenarios"]) == 2        # both evaluated
    assert len(out["comparisons"]) == 1      # only B compared
    assert out["comparisons"][0]["label"] == "B"
    assert out["comparisons"][0]["vs_baseline"] == "A"


def test_smaller_loan_saves_interest_and_improves_liquidity():
    profile = FinancialProfile(80000, 20000, 10000, 300000)
    scenarios = [LoanScenario("A", 800000, 11, 5), LoanScenario("B", 600000, 11, 5)]

    smaller = compare_scenarios(profile, scenarios)["comparisons"][0]

    assert smaller["total_interest_delta"] < 0
    assert smaller["emergency_fund_months_delta"] > 0


def test_longer_tenure_lowers_emi_but_raises_total_interest():
    """The core trade-off: cheaper monthly, more expensive overall."""
    profile = FinancialProfile(80000, 20000, 10000, 300000)
    scenarios = [LoanScenario("A", 800000, 11, 5), LoanScenario("C", 800000, 11, 7)]

    longer = compare_scenarios(profile, scenarios)["comparisons"][0]

    assert longer["emi_delta"] < 0
    assert longer["total_interest_delta"] > 0


def test_empty_scenario_list_raises():
    profile = FinancialProfile(80000, 20000, 10000, 300000)
    with pytest.raises(ValueError):
        compare_scenarios(profile, [])

def test_simulation_is_reproducible_with_a_seed():
    """Same seed must give identical results, or nothing downstream is verifiable."""
    profile = FinancialProfile(80000, 20000, 10000, 300000)
    a = SimulationAssumptions(n_trials=1000, seed=42)

    first = simulate_scenario(profile, 27393.94, a)
    second = simulate_scenario(profile, 27393.94, a)

    assert first == second


def test_different_seeds_give_different_results():
    profile = FinancialProfile(80000, 20000, 10000, 300000)
    r1 = simulate_scenario(profile, 27393.94, SimulationAssumptions(n_trials=1000, seed=1))
    r2 = simulate_scenario(profile, 27393.94, SimulationAssumptions(n_trials=1000, seed=2))

    assert r1["median_ending_savings"] != r2["median_ending_savings"]


def test_larger_emi_increases_risk():
    """A property test: more debt service must not reduce simulated risk."""
    profile = FinancialProfile(55000, 28000, 8000, 120000)
    a = SimulationAssumptions(n_trials=2000)

    small = simulate_scenario(profile, 15000, a)
    large = simulate_scenario(profile, 30000, a)

    assert large["p_savings_depleted"] >= small["p_savings_depleted"]
    assert large["mean_negative_months"] >= small["mean_negative_months"]


def test_probabilities_are_valid():
    profile = FinancialProfile(80000, 20000, 10000, 300000)
    result = simulate_scenario(profile, 27393.94, SimulationAssumptions(n_trials=1000))

    for key in ["p_negative_cashflow_month", "p_thin_margin_month", "p_savings_depleted"]:
        assert 0.0 <= result[key] <= 1.0


def test_negative_month_count_within_horizon():
    profile = FinancialProfile(55000, 28000, 8000, 120000)
    a = SimulationAssumptions(n_trials=1000, horizon_months=24)
    result = simulate_scenario(profile, 25000, a)

    assert 0 <= result["median_negative_months"] <= 24
    assert 0 <= result["p95_negative_months"] <= 24

def test_weights_sum_to_one():
    """If weights don't sum to 1, the composite isn't on a 0-100 scale."""
    assert sum(WEIGHTS.values()) == pytest.approx(1.0)


def test_score_bounded_zero_to_hundred():
    profile = FinancialProfile(55000, 28000, 8000, 50000)
    result = borrowing_stress_score(evaluate_scenario(profile, LoanScenario("X", 900000, 14, 3)))
    assert 0 <= result["stress_score"] <= 100


def test_higher_dti_scores_higher_stress():
    assert score_debt_burden(0.50) > score_debt_burden(0.30)


def test_more_liquidity_scores_lower_stress():
    assert score_liquidity(12) < score_liquidity(6) < score_liquidity(1)


def test_missing_ratios_score_maximum_stress():
    """A None ratio means a degenerate profile -- treat as maximum stress,
    never as zero stress, which would be dangerously wrong."""
    assert score_debt_burden(None) == 100.0
    assert score_liquidity(None) == 100.0


def test_stretched_profile_scores_higher_than_comfortable():
    comfortable = FinancialProfile(80000, 20000, 10000, 300000)
    stretched = FinancialProfile(55000, 28000, 8000, 120000)
    loan = LoanScenario("A", 800000, 11, 5)

    c = borrowing_stress_score(evaluate_scenario(comfortable, loan))["stress_score"]
    s = borrowing_stress_score(evaluate_scenario(stretched, loan))["stress_score"]

    assert s > c


def test_components_are_exposed():
    """The score must never be a black box -- components drive explainability."""
    profile = FinancialProfile(80000, 20000, 10000, 300000)
    result = borrowing_stress_score(evaluate_scenario(profile, LoanScenario("A", 800000, 11, 5)))

    assert set(result["components"]) == set(WEIGHTS)
    assert result["largest_contributor"] in WEIGHTS


def test_zero_interest_loan_has_no_interest_load():
    assert score_interest_load(0, 500000) == 0.0