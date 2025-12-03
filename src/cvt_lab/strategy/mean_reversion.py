


from cvt_lab.strategy.base import BaseTrade

from cvt_lab.signal import stationarity


class MeanReversion(BaseTrade):

    def __init__(
            self,
            series,
            funds,
            position
    ):
        super().__init__(
            series=series,
            funds=funds,
            position=position
        )

    def add_data(self, new_data):
        raise NotImplemented(f"Implement add_new_data(...) in this class: {type(self)}")

    def clip_data(self, *args, **kwargs):
        pass

    def execute(self, *args, **kwargs):
        raise NotImplemented(f"Implement execute(...) in this class: {type(self)}")

    def buy(self):
        raise NotImplemented(f"Implement buy(...) in this class: {type(self)}")

    def should_buy(self):
        raise NotImplemented(f"Implement should_buy(...) in this class: {type(self)}")

    def sell(self):
        raise NotImplemented(f"Implement sell(...) in this class: {type(self)}")

    def should_sell(self):
        raise NotImplemented(f"Implement should_sell(...) in this class: {type(self)}")

    def exit_position(self):
        raise NotImplemented(f"Implement exit_position(...) in this class: {type(self)}")

    def should_exit_position(self):
        raise NotImplemented(f"Implement should_exit_position(...) in this class: {type(self)}")

    def eval_target_ranges(self, series=None):
        pass

    def trim_to_target_range(self, series=None):
        pass

    def trim_to_next_target_range(self, series=None):
        pass

    def is_stationary(self, series=None):
        pass

    def get_lower_band(self, series=None):
        pass

    def get_upper_band(self, series=None):
        pass

    def get_mean(self, series=None):
        pass

    def get_standard_dev(self, series=None):
        pass
