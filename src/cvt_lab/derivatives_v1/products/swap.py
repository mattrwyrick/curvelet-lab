

import datetime as dt

import numpy as np
import pandas as pd
import QuantLib as ql

import plotly.express as px


class Swap:
    def __init__(
        self,
        notional: float,
        fixed_rate: float,
        effective_dt: dt.date,
        termination_dt: dt.date,
        pay_fixed: bool = True,
        float_index: str = "USDLibor",
        float_tenor: ql.Period = ql.Period(3, ql.Months),
        fixed_freq = ql.Semiannual,  # ql.Frequency
        float_freq = ql.Semiannual,  # ql.Frequency
        day_count: ql.DayCounter = ql.Actual360(),
        calendar: ql.Calendar = ql.UnitedStates(),
        discount_curve: ql.YieldTermStructure = None,
        flat_rate: float = 0.03,  # used only if discount_curve is None
    ):
        self.notional = notional
        self.fixed_rate = fixed_rate
        self.pay_fixed = pay_fixed
        self.calendar = calendar
        self.day_count = day_count

        # Dates
        self.effective_date = ql.Date(effective_dt.day, effective_dt.month, effective_dt.year)
        self.termination_date = ql.Date(termination_dt.day, termination_dt.month, termination_dt.year)

        # Discount curve
        if discount_curve is not None:
            self.discount_curve = discount_curve
        else:
            self.discount_curve = ql.FlatForward(
                self.effective_date,
                ql.QuoteHandle(ql.SimpleQuote(flat_rate)),
                day_count
            )

        self.discount_handle = ql.YieldTermStructureHandle(self.discount_curve)

        # Index
        if float_index == "USDLibor":
            self.index = ql.USDLibor(float_tenor, self.discount_handle)
        else:
            raise NotImplementedError("Only USDLibor supported")

        # Schedules
        self.fixed_schedule = ql.Schedule(
            self.effective_date,
            self.termination_date,
            ql.Period(fixed_freq),
            calendar,
            ql.ModifiedFollowing,
            ql.ModifiedFollowing,
            ql.DateGeneration.Forward,
            False
        )

        self.float_schedule = ql.Schedule(
            self.effective_date,
            self.termination_date,
            ql.Period(float_freq),
            calendar,
            ql.ModifiedFollowing,
            ql.ModifiedFollowing,
            ql.DateGeneration.Forward,
            False
        )

        self._build_swap()

    def _build_swap(self):
        """Internal method to build/rebuild the QuantLib swap."""
        swap_type = ql.VanillaSwap.Payer if self.pay_fixed else ql.VanillaSwap.Receiver
        self.swap = ql.VanillaSwap(
            swap_type,
            self.notional,
            self.fixed_schedule,
            self.fixed_rate,
            self.day_count,
            self.float_schedule,
            self.index,
            0.0,
            self.day_count
        )
        self.engine = ql.DiscountingSwapEngine(self.discount_handle)
        self.swap.setPricingEngine(self.engine)

    def set_curve(self, new_curve: ql.YieldTermStructure):
        """Swap in a new curve and reprice."""
        self.discount_curve = new_curve
        self.discount_handle = ql.YieldTermStructureHandle(new_curve)
        self.index = ql.USDLibor(self.index.tenor(), self.discount_handle)
        self._build_swap()

    def npv(self):
        return self.swap.NPV()

    def fair_rate(self):
        return self.swap.fairRate()

    def pv01(self):
        return self.swap.fixedLegBPS()

    def summary(self):
        return {
            "NPV": self.npv(),
            "Fair Rate": self.fair_rate(),
            "Fixed Leg PV01": self.pv01()
        }

    def to_dataframe(self):
        """
        Returns a DataFrame of fixed and floating leg cashflows.
        """
        data = []

        # Fixed leg
        for cf in self.swap.leg(0):  # 0 = fixed
            if isinstance(cf, ql.FixedRateCoupon):
                data.append({
                    "Date": cf.date(),
                    "Type": "Fixed",
                    "Amount": cf.amount(),
                    "Rate": cf.rate(),
                    "Accrual Start": cf.accrualStartDate(),
                    "Accrual End": cf.accrualEndDate(),
                    "DF": self.discount_handle.discount(cf.date()),
                    "PV": cf.amount() * self.discount_handle.discount(cf.date())
                })

        # Floating leg
        for cf in self.swap.leg(1):  # 1 = float
            if isinstance(cf, ql.FloatingRateCoupon):
                data.append({
                    "Date": cf.date(),
                    "Type": "Float",
                    "Amount": cf.amount(),
                    "Rate": cf.rate(),
                    "Accrual Start": cf.accrualStartDate(),
                    "Accrual End": cf.accrualEndDate(),
                    "DF": self.discount_handle.discount(cf.date()),
                    "PV": cf.amount() * self.discount_handle.discount(cf.date())
                })

        df = pd.DataFrame(data)
        df.sort_values("Date", inplace=True)
        return df.reset_index(drop=True)