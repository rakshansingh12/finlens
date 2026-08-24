"""
End-to-end FinLens pipeline: analyse a household's borrowing options
and persist every result.

Usage (from repo root):
    python -m scripts.run_pipeline
"""

from src.profile import FinancialProfile, LoanScenario, SimulationAssumptions
from src.engine import evaluate_scenario
from src.simulation import simulate_scenario
from src.scoring import borrowing_stress_score
from src.db import (
    get_engine,
    save_profile,
    save_scenario,
    save_evaluation,
    save_simulation,
    load_scenario_comparison,
)


def analyse_and_persist(profile, scenarios, assumptions):
    """Run the full analysis for one profile and store everything.

    All writes happen inside a single transaction: if any step fails,
    nothing is committed. A half-written analysis would be worse than
    none, since it would look complete.
    """
    engine = get_engine()

    with engine.begin() as conn:          # begin() = transactional block
        profile_id = save_profile(conn, profile)

        for scenario in scenarios:
            scenario_id = save_scenario(conn, profile_id, scenario)

            evaluation = evaluate_scenario(profile, scenario)
            score = borrowing_stress_score(
                evaluation, target_months=profile.emergency_fund_target_months
            )
            save_evaluation(conn, scenario_id, evaluation, score)

            simulation = simulate_scenario(
                profile, evaluation["total_emi"], assumptions
            )
            save_simulation(
                conn, scenario_id, evaluation["total_emi"], assumptions, simulation
            )

    return profile_id


def main():
    profile = FinancialProfile(
        monthly_income=55000,
        monthly_expenses=28000,
        existing_emi=8000,
        savings=120000,
    )

    scenarios = [
        LoanScenario("A: 8L / 5yr", 800000, 11, 5),
        LoanScenario("B: 5L / 5yr", 500000, 11, 5),
        LoanScenario("C: 8L / 7yr", 800000, 11, 7),
        LoanScenario("D: 8L / 5yr @ 9%", 800000, 9, 5),
    ]

    assumptions = SimulationAssumptions(n_trials=10_000, seed=42)

    print("Running analysis and persisting to database...")
    profile_id = analyse_and_persist(profile, scenarios, assumptions)
    print(f"Saved as profile_id = {profile_id}\n")

    # Read it back the way the API eventually will
    engine = get_engine()
    with engine.connect() as conn:
        rows = load_scenario_comparison(conn, profile_id)

    header = (
        f"{'Scenario':<18}{'EMI':>9}{'TotInt':>11}{'Stress':>8}"
        f"{'Band':>10}{'P(dep)':>9}{'AvgNeg':>8}"
    )
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['label']:<18}{r['emi']:>9,.0f}{r['total_interest']:>11,.0f}"
            f"{r['stress_score']:>8.1f}{r['stress_band']:>10}"
            f"{r['p_savings_depleted']:>9.1%}{r['mean_negative_months']:>8.1f}"
        )
    print()
    print(f"Reproducibility: seed={rows[0]['seed']}, trials={rows[0]['n_trials']:,}")


if __name__ == "__main__":
    main()