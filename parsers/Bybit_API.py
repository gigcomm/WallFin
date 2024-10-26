import os

from pybit.unified_trading import HTTP


def get_price_cryptocurrency(name_cryptocurrency: str = ""):
    session = HTTP(
        api_key=os.getenv("CRYPTO_BYBIT_API_KEY"),
        api_secret=os.getenv("CRYPTO_BYBIT_API_SECRET")
    )
    r = session.get_orderbook(category="spot", symbol=name_cryptocurrency)
    return float(r['result']['a'][0][0])

#ввод SOLUSDT для выдачи цены криптовалюты
# get_price_cryptocurrency("SOLUSDT")