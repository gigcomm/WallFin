import asyncio
import json
import os

from redis import Redis
from celery_app import celery_app

from database.engine import session_maker
from database.orm_query import orm_get_cryptocurrency_all, orm_get_share_all, orm_get_fund_all, orm_get_currency_all
from parsers.Bybit_API import get_price_cryptocurrency
from parsers.parser_currency_rate import get_exchange_rate
from parsers.tinkoff_invest_API import get_price_share, get_price_fund
from tg_bot.logger import logger

redis_client = Redis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), db=0, decode_responses=True)


async def update_cryptocurrencies():
    async with session_maker() as session:
        cryptocurrencies = await orm_get_cryptocurrency_all(session)
        updated_assets = []

        for crypto in cryptocurrencies:
            try:
                crypto_name = crypto.name
                if crypto_name != "USDT":
                    crypto_name += "USDT"
                    new_price = get_price_cryptocurrency(crypto_name)

                    if not new_price:
                        logger.warning(f"⚠️ Цена для {crypto_name} не найдена, не обновляем market_price")
                        continue

                    crypto.market_price = new_price
                    updated_assets.append(crypto)

                    redis_client.setex(f"price:crypto:{crypto.name}", 60, json.dumps({"price": new_price}))

            except Exception as e:
                logger.exception(f"Ошибка обновления криптовалюты {crypto.name}: {e}")

        await session.commit()
        return updated_assets


async def update_shares_and_funds():
    async with session_maker() as session:
        shares = await orm_get_share_all(session)
        funds = await orm_get_fund_all(session)
        updated_assets = []

        for share in shares:
            try:
                new_price_data = await get_price_share(share.name)

                if not new_price_data:
                    logger.warning(f"⚠️ Цена для {share.name} не найдена, не обновляем market_price")
                    continue

                new_price = new_price_data[0]

                share.market_price = new_price
                updated_assets.append(share)

                redis_client.setex(f"price:share:{share.name}", 60, json.dumps({"price": new_price}))

            except Exception as e:
                logger.exception(f"Ошибка обновления акции{share.name}: {e}")

        for fund in funds:
            try:
                new_price_data = await get_price_fund(fund.name)

                if not new_price_data:
                    logger.warning(f"⚠️ Цена для {fund.name} не найдена, не обновляем market_price")
                    continue

                new_price = new_price_data[0]

                fund.market_price = new_price
                updated_assets.append(fund)

                redis_client.setex(f"price:fund:{fund.name}", 60, json.dumps({"price": new_price}))

            except Exception as e:
                logger.exception(f"Ошибка обновления фонда{fund.name}: {e}")

        await session.commit()
        return updated_assets


async def update_currencies():
    async with session_maker() as session:
        currencies = await orm_get_currency_all(session)
        updated_assets = []

        for currency in currencies:
            try:
                new_rate = get_exchange_rate(currency.name, 'RUB')

                if new_rate is not None:
                    currency.market_price = new_rate
                    updated_assets.append(currency)

                    redis_client.setex(f"price:currency:{currency.name}_RUB", 60, json.dumps({"rate": new_rate}))
                else:
                    print(f"⚠️ Цена для {currency.name} не найдена, не обновляем курс валюты")

            except Exception as e:
                logger.exception(f"Ошибка обновления курса {currency.name}/'RUB': {e}")

        await session.commit()
        return updated_assets


@celery_app.task
def test_task():
    return "Сельдерей работает!"


@celery_app.task
def update_price():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(update_all_prices())


async def update_all_prices():
    await asyncio.gather(
        update_cryptocurrencies(),
        update_shares_and_funds(),
        update_currencies()
    )
    print("✅ Данные обновлены и сохранены в БД")
