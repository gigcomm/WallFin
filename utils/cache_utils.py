import json

from database.orm_query import orm_get_cryptocurrency_name, orm_get_share_name, orm_get_fund_name, orm_get_currency_name
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

        if asset_type == "crypto":
            asset = await orm_get_cryptocurrency_name(session, asset_name)
        elif asset_type == "share":
            asset = await orm_get_share_name(session, asset_name)
        elif asset_type == "fund":
            asset = await orm_get_fund_name(session, asset_name)
        elif asset_type == "currency":
            asset = await orm_get_currency_name(session, asset_name)
        else:
            logger.error(f"Некорректный тип актива: {asset_type}")
            return None

        if asset and asset.market_price is not None:
            redis_client.setex(key, 60, json.dumps({"price": float(asset.market_price)}))
            return asset.market_price

        logger.warning(f"Цена для {asset_type} '{asset_name}' не найдена в базе данных.")
        return None

    except Exception as e:
        logger.error(f"Ошибка при получении цены {asset_type} '{asset_name}': {e}")
        return None
