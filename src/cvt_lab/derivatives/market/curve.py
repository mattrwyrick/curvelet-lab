# curve.py


import QuantLib as ql
from typing import Dict, Tuple


def build_usd_libor_curve(
    settlement_date: ql.Date,
    depo_rates: Dict[Tuple[int, ql.TimeUnit], float],
    swap_rates: Dict[Tuple[int, ql.TimeUnit], float],
    calendar: ql.Calendar = ql.UnitedStates()
) -> ql.YieldTermStructure:
    """
    Build a bootstrapped USD LIBOR curve from deposit and swap rates.
    Returns a QuantLib YieldTermStructure.
    """
    ql.Settings.instance().evaluationDate = settlement_date

    day_count = ql.Actual360()
    fixed_leg_daycount = ql.Thirty360()

    # List of RateHelpers
    helpers = []

    # Deposit instruments
    for (n, unit), rate in depo_rates.items():
        quote = ql.QuoteHandle(ql.SimpleQuote(rate))
        tenor = ql.Period(n, unit)
        helper = ql.DepositRateHelper(
            quote,
            tenor,
            2,  # settlement days
            calendar,
            ql.ModifiedFollowing,
            False,
            day_count
        )
        helpers.append(helper)

    # Swap instruments
    for (n, unit), rate in swap_rates.items():
        quote = ql.QuoteHandle(ql.SimpleQuote(rate))
        tenor = ql.Period(n, unit)
        index = ql.USDLibor(ql.Period(3, ql.Months))
        helper = ql.SwapRateHelper(
            quote,
            tenor,
            calendar,
            ql.Annual,
            ql.ModifiedFollowing,
            fixed_leg_daycount,
            index
        )
        helpers.append(helper)

    # Bootstrapped zero curve
    curve = ql.PiecewiseLinearZero(
        settlement_date,
        helpers,
        ql.Actual365Fixed()
    )
    curve.enableExtrapolation()
    return curve


import pandas as pd

def curve_to_dataframe(curve: ql.YieldTermStructure, max_years: int = 30, freq_months: int = 6) -> pd.DataFrame:
    """
    Export zero rates and discount factors from a QuantLib curve into a DataFrame.

    Parameters:
        - curve: bootstrapped YieldTermStructure
        - max_years: max tenor in years
        - freq_months: spacing in months for tenors

    Returns:
        - DataFrame with Tenor (in years), Date, Zero Rate, and Discount Factor
    """
    calendar = ql.UnitedStates()
    today = curve.referenceDate()
    dates, tenors, zeros, dfs = [], [], [], []

    for months in range(freq_months, max_years * 12 + 1, freq_months):
        d = calendar.advance(today, ql.Period(months, ql.Months))
        t = curve.dayCounter().yearFraction(today, d)
        z = curve.zeroRate(d, curve.dayCounter(), ql.Continuous).rate()
        df = curve.discount(d)

        dates.append(d)
        tenors.append(t)
        zeros.append(z)
        dfs.append(df)

    return pd.DataFrame({
        "Tenor (Y)": tenors,
        "Date": [ql.Date(d).ISO() for d in dates],
        "Zero Rate": zeros,
        "Discount Factor": dfs
    })

