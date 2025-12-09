# vol.py

import QuantLib as ql
import pandas as pd

class SwaptionVolSurface:
    def __init__(self, settlement_date, atm_vol_quotes):
        """
        atm_vol_quotes = dict{ (expiry, tenor): vol }
        """

        self.calendar = ql.UnitedStates()
        self.day_count = ql.Actual365Fixed()

        self.settlement_date = settlement_date
        ql.Settings.instance().evaluationDate = settlement_date

        self.atm_quotes = atm_vol_quotes

        self._build_surface()

    def _build_surface(self):
        helpers = []

        for (exp_n, exp_unit, ten_n, ten_unit), vol in self.atm_quotes.items():
            expiry = ql.Period(exp_n, exp_unit)
            tenor = ql.Period(ten_n, ten_unit)
            quote = ql.QuoteHandle(ql.SimpleQuote(vol))

            helper = ql.SwaptionHelper(
                expiry,
                tenor,
                quote,
                ql.USDLibor(ql.Period(3, ql.Months)),
                ql.Annual,
                self.calendar,
                ql.ModifiedFollowing,
                ql.Thirty360(),
                ql.BlackCalibrationHelper.RelativePriceError,
            )
            helpers.append(helper)

        self.surface = ql.SwaptionVolatilityStructure(
            self.settlement_date,
            self.calendar,
            ql.ModifiedFollowing,
            ql.BlackVarianceSurface
        )

    def atm_matrix(self):
        data = []
        for key, vol in self.atm_quotes.items():
            (e_n, e_u, t_n, t_u) = key
            data.append({
                "Expiry": f"{e_n}{e_u.name[0]}",
                "Tenor": f"{t_n}{t_u.name[0]}",
                "ATM Vol": vol,
            })
        return pd.DataFrame(data)
