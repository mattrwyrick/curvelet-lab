# risk_metrics.py

import QuantLib as ql
import pandas as pd
import numpy as np
from typing import Dict, Tuple
from copy import deepcopy


def compute_parallel_delta(product, curve, bump_bp: float = 1.0):
    """
    Parallel rate delta using 1bp shift.
    """
    base_npv = product.npv()

    orig_rate = curve.zeroRate(
        curve.referenceDate(), curve.dayCounter(), ql.Continuous
    ).rate()
    bumped_curve = ql.FlatForward(
        curve.referenceDate(),
        ql.QuoteHandle(ql.SimpleQuote(orig_rate + bump_bp / 10000.0)),
        curve.dayCounter()
    )

    product.set_curve(bumped_curve)
    bumped_npv = product.npv()

    product.set_curve(curve)
    return (bumped_npv - base_npv) * 1e4  # in $/bp


def compute_parallel_gamma(product, curve, bump_bp: float = 1.0):
    """
    Parallel rate gamma using central difference.
    """
    base_npv = product.npv()
    orig_rate = curve.zeroRate(curve.referenceDate(), curve.dayCounter(), ql.Continuous).rate()

    bumped_up = ql.FlatForward(
        curve.referenceDate(),
        ql.QuoteHandle(ql.SimpleQuote(orig_rate + bump_bp / 10000.0)),
        curve.dayCounter()
    )
    bumped_down = ql.FlatForward(
        curve.referenceDate(),
        ql.QuoteHandle(ql.SimpleQuote(orig_rate - bump_bp / 10000.0)),
        curve.dayCounter()
    )

    product.set_curve(bumped_up)
    npv_up = product.npv()
    product.set_curve(bumped_down)
    npv_down = product.npv()
    product.set_curve(curve)

    gamma = (npv_up + npv_down - 2 * base_npv) / ((bump_bp / 10000.0) ** 2)
    return gamma


def compute_vega(product, bump_vol: float = 0.0001):
    """
    Estimate vega by bumping model volatility (Hull-White).
    """
    base_npv = product.npv()
    model = ql.HullWhite(product.swap.discount_handle)

    bumped_model = ql.HullWhite(product.swap.discount_handle, a=model.a(), sigma=model.sigma() + bump_vol)
    engine = ql.TreeSwaptionEngine(bumped_model, 50)
    product.swaption.swaption.setPricingEngine(engine)
    bumped_npv = product.npv()

    product.swaption = product.swaption.__class__(product.swap, product.exercise_dates)
    return (bumped_npv - base_npv) / bump_vol


def compute_one_day_carry(product, curve, calendar=ql.UnitedStates()):
    """
    Computes carry (theta) over a single business day.
    """
    today = ql.Settings.instance().evaluationDate
    next_bd = calendar.advance(today, 1, ql.Days)

    ql.Settings.instance().evaluationDate = today
    base_npv = product.npv()

    ql.Settings.instance().evaluationDate = next_bd
    bumped_npv = product.npv()

    ql.Settings.instance().evaluationDate = today

    return bumped_npv - base_npv


def compute_rolldown(product, curve, calendar=ql.UnitedStates(), bump_days=1):
    """
    Simulates 1-day rolldown: forward evaluation date AND slide curve.
    """
    today = ql.Settings.instance().evaluationDate
    fwd_date = calendar.advance(today, bump_days, ql.Days)

    ql.Settings.instance().evaluationDate = today
    base_npv = product.npv()

    fwd_rate = curve.zeroRate(fwd_date, curve.dayCounter(), ql.Continuous).rate()
    rolled_curve = ql.FlatForward(
        fwd_date,
        ql.QuoteHandle(ql.SimpleQuote(fwd_rate)),
        curve.dayCounter()
    )

    ql.Settings.instance().evaluationDate = fwd_date
    product.set_curve(rolled_curve)
    rolled_npv = product.npv()

    ql.Settings.instance().evaluationDate = today
    product.set_curve(curve)

    return rolled_npv - base_npv


def full_risk_report(product, curve):
    return {
        "Delta ($/bp)": compute_parallel_delta(product, curve),
        "Gamma ($)": compute_parallel_gamma(product, curve),
        "Vega ($)": compute_vega(product) if hasattr(product, 'swaption') else None,
        "Carry ($/1bd)": compute_one_day_carry(product, curve),
        "Rolldown ($/1bd)": compute_rolldown(product, curve),
    }
