import datetime as dt
import pandas as pd
import QuantLib as ql

import matplotlib.pyplot as plt
import plotly.graph_objects as go


DEFAULT_TENORS = ('1Y', '2Y', '3Y', '5Y', '7Y', '10Y', '15Y', '20Y', '30Y')


def ql_to_date(ql_date: ql.Date) -> dt.date:
    """Convert QuantLib Date to Python datetime.date"""
    return dt.date(ql_date.year(), ql_date.month(), ql_date.dayOfMonth())


class DiscountCurve:
    """
    Base class for discount curves.

    Stores effective date, day count convention, float tenor, and flat rate (if applicable).
    """

    def __init__(
        self,
        effective_dt: dt.date,
        float_tenor: ql.Period = ql.Period(3, ql.Months),
        day_count: ql.DayCounter = ql.Actual360(),
        flat_rate: float = 0.03
    ):
        self.effective_date = ql.Date(effective_dt.day, effective_dt.month, effective_dt.year)
        self.float_tenor = float_tenor
        self.day_count = day_count
        self.flat_rate = flat_rate
        self.discount_curve = None

    def bump(self, *args, **kwargs):
        """
        Implement in subclass
        """
        raise NotImplementedError("Implement at Subclass Level")

    def to_dataframe(self, *args, **kwargs) -> pd.DataFrame:
        """
        Implement in subclass
        """
        raise NotImplementedError("Implement at Subclass Level")

    def to_csv(self, path: str, tenors: list[str] = None):
        """
        Save the curve
        :param path:
        :param tenors:
        :return:
        """
        df = self.to_dataframe(tenors)
        df.to_csv(path, index=False)
        return path

    def spot_rate(
        self,
        maturity_date: dt.date,
        compounding: ql.Compounding = ql.Continuous,
        freq: ql.Frequency = ql.Annual
    ) -> float:
        """
        Get the spot zero rate from today to the given maturity date.
        """
        ql_date = ql.Date(maturity_date.day, maturity_date.month, maturity_date.year)
        return self.discount_curve.zeroRate(ql_date, self.day_count, compounding, freq).rate()

    def forward_rate(
        self,
        start_date: dt.date,
        end_date: dt.date,
        compounding: ql.Compounding = ql.Continuous,
        freq: ql.Frequency = ql.Annual
    ) -> float:
        """
        Get the forward rate from start_date to end_date.
        """
        ql_start = ql.Date(start_date.day, start_date.month, start_date.year)
        ql_end = ql.Date(end_date.day, end_date.month, end_date.year)
        return self.discount_curve.forwardRate(ql_start, ql_end, self.day_count, compounding, freq).rate()

    def plot(
            self,
            library="plotly",
            tenors: list[str] = None,
            include_discount_factors: bool = False,
            title: str = "Discount Curve",
            fig_size=(10, 5),
            show: bool = True
    ):
        """
        Plot zero rates (and optionally discount factors) using matplotlib or plotly.

        :param tenors: List of tenors (e.g. ['1Y', '2Y', ...]). Defaults to standard tenors.
        :param include_discount_factors: If True, also plot discount factors.
        :param library: 'matplotlib' or 'plotly'
        :param title: Chart title
        :param fig_size: Figure size (for matplotlib)
        :param show: show fig
        :return: plog fig:
        """
        library = library.lower().strip()
        if tenors is None:
            tenors = DEFAULT_TENORS

        if library == "matplotlib":
            fig = self._plot_matplotlib(tenors, include_discount_factors, title, fig_size, show)
        elif library == "plotly":
            fig = self._plot_plotly(tenors, include_discount_factors, title, show)
        else:
            raise ValueError(f"Unsupported plot library: '{library}'")

        return fig

    def _plot_matplotlib(
            self,
            tenors: list[str] = None,
            include_discount_factors: bool = False,
            title: str = "Discount Curve",
            fig_size=(10, 5),
            show: bool = True
    ):
        """
        Plot the curve using matplotlib
        :return:
        """
        if tenors is None:
            tenors = DEFAULT_TENORS

        df = self.to_dataframe(tenors)

        fig, ax1 = plt.subplots(figsize=fig_size)

        ax1.plot(df["Date"], df["ZeroRate"], label="Zero Rate", marker='o')
        ax1.set_ylabel("Zero Rate", color="blue")
        ax1.tick_params(axis='y', labelcolor="blue")

        if include_discount_factors:
            ax2 = ax1.twinx()
            ax2.plot(
                df["Date"],
                df["DiscountFactor"],
                label="Discount Factor",
                 color="green",
                linestyle="--",
                marker='x'
            )
            ax2.set_ylabel("Discount Factor", color="green")
            ax2.tick_params(axis='y', labelcolor="green")

        ax1.set_title(title)
        ax1.set_xlabel("Maturity Date")
        fig.tight_layout()
        plt.grid(True)

        if show:
            plt.show()
        return fig

    def _plot_plotly(
            self,
            tenors: list[str] = None,
            include_discount_factors: bool = False,
            title: str = "Discount Curve",
            show: bool = True
    ):
        """
        Plot the curve using plotly
        :return:
        """
        if tenors is None:
            tenors = DEFAULT_TENORS

        df = self.to_dataframe(tenors)
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=df["Date"],
                y=df["ZeroRate"],
                mode='lines+markers',
                name='Zero Rate'
            )
        )

        if include_discount_factors:
            fig.add_trace(
                go.Scatter(
                    x=df["Date"],
                    y=df["DiscountFactor"],
                    mode='lines+markers',
                    name='Discount Factor'
                )
            )

        fig.update_layout(
            title=title,
            xaxis_title="Maturity Date",
            yaxis_title="Rate / DF",
            template="plotly_white",
            legend=dict(x=0.01, y=0.99)
        )

        if show:
            fig.show()

        return fig


class FlatForwardDiscountCurve(DiscountCurve):
    """
    Flat forward yield curve based on a constant interest rate.
    """

    def __init__(
        self,
        effective_dt: dt.date,
        float_tenor: ql.Period = ql.Period(3, ql.Months),
        day_count: ql.DayCounter = ql.Actual360(),
        flat_rate: float = 0.03
    ):
        super().__init__(effective_dt, float_tenor, day_count, flat_rate)

        self.discount_curve = ql.FlatForward(
            self.effective_date,
            ql.QuoteHandle(ql.SimpleQuote(self.flat_rate)),
            self.day_count
        )
        self.discount_curve.enableExtrapolation()

        self.discount_handle = ql.YieldTermStructureHandle(self.discount_curve)
        self.index = ql.USDLibor(self.float_tenor, self.discount_handle)

    def bump(self, bump_bp: float, double_sided: bool = False):
        """
        Return a bumped FlatForwardDiscountCurve instance (or both up/down if double_sided).

        :param bump_bp: Size of bump in basis points.
        :param double_sided: If True, return both (up, down) bumped curves.
        :return: FlatForwardDiscountCurve or tuple of two.
        """
        if double_sided:
            bump_up = self.bump(abs(bump_bp))
            bump_down = self.bump(-abs(bump_bp))
            return bump_up, bump_down

        bumped_rate = self.flat_rate + bump_bp / 10000.0

        return FlatForwardDiscountCurve(
            effective_dt=dt.date(
                self.effective_date.year(),
                self.effective_date.month(),
                self.effective_date.dayOfMonth()
            ),
            float_tenor=self.float_tenor,
            day_count=self.day_count,
            flat_rate=bumped_rate
        )

    def to_dataframe(self, tenors: list[str] = None) -> pd.DataFrame:
        """
        Return a DataFrame with constant zero rates and discount factors across tenors.

        :param tenors: Optional list of tenors (e.g., ['1Y', '5Y', '10Y']). Defaults to standard buckets.
        :return: pd.DataFrame with Tenor, Date, ZeroRate, and DiscountFactor.
        """
        if tenors is None:
            tenors = DEFAULT_TENORS

        dates = [ql.TARGET().advance(self.effective_date, ql.Period(t)) for t in tenors]

        rows = []
        for tenor, date in zip(tenors, dates):
            zero_rate = self.discount_curve.zeroRate(date, self.day_count, ql.Continuous).rate()
            df = self.discount_curve.discount(date)
            rows.append({
                "Tenor": tenor,
                "Date": ql_to_date(date),
                "ZeroRate": zero_rate,
                "DiscountFactor": df
            })

        return pd.DataFrame(rows)


class KeyRateDiscountCurve(DiscountCurve):
    """
    Discount curve built from key rate tenors and zero rates (i.e., a zero curve).

    Supports single tenor bumps for key rate DV01/gamma analysis.
    """

    def __init__(
        self,
        effective_dt: dt.date,
        rates: list[float],
        tenors: list[str] = DEFAULT_TENORS,
        float_tenor: ql.Period = ql.Period(3, ql.Months),
        day_count: ql.DayCounter = ql.Actual360()
    ):
        super().__init__(effective_dt, float_tenor, day_count)
        self.rates = rates
        self.tenors = tenors

        self.discount_curve = ql.ZeroCurve(
            [ql.TARGET().advance(self.effective_date, ql.Period(t)) for t in self.tenors],
            self.rates,
            self.day_count
        )
        self.discount_curve.enableExtrapolation()

        self.discount_handle = ql.YieldTermStructureHandle(self.discount_curve)
        self.index = ql.USDLibor(self.float_tenor, self.discount_handle)

    def bump(self, bump_bp: float, tenor: str, double_sided: bool = False):
        """
        Bump a single tenor's zero rate and return a new KeyRateDiscountCurve.

        :param bump_bp: Size of bump in basis points.
        :param tenor: The tenor to bump (e.g., '5Y').
        :param double_sided: If True, return (bump_up, bump_down) curves.
        :return: KeyRateDiscountCurve or tuple of two.
        """
        if tenor not in self.tenors:
            raise ValueError(f"Tenor '{tenor}' not in curve tenors: {self.tenors}")

        idx = self.tenors.index(tenor)

        if double_sided:
            bump_up = self.bump(abs(bump_bp), tenor)
            bump_down = self.bump(-abs(bump_bp), tenor)
            return bump_up, bump_down

        bumped_rates = self.rates.copy()
        bumped_rates[idx] += bump_bp / 10000.0

        return KeyRateDiscountCurve(
            effective_dt=dt.date(
                self.effective_date.year(),
                self.effective_date.month(),
                self.effective_date.dayOfMonth()
            ),
            tenors=self.tenors,
            rates=bumped_rates,
            float_tenor=self.float_tenor,
            day_count=self.day_count
        )

    def to_dataframe(self, tenors: list[str] = None) -> pd.DataFrame:
        """
        Return a DataFrame with zero rates and discount factors across tenors.

        :param tenors: Optional list of tenors (defaults to curve's tenors).
        :return: pd.DataFrame with Tenor, Date, ZeroRate, and DiscountFactor.
        """
        if tenors is None:
            tenors = self.tenors

        dates = [ql.TARGET().advance(self.effective_date, ql.Period(t)) for t in tenors]

        rows = []
        for tenor, date in zip(tenors, dates):
            zero_rate = self.discount_curve.zeroRate(date, self.day_count, ql.Continuous).rate()
            df = self.discount_curve.discount(date)
            rows.append({
                "Tenor": tenor,
                "Date": ql_to_date(date),
                "ZeroRate": zero_rate,
                "DiscountFactor": df
            })

        return pd.DataFrame(rows)
