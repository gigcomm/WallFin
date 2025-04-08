import os
import asyncio

from tinkoff.invest import AsyncClient, InstrumentType, InstrumentIdType

from tg_bot.logger import logger

INVEST_TOKEN = os.getenv("INVEST_TINKOFF_TOKEN")


async def get_instrument_currency(figi: str) -> str | None:
    async with AsyncClient(INVEST_TOKEN) as client:
        try:
            instrument_info = await client.instruments.get_instrument_by(
                id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI,
                id=figi
            )
            return instrument_info.instrument.currency
        except Exception as e:
            logger.exception(f"Ошибка при запросе валюты инструмента: {e}")
            return None


async def get_price_share(name_share: str = ""):
    async with (AsyncClient(INVEST_TOKEN) as client):
        response = await client.instruments.shares()

        instrument = next((instr for instr in response.instruments if instr.ticker == name_share), None)

        if not instrument:
            logger.error(f"Инструмент с тикером {name_share} не найден.")
            print(f"Инструмент с тикером {name_share} не найден.")
            return None

        currency = await get_instrument_currency(figi=instrument.figi) #ответ в низком регистре
        currency = currency.upper()
        if not currency:
            logger.error(f"Не удалось определить валюту для инструмента {instrument.figi}.")
            print(f"Не удалось определить валюту для инструмента {instrument.figi}.")
            return None

        if instrument is not None:
            # print(f"Название акции: {instrument.ticker}, figi:{instrument.figi}, {instrument.name}")
            price_response = await client.market_data.get_last_prices(figi=[instrument.figi])
            if price_response.last_prices:
                price_info = price_response.last_prices[0].price
                if price_info.units != 0 or price_info.nano != 0:
                    last_price = price_info.units + price_info.nano / 1e9
                    # print(f"Текущая цена: {last_price} RUB")
                    return last_price, currency
                else:
                    logger.error("Не удалось получить цену акции, данные недоступны.")
                    print("Не удалось получить цену акции, данные недоступны.")
            else:
                logger.error("Цена акции не найдена.")
                print("Цена акции не найдена.")
        else:
            logger.error(f"Инструмент (акция) с тикером: {name_share} не найден.")
            print(f"Инструмент (акция) с тикером: {name_share} не найден.")


# указать тикер акции
# asyncio.run(get_price_share(name_share="VTBR"))


async def get_price_fund(name_fund: str = ""):
    async with (AsyncClient(INVEST_TOKEN) as client):
        response = await client.instruments.find_instrument(
            query=name_fund,
            instrument_kind=InstrumentType.INSTRUMENT_TYPE_ETF
        )
        instrument = next(
            (instr for instr in response.instruments
             if instr.ticker == name_fund),
            None
        )

        currency = await get_instrument_currency(figi=instrument.figi)
        if not currency:
            logger.error(f"Не удалось определить валюту для инструмента {instrument.figi}.")
            print(f"Не удалось определить валюту для инструмента {instrument.figi}.")
            return None

        if instrument is not None:
            # print(f"Название фонда: {instrument.name}, figi:{instrument.figi}")
            price_response = await client.market_data.get_last_prices(figi=[instrument.figi])
            if price_response.last_prices:
                price_info = price_response.last_prices[0].price
                if price_info.units != 0 or price_info.nano != 0:
                    last_price = price_info.units + price_info.nano / 1e9
                    # print(f"Текущая цена: {last_price} RUB")
                    return last_price, currency
                else:
                    logger.error("Не удалось получить цену фонда, данные недоступны.")
                    print("Не удалось получить цену фонда, данные недоступны.")
            else:
                logger.error("Цена фонда не найдена.")
                print("Цена фонда не найдена.")
        else:
            logger.error(f"Инструмент (фонд) с тикером: {name_fund} не найден.")
            print(f"Инструмент (фонд) с тикером: {name_fund} не найден.")