import json

from database.orm_query import orm_get_cryptocurrency_all, orm_get_share_all, orm_get_currency, orm_get_fund_all, \
    orm_get_currency_all
from tasks.update_price_assets import redis_client


async def get_cache_price(asset_type: str, asset_name: str, session):
    key = f"price:{asset_type}:{asset_name}"

    cached_data = redis_client.get(key)
    if cached_data:
        return json.loads(cached_data)["price"]


    if asset_type == "cryptocurrency":
        asset = await orm_get_cryptocurrency_all(session)
    elif asset_type == "share":
        asset = await orm_get_share_all(session)
    elif asset_type == "fund":
        asset = await orm_get_fund_all(session)
    elif asset_type == "currency":
        asset = await orm_get_currency_all(session)
    else:
        return None

    if asset:
        redis_client.setex(key, 60, json.dumps({"price": asset.market_price}))
        return asset.market_price

    return None
