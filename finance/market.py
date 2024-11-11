from abc import abstractmethod, ABC


class MarketLogic(ABC):
    def __init__(self, name):
        self.name = name
        self.portfolio = None


class StockMarketLogic(MarketLogic):
    def __init__(self, shares, funds, name):
        super().__init__(name)
        self.shares = shares
        self.funds = funds


class ShareLogic:
    def __init__(self, share_name, purchase_price, selling_price, market_price, quantity):
        self.share_name = share_name
        self.purchase_price = purchase_price
        self.selling_price = selling_price
        self.market_price = market_price
        self.quantity = quantity


class FundLogic:
    def __init__(self, fund_name, purchase_price, selling_price, market_price, quantity):
        self.fund_name = fund_name
        self.purchase_price = purchase_price
        self.selling_price = selling_price
        self.market_price = market_price
        self.quantity = quantity


# class BondLogic:
#     def __init__(self, bond_name, purchase_price, selling_price, quantity):
#         self.bond_name = bond_name
#         self.purchase_price = purchase_price
#         self.selling_price = selling_price
#         self.quantity = quantity


class CryptoMarketLogic(MarketLogic):
    def __init__(self, cryptocurrencies, name):
        super().__init__(name)
        self.cryptocurrencies = cryptocurrencies

    def total_balance(self):
        pass


class СryptocurrencyLogic:
    def __init__(self, cryptocur_name, cryptocur_balance, purchase_price, selling_price, market_price):
        self.cryptocur_name = cryptocur_name
        self.cryptocur_balance = cryptocur_balance
        self.purchase_price = purchase_price
        self.selling_price = selling_price
        self.market_price = market_price
