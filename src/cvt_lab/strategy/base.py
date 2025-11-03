

class BaseTrade(object):

    def __init__(
            self,
            series,
            funds,
            position,
    ):
        self.series = series
        self.funds = funds
        self.position = position

    def deposit_funds(self, amount, allow_negative=False, raise_exception=False):
        if allow_negative:
            self.funds += amount
            return True
        elif amount < (-1.0 * self.funds):
            if raise_exception:
                raise ValueError(f"Insufficient Funds. Capital: {self.funds} Add: {amount}")
            return False
        else:
            self.funds += amount
            return True

    def withdraw_funds(self, amount, allow_negative=False, raise_exception=False):
        if allow_negative:
            self.funds -= amount
            return True
        elif (-1.0 * amount) > self.funds:
            if raise_exception:
                raise ValueError(f"Insufficient Funds. Capital: {self.funds} Add: {amount}")
            return False
        else:
            self.funds -= amount
            return True

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

