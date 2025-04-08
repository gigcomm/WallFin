import os

from pybit.unified_trading import HTTP

from tg_bot.logger import logger


def get_price_cryptocurrency(name_cryptocurrency: str = "") -> object:
    try:
        session = HTTP(
            api_key=os.getenv("CRYPTO_BYBIT_API_KEY"),
            api_secret=os.getenv("CRYPTO_BYBIT_API_SECRET")
        )
        r = session.get_orderbook(category="spot", symbol=name_cryptocurrency)
        price = float(r['result']['a'][0][0])
        logger.info(f"Успешное получение цены {name_cryptocurrency}: {price}")
        return price

    except KeyError:
        logger.warning(f"⚠️ Некорректный формат ответа от API для {name_cryptocurrency}")
        return None

    except ConnectionError:
        logger.error(f"🚨 Проблема с соединением при запросе {name_cryptocurrency}")
        return None

    except Exception:
        logger.exception(f"❌ Ошибка при получении цены {name_cryptocurrency}")
        return None