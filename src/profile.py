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