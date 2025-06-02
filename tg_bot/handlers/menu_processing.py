from datetime import datetime
from decimal import Decimal
from typing import Optional

from aiogram.types import InputMediaPhoto
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import (
    orm_get_banner,
    orm_get_user,
    orm_get_bank,
    orm_get_stock_market,
    orm_get_cryptomarket,
    orm_get_bank_by_id,
    orm_get_cryptomarket_by_id,
    orm_delete_deposit,
    orm_get_deposit_by_bank_id,
    orm_get_account_by_bank_id,
    orm_delete_account,
    orm_get_currency_by_bank_id,
    orm_get_cryptocurrency_by_cryptomarket_id,
    orm_delete_cryptocurrency,
    orm_get_fund_by_stockmarket_id,
    orm_delete_fund,
    orm_get_share_by_stockmarket_id,
    orm_delete_share,
    orm_get_stock_market_by_id,
    orm_delete_currency)

from dateutil.relativedelta import relativedelta

from finance.bank import DepositLogic
from tg_bot.keyboards.inline import (
    get_user_main_btns,
    get_user_assets_btns,
    get_user_banks_btns,
    get_user_stockmarkets_btns,
    get_user_cryptomarkets_btns,
    get_user_assets_bank_btns,
    get_user_assets_cryptomarkets_btns,
    get_user_assets_stockmarkets_btns,
    get_deposit_btns,
    get_account_btns,
    get_currency_btns,
    get_cryptocurrencies_btns,
    get_shares_btns,
    get_funds_btns,
    get_confirm_delete_bank,
    get_confirm_delete_stockmarket,
    get_confirm_delete_cryptomarket)

from utils.cache_utils import get_cache_price
from utils.paginator import Paginator


async def main_menu(session, level, menu_name, user_tg_id):
    banner = await orm_get_banner(session, menu_name)
    image = InputMediaPhoto(media=banner.image, caption=banner.description)

    kbds = get_user_main_btns(level=level, user_tg_id=user_tg_id)
    return image, kbds


async def assets(session, level, menu_name, user_tg_id):
    banner = await orm_get_banner(session, menu_name)
    image = InputMediaPhoto(media=banner.image, caption=banner.description)

    categories = ['Банки', 'Финбиржи', 'Криптобиржи']
    kbds = get_user_assets_btns(level=level, categories=categories, user_tg_id=user_tg_id)
    return image, kbds


async def banks(session, level, menu_name, user_tg_id):
    banner = await orm_get_banner(session, menu_name.strip())
    image = InputMediaPhoto(media=banner.image, caption=banner.description)
    user_id = await orm_get_user(session, user_tg_id)
    banks = await orm_get_bank(session, user_id)
    # for bank in banks:
    #     description_for_info[bank.name] = f"В банке {bank.name} содержаться активы:"
    kbds = get_user_banks_btns(level=level, banks=banks, user_tg_id=user_tg_id)
    return image, kbds


async def stockmarkets(session, level, menu_name, user_tg_id):
    banner = await orm_get_banner(session, menu_name)
    image = InputMediaPhoto(media=banner.image, caption=banner.description)
    user_id = await orm_get_user(session, user_tg_id)
    stockmarkets = await orm_get_stock_market(session, user_id)
    # for stockmarket in stockmarkets:
    #     description_for_info[stockmarket.name] = f"На финбирже {stockmarket.name} содержаться активы:"

    kbds = get_user_stockmarkets_btns(level=level, stockmarkets=stockmarkets, user_tg_id=user_tg_id)
    return image, kbds


async def cryptomarkets(session, level, menu_name, user_tg_id):
    banner = await orm_get_banner(session, menu_name)
    image = InputMediaPhoto(media=banner.image, caption=banner.description)
    user_id = await orm_get_user(session, user_tg_id)
    cryptomarkets = await orm_get_cryptomarket(session, user_id)
    # for cryptomarket in cryptomarkets:
    #     description_for_info[cryptomarket.name] = f"На криптобирже {cryptomarket.name} содержаться активы:"

    kbds = get_user_cryptomarkets_btns(level=level, cryptomarkets=cryptomarkets, user_tg_id=user_tg_id)
    return image, kbds


# определен общая сумма активов для банка, нужен процесс тестирования
async def choose_banks(session, level, bank_id):
    bank = await orm_get_bank_by_id(session, bank_id)
    bank_logic = bank.to_logic()

    total_balance_rubls = bank_logic.get_total_balance_bank_rubls()
    total_balance_dollars = await bank_logic.get_total_balance_bank_dollars()
    total_balance_accounts = bank_logic.get_total_balance_accounts_rubls()
    total_balance_currencies = bank_logic.get_total_balance_currencies_rubls()
    total_balance_deposits = bank_logic.get_total_balance_deposits_rubls()

    caption = (
        f"<b>🏦 Банк: {bank.name}</b>\n\n"
        f"<u>Балансы по счетам:</u>\n"
        f"• Все счета: {total_balance_accounts:,.2f} ₽\n"
        f"• Валютные счета: {total_balance_currencies:,.2f} $\n"
        f"• Депозиты: {total_balance_deposits:,.2f} ₽\n\n"
        f"<u>Итоговый баланс активов банка:</u>\n"
        f"<b>→ В рублях: {total_balance_rubls:,.2f} ₽</b>\n"
        f"<b>→ В долларах: {total_balance_dollars:,.2f} $</b>\n")

    assets_bank = ['Счета', 'Вклады', 'Валюты']

    kbds = get_user_assets_bank_btns(level=level, assets_bank=assets_bank, bank_id=bank_id)
    return caption, kbds


async def confirm_delete_bank(session, level, bank_id):
    bank = await orm_get_bank_by_id(session, bank_id)
    caption = (
        f"‼ Вы уверены, что хотите <b>удалить банк {bank.name}</b>?\n\n"
        f"Все связанные счета и данные будут безвозвратно удалены.")

    kbds = get_confirm_delete_bank(level=level, bank_name=bank.name, bank_id=bank_id)
    return caption, kbds


async def choose_cryptomarkets(session, level, cryptomarket_id):
    cryptomarket = await orm_get_cryptomarket_by_id(session, cryptomarket_id)
    cryptomarket_logic = cryptomarket.to_logic()
    total_balance_dollars = cryptomarket_logic.get_total_balance_cryptomarket_in_dollars()
    total_balance_rubls = await cryptomarket_logic.get_total_balance_cryptomarket_in_rubls()
    caption = (
        f"<b>💸🔒 Криптобиржа {cryptomarket.name}</b>\n\n"
        f"<u>Общий баланс активов:</u>\n"
        f"• <b>{total_balance_dollars:,.2f} $</b>\n"
        f"• <b>{total_balance_rubls:,.2f} ₽</b>\n"
    )

    assets_cryptomarkets = ['Криптовалюты']

    kbds = get_user_assets_cryptomarkets_btns(level=level, assets_cryptomarkets=assets_cryptomarkets,
                                              cryptomarket_id=cryptomarket.id)
    return caption, kbds


async def confirm_delete_stockmarket(session, level, stockmarket_id):
    stockmarket = await orm_get_stock_market_by_id(session, stockmarket_id)
    caption = (
        f"‼ Вы уверены, что хотите <b>удалить банк {stockmarket.name}</b>?\n\n"
        f"Все связанные счета и данные будут безвозвратно удалены.")
    kbds = get_confirm_delete_stockmarket(level=level, stockmarket_name=stockmarket.name, stockmarket_id=stockmarket_id)
    return caption, kbds


async def choose_stockmarkets(session, level, stockmarket_id):
    stockmarket = await orm_get_stock_market_by_id(session, stockmarket_id)
    stockmarket_logic = stockmarket.to_logic()
    total_balance_dollars = await stockmarket_logic.get_total_balance_stockmarket_in_dollars()
    total_balance_rubls = await stockmarket_logic.get_total_balance_stockmarket_in_rubls()
    caption = (
        f"<b>💸🔒 Фондовая биржа {stockmarket.name}</b>\n\n"
        f"<u>Общий баланс активов:</u>\n"
        f"• <b>{total_balance_dollars:,.2f} $</b>\n"
        f"• <b>{total_balance_rubls:,.2f} ₽</b>\n"
    )

    assets_stockmarkets = ['Акции', 'Фонды']

    kbds = get_user_assets_stockmarkets_btns(level=level, assets_stockmarkets=assets_stockmarkets,
                                             stockmarket_id=stockmarket.id)
    return caption, kbds


async def confirm_delete_cryptomarket(session, level, cryptomarket_id):
    cryptomarket = await orm_get_cryptomarket_by_id(session, cryptomarket_id)
    caption = (
        f"‼ Вы уверены, что хотите <b>удалить банк {cryptomarket.name}</b>?\n\n"
        f"Все связанные счета и данные будут безвозвратно удалены.")
    kbds = get_confirm_delete_cryptomarket(level=level, cryptomarket_name=cryptomarket.name, cryptomarket_id=cryptomarket_id)
    return caption, kbds


def pages(paginator: Paginator):
    btns = dict()
    if paginator.has_previous():
        btns['⬅Пред.'] = "previous"

    if paginator.has_next():
        btns['След.➡'] = "next"

    return btns


async def accounts(session, level, menu_name, bank_id, bank_name, page):
    accounts_list = await orm_get_account_by_bank_id(session, bank_id)

    if not accounts_list:
        caption = "Добавьте счет, что посмотреть"
        kbds = get_account_btns(
            level=level,
            page=1,
            pagination_btns={},
            bank_id=bank_id,
            bank_name=bank_name,
            account_id=None
        )
        return caption, kbds

    paginator = Paginator(accounts_list, page=page)

    if menu_name == "delete_account":
        account = paginator.get_page()[0]
        await orm_delete_account(session, account.id)

        accounts_list = await orm_get_account_by_bank_id(session, bank_id)
        paginator = Paginator(accounts_list, page=page)
        if page > 1 and not paginator.get_page():
            page -= 1
            paginator = Paginator(accounts_list, page=page)

    if not accounts_list:
        caption = "Добавьте вклад, чтобы просмотреть"
        kbds = get_account_btns(
            level=level,
            page=1,
            pagination_btns={},
            bank_id=bank_id,
            bank_name=bank_name,
            account_id=None
        )
        return caption, kbds

    account = paginator.get_page()[0]
    caption = (
        f"<b>💳 Счёт: {account.name}</b>\n\n"
        f"<b>Доступный баланс:</b>\n"
        f"{account.balance:,.2f} ₽"
    )

    pagination_btns = pages(paginator)

    kbds = get_account_btns(
        level=level,
        page=page,
        pagination_btns=pagination_btns,
        bank_id=bank_id,
        bank_name=bank_name,
        account_id=account.id
    )

    return caption, kbds


async def currencies(session, level, menu_name, bank_id, bank_name, page):
    currencies_list = await orm_get_currency_by_bank_id(session, bank_id)

    if not currencies_list:
        caption = "Добавьте валюту, чтобы просмотреть"
        kbds = get_currency_btns(
            level=level,
            page=1,
            pagination_btns={},
            bank_id=bank_id,
            bank_name=bank_name,
            currency_id=None
        )

        return caption, kbds

    paginator = Paginator(currencies_list, page=page)

    if menu_name == "delete_currency":
        currency = paginator.get_page()[0]
        await orm_delete_currency(session, currency.id)

        currencies_list = await orm_get_currency_by_bank_id(session, bank_id)
        paginator = Paginator(currencies_list, page=page)
        if page > 1 and not paginator.get_page():
            page -= 1
            paginator = Paginator(currencies_list, page=page)

    if not currencies_list:
        caption = "Добавьте валюту, чтобы просмотреть"
        kbds = get_currency_btns(
            level=level,
            page=1,
            pagination_btns={},
            bank_id=bank_id,
            bank_name=bank_name,
            currency_id=None
        )
        return caption, kbds

    currency = paginator.get_page()[0]
    market_price = await get_cache_price("currency", currency.name, session)

    caption = (
        f"<b>💰 Валюта: {currency.name}</b>\n\n"
        f"<b>Доступный баланс:</b>\n"
        f"{currency.balance:,.2f} {currency.name}\n"
        f"{float(market_price)} x {float(currency.balance)} = {(float(market_price) * float(currency.balance)):,.2f} ₽"
    )

    pagination_btns = pages(paginator)

    kbds = get_currency_btns(
        level=level,
        page=page,
        pagination_btns=pagination_btns,
        bank_id=bank_id,
        bank_name=bank_name,
        currency_id=currency.id
    )

    return caption, kbds


async def deposits(session, level, menu_name, bank_id, bank_name, page):
    deposits_list = await orm_get_deposit_by_bank_id(session, bank_id)

    if not deposits_list:
        caption = "Добавьте вклад, чтобы просмотреть"
        kbds = get_deposit_btns(
            level=level,
            page=1,
            pagination_btns={},
            bank_id=bank_id,
            bank_name=bank_name,
            deposit_id=None
        )
        return caption, kbds

    paginator = Paginator(deposits_list, page=page)

    if menu_name == "delete_deposit":
        deposit = paginator.get_page()[0]
        await orm_delete_deposit(session, deposit.id)

        deposits_list = await orm_get_deposit_by_bank_id(session, bank_id)
        paginator = Paginator(deposits_list, page=page)
        if page > 1 and not paginator.get_page():
            page -= 1
            paginator = Paginator(deposits_list, page=page)

    if not deposits_list:
        caption = "Добавьте вклад, чтобы просмотреть"
        kbds = get_deposit_btns(
            level=level,
            page=1,
            pagination_btns={},
            bank_id=bank_id,
            bank_name=bank_name,
            deposit_id=None
        )
        return caption, kbds

    deposit = paginator.get_page()[0]
    deposit_logic = DepositLogic(deposit.name, deposit.start_date, deposit.deposit_term, deposit.interest_rate, deposit.balance)
    final_amount = deposit_logic.calculating_final_amount(deposit_logic.deposit_balance, deposit_logic.deposit_term, deposit_logic.interest_rate)
    income = Decimal(str(final_amount)) - Decimal(str(deposit.balance))

    caption = (
        f"<b>🏦 {deposit.name}</b>\n\n"
        f"<u>📅 Срок вклада:</u>\n"
        f"• Начало: <code>{deposit.start_date}</code>\n"
        f"• Окончание: <code>{deposit.start_date + relativedelta(months=deposit.deposit_term)}</code>\n\n"
        f"<u>💰 Финансовые параметры:</u>\n"
        f"• Сумма вклада: <code>{deposit.balance:,.2f}</code> ₽\n"
        f"• Процентная ставка: <b>{deposit.interest_rate}%</b>\n\n"
        f"<b>🏁 Итоговая сумма:</b>\n"
        f"<code>{final_amount:,.2f}</code> ₽\n"
        f"+{income:,.2f} ₽ доход"
    )

    pagination_btns = pages(paginator)

    kbds = get_deposit_btns(
        level=level,
        page=page,
        pagination_btns=pagination_btns,
        bank_id=bank_id,
        bank_name=bank_name,
        deposit_id=deposit.id
    )

    return caption, kbds


async def cryptocurrencies(session, level, menu_name, cryptomarket_id, cryptomarket_name, page):
    cryptocurrencies_list = await orm_get_cryptocurrency_by_cryptomarket_id(session, cryptomarket_id)

    if not cryptocurrencies_list:
        caption = "Добавьте криптовалюту, чтобы просмотреть"
        kbds = get_cryptocurrencies_btns(
            level=level,
            page=1,
            pagination_btns={},
            cryptomarket_id=cryptomarket_id,
            cryptomarket_name=cryptomarket_name,
            cryptocurrency_id=None
        )
        return caption, kbds

    paginator = Paginator(cryptocurrencies_list, page=page)

    if menu_name == "delete_cryptocurrency":
        deposit = paginator.get_page()[0]
        await orm_delete_cryptocurrency(session, deposit.id)

        cryptocurrencies_list = await orm_get_cryptocurrency_by_cryptomarket_id(session, cryptomarket_id)
        paginator = Paginator(cryptocurrencies_list, page=page)
        if page > 1 and not paginator.get_page():
            page -= 1
            paginator = Paginator(cryptocurrencies_list, page=page)

    if not cryptocurrencies_list:
        caption = "Добавьте криптовалюту, чтобы просмотреть"
        kbds = get_cryptocurrencies_btns(
            level=level,
            page=1,
            pagination_btns={},
            cryptomarket_id=cryptomarket_id,
            cryptomarket_name=cryptomarket_name,
            cryptocurrency_id=None
        )
        return caption, kbds

    cryptocurrency = paginator.get_page()[0]
    market_price = await get_cache_price("crypto", cryptocurrency.name, session)
    current_value = float(market_price) * float(cryptocurrency.balance)
    initial_value = float(cryptocurrency.purchase_price) * float(cryptocurrency.balance)
    price_change = Decimal(str(market_price)) - Decimal(str(cryptocurrency.purchase_price))
    percentage_change = (price_change / Decimal(str(cryptocurrency.purchase_price))) * 100

    caption = (
        f"<b> {cryptocurrency.name}</b>\n\n"
        f"<u>💰 Цены:</u>\n"
        f"• Куплено по: <code>{cryptocurrency.purchase_price:,.4f} $</code>\n"
        f"• Текущая цена: <code>{market_price:,.4f} $</code>\n"
        f"• Изменение: <b>{price_change:+,.4f} USD</b> ({percentage_change:+.2f}%)\n\n"
        f"<u>🔢 Позиция:</u>\n"
        f"• Количество: <code>{Decimal(cryptocurrency.balance):,.8f}</code>\n"
        f"• Текущая стоимость: <code>{Decimal(current_value):,.2f} $</code>\n"
    )

    change = current_value - initial_value
    caption += f"<b>Доход: {'🟢+' if change >= 0 else '🔴-'}{abs(change):.2f} $</b>"

    pagination_btns = pages(paginator)

    kbds = get_cryptocurrencies_btns(
        level=level,
        page=page,
        pagination_btns=pagination_btns,
        cryptomarket_id=cryptomarket_id,
        cryptomarket_name=cryptomarket_name,
        cryptocurrency_id=cryptocurrency.id
    )

    return caption, kbds


async def funds(session, level, menu_name, stockmarket_id, stockmarket_name, page):
    funds_list = await orm_get_fund_by_stockmarket_id(session, stockmarket_id)

    if not funds_list:
        caption = "Добавьте фонд, чтобы просмотреть"
        kbds = get_funds_btns(
            level=level,
            page=1,
            pagination_btns={},
            stockmarket_id=stockmarket_id,
            stockmarket_name=stockmarket_name,
            fund_id=None
        )
        return caption, kbds

    paginator = Paginator(funds_list, page=page)

    if menu_name == "delete_fund":
        fund = paginator.get_page()[0]
        await orm_delete_fund(session, fund.id)

        funds_list = await orm_get_fund_by_stockmarket_id(session, stockmarket_id)
        paginator = Paginator(funds_list, page=page)
        if page > 1 and not paginator.get_page():
            page -= 1
            paginator = Paginator(funds_list, page=page)

    if not funds_list:
        caption = "Добавьте фонд, чтобы просмотреть"
        kbds = get_funds_btns(
            level=level,
            page=1,
            pagination_btns={},
            stockmarket_id=stockmarket_id,
            stockmarket_name=stockmarket_name,
            fund_id=None
        )
        return caption, kbds

    fund = paginator.get_page()[0]
    market_price = await get_cache_price("fund", fund.name, session)
    current_value = float(market_price) * float(fund.quantity)
    initial_value = float(fund.purchase_price) * float(fund.quantity)
    price_change = Decimal(str(market_price)) - Decimal(str(fund.purchase_price))
    percentage_change = (price_change / Decimal(str(fund.purchase_price))) * 100

    caption = (
        f"<b> {fund.name}</b>\n\n"
        f"<u>💰 Цены:</u>\n"
        f"• Куплено по: <code>{fund.purchase_price:,.4f} {fund.currency}</code>\n"
        f"• Текущая цена: <code>{market_price:,.4f} {fund.currency}</code>\n"
        f"• Изменение: <b>{price_change:+,.2f} {fund.currency}</b> ({percentage_change:+.2f}%)\n\n"
        f"<u>🔢 Позиция:</u>\n"
        f"• Количество: <code>{Decimal(fund.quantity):,.2f}</code>\n"
        f"• Текущая стоимость: <code>{Decimal(current_value):,.2f} {fund.currency}</code>\n"
    )

    change = current_value - initial_value
    caption += f"<b>Доход: {'🟢+' if change >= 0 else '🔴-'}{abs(change):.2f} {fund.currency}</b>"

    pagination_btns = pages(paginator)

    kbds = get_funds_btns(
        level=level,
        page=page,
        pagination_btns=pagination_btns,
        stockmarket_id=stockmarket_id,
        stockmarket_name=stockmarket_name,
        fund_id=fund.id
    )

    return caption, kbds


async def shares(session, level, menu_name, stockmarket_id, stockmarket_name, page):
    shares_list = await orm_get_share_by_stockmarket_id(session, stockmarket_id)

    if not shares_list:
        caption = "Добавьте акцию, чтобы просмотреть"
        kbds = get_shares_btns(
            level=level,
            page=1,
            pagination_btns={},
            stockmarket_id=stockmarket_id,
            stockmarket_name=stockmarket_name,
            share_id=None
        )
        return caption, kbds

    paginator = Paginator(shares_list, page=page)

    if menu_name == "delete_share":
        share = paginator.get_page()[0]
        await orm_delete_share(session, share.id)

        shares_list = await orm_get_share_by_stockmarket_id(session, stockmarket_id)
        paginator = Paginator(shares_list, page=page)
        if page > 1 and not paginator.get_page():
            page -= 1
            paginator = Paginator(shares_list, page=page)

    if not shares_list:
        caption = "Добавьте акцию, чтобы просмотреть"
        kbds = get_shares_btns(
            level=level,
            page=1,
            pagination_btns={},
            stockmarket_id=stockmarket_id,
            stockmarket_name=stockmarket_name,
            share_id=None
        )
        return caption, kbds

    share = paginator.get_page()[0]
    market_price = await get_cache_price("share", share.name, session)
    current_value = float(market_price) * float(share.quantity)
    initial_value = float(share.purchase_price) * float(share.quantity)
    price_change = Decimal(str(market_price)) - Decimal(str(share.purchase_price))
    percentage_change = (price_change / Decimal(str(share.purchase_price))) * 100

    caption = (
        f"<b> {share.name}</b>\n\n"
        f"<u>💰 Цены:</u>\n"
        f"• Куплено по: <code>{share.purchase_price:,.4f} {share.currency}</code>\n"
        f"• Текущая цена: <code>{market_price:,.4f} {share.currency}</code>\n"
        f"• Изменение: <b>{price_change:+,.2f} {share.currency}</b> ({percentage_change:+.2f}%)\n\n"
        f"<u>🔢 Позиция:</u>\n"
        f"• Количество: <code>{Decimal(share.quantity):,.2f}</code>\n"
        f"• Текущая стоимость: <code>{Decimal(current_value):,.2f} {share.currency}</code>\n"
    )

    change = current_value - initial_value
    caption += f"<b>Доход: {'🟢+' if change >= 0 else '🔴-'}{abs(change):.2f} {share.currency}</b>"


    pagination_btns = pages(paginator)

    kbds = get_shares_btns(
        level=level,
        page=page,
        pagination_btns=pagination_btns,
        stockmarket_id=stockmarket_id,
        stockmarket_name=stockmarket_name,
        share_id=share.id
    )

    return caption, kbds


async def get_menu_content(
        session: AsyncSession,
        level: int,
        menu_name: str,
        user_tg_id: int | None = None,
        bank_id: int | None = None,
        cryptomarket_id: int | None = None,
        stockmarket_id: int | None = None,
        page: int | None = None,
        action: Optional[str] | None = None
):
    if level == 0:
        return await main_menu(session, level, menu_name, user_tg_id)
    elif level == 1:
        return await assets(session, level, menu_name, user_tg_id)
    elif level == 2 and menu_name == 'Банки':
        return await banks(session, level, menu_name, user_tg_id)
    elif level == 2 and menu_name == 'Финбиржи':
        return await stockmarkets(session, level, menu_name, user_tg_id)
    elif level == 2 and menu_name == 'Криптобиржи':
        return await cryptomarkets(session, level, menu_name, user_tg_id)

    orm_user_id = await orm_get_user(session, user_tg_id)
    orm_banks = await orm_get_bank(session, orm_user_id)

    for bank in orm_banks:
        if level == 3 and menu_name == bank.name:
            return await choose_banks(session, level, menu_name, bank_id)

    if level == 3 and menu_name == "delete_bank":
        return await confirm_delete_bank(session, level, bank_id)

    if level == 3 and menu_name == "delete_stockmarket":
        return await confirm_delete_stockmarket(session, level, stockmarket_id)

    if level == 3 and menu_name == "delete_cryptomarket":
        return await confirm_delete_cryptomarket(session, level, cryptomarket_id)

    orm_user_id = await orm_get_user(session, user_tg_id)
    orm_cryptomarkets = await orm_get_cryptomarket(session, orm_user_id)

    for cryptomarket in orm_cryptomarkets:
        if level == 3 and menu_name == cryptomarket.name:
            return await choose_cryptomarkets(session, level, menu_name, cryptomarket.id)

    orm_user_id = await orm_get_user(session, user_tg_id)
    orm_stockmarkets = await orm_get_stock_market(session, orm_user_id)

    for stockmarket in orm_stockmarkets:
        if level == 3 and menu_name == stockmarket.name:
            return await choose_stockmarkets(session, level, menu_name, stockmarket_id)

    bank = await orm_get_bank_by_id(session, bank_id)

    if level == 4:
        if menu_name in ["Вклады", "delete_deposit", "change_deposit"]:
            return await deposits(session, level, menu_name, bank_id, bank.name, page)
        if menu_name in ["Счета", "delete_account", "change_account"]:
            return await accounts(session, level, menu_name, bank_id, bank.name, page)
        if menu_name in ["Валюты", "delete_currency", "change_currency"]:
            return await currencies(session, level, menu_name, bank_id, bank.name, page)

    cryptomarket = await orm_get_cryptomarket_by_id(session, cryptomarket_id)

    if level == 4:
        if menu_name in ["Криптовалюты", "delete_cryptocurrency", "change_cryptocurrency"]:
            return await cryptocurrencies(session, level, menu_name, cryptomarket_id, cryptomarket.name, page)

    stockmarket = await orm_get_stock_market_by_id(session, stockmarket_id)

    if level == 4:
        if menu_name in ["Фонды", "delete_fund", "change_fund"]:
            return await funds(session, level, menu_name, stockmarket_id, stockmarket.name, page)

        if menu_name in ["Акции", "delete_share", "change_share"]:
            return await shares(session, level, menu_name, stockmarket_id, stockmarket.name, page)
