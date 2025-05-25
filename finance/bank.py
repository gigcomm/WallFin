from decimal import Decimal

from utils.cache_utils import get_exchange_rate_cached


class BankLogic:
    def __init__(self, bank_name, accounts, currencies, deposits):
        self.bank_name = bank_name
        self.accounts = accounts
        self.currencies = currencies
        self.deposits = deposits
        # self.credit = None

    def get_total_balance_accounts_rubls(self):
        return sum(account.account_balance for account in self.accounts)

    async def get_total_balance_accounts_dollars(self):
        result = sum(account.account_balance for account in self.accounts)
        rate = await get_exchange_rate_cached("RUB", "USD")
        return f"{result * rate:.2f}"

    def get_total_balance_currencies_rubls(self):
        return sum(currency.currency_balance * currency.market_price for currency in self.currencies)

    async def get_total_balance_currencies_dollars(self):
        result = sum(currency.currency_balance * currency.market_price for currency in self.currencies)
        rate = await get_exchange_rate_cached("RUB", "USD")
        return f"{result * rate:.2f}"

    def get_total_balance_deposits_rubls(self):
        return sum(deposit.deposit_balance for deposit in self.deposits)

    async def get_total_balance_deposits_dollars(self):
        result = sum(deposit.deposit_balance for deposit in self.deposits)
        rate = await get_exchange_rate_cached("RUB", "USD")
        return f"{result * rate:.2f}"

    def get_total_balance_bank_rubls(self):
        return (
                Decimal(self.get_total_balance_accounts_rubls()) +
                Decimal(self.get_total_balance_deposits_rubls()) +
                Decimal(self.get_total_balance_currencies_rubls())
        )

    async def get_total_balance_bank_dollars(self):
        acc = await self.get_total_balance_accounts_dollars()
        dep = await self.get_total_balance_deposits_dollars()
        cur = await self.get_total_balance_currencies_dollars()
        return Decimal(acc) + Decimal(dep) + Decimal(cur)


class CurrencyLogic:
    def __init__(self, cur_name, cur_balance, market_price):
        self.cur_name = cur_name
        self.__cur_balance = cur_balance
        self.market_price = market_price

    # требуется реализация миксина для сетера и гетера
    @property
    def currency_balance(self):
        return self.__cur_balance

    @currency_balance.setter
    def currency_balance(self, another_balance):
        if another_balance <= 0:
            raise ValueError("Сумма должна быть положительной")
        self.__cur_balance = another_balance


class DepositLogic:
    def __init__(self, deposit_name, start_date, deposit_term, interest_rate, deposit_balance):
        self.deposit_name = deposit_name
        self.start_date = start_date
        self.deposit_term = deposit_term
        self.interest_rate = interest_rate
        self.__deposit_balance = deposit_balance

    def calculating_final_amount(self, deposit_balance, deposit_term, interest_rate):
        final_deposit = float(deposit_balance) * (1 + (interest_rate / 100) / 12) ** deposit_term
        return final_deposit

    @property
    def deposit_balance(self):
        return self.__deposit_balance

    @deposit_balance.setter
    def deposit_balance(self, another_balance):
        if another_balance <= 0:
            raise ValueError("Сумма должна быть положительной")
        self.__deposit_balance = another_balance


class AccountLogic:
    def __init__(self, account_name, acc_balance):
        self.account_name = account_name
        self.__acc_balance = acc_balance

    @property
    def account_balance(self):
        return self.__acc_balance

    @account_balance.setter
    def account_balance(self, another_balance):
        if another_balance <= 0:
            raise ValueError("Сумма должна быть положительной")
        self.__acc_balance = another_balance


class CreditCardLogic(BankLogic):
    pass
