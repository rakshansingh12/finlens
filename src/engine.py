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
    # Convert annual percentage -> monthly decimal rate.
    # 11% per year -> 0.11 per year -> 0.11/12 per month
    monthly_rate = annual_rate / 100 / 12

    # Convert years -> number of monthly installments
    n_months = tenure_years * 12

    # Zero-interest edge case: the general formula divides by
    # ((1+r)^n - 1), which is 0 when r = 0 -> ZeroDivisionError.
    # With no interest, you simply split the principal evenly.
    if monthly_rate == 0:
        return principal / n_months

    growth = (1 + monthly_rate) ** n_months
    emi = principal * (monthly_rate * growth) / (growth - 1)

    return emi
