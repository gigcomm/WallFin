from abc import abstractmethod, ABC


class Portfolio(ABC):

    def __init__(self, portfolio_name):
        self.portfolio_name = portfolio_name
        self.assets = []

    @abstractmethod
    def add_asset(self, asset):
        pass

    @abstractmethod
    def get_total_balance(self):
        pass


class StockPortfolio(Portfolio):
    def __init__(self, name):
        super().__init__(name)


class CryptoPortfolio(Portfolio):
    def __init__(self, name):
        super().__init__(name)
