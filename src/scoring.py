"""
Borrowing Stress Score: an interpretable 0-100 measure of the financial
strain a borrowing decision places on a household.

Deliberately built from STATIC, decision-time inputs only -- no simulation
output feeds into it. This independence is what makes RQ-B ("does a cheap
static score track what expensive simulation reveals?") a real test rather
than a circular one.

Higher score = more stress.
"""


def _piecewise_score(value: float, breakpoints: list[tuple[float, float]]) -> float:
    """
    Map a raw metric onto a 0-100 stress scale by linear interpolation
    between named breakpoints.

    breakpoints is a list of (metric_value, stress_score) pairs, ordered by
    ascending stress. Values outside the range clamp to the nearest endpoint.
    """
    # Ordered from least-stressful metric value to most
    for i in range(len(breakpoints) - 1):
        (v_low, s_low), (v_high, s_high) = breakpoints[i], breakpoints[i + 1]

        lo, hi = min(v_low, v_high), max(v_low, v_high)
        if lo <= value <= hi:
            if v_high == v_low:
                return s_high
            # Linear interpolation between the two breakpoints
            fraction = (value - v_low) / (v_high - v_low)
            return s_low + fraction * (s_high - s_low)

    # Outside the defined range: clamp to whichever end is closer
    first_value, first_score = breakpoints[0]
    last_value, last_score = breakpoints[-1]
    if abs(value - first_value) < abs(value - last_value):
        return first_score
    return last_score


def score_debt_burden(debt_to_income: float | None) -> float:
    """DTI bands follow conventional lending practice."""
    if debt_to_income is None:
        return 100.0
    return _piecewise_score(
        debt_to_income,
        [(0.00, 0), (0.28, 20), (0.36, 45), (0.43, 70), (0.50, 90), (0.70, 100)],
    )


def score_liquidity(emergency_fund_months: float | None, target_months: int = 6) -> float:
    """Coverage relative to the conventional 6-month emergency fund benchmark."""
    if emergency_fund_months is None:
        return 100.0
    return _piecewise_score(
        emergency_fund_months,
        [(float(target_months * 2), 0), (float(target_months), 20),
         (3.0, 50), (1.0, 80), (0.0, 100)],
    )


def score_surplus_margin(savings_rate: float | None) -> float:
    """Monthly breathing room as a share of income."""
    if savings_rate is None:
        return 100.0
    return _piecewise_score(
        savings_rate,
        [(0.40, 0), (0.30, 15), (0.20, 35), (0.10, 65), (0.00, 90), (-0.20, 100)],
    )


def score_interest_load(total_interest: float, principal: float) -> float:
    """Lifetime interest cost relative to the amount borrowed."""
    if principal <= 0:
        return 0.0
    ratio = total_interest / principal
    return _piecewise_score(
        ratio,
        [(0.00, 0), (0.15, 20), (0.30, 45), (0.50, 70), (0.75, 90), (1.00, 100)],
    )


WEIGHTS = {
    "debt_burden": 0.30,
    "liquidity": 0.30,
    "surplus_margin": 0.25,
    "interest_load": 0.15,
}


def borrowing_stress_score(evaluation: dict, target_months: int = 6) -> dict:
    """
    Compute the composite stress score for one evaluated scenario.

    Args:
        evaluation: output of engine.evaluate_scenario
        target_months: the household's emergency fund target

    Returns:
        The composite score plus every component, so the score is never
        a black box -- a user can always see what drove it.
    """
    components = {
        "debt_burden": score_debt_burden(evaluation["debt_to_income"]),
        "liquidity": score_liquidity(evaluation["emergency_fund_months"], target_months),
        "surplus_margin": score_surplus_margin(evaluation["savings_rate"]),
        "interest_load": score_interest_load(
            evaluation["total_interest"], evaluation["principal"]
        ),
    }

    composite = sum(components[name] * WEIGHTS[name] for name in WEIGHTS)

    return {
        "stress_score": round(composite, 2),
        "band": _band(composite),
        "components": {k: round(v, 2) for k, v in components.items()},
        "weights": dict(WEIGHTS),
        "largest_contributor": max(
            WEIGHTS, key=lambda name: components[name] * WEIGHTS[name]
        ),
    }


def _band(score: float) -> str:
    """Translate a numeric score into a qualitative band."""
    if score < 25:
        return "low"
    if score < 45:
        return "moderate"
    if score < 65:
        return "elevated"
    return "high"