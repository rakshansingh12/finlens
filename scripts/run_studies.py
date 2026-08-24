"""
Run all three FinLens empirical studies and print the results.

Usage (from repo root):
    python -m scripts.run_studies
"""

import numpy as np
from scipy import stats

from src.profile import FinancialProfile, LoanScenario, SimulationAssumptions
from src.engine import evaluate_scenario
from src.simulation import simulate_scenario
from src.studies import generate_population, run_population_study

POPULATION_SIZE = 600
TRIALS = 1500


def study_rq_a(rows: list[dict]) -> None:
    """How much does simulated risk vary within a fixed 'acceptable' DTI band?"""
    print("=" * 62)
    print("RQ-A: RISK SPREAD WITHIN A FIXED DTI BAND (33-37%)")
    print("=" * 62)

    band = [r for r in rows if 0.33 <= r["debt_to_income"] <= 0.37]
    depletion = np.array([r["p_savings_depleted"] for r in band])

    print(f"Households in band: {len(band)} (all would pass a conventional DTI check)")
    print()
    print("Simulated probability of savings depletion:")
    print(f"  min    : {depletion.min():.1%}")
    print(f"  p25    : {np.percentile(depletion, 25):.1%}")
    print(f"  median : {np.median(depletion):.1%}")
    print(f"  p75    : {np.percentile(depletion, 75):.1%}")
    print(f"  max    : {depletion.max():.1%}")
    print()

    low_liq = [r["p_savings_depleted"] for r in band if r["emergency_fund_months"] < 3]
    high_liq = [r["p_savings_depleted"] for r in band if r["emergency_fund_months"] >= 6]
    low_vol = [r["p_savings_depleted"] for r in band if r["income_volatility"] < 0.10]
    high_vol = [r["p_savings_depleted"] for r in band if r["income_volatility"] > 0.25]

    print("Same DTI band, split by factors DTI does not measure:")
    print(f"  liquidity < 3 months  : mean {np.mean(low_liq):.1%}  (n={len(low_liq)})")
    print(f"  liquidity >= 6 months : mean {np.mean(high_liq):.1%}  (n={len(high_liq)})")
    print(f"  income vol < 10%      : mean {np.mean(low_vol):.1%}  (n={len(low_vol)})")
    print(f"  income vol > 25%      : mean {np.mean(high_vol):.1%}  (n={len(high_vol)})")
    print()


def study_rq_b(rows: list[dict]) -> None:
    """Does the static stress score track simulated risk better than DTI alone?"""
    print("=" * 62)
    print("RQ-B: DOES THE STATIC SCORE TRACK SIMULATED RISK?")
    print("=" * 62)

    depletion = np.array([r["p_savings_depleted"] for r in rows])
    measures = {
        "Stress score": np.array([r["stress_score"] for r in rows]),
        "DTI alone": np.array([r["debt_to_income"] for r in rows]),
        "EF months alone": np.array([r["emergency_fund_months"] for r in rows]),
    }

    print(f"n = {len(rows)}")
    print()
    print("Spearman rank correlation with simulated depletion probability:")
    for name, values in measures.items():
        rho, p_value = stats.spearmanr(values, depletion)
        print(f"  {name:<18} rho = {rho:+.3f}   (p = {p_value:.2e})")
    print()
    print("Note: EF months correlates negatively by construction (more savings")
    print("= less risk). Some correlation is structural, since both the score")
    print("and the simulation take savings and expenses as inputs -- the claim")
    print("supported is 'good ranking proxy', not 'measures the same thing'.")
    print()


def study_sensitivity() -> None:
    """How much do the headline numbers depend on assumptions we invented?"""
    print("=" * 62)
    print("SENSITIVITY: HOW MUCH DO ASSUMPTIONS DRIVE THE RESULT?")
    print("=" * 62)

    profile = FinancialProfile(55000, 28000, 8000, 120000)
    evaluation = evaluate_scenario(profile, LoanScenario("A", 800000, 11, 5))
    total_emi = evaluation["total_emi"]

    baseline = simulate_scenario(profile, total_emi, SimulationAssumptions())
    base_p = baseline["p_savings_depleted"]

    print("Stretched profile (55k income, 28k expenses, 1.2L savings), 8L/5yr loan")
    print(f"Baseline P(savings depleted) under default assumptions: {base_p:.1%}")
    print()

    variants = [
        ("job-loss prob 1% (half)", dict(job_loss_monthly_prob=0.01)),
        ("job-loss prob 4% (double)", dict(job_loss_monthly_prob=0.04)),
        ("income vol 2.5% (half)", dict(income_volatility=0.025)),
        ("income vol 10% (double)", dict(income_volatility=0.10)),
        ("expense shock 1.5% (half)", dict(expense_shock_monthly_prob=0.015)),
        ("expense shock 6% (double)", dict(expense_shock_monthly_prob=0.06)),
        ("job-loss income 40% (2x)", dict(job_loss_income_fraction=0.40)),
        ("no expense compression", dict(shock_expense_compression=0.0)),
    ]

    print("Perturbing one assumption at a time:")
    for label, overrides in variants:
        result = simulate_scenario(
            profile, total_emi, SimulationAssumptions(**overrides)
        )
        value = result["p_savings_depleted"]
        print(f"  {label:<28} {value:>6.1%}   ({value - base_p:+.1%})")

    print()
    print("Interpretation: the headline probability is dominated by the")
    print("job-loss rate, an unvalidated assumption. Absolute probability")
    print("claims are therefore unsupported. Relative comparisons between")
    print("scenarios remain valid, since all share identical assumptions.")
    print()


def main() -> None:
    print()
    print(f"Generating population of {POPULATION_SIZE} household/loan combinations...")
    population = generate_population(POPULATION_SIZE)

    print(f"Simulating {TRIALS} trials each (this takes a moment)...")
    rows = run_population_study(population, n_trials=TRIALS)
    print()

    study_rq_a(rows)
    study_rq_b(rows)
    study_sensitivity()


if __name__ == "__main__":
    main()