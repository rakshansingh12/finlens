"""
Database persistence for FinLens.

Uses SQLAlchemy Core for connection handling and safe parameter binding,
but writes explicit SQL rather than using the ORM -- the queries are part
of what this project is meant to demonstrate.
"""

import json
import os
from dataclasses import asdict

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from src.profile import FinancialProfile, LoanScenario, SimulationAssumptions

load_dotenv()


def get_engine():
    """Create a database engine from DATABASE_URL.

    Fails loudly if the variable is missing -- a silent fallback to some
    default connection string would be worse than a clear error.
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy .env.example to .env and fill it in."
        )
    return create_engine(url, future=True)


def save_profile(conn, profile: FinancialProfile) -> int:
    """Insert a financial profile and return its generated id."""
    result = conn.execute(
        text("""
            INSERT INTO financial_profiles
                (monthly_income, monthly_expenses, existing_emi,
                 savings, emergency_fund_target_months)
            VALUES
                (:income, :expenses, :existing_emi,
                 :savings, :target_months)
            RETURNING id
        """),
        {
            "income": profile.monthly_income,
            "expenses": profile.monthly_expenses,
            "existing_emi": profile.existing_emi,
            "savings": profile.savings,
            "target_months": profile.emergency_fund_target_months,
        },
    )
    return result.scalar_one()


def save_scenario(conn, profile_id: int, scenario: LoanScenario) -> int:
    """Insert a loan scenario against a profile and return its id."""
    result = conn.execute(
        text("""
            INSERT INTO loan_scenarios
                (profile_id, label, principal, annual_rate, tenure_years)
            VALUES
                (:profile_id, :label, :principal, :rate, :tenure)
            RETURNING id
        """),
        {
            "profile_id": profile_id,
            "label": scenario.label,
            "principal": scenario.principal,
            "rate": scenario.annual_rate,
            "tenure": scenario.tenure_years,
        },
    )
    return result.scalar_one()


def save_evaluation(conn, scenario_id: int, evaluation: dict, score: dict) -> int:
    """
    Cache a scenario's deterministic evaluation and stress score.

    ON CONFLICT re-evaluates in place rather than erroring, so re-running
    the pipeline is idempotent.
    """
    result = conn.execute(
        text("""
            INSERT INTO scenario_evaluations
                (scenario_id, emi, total_interest, total_repayment, total_emi,
                 debt_to_income, monthly_surplus, savings_rate,
                 emergency_fund_months, expense_coverage_months,
                 stress_score, stress_band, stress_components)
            VALUES
                (:scenario_id, :emi, :total_interest, :total_repayment, :total_emi,
                 :dti, :surplus, :savings_rate,
                 :ef_months, :expense_coverage,
                 :stress_score, :stress_band, CAST(:components AS JSONB))
            ON CONFLICT (scenario_id) DO UPDATE SET
                emi                     = EXCLUDED.emi,
                total_interest          = EXCLUDED.total_interest,
                total_repayment         = EXCLUDED.total_repayment,
                total_emi               = EXCLUDED.total_emi,
                debt_to_income          = EXCLUDED.debt_to_income,
                monthly_surplus         = EXCLUDED.monthly_surplus,
                savings_rate            = EXCLUDED.savings_rate,
                emergency_fund_months   = EXCLUDED.emergency_fund_months,
                expense_coverage_months = EXCLUDED.expense_coverage_months,
                stress_score            = EXCLUDED.stress_score,
                stress_band             = EXCLUDED.stress_band,
                stress_components       = EXCLUDED.stress_components,
                evaluated_at            = now()
            RETURNING id
        """),
        {
            "scenario_id": scenario_id,
            "emi": evaluation["emi"],
            "total_interest": evaluation["total_interest"],
            "total_repayment": evaluation["total_repayment"],
            "total_emi": evaluation["total_emi"],
            "dti": evaluation["debt_to_income"],
            "surplus": evaluation["monthly_surplus"],
            "savings_rate": evaluation["savings_rate"],
            "ef_months": evaluation["emergency_fund_months"],
            "expense_coverage": evaluation["expense_coverage_months"],
            "stress_score": score["stress_score"],
            "stress_band": score["band"],
            "components": json.dumps(score["components"]),
        },
    )
    return result.scalar_one()


def save_simulation(
    conn,
    scenario_id: int,
    total_emi: float,
    assumptions: SimulationAssumptions,
    results: dict,
) -> int:
    """
    Persist a simulation run and its results.

    The assumptions and seed are stored alongside the outputs precisely so
    a specific stochastic result can be reproduced later. Without this, a
    reported probability is not verifiable.
    """
    run_id = conn.execute(
        text("""
            INSERT INTO simulation_runs
                (scenario_id, n_trials, horizon_months, seed, assumptions, total_emi)
            VALUES
                (:scenario_id, :n_trials, :horizon, :seed,
                 CAST(:assumptions AS JSONB), :total_emi)
            RETURNING id
        """),
        {
            "scenario_id": scenario_id,
            "n_trials": assumptions.n_trials,
            "horizon": assumptions.horizon_months,
            "seed": assumptions.seed,
            "assumptions": json.dumps(asdict(assumptions)),
            "total_emi": total_emi,
        },
    ).scalar_one()

    conn.execute(
        text("""
            INSERT INTO simulation_results
                (run_id, p_negative_cashflow_month, p_thin_margin_month,
                 p_savings_depleted, median_negative_months, p95_negative_months,
                 mean_negative_months, median_thin_months, median_ending_savings,
                 p5_ending_savings, p25_ending_savings,
                 p5_min_monthly_surplus, median_min_monthly_surplus)
            VALUES
                (:run_id, :p_neg, :p_thin, :p_dep, :med_neg, :p95_neg,
                 :mean_neg, :med_thin, :med_end, :p5_end, :p25_end,
                 :p5_surplus, :med_surplus)
        """),
        {
            "run_id": run_id,
            "p_neg": results["p_negative_cashflow_month"],
            "p_thin": results["p_thin_margin_month"],
            "p_dep": results["p_savings_depleted"],
            "med_neg": results["median_negative_months"],
            "p95_neg": results["p95_negative_months"],
            "mean_neg": results["mean_negative_months"],
            "med_thin": results["median_thin_months"],
            "med_end": results["median_ending_savings"],
            "p5_end": results["p5_ending_savings"],
            "p25_end": results["p25_ending_savings"],
            "p5_surplus": results["p5_min_monthly_surplus"],
            "med_surplus": results["median_min_monthly_surplus"],
        },
    )

    return run_id


def load_scenario_comparison(conn, profile_id: int) -> list[dict]:
    """
    Fetch every scenario for a profile with its evaluation and latest
    simulation result, ready to serve as API evidence.

    Uses DISTINCT ON to pick only the most recent simulation run per
    scenario -- a Postgres-specific feature that avoids a window-function
    subquery for this common "latest row per group" pattern.
    """
    rows = conn.execute(
        text("""
            SELECT
                ls.label,
                ls.principal,
                ls.annual_rate,
                ls.tenure_years,
                se.emi,
                se.total_interest,
                se.debt_to_income,
                se.monthly_surplus,
                se.emergency_fund_months,
                se.stress_score,
                se.stress_band,
                se.stress_components,
                sr.p_savings_depleted,
                sr.mean_negative_months,
                sr.p5_ending_savings,
                run.seed,
                run.n_trials
            FROM loan_scenarios ls
            JOIN scenario_evaluations se ON se.scenario_id = ls.id
            LEFT JOIN LATERAL (
                SELECT * FROM simulation_runs r
                WHERE r.scenario_id = ls.id
                ORDER BY r.run_at DESC
                LIMIT 1
            ) run ON TRUE
            LEFT JOIN simulation_results sr ON sr.run_id = run.id
            WHERE ls.profile_id = :profile_id
            ORDER BY ls.id
        """),
        {"profile_id": profile_id},
    )
    return [dict(row._mapping) for row in rows]