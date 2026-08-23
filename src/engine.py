"""
Deterministic financial engine.

Pure functions for loan mathematics and affordability ratios.
No simulation, no I/O, no side effects -- every function here takes
numbers in and returns numbers out, which makes them trivially testable.
"""


def calculate_emi(principal: float, annual_rate: float, tenure_years: int) -> float:
    """
    Calculate the fixed monthly installment (EMI) for a reducing-balance loan.

    EMI = P * [ r(1+r)^n ] / [ (1+r)^n - 1 ]

    Args:
        principal:    Loan amount (e.g. 800000)
        annual_rate:  Annual interest rate as a percentage (e.g. 11 for 11%)
        tenure_years: Loan tenure in years (e.g. 5)

    Returns:
        The fixed monthly payment amount.
    """
    monthly_rate = annual_rate / 100 / 12

    n_months = tenure_years * 12

# edge case
    if monthly_rate == 0:
        return principal / n_months

    growth = (1 + monthly_rate) ** n_months
    emi = principal * (monthly_rate * growth) / (growth - 1)

    return emi

def generate_amortization_schedule(
        principal: float, annual_rate: float, tenure_years: int
) -> list[dict]:
    monthly_rate = annual_rate/ 100 / 12
    n_months = tenure_years * 12
    emi = calculate_emi(principal, annual_rate, tenure_years)

    schedule  = []
    balance = principal

    for month in range(1, n_months + 1):
        interest_component = balance * monthly_rate
        principal_component = emi - interest_component
        balance = balance - principal_component

        if month == n_months:
            balance = max(balance, 0.0)

        schedule.append({
            "month": month,
            "emi": round(emi, 2),
            "interest": round(interest_component, 2),
            "principal": round(principal_component, 2),
            "balance": round(balance, 2),
        })

    return schedule

def total_interest_paid(schedule: list[dict]) -> float:
    return round(sum(row["interest"] for row in schedule), 2)