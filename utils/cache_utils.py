import json

from database.orm_query import orm_get_cryptocurrency_all, orm_get_share_all, orm_get_fund_all, \
    orm_get_currency_all, orm_get_cryptocurrency, orm_get_cryptocurrency_first, orm_get_share_first, orm_get_fund_first, \
    orm_get_currency_first
from tasks.update_price_assets import redis_client


async def get_cache_price(asset_type: str, asset_name: str, session):
    key = f"price:{asset_type}:{asset_name}"

    cached_data = redis_client.get(key)
    if cached_data:
        return json.loads(cached_data)["price"]


    if asset_type == "cryptocurrency":
        asset = await orm_get_cryptocurrency_first(session)
    elif asset_type == "share":
        asset = await orm_get_share_first(session)
    elif asset_type == "fund":
        asset = await orm_get_fund_first(session)
    elif asset_type == "currency":
        asset = await orm_get_currency_first(session)
    else:
        return None

    if asset:
        redis_client.setex(key, 60, json.dumps({"price": float(asset.market_price)}))
        return asset.market_price

    return None
