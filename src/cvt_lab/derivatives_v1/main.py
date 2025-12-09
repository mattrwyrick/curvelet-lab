# main.py

import datetime as dt
import QuantLib as ql
import matplotlib.pyplot as plt

from cvt_lab.derivatives_v2.market.curve import build_usd_libor_curve, curve_to_dataframe
from cvt_lab.derivatives_v2.market.vol import SwaptionVolSurface
from cvt_lab.derivatives_v2.market.vol_diagnostics import (
    build_atm_vol_matrix,
    plot_atm_vol_surface,
    plot_smile,
    test_calendar_arbitrage,
    test_butterfly_arbitrage,
)

from cvt_lab.derivatives_v2.products.swap import Swap
from cvt_lab.derivatives_v2.products.cancellable_swap import CancellableSwap

from cvt_lab.derivatives_v2.risk.risk import compute_bucketed_pv01, bermudan_vega_ladder
from cvt_lab.derivatives_v2.risk.risk_metrics import full_risk_report


def main():
    # === 1. Market Setup ===
    settlement_date = ql.Date(1, 1, 2024)
    ql.Settings.instance().evaluationDate = settlement_date

    depo = {
        (1, ql.Months): 0.015,
        (3, ql.Months): 0.017
    }
    swaps = {
        (1, ql.Years): 0.018,
        (2, ql.Years): 0.020,
        (5, ql.Years): 0.022,
        (10, ql.Years): 0.025
    }
    curve = build_usd_libor_curve(settlement_date, depo, swaps)

    # === 2. Product Construction ===
    vanilla_swap = Swap(
        notional=100_000_000,
        fixed_rate=0.025,
        effective_dt=dt.date(2024, 1, 1),
        termination_dt=dt.date(2034, 1, 1),
        discount_curve=curve
    )

    cancel_swap = CancellableSwap(vanilla_swap, cancel_after_years=2)

    # === 3. Price Summary ===
    print("\n--- Cancellable Swap NPV Breakdown ---")
    for k, v in cancel_swap.summary().items():
        print(f"{k:<25}: {v:,.2f}")

    # === 4. Risk Metrics (Core Greeks) ===
    print("\n--- Core Greeks ---")
    print(f"PV01 (parallel 1bp): {cancel_swap.pv01_fd():,.2f} USD")
    print(f"Vega (sigma +1bp):   {cancel_swap.vega_fd(0.0001):,.2f} USD")

    # === 5. Curve Report ===
    curve_df = curve_to_dataframe(curve)
    print("\n--- Zero Curve Snapshot ---")
