import asyncio
import json
import os

from redis import Redis
from celery_app import celery_app

from database.engine import session_maker
from database.orm_query import (
    orm_get_cryptocurrency_all,
    orm_get_share_all,
    orm_get_fund_all,
    orm_get_currency_all
)
from parsers.Bybit_API import get_price_cryptocurrency
from parsers.parser_currency_rate import get_exchange_rate
from parsers.tinkoff_invest_API import get_price_share, get_price_fund
from tg_bot.logger import logger

redis_client = Redis(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0,
    password=os.getenv("REDIS_PASSWORD"),
    decode_responses=True
)


async def update_price_assets(
        asset_type: str,
        get_all_func,
        get_all_price,
        ttl: int = 300,
        suffix: str = ""
) -> list:
    """
        Универсальная функция обновления цен активов.

        :param asset_type: тип актива ('cryptocurrency', 'share', 'fund', 'currency')
        :param get_all_func: функция ORM для получения всех активов
        :param get_all_price: функция для получения цены актива
        :param ttl: время жизни кеша в секундах
        :param suffix: суффикс для тикера (например 'USDT' для криптовалют)
        """
    async with session_maker() as session:
        assets = await get_all_func(session)
        updated_assets = []
        seen_prices = {}

        for asset in assets:
            asset_name = asset.name
            ticker = asset_name
            try:
                if asset_type == 'crypto' and asset_name != 'USDT' and suffix:
                    ticker = asset_name + suffix

                if asset_name in seen_prices:
                    new_price = seen_prices[asset_name]
                else:
                    cache_key = f"price:{asset_type}:{asset_name}_RUB" if asset_type == "currency" else f"price:{asset_type}:{ticker}"
                    cached = redis_client.get(cache_key)

                    if cached:
                        new_price = json.loads(cached)['price']
                        logger.info(f"Взяли цену {asset_type} {asset_name} из Redis: {new_price}")
                    else:
                        if asyncio.iscoroutinefunction(get_all_price):
                            price_data = await get_all_price(ticker)
                        else:
                            price_data = get_all_price(ticker)
                        if not price_data:
                            logger.warning(f"⚠️ Цена для {asset_type} {ticker} не найдена")
                            continue

                        new_price = price_data[0] if isinstance(price_data, (list, tuple)) else price_data

                        redis_client.setex(cache_key, ttl, json.dumps({"price": new_price}))
                        logger.info(f"Получили цену {asset_type} {ticker} из API: {new_price}")

                    seen_prices[asset_name] = new_price

                if new_price is not None:
                    asset.market_price = new_price
                    updated_assets.append(asset)

            except Exception as e:
                logger.exception(f"Ошибка обновления {asset_type} {asset_name}: {e}")

    await session.commit()
    return updated_assets


async def update_cryptocurrencies():
    return await update_price_assets(
        asset_type='crypto',
        get_all_func=orm_get_cryptocurrency_all,
        get_all_price=get_price_cryptocurrency,
        ttl=300,
        suffix='USDT'
    )


async def update_shares():
    return await update_price_assets(
        asset_type='share',
        get_all_func=orm_get_share_all,
        get_all_price=get_price_share,
        ttl=120
    )


async def update_funds():
    return await update_price_assets(
        asset_type='fund',
        get_all_func=orm_get_fund_all,
        get_all_price=get_price_fund,
        ttl=120
    )


async def update_currencies():
    return await update_price_assets(
        asset_type='currency',
        get_all_func=orm_get_currency_all,
        get_all_price=get_exchange_rate,
        ttl=120
    )


@celery_app.task
def test_task():
    return "Сельдерей работает!"


@celery_app.task
def update_price():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(update_all_prices())
    print("🔄 Запуск обновления цен через Celery...")


async def update_all_prices():
    await asyncio.gather(
        update_cryptocurrencies(),
        update_shares(),
        update_funds(),
        update_currencies()
    )
    print("✅ Данные обновлены и сохранены в БД")
