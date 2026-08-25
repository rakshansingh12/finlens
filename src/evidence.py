"""
Compile analysis output into a minimal, self-contained evidence set.

Deliberately narrower than the full API payload. Every number the LLM
could reasonably need -- including derived deltas -- is pre-computed here,
so the model never has to do arithmetic and any number it states that is
not present in this object is unsupported by construction.
"""


def compile_evidence(analysis: dict) -> dict:
    """
    Args:
        analysis: the payload returned by the /analyse endpoint

    Returns:
        A trimmed evidence object safe to pass to an LLM.
    """
    scenarios = []
    for s in analysis["scenarios"]:
        sim = s["simulation"]
        scenarios.append({
            "label": s["label"],
            "loan_amount": s["principal"],
            "annual_rate_percent": s["annual_rate"],
            "tenure_years": s["tenure_years"],
            "monthly_emi": s["emi"],
            "total_emi_including_existing": s["total_emi"],
            "total_interest": s["total_interest"],
            "total_repayment": s["total_repayment"],
            "debt_to_income_ratio": s["debt_to_income"],
            "monthly_surplus": s["monthly_surplus"],
            "emergency_fund_months": s["emergency_fund_months"],
            "stress_score_out_of_100": s["stress_score"],
            "stress_band": s["stress_band"],
            "largest_stress_driver": s["largest_stress_contributor"],
            "simulated_depletion_probability_percent": round(
                sim["p_savings_depleted"] * 100, 1
            ),
            "simulated_median_negative_months": sim["median_negative_months"],
            "simulated_worst_case_ending_savings": sim["p5_ending_savings"],
        })

    return {
        "baseline_scenario": analysis["baseline"],
        "scenarios": scenarios,
        "comparisons_vs_baseline": analysis["comparisons"],
        "simulation_settings": {
            "trials": analysis["assumptions"]["n_trials"],
            "horizon_months": analysis["assumptions"]["horizon_months"],
        },
        "important_caveat": analysis["caveat"],
    }