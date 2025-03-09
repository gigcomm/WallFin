import json

from database.orm_query import orm_get_cryptocurrency_name, orm_get_share_name, orm_get_fund_name, orm_get_currency_name
from tasks.update_price_assets import redis_client


async def get_cache_price(asset_type: str, asset_name: str, session):
    key = f"price:{asset_type}:{asset_name}"

    cached_data = redis_client.get(key)
    if cached_data:
        print(cached_data)
        price = json.loads(cached_data)["price"]
        if price is not None:
            return price

    if asset_type == "crypto":
        asset = await orm_get_cryptocurrency_name(session, asset_name)
    elif asset_type == "share":
        asset = await orm_get_share_name(session, asset_name)
    elif asset_type == "fund":
        asset = await orm_get_fund_name(session, asset_name)
    elif asset_type == "currency":
        asset = await orm_get_currency_name(session, asset_name)
    else:
        return None

    if asset and asset.market_price is not None:
        redis_client.setex(key, 60, json.dumps({"price": float(asset.market_price)}))
        return asset.market_price

    return None
