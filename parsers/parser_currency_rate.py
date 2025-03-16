import json
import os

import requests
from bs4 import BeautifulSoup

from tg_bot.logger import logger


def get_exchange_rate(from_currency, to_currency):
    headers = json.loads(os.getenv('HEADERS'))
    url = f"https://www.x-rates.com/calculator/?from={from_currency}&to={to_currency}&amount=1"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        logger.info(f"Успешный запрос курса валюты: {from_currency} -> {to_currency}")

        soup = BeautifulSoup(response.text, "lxml")
        rate = soup.find("span", class_="ccOutputRslt")

        if rate is None:
            raise ValueError("Не удалось найти курс.")

        exchange_rate = float(rate.text.split(' ')[0])
        logger.info(f"Курс {from_currency} к {to_currency}: {exchange_rate}")
        return exchange_rate

    except requests.RequestException as e:
        logger.error(f"Ошибка при выполнении запроса к {url}: {e}")
        raise
    except (ValueError, AttributeError) as e:
        logger.error(f"Ошибка при парсинге курса валюты с {url}: {e}")
        raise