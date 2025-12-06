
import datetime as dt
import pandas as pd
import QuantLib as ql
import matplotlib.pyplot as plt


class Swap:
    """
    Vanilla Interest Rate Swap
    """
    def __init__(
        self,
        notional: float,
        fixed_rate: float,
        effective_dt: dt.date,
        termination_dt: dt.date,
        pay_fixed: bool = True,
        float_tenor: ql.Period = ql.Period(3, ql.Months),
        fixed_freq: ql.Frequency = ql.Semiannual,
        float_freq: ql.Frequency = ql.Quarterly,
        day_count: ql.DayCounter = ql.Actual360(),
        calendar: ql.Calendar = ql.UnitedStates(),
        discount_curve: ql.YieldTermStructure = None,
        flat_rate: float = 0.03
    ):
        self.notional = notional
        self.fixed_rate = fixed_rate
        self.pay_fixed = pay_fixed
        self.day_count = day_count
        self.calendar = calendar

        self.effective_date = ql.Date(effective_dt.day, effective_dt.month, effective_dt.year)
        self.termination_date = ql.Date(termination_dt.day, termination_dt.month, termination_dt.year)

        if discount_curve is not None:
            self.discount_curve = discount_curve
        else:
            self.discount_curve = ql.FlatForward(
                self.effective_date,
                ql.QuoteHandle(ql.SimpleQuote(flat_rate)),
                day_count
            )

        self.discount_handle = ql.YieldTermStructureHandle(self.discount_curve)
        self.index = ql.USDLibor(float_tenor, self.discount_handle)

        self.fixed_schedule = ql.Schedule(
            self.effective_date, self.termination_date,
            ql.Period(fixed_freq), calendar,
            ql.ModifiedFollowing, ql.ModifiedFollowing,
            ql.DateGeneration.Forward, False
        )
        self.float_schedule = ql.Schedule(
            self.effective_date, self.termination_date,
            ql.Period(float_freq), calendar,
            ql.ModifiedFollowing, ql.ModifiedFollowing,
            ql.DateGeneration.Forward, False
        )

        self._build_swap()

    def _build_swap(self):
        swap_type = ql.VanillaSwap.Payer if self.pay_fixed else ql.VanillaSwap.Receiver
        self.swap = ql.VanillaSwap(
            swap_type,
            self.notional,
            self.fixed_schedule, self.fixed_rate, self.day_count,
            self.float_schedule, self.index, 0.0, self.day_count
        )
        self.engine = ql.DiscountingSwapEngine(self.discount_handle)
        self.swap.setPricingEngine(self.engine)

    def set_curve(self, new_curve: ql.YieldTermStructure):
        """
        Update the underlying curve of this instrument
        :param new_curve:
        :return:
        """
        self.discount_curve = new_curve
        self.discount_handle = ql.YieldTermStructureHandle(new_curve)
        self.index = ql.USDLibor(self.index.tenor(), self.discount_handle)
        self._build_swap()

    def get_npv(self):
        """
        Get the Net Present Value of the instrument
        :return:
        """
        npv = self.swap.NPV()
        return npv

    def get_pv01(self, bump_bp: float = 1.0):
        """
        Get PV01 by shocking the Underlying / Discount Factor Curve in parallel by 1bp
        :param bump_bp:
        :return:
        """
        bump = bump_bp / 10000
        base_npv = self.get_npv()
        r = self.discount_curve.zeroRate(self.effective_date, self.day_count, ql.Continuous).rate()
        bumped_curve = ql.FlatForward(self.effective_date, ql.QuoteHandle(ql.SimpleQuote(r + bump)), self.day_count)
        self.set_curve(bumped_curve)
        bumped_npv = self.get_npv()
        self.set_curve(self.discount_curve)
        pv01 = (bumped_npv - base_npv)
        return pv01

    @staticmethod
    def get_vega_pnl():
        """
        Linear products do not have vega / vol
        :return:
        """
        vega_pnl = 0.0
        return vega_pnl


    def get_theta_pnl(self):
        """
        Calculate Theta as Carry + Rolldown
        :return:
        """
        theta_pnl = self.get_carry_pnl() + self.get_rolldown_pnl()
        return theta_pnl

    def get_carry_pnl(self):
        """
        Calculate Carry of by advancing 1 day with no market data changes
        :return:
        """
        today = ql.Settings.instance().evaluationDate
        next_bd = self.calendar.advance(today, 1, ql.Days)
        ql.Settings.instance().evaluationDate = next_bd
        carry_npv = self.get_npv()  # Same market data
        ql.Settings.instance().evaluationDate = today
        return carry_npv - self.get_npv()

    def get_rolldown_pnl(self):
        """
        Calculate Rolldown by sliding down the Underlying / Discount Factor Curve 1 business day
        :return:
        """
        today = ql.Settings.instance().evaluationDate
        next_bd = self.calendar.advance(today, 1, ql.Days)
        fwd_rate = self.discount_curve.zeroRate(next_bd, self.day_count, ql.Continuous).rate()
        rolled_curve = ql.FlatForward(next_bd, ql.QuoteHandle(ql.SimpleQuote(fwd_rate)), self.day_count)
        rolled_curve.enableExtrapolation()
        ql.Settings.instance().evaluationDate = next_bd
        self.set_curve(rolled_curve)
        rolled_npv = self.get_npv()
        ql.Settings.instance().evaluationDate = today
        self.set_curve(self.discount_curve)
        rolldown = rolled_npv - self.get_npv()
        return rolldown

    def get_spot_delta_pnl(self, rate_change: float):
        """
        Calculate the Delta PnL (Spot) using Taylor Expansion
        :param rate_change:
        :return:
        """
        delta_pnl = self.get_spot_delta_rate() * rate_change
        return delta_pnl

    def get_spot_delta_rate(self, bump_bp=1.0):
        """
        Calculate the Delta Rate as a finite definite doublesided underlying bump
        :param bump_bp:
        :return:
        """
        base_npv = self.get_npv()
        r = self.discount_curve.zeroRate(self.effective_date, self.day_count, ql.Continuous).rate()
        bumped = ql.FlatForward(self.effective_date, ql.QuoteHandle(ql.SimpleQuote(r + bump_bp / 10000)), self.day_count)
        self.set_curve(bumped)
        bumped_npv = self.get_npv()
        self.set_curve(self.discount_curve)
        delta_rate = (bumped_npv - base_npv) / (bump_bp / 10000)
        return delta_rate

    def get_spot_gamma_pnl(self, rate_change: float):
        """
        Calculate the Gamma PnL (Spot) using Taylor Expansion
        :param rate_change:
        :return:
        """
        gamma = self.get_spot_gamma_rate()
        gamma_pnl = 0.5 * gamma * rate_change ** 2
        return gamma_pnl

    def get_spot_gamma_rate(self, bump_bp=1.0):
        """
        Calculate Gamma Rate as a finite definite doublesided underlying bump
        :param bump_bp:
        :return:
        """
        r = self.discount_curve.zeroRate(self.effective_date, self.day_count, ql.Continuous).rate()
        bump = bump_bp / 10000
        up = ql.FlatForward(self.effective_date, ql.QuoteHandle(ql.SimpleQuote(r + bump)), self.day_count)
        down = ql.FlatForward(self.effective_date, ql.QuoteHandle(ql.SimpleQuote(r - bump)), self.day_count)
        base_npv = self.get_npv()

        self.set_curve(up)
        npv_up = self.get_npv()
        self.set_curve(down)
        npv_down = self.get_npv()
        self.set_curve(self.discount_curve)

        gamma_rate = (npv_up + npv_down - 2 * base_npv) / (bump ** 2)
        return gamma_rate

    def get_spot_pnl_attribution(
            self,
            rate_change: float = 0.0001,
            include_delta: bool = True,
            include_gamma: bool = True,
            include_vega: bool = False,
            include_theta: bool = True,
            decompose_theta: bool = True
    ):
        """
        Return a dictionary with attributions explaining the PnL
        :param rate_change:
        :param include_delta:
        :param include_gamma:
        :param include_vega:
        :param include_theta:
        :param decompose_theta:
        :return:
        """
        # (Greeks as of T-1)
        attr_dict = dict()
        explained = 0
        if include_delta:
            delta_pnl = self.get_spot_delta_pnl(rate_change)
            explained += delta_pnl
            attr_dict["Delta"] = delta_pnl

        if include_gamma:
            gamma_pnl = self.get_spot_gamma_pnl(rate_change)
            attr_dict["Gamma"] = gamma_pnl
            explained += gamma_pnl

        if include_vega:
            vega_pnl = self.get_vega_pnl()
            attr_dict["Vega"] = vega_pnl
            explained += vega_pnl

        if include_theta:
            if decompose_theta:
                carry = self.get_carry_pnl()
                attr_dict["Carry"] = carry
                explained += carry
                rolldown = self.get_rolldown_pnl()
                attr_dict["Rolldown"] = rolldown
                explained += rolldown
            else:
                theta_pnl = self.get_theta_pnl()
                attr_dict["Theta"] = theta_pnl
                explained += theta_pnl

        # Get NPV for T-1
        base_npv = self.get_npv()
        today = ql.Settings.instance().evaluationDate

        # Advance to T
        next_bd = self.calendar.advance(today, 1, ql.Days)
        fwd_rate = self.discount_curve.zeroRate(next_bd, self.day_count, ql.Continuous).rate()
        new_curve = ql.FlatForward(next_bd, ql.QuoteHandle(ql.SimpleQuote(fwd_rate + rate_change)), self.day_count)
        new_curve.enableExtrapolation()
        ql.Settings.instance().evaluationDate = next_bd
        self.set_curve(new_curve)
        new_npv = self.get_npv()

        # Reset underlying to T-1 (optional)
        ql.Settings.instance().evaluationDate = today
        self.set_curve(self.discount_curve)

        # Total PnL and Residual
        total_pnl = new_npv - base_npv
        attr_dict["Total PnL"] = total_pnl
        residual = total_pnl - explained
        attr_dict["Residual"] = residual

        return attr_dict

    def plot_spot_pnl_attribution(self, rate_change: float = 0.0001):
        """
        Plot a pie chart of the PnL Attribution
        :param rate_change:
        :return:
        """
        attr_dict = self.get_spot_pnl_attribution(rate_change)
        attribution_types = list()
        attribution_pnls = list()
        for attr, pnl in attr_dict.items():
            if attr not in ["Total PnL"]:
                attribution_types.append(attr)
                attribution_pnls.append(pnl)

        fig, ax = plt.subplots()
        ax.pie(attribution_pnls, labels=attribution_types, autopct="%1.1f%%", startangle=140)
        ax.set_title("PnL Attribution (Spot)")
        plt.tight_layout()
        plt.show()

    def get_bucketed_risks(self, tenors=None, bump_bp=1.0):
        if tenors is None:
            tenors = ['1Y', '2Y', '3Y', '5Y', '7Y', '10Y', '15Y', '20Y', '30Y']

        today = ql.Settings.instance().evaluationDate
        bump = bump_bp / 10000
        base_npv = self.get_npv()
        risks = []

        for tenor_str in tenors:
            tenor = ql.PeriodParser.parse(tenor_str)
            bump_date = self.calendar.advance(today, tenor)
            base_rate = self.discount_curve.zeroRate(bump_date, self.day_count, ql.Continuous).rate()

            bumped_up = ql.FlatForward(self.effective_date, ql.QuoteHandle(ql.SimpleQuote(base_rate + bump)), self.day_count)
            bumped_down = ql.FlatForward(self.effective_date, ql.QuoteHandle(ql.SimpleQuote(base_rate - bump)), self.day_count)
            bumped_up.enableExtrapolation()
            bumped_down.enableExtrapolation()

            self.set_curve(bumped_up)
            npv_up = self.get_npv()
            self.set_curve(bumped_down)
            npv_down = self.get_npv()
            self.set_curve(self.discount_curve)

            delta = (npv_up - npv_down) / (2 * bump)
            gamma = (npv_up + npv_down - 2 * base_npv) / (bump ** 2)
            pv01 = delta * bump

            risks.append({"Tenor": tenor_str, "Delta": delta, "Gamma": gamma, "PV01": pv01})

        return pd.DataFrame(risks)

    def get_delta_bucketed_rate(self, bump_bp=1.0, tenors=None):
        return self.get_bucketed_risks(tenors=tenors, bump_bp=bump_bp)[["Tenor", "Delta"]]

    def get_delta_bucketed_pnl(self, rate_change: float, bump_bp=1.0, tenors=None):
        df = self.get_delta_bucketed_rate(bump_bp=bump_bp, tenors=tenors)
        df["PnL"] = df["Delta"] * rate_change
        return df

    def get_gamma_bucketed_rate(self, bump_bp=1.0, tenors=None):
        return self.get_bucketed_risks(tenors=tenors, bump_bp=bump_bp)[["Tenor", "Gamma"]]

    def get_gamma_bucketed_pnl(self, rate_change: float, bump_bp=1.0, tenors=None):
        df = self.get_gamma_bucketed_rate(bump_bp=bump_bp, tenors=tenors)
        df["PnL"] = 0.5 * df["Gamma"] * rate_change**2
        return df

    def get_pv01_bucketed_pnl(self, bump_bp=1.0, tenors=None):
        return self.get_bucketed_risks(tenors=tenors, bump_bp=bump_bp)[["Tenor", "PV01"]]

    def get_combined_risks_pnl(self, rate_change: float = 0.0001, bump_bp: float = 1.0, tenors=None):
        return {
            "Delta_Spot_PnL": self.get_delta_spot_pnl(rate_change),
            "Gamma_Spot_PnL": self.get_gamma_spot_pnl(rate_change),
            "PV01_Spot_PnL": self.get_pv01_spot_pnl(bump_bp),
            "Delta_Bucketed_PnL": self.get_delta_bucketed_pnl(rate_change, bump_bp, tenors),
            "Gamma_Bucketed_PnL": self.get_gamma_bucketed_pnl(rate_change, bump_bp, tenors),
            "PV01_Bucketed_PnL": self.get_pv01_bucketed_pnl(bump_bp, tenors),
            "Theta_PnL": self.get_theta_pnl()
        }

    def plot_bucketed_risks(self, bump_bp=1.0, tenors=None):
        df = self.get_bucketed_risks(tenors=tenors, bump_bp=bump_bp)
        fig, ax = plt.subplots(figsize=(10, 6))

        ax.bar(df["Tenor"], df["PV01"], width=0.4, label="PV01", align='center', alpha=0.7)
        ax.plot(df["Tenor"], df["Delta"], label="Delta", marker='o', linestyle='-', linewidth=2)
        ax.plot(df["Tenor"], df["Gamma"], label="Gamma", marker='x', linestyle='--', linewidth=2)

        ax.set_xlabel("Tenor")
        ax.set_ylabel("Risk Sensitivities")
        ax.set_title("Bucketed PV01 / Delta / Gamma")
        ax.legend()
        ax.grid(True)
        plt.tight_layout()
        plt.show()
