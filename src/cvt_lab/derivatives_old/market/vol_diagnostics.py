# vol_diagnostics.py

import QuantLib as ql
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, Tuple


def build_atm_vol_matrix(atm_vols: Dict[Tuple[int, ql.TimeUnit, int, ql.TimeUnit], float]):
    """
    Builds a pivoted ATM vol matrix for plotting
    """
    records = []
    for (exp_n, exp_u, ten_n, ten_u), vol in atm_vols.items():
        expiry = f"{exp_n}{exp_u.name[0]}"
        tenor = f"{ten_n}{ten_u.name[0]}"
        records.append({"Expiry": expiry, "Tenor": tenor, "ATM Vol": vol})

    df = pd.DataFrame(records)
    vol_matrix = df.pivot(index="Expiry", columns="Tenor", values="ATM Vol")
    return df, vol_matrix


def plot_atm_vol_surface(vol_matrix):
    """
    Plots the ATM vol surface heatmap
    """
    plt.figure(figsize=(10, 6))
    sns.heatmap(vol_matrix.astype(float), annot=True, fmt=".3f", cmap="coolwarm")
    plt.title("ATM Swaption Vol Surface")
    plt.ylabel("Expiry")
    plt.xlabel("Tenor")
    plt.tight_layout()
    plt.show()


def plot_smile(expiry: str, strikes: list, vols: list):
    """
    Plots a smile for given expiry
    """
    plt.figure(figsize=(6, 4))
    plt.plot(strikes, vols, marker='o')
    plt.title(f"Smile for {expiry}")
    plt.xlabel("Strike")
    plt.ylabel("Volatility")
    plt.grid(True)
    plt.show()


def test_calendar_arbitrage(atm_matrix: pd.DataFrame):
    """
    Validates that vols increase with expiry for each tenor
    """
    pivot = atm_matrix.pivot(index="Expiry", columns="Tenor", values="ATM Vol")
    issues = []
    for tenor in pivot.columns:
        vols = pivot[tenor].dropna().values
        if not np.all(np.diff(vols) >= -1e-4):
            issues.append(f"Calendar arbitrage found in tenor {tenor}")

    return issues


def test_butterfly_arbitrage(strikes: list, vols: list):
    """
    Basic convexity check on smile: 2*mid > wings
    """
    arbitrage = False
    n = len(strikes)
    for i in range(1, n - 1):
        if vols[i] < 0.5 * (vols[i - 1] + vols[i + 1]) - 1e-4:
            arbitrage = True
    return arbitrage


def calibrate_hull_white_to_surface(
        helpers: list,
        discount_curve: ql.YieldTermStructureHandle,
        guess: Tuple[float, float] = (0.01, 0.01)
):
    model = ql.HullWhite(discount_curve)
    model.setParams(guess)

    optimization_method = ql.LevenbergMarquardt()

    def cost_function(params):
        a, sigma = params
        model.setParams((a, sigma))
        error = 0.0
        for helper in helpers:
            helper.setPricingEngine(ql.JamshidianSwaptionEngine(model))
            diff = helper.modelValue() - helper.marketValue()
            error += diff * diff
        return np.sqrt(error / len(helpers))

    result = optimization_method.minimize(
        ql.NoConstraint(),
        ql.InitialGuess(guess),
        cost_function
    )

    return model, result