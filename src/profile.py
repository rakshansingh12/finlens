from dataclasses import dataclass

@dataclass
class FinancialProfile:
    monthly_income: float
    monthly_expenses: float
    existing_emi: float
    savings: float
    emergency_fund_target_months: int = 6

@dataclass
class LoanScenario:
    label: str
    principal: float
    annual_rate: float
    tenure_years: int

@dataclass
class SimulationAssumptions:
    """Every assumption the Monte Carlo makes, in one auditable place.

    These are defensible defaults, not measured facts. Sensitivity analysis
    re-runs the simulation under perturbed versions of these values to show
    how much the conclusions actually depend on them.
    """
    horizon_months: int = 24
    n_trials: int = 10_000

    income_volatility: float = 0.05        # sd as fraction of base income
    expense_volatility: float = 0.10

    job_loss_monthly_prob: float = 0.02
    job_loss_min_months: int = 2
    job_loss_max_months: int = 6
    job_loss_income_fraction: float = 0.20  # income retained during unemployment

    discretionary_expense_fraction: float = 0.40
    shock_expense_compression: float = 0.40  # cut this share of discretionary

    expense_shock_monthly_prob: float = 0.03
    expense_shock_min: float = 20_000
    expense_shock_max: float = 80_000

    thin_margin_threshold: float = 5_000    # "close to the edge" surplus level
    seed: int | None = 42