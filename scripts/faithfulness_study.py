"""
RQ-C: evaluate whether LLM explanations stay grounded in computed evidence.

Runs the explanation layer across varied household/loan analyses and
reports aggregate faithfulness. Uses the strict checker, which is known
to over-flag scale references such as the literal 100 in "out of 100" --
see docs/findings.md. That over-flagging is retained deliberately: a
checker tuned until it reports success would defeat the purpose.

Usage (from repo root):
    python -m scripts.run_faithfulness_study
"""

import json
import time
from collections import Counter

import numpy as np

from src.profile import FinancialProfile, LoanScenario, SimulationAssumptions
from src.engine import evaluate_scenario
from src.simulation import simulate_scenario
from src.scoring import borrowing_stress_score
from src.evidence import compile_evidence
from src.explain import generate_explanation
from src.faithfulness import check_faithfulness

N_CASES = 20
QUESTIONS = [
    None,
    "Should I be worried about taking the larger loan?",
    "Which option leaves me with the most breathing room?",
    "What is the main risk here?",
]


def build_analysis(profile, scenarios, assumptions):
    """Reproduce the /analyse payload shape without the HTTP layer."""
    results = []
    for scenario in scenarios:
        evaluation = evaluate_scenario(profile, scenario)
        score = borrowing_stress_score(evaluation)
        simulation = simulate_scenario(profile, evaluation["total_emi"], assumptions)
        results.append({
            **evaluation,
            "stress_score": score["stress_score"],
            "stress_band": score["band"],
            "stress_components": score["components"],
            "largest_stress_contributor": score["largest_contributor"],
            "simulation": simulation,
        })

    baseline = results[0]
    comparisons = [
        {
            "label": r["label"],
            "vs_baseline": baseline["label"],
            "emi_delta": round(r["emi"] - baseline["emi"], 2),
            "total_interest_delta": round(r["total_interest"] - baseline["total_interest"], 2),
            "stress_score_delta": round(r["stress_score"] - baseline["stress_score"], 2),
            "depletion_risk_delta": round(
                r["simulation"]["p_savings_depleted"]
                - baseline["simulation"]["p_savings_depleted"], 4
            ),
        }
        for r in results[1:]
    ]

    return {
        "baseline": baseline["label"],
        "scenarios": results,
        "comparisons": comparisons,
        "assumptions": assumptions.__dict__,
        "caveat": (
            "Absolute probabilities depend on unvalidated shock-rate assumptions "
            "and should not be read as calibrated forecasts. Relative comparisons "
            "between scenarios are supported, since all scenarios share identical "
            "assumptions."
        ),
    }


def generate_cases(n, seed=11):
    """Sample varied households and loan pairs to exercise a range of outputs."""
    rng = np.random.default_rng(seed)
    cases = []
    for i in range(n):
        income = float(rng.uniform(35_000, 150_000))
        expenses = income * float(rng.uniform(0.25, 0.55))
        profile = FinancialProfile(
            monthly_income=income,
            monthly_expenses=expenses,
            existing_emi=income * float(rng.uniform(0, 0.15)),
            savings=expenses * float(rng.uniform(0.5, 15)),
        )
        principal = float(rng.uniform(300_000, 1_500_000))
        rate = float(rng.uniform(9, 16))
        tenure = int(rng.integers(3, 8))
        cases.append({
            "profile": profile,
            "scenarios": [
                LoanScenario("A", principal, rate, tenure),
                LoanScenario("B", principal * 0.65, rate, tenure),
            ],
            "question": QUESTIONS[i % len(QUESTIONS)],
        })
    return cases


def main():
    assumptions = SimulationAssumptions(n_trials=3000, seed=42)
    cases = generate_cases(N_CASES)

    rates, failures, all_unsupported = [], 0, []
    records = []

    print(f"Running {N_CASES} explanation cases...\n")

    for i, case in enumerate(cases, start=1):
        analysis = build_analysis(case["profile"], case["scenarios"], assumptions)
        evidence = compile_evidence(analysis)

        try:
            explanation = generate_explanation(evidence, case["question"])
        except Exception as exc:
            print(f"  case {i:2d}: API error -- {exc}")
            continue

        result = check_faithfulness(explanation, evidence)
        rates.append(result["faithfulness_rate"])
        if not result["passed"]:
            failures += 1
            all_unsupported.extend(result["unsupported_values"])

        print(
            f"  case {i:2d}: {result['numbers_supported']}/{result['numbers_checked']} "
            f"= {result['faithfulness_rate']:.1%}"
            + ("" if result["passed"] else f"  unsupported: {result['unsupported_values']}")
        )

        records.append({
            "case": i,
            "question": case["question"],
            "explanation": explanation,
            "faithfulness": result,
        })

        time.sleep(1)   # stay well inside free-tier rate limits

    rates = np.array(rates)
    print()
    print("=" * 58)
    print("RQ-C: LLM EXPLANATION FAITHFULNESS")
    print("=" * 58)
    print(f"Cases evaluated        : {len(rates)}")
    print(f"Mean faithfulness rate : {rates.mean():.1%}")
    print(f"Median                 : {np.median(rates):.1%}")
    print(f"Minimum                : {rates.min():.1%}")
    print(f"Cases with 100% rate   : {(rates == 1.0).sum()} / {len(rates)}")
    print(f"Cases with any failure : {failures} / {len(rates)}")
    print()
    if all_unsupported:
        print("Most common unsupported values:")
        for value, count in Counter(all_unsupported).most_common(10):
            print(f"  {value:>14,.2f}  x{count}")
        print()
        print("Note: the strict checker flags scale references (e.g. the literal")
        print("100 in 'out of 100') as unsupported. These are false positives and")
        print("are retained rather than special-cased -- see docs/findings.md.")

    with open("docs/faithfulness_results.json", "w") as f:
        json.dump(records, f, indent=2)
    print()
    print("Full transcripts written to docs/faithfulness_results.json")


if __name__ == "__main__":
    main()