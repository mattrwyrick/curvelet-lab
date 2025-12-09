

import datetime as dt
import pandas as pd
import QuantLib as ql
import matplotlib.pyplot as plt



class InterestRateDerivative:

    def __init__(
        self,
        notional: float,
        effective_dt: dt.date,
        termination_dt: dt.date,
        day_count: ql.DayCounter = ql.Actual360(),
        calendar: ql.Calendar = ql.UnitedStates(),
    ):
        self.notional = notional
        self.day_count = day_count
        self.calendar = calendar

        self.effective_date = ql.Date(effective_dt.day, effective_dt.month, effective_dt.year)
        self.termination_date = ql.Date(termination_dt.day, termination_dt.month, termination_dt.year)

        self.discount_curve = None
        self.discount_handle = None
        self.index = None

    def _build_product(self):
        """
        Build the interest rate product
        :return:
        """
        pass

    def set_curve(self, new_curve: ql.YieldTermStructure):
        """
        Update the underlying curve of this instrument
        :param new_curve:
        :return:
        """
        self.discount_curve = new_curve
        self.discount_handle = ql.YieldTermStructureHandle(new_curve)
        self.index = ql.USDLibor(self.index.tenor(), self.discount_handle)
        self._build_product()





