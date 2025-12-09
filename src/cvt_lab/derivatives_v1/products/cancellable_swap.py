# cancellable_swap.py

from swap import Swap
from cvt_lab.derivatives_v2.products.bermudan_swaption import BermudanSwaption
import QuantLib as ql


class CancellableSwap:
    def __init__(
        self,
        swap: Swap,
        cancel_after_years: int = 2,
        cancel_freq: ql.Period = ql.Period(3, ql.Months)
    ):
        """
        Wraps a vanilla swap and adds Bermudan cancellation rights.
        """
        self.swap = swap

        # Build exercise dates (starting after X years)
        self.exercise_dates = [
            d for d in swap.fixed_schedule
            if d > ql.UnitedStates().advance(swap.effective_date, ql.Period(cancel_after_years, ql.Years))
        ][::int(cancel_freq.length())]

        self.swaption = BermudanSwaption(swap, self.exercise_dates)

    def npv(self):
        return self.swap.npv() - self.swaption.npv()

    def summary(self):
        return {
            "Swap NPV": self.swap.npv(),
            "Bermudan NPV": self.swaption.npv(),
            "Cancellable Swap NPV": self.npv()
        }

    def pv01_fd(self, bump_bp=1.0):
        """
        Approximate PV01 of cancellable swap: bump curve up by X bp.
        """
        base_npv = self.npv()

        # Clone curve and bump rate
        orig_rate = self.swap.discount_curve.zeroRate(
            self.swap.effective_date, self.swap.day_count, ql.Continuous).rate()
        bumped_rate = orig_rate + bump_bp / 10000.0
        bumped_curve = ql.FlatForward(
            self.swap.effective_date,
            ql.QuoteHandle(ql.SimpleQuote(bumped_rate)),
            self.swap.day_count
        )
        self.swap.set_curve(bumped_curve)
        self.swaption = BermudanSwaption(self.swap, self.exercise_dates)  # rebuild with new curve

        bumped_npv = self.npv()

        # Reset
        self.swap.set_curve(self.swap.discount_curve)  # reset to original
        self.swaption = BermudanSwaption(self.swap, self.exercise_dates)

        return (bumped_npv - base_npv) * 1e4  # in bp

    def vega_fd(self, bump_vol=0.0001):
        """
        Approximate Vega (∂NPV/∂volatility) by bumping HW model vol.
        """
        base_model = ql.HullWhite(self.swap.discount_handle)
        base_npv = self.npv()

        # Bumped model
        bumped_model = ql.HullWhite(self.swap.discount_handle, a=base_model.a(), sigma=base_model.sigma() + bump_vol)
        bumped_engine = ql.TreeSwaptionEngine(bumped_model, 50)

        self.swaption.swaption.setPricingEngine(bumped_engine)
        bumped_npv = self.npv()

        # Reset engine
        self.swaption = BermudanSwaption(self.swap, self.exercise_dates)

        return (bumped_npv - base_npv) / bump_vol  # dollar vega

