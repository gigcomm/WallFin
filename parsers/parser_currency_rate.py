import json
import os

import requests
from bs4 import BeautifulSoup


def get_exchange_rate(from_currency, to_currency):
    headers = json.loads(os.getenv('HEADERS'))
    url = f"https://www.x-rates.com/calculator/?from={from_currency}&to={to_currency}&amount=1"

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "lxml")
    rate = soup.find("span", class_="ccOutputRslt")
    return float(rate.text.split(' ')[0])