from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import (
    orm_get_bank,
    orm_get_stock_market,
    orm_get_cryptomarket,
    orm_update_banner_description,
    orm_get_user,
)
from utils.cache_utils import get_exchange_rate_cached


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
    user_id = await orm_get_user(session, user_tg_id)
    banks = await orm_get_bank(session, user_id)
    stockmarkets = await orm_get_stock_market(session, user_id)
    cryptomarkets = await orm_get_cryptomarket(session, user_id)

    total_balance_calculator = TotalBalance(banks, stockmarkets, cryptomarkets)

    total_balance_rub = await total_balance_calculator.get_total_assets()
    total_balance_usd = await get_exchange_rate_cached("RUB", "USD") * total_balance_rub
    banks_total_rub = sum(bank.to_logic().get_total_balance_bank_rubls() for bank in banks)
    banks_total_usd = await get_exchange_rate_cached("RUB", "USD") * banks_total_rub
    stockmarkets_total_rub = sum([await stockmarket.to_logic().get_total_balance_stockmarket_in_rubls() for stockmarket in stockmarkets])
    stockmarkets_total_usd = await get_exchange_rate_cached("RUB", "USD") * stockmarkets_total_rub
    cryptomarket_total_usd = sum(cryptomarket.to_logic().get_total_balance_cryptomarket_in_dollars() for cryptomarket in cryptomarkets)
    cryptomarket_total_rub = await get_exchange_rate_cached("USD", "RUB") * cryptomarket_total_usd
    rate_usd = await get_exchange_rate_cached("USD", "RUB")
    rate_eur = await get_exchange_rate_cached("EUR", "RUB")

    description = (
        f"📊 <b>Общий баланс активов</b>\n"
        f"• {total_balance_rub:,.2f} ₽\n"
        f"• {total_balance_usd:,.2f} $\n\n"

        f"🏦 <b>Банки:</b>\n"
        f"• {banks_total_rub:,.2f} ₽\n"
        f"• {banks_total_usd:,.2f} $\n\n"

        f"📈 <b>Фондовые биржи:</b>\n"
        f"• {stockmarkets_total_rub:,.2f} ₽\n"
        f"• {stockmarkets_total_usd:,.2f} $\n\n"

        f"💸🔒 <b>Криптобиржи:</b>\n"
        f"• {cryptomarket_total_rub:,.2f} ₽\n"
        f"• {cryptomarket_total_usd:,.2f} $\n\n"
        
        f"📈 <b>Курс валют к рублю:</b>\n"
        f"💵 <b>Доллар</b> {rate_usd:,.2f} ₽\n"
        f"💶 <b>Евро</b> {rate_eur:,.2f} ₽"
    )

    try:
        await orm_update_banner_description(session, name="total_balance", description=description)
    except Exception as e:
        print(f"Ошибка при обновлении описания баннера: {e}")
