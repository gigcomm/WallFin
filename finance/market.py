from abc import abstractmethod, ABC
from decimal import Decimal

from parsers.parser_currency_rate import get_exchange_rate


class MarketLogic(ABC):
    def __init__(self, name):
        self.name = name
        self.portfolio = None


class StockMarketLogic(MarketLogic):
    def __init__(self, shares, funds, name):
        super().__init__(name)
        self.shares = shares
        self.funds = funds

    def get_total_balance_shares_in_dollars(self):
        result = sum(
            (share.market_price * share.quantity) * Decimal(get_exchange_rate(share.currency, "USD")) for share in
            self.shares)
        return f"{result:.2f}"

    def get_total_balance_shares_in_rubls(self):
        result =  sum(
            (share.market_price * share.quantity) * Decimal(get_exchange_rate(share.currency, "RUB")) for share in
            self.shares)
        return f"{result:.2f}"

    def get_total_balance_funds_in_dollars(self):
        result =  sum((fund.market_price * fund.quantity) * Decimal(get_exchange_rate(fund.currency, "USD")) for fund in
                   self.funds)
        return f"{result:.2f}"

    def get_total_balance_funds_in_rubls(self):
        result =  sum((fund.market_price * fund.quantity) * Decimal(get_exchange_rate(fund.currency, "RUB")) for fund in
                   self.funds)
        return f"{result:.2f}"

    def get_total_balance_stockmarket_in_dollars(self):
        return Decimal(self.get_total_balance_shares_in_dollars()) + Decimal(self.get_total_balance_funds_in_dollars())

    def get_total_balance_stockmarket_in_rubls(self):
        return Decimal(self.get_total_balance_shares_in_rubls()) + Decimal(self.get_total_balance_funds_in_rubls())



class ShareLogic:
    def __init__(self, share_name, purchase_price, selling_price, market_price, quantity, currency):
        self.share_name = share_name
        self.purchase_price = purchase_price
        self.selling_price = selling_price
        self.market_price = market_price
        self.quantity = quantity
        self.currency = currency


class FundLogic:
    def __init__(self, fund_name, purchase_price, selling_price, market_price, quantity, currency):
        self.fund_name = fund_name
        self.purchase_price = purchase_price
        self.selling_price = selling_price
        self.market_price = market_price
        self.quantity = quantity
        self.currency = currency


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

    def get_total_balance_cryptocurrencies(self):
        return sum(
            cryptocurrency.market_price * cryptocurrency.cryptocur_balance for cryptocurrency in self.cryptocurrencies)

    def get_total_balance_cryptomarket_in_dollars(self):
        return self.get_total_balance_cryptocurrencies()

    def get_total_balance_cryptomarket_in_rubls(self):
        exchange_rate = Decimal(get_exchange_rate("USD", "RUB"))
        result = self.get_total_balance_cryptomarket_in_dollars() * exchange_rate
        return f"{result:.2f}"


class СryptocurrencyLogic:
    def __init__(self, cryptocur_name, cryptocur_balance, purchase_price, selling_price, market_price):
        self.cryptocur_name = cryptocur_name
        self.cryptocur_balance = cryptocur_balance
        self.purchase_price = purchase_price
        self.selling_price = selling_price
        self.market_price = market_price
