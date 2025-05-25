import json
from decimal import Decimal

from database.orm_query import orm_get_cryptocurrency_name, orm_get_share_name, orm_get_fund_name, orm_get_currency_name
from parsers.parser_currency_rate import get_exchange_rate

from tasks.update_price_assets import redis_client
from tg_bot.logger import logger


async def get_cache_price(asset_type: str, asset_name: str, session):
    key = f"price:{asset_type}:{asset_name}"
    logger.info(f"Получение цены для {asset_type} '{asset_name}' из кэша.")

    try:
        cached_data = redis_client.get(key)
        if cached_data:
            price = json.loads(cached_data)["price"]
            if price is not None:
                logger.info(f"Цена {asset_type} '{asset_name}' из кэша: {price}")
                return price

        logger.info("Цена не найдена в кэше, получение из базы данных.")

        query_funcs = {
            "crypto": orm_get_cryptocurrency_name,
            "share": orm_get_share_name,
            "fund": orm_get_fund_name,
            "currency": orm_get_currency_name,
        }

        query_funcs = query_funcs.get(asset_type)
        if not query_funcs:
            logger.error(f"Некорректный тип актива: {asset_type}")
            return None

        asset = await query_funcs(session, asset_name)

        if asset and asset.market_price is not None:
            ttl_map = {
                "crypto": 100,
                "share": 200,
                "fund": 200,
                "currency": 100,
            }
            ttl = ttl_map.get(asset_type, 300)
            redis_client.setex(key, ttl, json.dumps({"price": float(asset.market_price)}))
            logger.info(
                f"Цена {asset_type} '{asset_name}' получена из базы данных и закэширована: {asset.market_price}")
            return asset.market_price

        logger.warning(f"Цена для {asset_type} '{asset_name}' не найдена в базе данных.")
        return None

    except Exception as e:
        logger.error(f"Ошибка при получении цены {asset_type} '{asset_name}': {e}")
        return None


async def get_exchange_rate_cached(from_currency: str, to_currency: str, ttl_seconds: int = 300) -> Decimal:
    key = f"exchange_rate:{from_currency}:{to_currency}"
    cached_rate = redis_client.get(key)

    if cached_rate:
        return Decimal(cached_rate)

    rate = Decimal(get_exchange_rate(from_currency, to_currency))

    redis_client.setex(key, ttl_seconds, str(rate))

    return rate
