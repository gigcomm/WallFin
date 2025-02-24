import asyncio
import json
import os

import redis
from redis import Redis
from celery_app import celery_app

from database.engine import session_maker
from database.orm_query import orm_get_cryptocurrency_all, orm_get_share_all, orm_get_fund_all, orm_get_currency_all
from parsers.Bybit_API import get_price_cryptocurrency
from parsers.parser_currency_rate import get_exchange_rate
from parsers.tinkoff_invest_API import get_price_share, get_price_fund

redis_host = os.getenv("REDIS_HOST", "redis")
redis_port = os.getenv("REDIS_P ORT")
redis_client = Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)


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
                    if new_price:
                        crypto.market_price = new_price
                        updated_assets.append(crypto)
                        redis_client.set(f"price:crypto:{crypto.name}", json.dumps({"price": new_price}))
                        print(f"Обновления криптовалюты {crypto.name}")

            except Exception as e:
                print(f"Ошибка обновления криптовалюты {crypto.name}:{e}")

        await session.commit()
        return updated_assets


async def update_shares_and_funds():
    async with session_maker() as session:
        shares = await orm_get_share_all(session)
        funds = await orm_get_fund_all(session)
        updated_assets = []

        for share in shares:
            try:
                new_price = await get_price_share(share.name)
                if new_price:
                    share.price = new_price
                    updated_assets.append(share)
                    redis_client.set(f"price:share:{share.name}", json.dumps({"price": new_price}))
                    print(f"Обновления акции {share.name}")

            except Exception as e:
                print(f"Ошибка обновления акции{share.name}:{e}")

        for fund in funds:
            try:
                new_price = await get_price_fund(fund.name)
                if new_price:
                    fund.price = new_price
                    updated_assets.append(fund)
                    redis_client.set(f"price:fund:{fund.name}", json.dumps({"price": new_price}))
                    print(f"Обновления фонда {fund.name}")

            except Exception as e:
                print(f"Ошибка обновления фонда{fund.name}:{e}")

        await session.commit()
        return updated_assets


async def update_currencies():
    async with session_maker() as session:
        currencies = await orm_get_currency_all(session)
        updated_assets = []

        for currency in currencies:
            try:
                new_rate = get_exchange_rate(currency.name, "RUB")
                if new_rate:
                    currency.price = new_rate
                    updated_assets.append(currency)
                    redis_client.set(f"price:currency:{currency.name}_'RUB'", json.dumps({"rate": new_rate}))
                    print(f"Обновления курса {currency.from_currency}/'RUB'")

            except Exception as e:
                print(f"Ошибка обновления курса {currency.from_currency}/'RUB': {e}")

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
