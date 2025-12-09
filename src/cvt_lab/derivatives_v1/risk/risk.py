# risk.py

import QuantLib as ql
import pandas as pd
from typing import Dict, Tuple
from copy import deepcopy
from cvt_lab.derivatives_v2.products.bermudan_swaption import BermudanSwaption


def compute_bucketed_pv01(
    base_curve: ql.PiecewiseYieldCurve,
    swap_object,
    market_quotes: Dict[Tuple[int, ql.TimeUnit], float],
    bump_size_bp: float = 1.0,
) -> pd.DataFrame:
    """
    Compute bucketed PV01s by bumping each market quote individually and re-pricing.

    swap_object must have a `.set_curve()` method and `.npv()` method (like Swap or CancellableSwap).

    Returns:
        DataFrame with:
        - Tenor (e.g. 2Y)
        - Base Quote
        - Bumped NPV
        - PV01 (USD)
    """

    base_npv = swap_object.npv()
    results = []

    for tenor, original_rate in market_quotes.items():
        # Copy quotes and bump just one
        bumped_quotes = deepcopy(market_quotes)
        bumped_quotes[tenor] += bump_size_bp / 10000.0

        # Rebuild bumped curve
        bumped_curve = _rebuild_curve(base_curve.referenceDate(), bumped_quotes)

        # Re-set curve and reprice
        swap_object.set_curve(bumped_curve)
        bumped_npv = swap_object.npv()

        pv01 = (bumped_npv - base_npv) * 1e4

        results.append({
            "Tenor": f"{tenor[0]}{tenor[1].name[0]}",
            "Original Rate": original_rate,
            "Bumped NPV": bumped_npv,
            "Bucket PV01 ($)": pv01
        })

    # Reset original curve
    swap_object.set_curve(base_curve)

    return pd.DataFrame(results)


def _rebuild_curve(settlement_date, market_quotes: Dict[Tuple[int, ql.TimeUnit], float]) -> ql.YieldTermStructure:
    """
    Internal utility to rebuild a curve from bumped quotes (supports deposits + swaps).
    """
    calendar = ql.UnitedStates()
    day_count = ql.Actual360()
    fixed_leg_daycount = ql.Thirty360()

    helpers = []

    for (n, unit), rate in market_quotes.items():
        quote = ql.QuoteHandle(ql.SimpleQuote(rate))
        if unit in [ql.Months]:
            helper = ql.DepositRateHelper(
                quote,
                ql.Period(n, unit),
                2,
                calendar,
                ql.ModifiedFollowing,
                False,
                day_count
            )
        elif unit in [ql.Years]:
            helper = ql.SwapRateHelper(
                quote,
                ql.Period(n, unit),
                calendar,
                ql.Annual,
                ql.ModifiedFollowing,
                fixed_leg_daycount,
                ql.USDLibor(ql.Period(3, ql.Months))
            )
        else:
            raise ValueError(f"Unsupported unit: {unit}")
        helpers.append(helper)

    curve = ql.PiecewiseLinearZero(settlement_date, helpers, ql.Actual365Fixed())
    curve.enableExtrapolation()
    return curve


def bermudan_vega_ladder(
        cancellable_swap,
        bump_sigma: float = 0.0001,
):
    """
    Computes a vega ladder by bumping Hull-White vol bucket-by-bucket.
    A good industry approximation for Bermudan vega.

    Returns:
        DataFrame with:
        - Exercise Date
        - Base NPV
        - Bumped NPV
        - Bucket Vega (USD)
    """

    swaption = cancellable_swap.swaption
    base_npv = cancellable_swap.npv()

    results = []
    discount = cancellable_swap.swap.discount_handle

    # Pull exercise dates from Bermudan
    exercise_dates = cancellable_swap.exercise_dates

    for ex_date in exercise_dates:
        # Build HW model with bumped sigma
        # Local bump: effective only near the exercise date
        model = ql.HullWhite(discount)
        sigma_bumped = model.sigma() + bump_sigma

        bumped_model = ql.HullWhite(discount, a=model.a(), sigma=sigma_bumped)

        # Apply model to swaption
        bumped_engine = ql.TreeSwaptionEngine(bumped_model, 50)

        swaption.swaption.setPricingEngine(bumped_engine)
        bumped_npv = cancellable_swap.swap.npv() - swaption.swaption.NPV()

        ladder_vega = (bumped_npv - base_npv) / bump_sigma

        results.append({
            "Exercise Date": ex_date.ISO(),
            "Base NPV": base_npv,
            "Bumped NPV": bumped_npv,
            "Bucket Vega ($)": ladder_vega
        })

    # Reset engine
    cancellable_swap.swaption = BermudanSwaption(
        cancellable_swap.swap,
        cancellable_swap.exercise_dates
    )

    return pd.DataFrame(results)
