"""
Monte Carlo simulation of household cash flow under uncertainty.

The deterministic engine answers "what does this loan cost?".
This module answers "how often does taking it go badly?".
"""

import numpy as np

from src.profile import FinancialProfile, SimulationAssumptions


def simulate_scenario(
    profile: FinancialProfile,
    total_emi: float,
    assumptions: SimulationAssumptions,
) -> dict:
    """
    Run N independent simulated futures for one loan scenario.

    Each trial walks month by month, drawing stochastic income and
    expenses, occasionally injecting a multi-month job loss or a one-off
    expense shock, and tracking the running savings balance.
    """
    rng = np.random.default_rng(assumptions.seed)

    n = assumptions.n_trials
    months = assumptions.horizon_months

    fixed_expenses = profile.monthly_expenses * (1 - assumptions.discretionary_expense_fraction)
    discretionary_expenses = profile.monthly_expenses * assumptions.discretionary_expense_fraction

    # Per-trial outcome trackers
    ever_negative_cashflow = np.zeros(n, dtype=bool)
    ever_thin_margin = np.zeros(n, dtype=bool)
    ever_savings_depleted = np.zeros(n, dtype=bool)
    min_surplus = np.full(n, np.inf)
    min_savings = np.full(n, np.inf)
    n_negative_months = np.zeros(n, dtype=int)
    n_thin_months = np.zeros(n, dtype=int)

    savings = np.full(n, float(profile.savings))
    # How many more months of job loss remain, per trial
    job_loss_remaining = np.zeros(n, dtype=int)

    for _ in range(months):
        # --- Job loss: start a new spell only where one isn't already running
        starts_job_loss = (
            (rng.random(n) < assumptions.job_loss_monthly_prob)
            & (job_loss_remaining == 0)
        )
        new_durations = rng.integers(
            assumptions.job_loss_min_months,
            assumptions.job_loss_max_months + 1,
            size=n,
        )
        job_loss_remaining = np.where(starts_job_loss, new_durations, job_loss_remaining)
        in_job_loss = job_loss_remaining > 0

        # --- Income: normal noise, reduced sharply during a job-loss spell
        income = rng.normal(
            profile.monthly_income,
            profile.monthly_income * assumptions.income_volatility,
            size=n,
        )
        income = np.where(
            in_job_loss, profile.monthly_income * assumptions.job_loss_income_fraction, income
        )
        income = np.maximum(income, 0.0)

        # --- Expenses: fixed + discretionary, discretionary compressed under shock
        discretionary = rng.normal(
            discretionary_expenses,
            discretionary_expenses * assumptions.expense_volatility,
            size=n,
        )
        discretionary = np.where(
            in_job_loss, discretionary * (1 - assumptions.shock_expense_compression), discretionary
        )
        expenses = np.maximum(fixed_expenses + discretionary, 0.0)

        # --- One-off expense shocks (medical, repairs), independent of job loss
        has_shock = rng.random(n) < assumptions.expense_shock_monthly_prob
        shock_size = rng.uniform(
            assumptions.expense_shock_min, assumptions.expense_shock_max, size=n
        )
        expenses = expenses + np.where(has_shock, shock_size, 0.0)

        # --- Cash flow and balance update. EMI is never compressed.
        surplus = income - expenses - total_emi
        savings = savings + surplus

        ever_negative_cashflow |= surplus < 0
        ever_thin_margin |= surplus < assumptions.thin_margin_threshold
        n_negative_months += (surplus < 0)
        n_thin_months += (surplus < assumptions.thin_margin_threshold)
        ever_savings_depleted |= savings < 0
        min_surplus = np.minimum(min_surplus, surplus)
        min_savings = np.minimum(min_savings, savings)

        job_loss_remaining = np.maximum(job_loss_remaining - 1, 0)

    return {
        "trials": n,
        "horizon_months": months,
        "p_negative_cashflow_month": round(float(ever_negative_cashflow.mean()), 4),
        "p_thin_margin_month": round(float(ever_thin_margin.mean()), 4),
        "p_savings_depleted": round(float(ever_savings_depleted.mean()), 4),
        "median_negative_months": int(np.median(n_negative_months)),
        "p95_negative_months": int(np.percentile(n_negative_months, 95)),
        "mean_negative_months": round(float(n_negative_months.mean()), 2),
        "median_thin_months": int(np.median(n_thin_months)),
        "median_ending_savings": round(float(np.median(savings)), 2),
        "p5_ending_savings": round(float(np.percentile(savings, 5)), 2),
        "p25_ending_savings": round(float(np.percentile(savings, 25)), 2),
        "p5_min_monthly_surplus": round(float(np.percentile(min_surplus, 5)), 2),
        "median_min_monthly_surplus": round(float(np.median(min_surplus)), 2),
    }

    """
    Run N independent simulated futures for one loan scenario.

    Reports both binary risk flags (did X ever happen) and counts
    (how often did X happen). Counts matter because over a 24-month
    horizon almost any household hits at least one bad month, so the
    binary flag saturates and stops discriminating between scenarios.
    """