from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import orm_get_bank, orm_get_stock_market, orm_get_cryptomarket, orm_update_banner_description, \
    orm_get_user
from parsers.parser_currency_rate import get_exchange_rate


class TotalBalance:
    def __init__(self, banks, stock_markets, crypto_markets):
        self.banks = banks
        self.stock_markets = stock_markets
        self.crypto_markets = crypto_markets

    async def get_total_assets(self):
        total_balance_rubls = Decimal(0.0)

        for bank in self.banks:
            bank_logic = bank.to_logic()
            total_balance_rubls += bank_logic.get_total_balance_bank_rubls()

        for stockmarket in self.stock_markets:
            stockmarket_logic = stockmarket.to_logic()
            total_balance_rubls += await stockmarket_logic.get_total_balance_stockmarket_in_rubls()

        for cryptomarket in self.crypto_markets:
            cryptomarket_logic = cryptomarket.to_logic()
            total_balance_rubls += await cryptomarket_logic.get_total_balance_cryptomarket_in_rubls()

        return total_balance_rubls


async def calculate_total_balance(session: AsyncSession, user_tg_id: int):
    # Получаем все банки, фин. биржи и криптобиржи для пользователя
    user_id = await orm_get_user(session, user_tg_id)
    banks = await orm_get_bank(session, user_id)
    stockmarkets = await orm_get_stock_market(session, user_id)
    cryptomarkets = await orm_get_cryptomarket(session, user_id)

    # Создаем объект TotalBalance для подсчета активов
    total_balance_calculator = TotalBalance(banks, stockmarkets, cryptomarkets)

    # Получаем общий баланс
    total_balance_rubls = await total_balance_calculator.get_total_assets()
    total_balance_dollars = Decimal(get_exchange_rate("RUB", "USD")) * total_balance_rubls

    description = (f"Ваш общий баланс активов составляет: {total_balance_rubls:.2f} рублей 💰\n"
                   f"{total_balance_dollars:.2f} долларов 💲")
    try:
        await orm_update_banner_description(session, name="total_balance", description=description)
    except Exception as e:
        print(f"Ошибка при обновлении описания баннера: {e}")
