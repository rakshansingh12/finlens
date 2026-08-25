"""
FastAPI backend exposing the FinLens analytics engine.

Design notes:
 * /analyse runs synchronously. Simulation takes ~1-2s for typical inputs,
   which is acceptable for a request. n_trials is capped in the request
   model so a caller cannot hang the server -- bounding the input was
   preferred over building async job infrastructure this project does
   not need.
 * Every analysis is persisted. Beyond retrieval, this accumulates the
   evidence corpus the LLM faithfulness evaluation depends on.
"""
from src.evidence import compile_evidence
from src.explain import generate_explanation
from src.faithfulness import check_faithfulness

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

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

app = FastAPI(
    title="FinLens",
    description="Scenario-based personal financial decision intelligence.",
    version="0.1.0",
)


# --------------------------------------------------------------------------
# Request models. Field(...) constraints are enforced by FastAPI before our
# code runs -- invalid input gets a 422 with a precise message, and the
# engine never sees a negative income or a million-trial request.
# --------------------------------------------------------------------------

class ProfileIn(BaseModel):
    monthly_income: float = Field(..., gt=0, le=100_000_000)
    monthly_expenses: float = Field(..., ge=0, le=100_000_000)
    existing_emi: float = Field(0, ge=0, le=100_000_000)
    savings: float = Field(0, ge=0, le=1_000_000_000)
    emergency_fund_target_months: int = Field(6, gt=0, le=60)


class ScenarioIn(BaseModel):
    label: str = Field(..., min_length=1, max_length=100)
    principal: float = Field(..., gt=0, le=1_000_000_000)
    annual_rate: float = Field(..., ge=0, le=100)
    tenure_years: int = Field(..., gt=0, le=40)


class AssumptionsIn(BaseModel):
    """Optional overrides. Anything omitted uses the documented defaults."""
    horizon_months: int = Field(24, gt=0, le=360)
    n_trials: int = Field(10_000, gt=0, le=50_000)   # capped: see module docstring
    income_volatility: float = Field(0.05, ge=0, le=2.0)
    job_loss_monthly_prob: float = Field(0.02, ge=0, le=1.0)
    expense_shock_monthly_prob: float = Field(0.03, ge=0, le=1.0)
    seed: int | None = 42


class AnalyseRequest(BaseModel):
    profile: ProfileIn
    scenarios: list[ScenarioIn] = Field(..., min_length=1, max_length=8)
    assumptions: AssumptionsIn = AssumptionsIn()

class ExplainRequest(BaseModel):
    analysis: dict
    question: str | None = None
# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------

@app.get("/health")
def health():
    """Liveness check that also verifies database connectivity."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")


@app.post("/analyse")
def analyse(request: AnalyseRequest):
    """
    Evaluate a household's borrowing options and persist the analysis.

    Returns deterministic metrics, a stress score with its components,
    and simulated risk for every scenario, plus deltas against the first
    scenario as baseline.
    """
    profile = FinancialProfile(
        monthly_income=request.profile.monthly_income,
        monthly_expenses=request.profile.monthly_expenses,
        existing_emi=request.profile.existing_emi,
        savings=request.profile.savings,
        emergency_fund_target_months=request.profile.emergency_fund_target_months,
    )

    assumptions = SimulationAssumptions(
        horizon_months=request.assumptions.horizon_months,
        n_trials=request.assumptions.n_trials,
        income_volatility=request.assumptions.income_volatility,
        job_loss_monthly_prob=request.assumptions.job_loss_monthly_prob,
        expense_shock_monthly_prob=request.assumptions.expense_shock_monthly_prob,
        seed=request.assumptions.seed,
    )

    labels = [s.label for s in request.scenarios]
    if len(labels) != len(set(labels)):
        raise HTTPException(status_code=400, detail="Scenario labels must be unique.")

    results = []
    engine = get_engine()

    # Single transaction: a partially-written analysis would look complete
    # while being wrong, which is worse than a clean failure.
    with engine.begin() as conn:
        profile_id = save_profile(conn, profile)

        for scenario_in in request.scenarios:
            scenario = LoanScenario(
                label=scenario_in.label,
                principal=scenario_in.principal,
                annual_rate=scenario_in.annual_rate,
                tenure_years=scenario_in.tenure_years,
            )
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
            "total_interest_delta": round(
                r["total_interest"] - baseline["total_interest"], 2
            ),
            "stress_score_delta": round(
                r["stress_score"] - baseline["stress_score"], 2
            ),
            "depletion_risk_delta": round(
                r["simulation"]["p_savings_depleted"]
                - baseline["simulation"]["p_savings_depleted"],
                4,
            ),
        }
        for r in results[1:]
    ]

    return {
        "profile_id": profile_id,
        "baseline": baseline["label"],
        "scenarios": results,
        "comparisons": comparisons,
        "assumptions": assumptions.__dict__,
        "caveat": (
            "Absolute probabilities depend on unvalidated shock-rate "
            "assumptions and should not be read as calibrated forecasts. "
            "Relative comparisons between scenarios are supported, since "
            "all scenarios share identical assumptions."
        ),
    }


@app.get("/profiles/{profile_id}/scenarios")
def get_profile_scenarios(profile_id: int):
    """Retrieve a previously stored analysis."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = load_scenario_comparison(conn, profile_id)

    if not rows:
        raise HTTPException(status_code=404, detail=f"No analysis for profile {profile_id}.")

    return {"profile_id": profile_id, "scenarios": rows}


@app.post("/explain")
def explain(request: ExplainRequest):
    """
    Generate a grounded explanation of an analysis, with an automated
    faithfulness check on the output.

    The check result is returned alongside the explanation rather than
    hidden -- a consumer should be able to see whether the text can be
    trusted, not just read it.
    """
    evidence = compile_evidence(request.analysis)
    explanation = generate_explanation(evidence, request.question)
    faithfulness = check_faithfulness(explanation, evidence)

    return {
        "explanation": explanation,
        "faithfulness": faithfulness,
        "evidence_used": evidence,
    }