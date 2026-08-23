"""Tests for the deterministic financial engine."""

import pytest

from src.engine import calculate_emi


def test_emi_standard_loan():
    """8L at 11% over 5 years should produce ~17,394/month.

    Reference value cross-checked against standard EMI calculators.
    """
    emi = calculate_emi(principal=800000, annual_rate=11, tenure_years=5)
    assert emi == pytest.approx(17393.94, abs=0.01)


def test_emi_zero_interest():
    """With no interest, the principal is simply split evenly."""
    emi = calculate_emi(principal=120000, annual_rate=0, tenure_years=1)
    assert emi == pytest.approx(10000.00, abs=0.01)


def test_longer_tenure_lowers_emi():
    """A longer tenure spreads repayment out, so each payment is smaller.

    This is a *property* test -- it doesn't hardcode a value, it asserts
    a relationship that must hold regardless of the exact numbers.
    """
    emi_5yr = calculate_emi(800000, 11, 5)
    emi_7yr = calculate_emi(800000, 11, 7)
    assert emi_7yr < emi_5yr


def test_longer_tenure_raises_total_interest():
    """But a longer tenure means paying interest for longer, so total cost rises.

    This is the core trade-off FinLens exists to make visible to users.
    """
    total_5yr = calculate_emi(800000, 11, 5) * 60
    total_7yr = calculate_emi(800000, 11, 7) * 84
    assert total_7yr > total_5yr
