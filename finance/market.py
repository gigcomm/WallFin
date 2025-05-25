from abc import abstractmethod, ABC
from decimal import Decimal

from parsers.parser_currency_rate import get_exchange_rate
from utils.cache_utils import get_exchange_rate_cached


class MarketLogic(ABC):
    def __init__(self, name):
        self.name = name
        self.portfolio = None


class StockMarketLogic(MarketLogic):
    def __init__(self, shares, funds, name):
        super().__init__(name)
        self.shares = shares
        self.funds = funds

    async def get_total_balance_shares_in_dollars(self):
        total = Decimal(0)
        for share in self.shares:
            rate = await get_exchange_rate_cached(share.currency, "USD")
            total += share.market_price * share.quantity * rate
        return total

    async def get_total_balance_shares_in_rubls(self):
        total = Decimal(0)
        for share in self.shares:
            rate = await get_exchange_rate_cached(share.currency, "RUB")
            total += share.market_price * share.quantity * rate
        return total

    async def get_total_balance_funds_in_dollars(self):
        total = Decimal(0)
        for fund in self.funds:
            rate = await get_exchange_rate_cached(fund.currency, "USD")
            total += fund.market_price * fund.quantity * rate
        return total

    async def get_total_balance_funds_in_rubls(self):
        total = Decimal(0)
        for fund in self.funds:
            rate = await get_exchange_rate_cached(fund.currency, "RUB")
            total += fund.market_price * fund.quantity * rate
        return total

    async def get_total_balance_stockmarket_in_dollars(self):
        shares_total = await self.get_total_balance_shares_in_dollars()
        funds_total = await self.get_total_balance_funds_in_dollars()
        return shares_total + funds_total

    async def get_total_balance_stockmarket_in_rubls(self):
        shares_total = await self.get_total_balance_shares_in_rubls()
        funds_total = await self.get_total_balance_funds_in_rubls()
        return shares_total + funds_total


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
            cryptocurrency.market_price * cryptocurrency.cryptocur_balance
            for cryptocurrency in self.cryptocurrencies
        )

    def get_total_balance_cryptomarket_in_dollars(self):
        return self.get_total_balance_cryptocurrencies()

    async def get_total_balance_cryptomarket_in_rubls(self):
        exchange_rate = await get_exchange_rate_cached("USD", "RUB")
        total_usd = self.get_total_balance_cryptomarket_in_dollars()
        return Decimal(total_usd) * Decimal(exchange_rate)


class СryptocurrencyLogic:
    def __init__(self, cryptocur_name, cryptocur_balance, purchase_price, selling_price, market_price):
        self.cryptocur_name = cryptocur_name
        self.cryptocur_balance = cryptocur_balance
        self.purchase_price = purchase_price
        self.selling_price = selling_price
        self.market_price = market_price
