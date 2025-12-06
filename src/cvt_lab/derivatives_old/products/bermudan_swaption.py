# swaption.py

import QuantLib as ql
from swap import Swap
from typing import List

class BermudanSwaption:
    def __init__(
        self,
        swap: Swap,
        exercise_dates: List[ql.Date],
        model: ql.HullWhite = None,
        engine_steps: int = 50,
    ):
        """
        Priced using Hull-White 1F model on the provided swap.
        """
        self.swap = swap
        self.exercise_dates = exercise_dates

        # Build Bermudan exercise object
        self.exercise = ql.BermudanExercise(exercise_dates)

        # Build swaption
        self.swaption = ql.Swaption(swap.swap, self.exercise)

        # Use Hull-White model with provided curve or create default
        self.model = model or ql.HullWhite(swap.discount_handle)

        self.engine = ql.TreeSwaptionEngine(self.model, engine_steps)
        self.swaption.setPricingEngine(self.engine)

    def npv(self):
        return self.swaption.NPV()

    def summary(self):
        return {
            "Bermudan Swaption NPV": self.npv(),
            "Num Exercise Dates": len(self.exercise_dates),
        }
