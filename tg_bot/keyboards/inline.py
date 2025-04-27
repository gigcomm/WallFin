from typing import Optional

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


class MenuCallBack(CallbackData, prefix="menu"):
    level: int
    menu_name: str | None = None
    user_tg_id: int | None = None
    bank_id: int | None = None
    cryptomarket_id: int | None = None
    stockmarket_id: int | None = None
    page: int = 1
    action: Optional[str] = None


def get_user_main_btns(*, level: int, user_tg_id: int, sizes: tuple[int] = (1,)):
    keyboard = InlineKeyboardBuilder()
    btns = {
        "Активы💼": "assets",
        "Общая стоимость активов💰": "total_balance",
        "О насℹ": "about",
        "Помощь🆘": "help"
    }
    for text, menu_name in btns.items():
        if menu_name == 'assets':
            keyboard.add(InlineKeyboardButton(
                text=text,
                callback_data=MenuCallBack(level=level + 1, menu_name=menu_name,
                                           user_tg_id=user_tg_id).pack()
            ))
        elif menu_name == 'total_balance':
            keyboard.add(InlineKeyboardButton(
                text=text,
                callback_data=MenuCallBack(level=level, menu_name=menu_name, user_tg_id=user_tg_id).pack()
            ))
        else:
            keyboard.add(InlineKeyboardButton(
                text=text,
                callback_data=MenuCallBack(level=level, menu_name=menu_name).pack()
            ))
    return keyboard.adjust(*sizes).as_markup()


def get_user_assets_btns(*, level: int, categories: list, user_tg_id: int, sizes: tuple[int] = (2, 1)):
    keyboard = InlineKeyboardBuilder()

    for c in categories:
        keyboard.add(InlineKeyboardButton(
            text=c,
            callback_data=MenuCallBack(level=level + 1, menu_name=c,
                                       user_tg_id=user_tg_id).pack()
        ))
    keyboard.add(InlineKeyboardButton(
        text='🔙Назад',
        callback_data=MenuCallBack(level=level - 1, menu_name='main').pack()
    ))
    return keyboard.adjust(*sizes).as_markup()


def get_user_banks_btns(*, level: int, banks: list, user_tg_id: int, sizes: tuple[int] = (2, 1)):
    keyboard = InlineKeyboardBuilder()

    for bank in banks:
        keyboard.add(InlineKeyboardButton(
            text=bank.name,
            callback_data=MenuCallBack(level=level + 1, menu_name=bank.name, user_tg_id=user_tg_id,
                                       bank_id=bank.id).pack()
        ))

    keyboard.add(InlineKeyboardButton(
        text='➕Добавить банк',
        callback_data='add_bank'
    ))

    keyboard.add(InlineKeyboardButton(
        text='🔙Назад',
        callback_data=MenuCallBack(level=level - 1, menu_name='assets').pack()
    ))

    return keyboard.adjust(*sizes).as_markup()


def get_user_stockmarkets_btns(*, level: int, stockmarkets: list, user_tg_id: int, sizes: tuple[int] = (2, )):
    keyboard = InlineKeyboardBuilder()

    for stockmarket in stockmarkets:
        keyboard.add(InlineKeyboardButton(
            text=stockmarket.name,
            callback_data=MenuCallBack(level=level + 1, menu_name=stockmarket.name, user_tg_id=user_tg_id,
                                       stockmarket_id=stockmarket.id).pack()
        ))

    keyboard.add(InlineKeyboardButton(
        text='➕Добавить финбиржу',
        callback_data='add_stockmarket'
    ))

    keyboard.add(InlineKeyboardButton(
        text='🔙Назад',
        callback_data=MenuCallBack(level=level - 1, menu_name='assets').pack()
    ))

    return keyboard.adjust(*sizes).as_markup()


def get_user_cryptomarkets_btns(*, level: int, cryptomarkets: list, user_tg_id: int, sizes: tuple[int] = (2, )):
    keyboard = InlineKeyboardBuilder()

    for cryptomarket in cryptomarkets:
        keyboard.add(InlineKeyboardButton(
            text=cryptomarket.name,
            callback_data=MenuCallBack(level=level + 1, menu_name=cryptomarket.name, user_tg_id=user_tg_id,
                                       cryptomarket_id=cryptomarket.id).pack()
        ))

    keyboard.add(InlineKeyboardButton(
        text='➕Добавить криптобиржу',
        callback_data='add_cryptomarket'
    ))

    keyboard.add(InlineKeyboardButton(
        text='🔙Назад',
        callback_data=MenuCallBack(level=level - 1, menu_name='assets').pack()
    ))

    return keyboard.adjust(*sizes).as_markup()


def get_user_assets_bank_btns(*, level: int, assets_bank: list, bank_id: int, sizes: tuple[int] = (3, 1, 1, 2)):
    keyboard = InlineKeyboardBuilder()

    for asset_bank in assets_bank:
        keyboard.add(InlineKeyboardButton(
            text=asset_bank,
            callback_data=MenuCallBack(level=level + 1, menu_name=asset_bank, bank_id=bank_id).pack()))
    if assets_bank:
        keyboard.add(InlineKeyboardButton(
            text='🔄Изменить банк',
            callback_data=f'change_bank:{bank_id}'
        ))

        keyboard.add(InlineKeyboardButton(
            text='❌Удалить банк',
            callback_data=MenuCallBack(level=level, menu_name="delete_bank", bank_id=bank_id).pack()
        ))

    keyboard.add(InlineKeyboardButton(
        text='🔙Назад',
        callback_data=MenuCallBack(level=level - 1, menu_name='Банки').pack()
    ))

    keyboard.add(InlineKeyboardButton(
        text='🔙Назад в главное меню',
        callback_data=MenuCallBack(level=level - 3, menu_name='main').pack()
    ))

    return keyboard.adjust(*sizes).as_markup()


def get_confirm_delete_bank(*, level: int, bank_name: str, bank_id: int, sizes: tuple[int] = (2,)):
    keyboard = InlineKeyboardBuilder()

    keyboard.add(InlineKeyboardButton(
        text='❌ДА, УДАЛИТЬ',
        callback_data=MenuCallBack(level=level - 1, menu_name='Банки', bank_id=bank_id, action="confirm_delete").pack()
    ))

    keyboard.add(InlineKeyboardButton(
        text='🔙Отмена',
        callback_data=MenuCallBack(level=level, menu_name=bank_name, bank_id=bank_id).pack()
    ))

    return keyboard.adjust(*sizes).as_markup()


def get_user_assets_stockmarkets_btns(*, level: int, assets_stockmarkets: list, stockmarket_id: int,
                                      sizes: tuple[int] = (2, 1, 1, 2)):
    keyboard = InlineKeyboardBuilder()

    for asset_stockmarket in assets_stockmarkets:
        keyboard.add(InlineKeyboardButton(
            text=asset_stockmarket,
            callback_data=MenuCallBack(level=level + 1, menu_name=asset_stockmarket,
                                       stockmarket_id=stockmarket_id).pack()
        ))
    if assets_stockmarkets:
        keyboard.add(InlineKeyboardButton(
            text='🔄Изменить финбиржу',
            callback_data=f'change_stockmarket:{stockmarket_id}'
        ))

        keyboard.add(InlineKeyboardButton(
            text='❌Удалить финбиржу',
            callback_data=MenuCallBack(level=level, menu_name='delete_stockmarket', stockmarket_id=stockmarket_id).pack()
        ))

    keyboard.add(InlineKeyboardButton(
        text='🔙Назад',
        callback_data=MenuCallBack(level=level - 1, menu_name='Финбиржи').pack()
    ))

    keyboard.add(InlineKeyboardButton(
        text='🔙Назад в главное меню',
        callback_data=MenuCallBack(level=level - 3, menu_name='main').pack()
    ))

    return keyboard.adjust(*sizes).as_markup()


def get_confirm_delete_stockmarket(*, level: int, stockmarket_name: str, stockmarket_id: int, sizes: tuple[int] = (2,)):
    keyboard = InlineKeyboardBuilder()

    keyboard.add(InlineKeyboardButton(
        text='❌ДА, УДАЛИТЬ',
        callback_data=MenuCallBack(level=level - 1, menu_name='Финбиржи', stockmarket_id=stockmarket_id,
                                   action="confirm_delete").pack()
    ))

    keyboard.add(InlineKeyboardButton(
        text="🔙Отмена",
        callback_data=MenuCallBack(level=level, menu_name=stockmarket_name, stockmarket_id=stockmarket_id).pack()
    ))

    return keyboard.adjust(*sizes).as_markup()


def get_user_assets_cryptomarkets_btns(*, level: int, assets_cryptomarkets: list, cryptomarket_id: int,
                                       sizes: tuple[int] = (1, 1, 1, 2)):
    keyboard = InlineKeyboardBuilder()

    for asset_cryptomarket in assets_cryptomarkets:
        keyboard.add(InlineKeyboardButton(
            text=asset_cryptomarket,
            callback_data=MenuCallBack(level=level + 1, menu_name=asset_cryptomarket,
                                       cryptomarket_id=cryptomarket_id).pack()

        ))
    if assets_cryptomarkets:
        keyboard.add(InlineKeyboardButton(
            text='🔄Изменить криптобиржу',
            callback_data=f'change_cryptomarket:{cryptomarket_id}'
        ))

        keyboard.add(InlineKeyboardButton(
            text='❌Удалить криптобиржу',
            callback_data=MenuCallBack(level=level, menu_name="delete_cryptomarket", cryptomarket_id=cryptomarket_id).pack()
        ))

    keyboard.add(InlineKeyboardButton(
        text='🔙Назад',
        callback_data=MenuCallBack(level=level - 1, menu_name='Криптобиржи').pack()
    ))

    keyboard.add(InlineKeyboardButton(
        text='🔙Назад в главное меню',
        callback_data=MenuCallBack(level=level - 3, menu_name='main').pack()
    ))

    return keyboard.adjust(*sizes).as_markup()


def get_confirm_delete_cryptomarket(*, level: int, cryptomarket_name: str, cryptomarket_id: int, sizes: tuple[int] = (2,)):
    keyboard = InlineKeyboardBuilder()

    keyboard.add(InlineKeyboardButton(
        text='❌ДА, УДАЛИТЬ',
        callback_data=MenuCallBack(level=level - 1, menu_name='Криптобиржи', cryptomarket_id=cryptomarket_id,
                                   action="confirm_delete").pack()
    ))

    keyboard.add(InlineKeyboardButton(
        text='🔙Отмена',
        callback_data=MenuCallBack(level=level, menu_name=cryptomarket_name, cryptomarket_id=cryptomarket_id).pack()
    ))

    return keyboard.adjust(*sizes).as_markup()


def get_account_btns(
        *,
        level: int,
        page: int | None,
        pagination_btns: dict | None,
        bank_id: int | None,
        bank_name: str | None,
        account_id: int | None,
        sizes: tuple[int] = (2, 1, 2, 1)
):
    keyboard = InlineKeyboardBuilder()

    row = []
    for text, menu_name in pagination_btns.items():
        if menu_name == 'next':
            row.append(InlineKeyboardButton(text=text,
                                            callback_data=MenuCallBack(
                                                level=level,
                                                menu_name='Счета',
                                                bank_id=bank_id,
                                                page=page + 1).pack()))

        elif menu_name == 'previous':
            row.append(InlineKeyboardButton(text=text,
                                            callback_data=MenuCallBack(
                                                level=level,
                                                menu_name='Счета',
                                                bank_id=bank_id,
                                                page=page - 1).pack()))

    if row:
        keyboard.row(*row)

    keyboard.add(InlineKeyboardButton(
        text='➕Добавить счет',
        callback_data=f'add_account:{bank_id}')
    )
    if account_id:
        keyboard.add(InlineKeyboardButton(
            text='🔄Изменить счет',
            callback_data=f"change_account:{account_id}"
        ))
        keyboard.add(InlineKeyboardButton(
            text='❌Удалить',
            callback_data=MenuCallBack(level=level, menu_name="delete_account", bank_id=bank_id, page=page).pack()
        ))

    keyboard.add(InlineKeyboardButton(
        text='🔙Назад',
        callback_data=MenuCallBack(level=level - 1, menu_name=bank_name, bank_id=bank_id).pack()
    ))

    keyboard.add(InlineKeyboardButton(
        text='🔙Назад в главное меню',
        callback_data=MenuCallBack(level=level-4, menu_name='main').pack()
    ))

    keyboard.adjust(*sizes)

    return keyboard.as_markup()


def get_currency_btns(
        *,
        level: int,
        page: int | None,
        pagination_btns: dict | None,
        bank_id: int | None,
        bank_name: str | None,
        currency_id: int | None,
        sizes: tuple[int] = (2, 1, 2, 1)
):
    keyboard = InlineKeyboardBuilder()

    row = []
    for text, menu_name in pagination_btns.items():
        if menu_name == 'next':
            row.append(InlineKeyboardButton(text=text,
                                            callback_data=MenuCallBack(
                                                level=level,
                                                menu_name='Валюты',
                                                bank_id=bank_id,
                                                page=page + 1).pack()))

        elif menu_name == 'previous':
            row.append(InlineKeyboardButton(text=text,
                                            callback_data=MenuCallBack(
                                                level=level,
                                                menu_name='Валюты',
                                                bank_id=bank_id,
                                                page=page - 1).pack()))

    if row:
        keyboard.row(*row)

    keyboard.add(InlineKeyboardButton(
        text='➕Добавить валюту',
        callback_data=f'add_currency:{bank_id}')
    )
    if currency_id:
        keyboard.add(InlineKeyboardButton(
            text='🔄Изменить валюту',
            callback_data=f"change_currency:{currency_id}"
        ))
        keyboard.add(InlineKeyboardButton(
            text='❌Удалить',
            callback_data=MenuCallBack(level=level, menu_name='delete_currency', bank_id=bank_id, page=page).pack()
        ))

    keyboard.add(InlineKeyboardButton(
        text='🔙Назад',
        callback_data=MenuCallBack(level=level - 1, menu_name=bank_name, bank_id=bank_id).pack()
    ))

    keyboard.add(InlineKeyboardButton(
        text='🔙Назад в главное меню',
        callback_data=MenuCallBack(level=level - 4, menu_name='main').pack()
    ))

    keyboard.adjust(*sizes)

    return keyboard.as_markup()


def get_deposit_btns(
        *,
        level: int,
        pagination_btns: dict | None,
        bank_id: int | None,
        bank_name: str | None,
        deposit_id: int | None,
        page: int | None,
        sizes: tuple[int] = (2, 1, 2, 1)
):
    keyboard = InlineKeyboardBuilder()

    row = []
    for text, menu_name in pagination_btns.items():
        if menu_name == 'next':
            row.append(InlineKeyboardButton(text=text,
                                            callback_data=MenuCallBack(
                                                level=level,
                                                menu_name='Вклады',
                                                bank_id=bank_id,
                                                page=page + 1).pack()))

        elif menu_name == 'previous':
            row.append(InlineKeyboardButton(text=text,
                                            callback_data=MenuCallBack(
                                                level=level,
                                                menu_name='Вклады',
                                                bank_id=bank_id,
                                                page=page - 1).pack()))

    if row:
        keyboard.row(*row)

    keyboard.add(InlineKeyboardButton(
        text='➕Добавить вклад',
        callback_data=f'add_deposit:{bank_id}')
    )
    if deposit_id:
        keyboard.add(InlineKeyboardButton(
            text='🔄Изменить вклад',
            callback_data=f"change_deposit:{deposit_id}"
        ))
        keyboard.add(InlineKeyboardButton(
            text='❌Удалить',
            callback_data=MenuCallBack(level=level, menu_name='delete_deposit', bank_id=bank_id, page=page).pack()
        ))

    keyboard.add(InlineKeyboardButton(
        text="🔙Назад",
        callback_data=MenuCallBack(level=level - 1, menu_name=bank_name, bank_id=bank_id).pack()
    ))

    keyboard.add(InlineKeyboardButton(
        text='🔙Назад в главное меню',
        callback_data=MenuCallBack(level=level - 4, menu_name='main').pack()
    ))

    keyboard.adjust(*sizes)

    return keyboard.as_markup()


def get_cryptocurrencies_btns(
        *,
        level: int,
        pagination_btns: dict | None,
        cryptomarket_id: int | None,
        cryptomarket_name: str | None,
        cryptocurrency_id: int | None,
        page: int | None,
        sizes: tuple[int] = (2, 1, 2, 1)
):
    keyboard = InlineKeyboardBuilder()

    row = []
    for text, menu_name in pagination_btns.items():
        if menu_name == 'next':
            row.append(InlineKeyboardButton(text=text,
                                            callback_data=MenuCallBack(
                                                level=level,
                                                menu_name='Криптовалюты',
                                                cryptomarket_id=cryptomarket_id,
                                                page=page + 1).pack()))

        elif menu_name == 'previous':
            row.append(InlineKeyboardButton(text=text,
                                            callback_data=MenuCallBack(
                                                level=level,
                                                menu_name='Криптовалюты',
                                                cryptomarket_id=cryptomarket_id,
                                                page=page - 1).pack()))

    if row:
        keyboard.row(*row)

    keyboard.add(InlineKeyboardButton(
        text='➕Добавить криптовалюту',
        callback_data=f'add_cryptocurrency:{cryptomarket_id}')
    )
    if cryptocurrency_id:
        keyboard.add(InlineKeyboardButton(
            text='🔄Изменить криптовалюту',
            callback_data=f"change_cryptocurrency:{cryptocurrency_id}"
        ))
        keyboard.add(InlineKeyboardButton(
            text='❌Удалить',
            callback_data=MenuCallBack(level=level, menu_name='delete_cryptocurrency', cryptomarket_id=cryptomarket_id,
                                       page=page).pack()
        ))

    keyboard.add(InlineKeyboardButton(
        text='🔙Назад',
        callback_data=MenuCallBack(level=level - 1, menu_name=cryptomarket_name, cryptomarket_id=cryptomarket_id).pack()
    ))

    keyboard.add(InlineKeyboardButton(
        text='🔙Назад в главное меню',
        callback_data=MenuCallBack(level=level - 4, menu_name='main').pack()
    ))

    keyboard.adjust(*sizes)

    return keyboard.as_markup()


def get_funds_btns(
        *,
        level: int,
        pagination_btns: dict | None,
        stockmarket_id: int | None,
        stockmarket_name: str | None,
        fund_id: int | None,
        page: int | None,
        sizes: tuple[int] = (2, 1, 2, 1)
):
    keyboard = InlineKeyboardBuilder()

    row = []
    for text, menu_name in pagination_btns.items():
        if menu_name == 'next':
            row.append(InlineKeyboardButton(text=text,
                                            callback_data=MenuCallBack(
                                                level=level,
                                                menu_name='Фонды',
                                                stockmarket_id=stockmarket_id,
                                                page=page + 1).pack()))

        elif menu_name == 'previous':
            row.append(InlineKeyboardButton(text=text,
                                            callback_data=MenuCallBack(
                                                level=level,
                                                menu_name='Фонды',
                                                stockmarket_id=stockmarket_id,
                                                page=page - 1).pack()))

    if row:
        keyboard.row(*row)

    keyboard.add(InlineKeyboardButton(
        text='➕Добавить фонд',
        callback_data=f'add_fund:{stockmarket_id}')
    )
    if fund_id:
        keyboard.add(InlineKeyboardButton(
            text='🔄Изменить фонд',
            callback_data=f"change_fund:{fund_id}"
        ))
        keyboard.add(InlineKeyboardButton(
            text='❌Удалить',
            callback_data=MenuCallBack(level=level, menu_name='delete_fund', stockmarket_id=stockmarket_id,
                                       page=page).pack()
        ))

    keyboard.add(InlineKeyboardButton(
        text='🔙Назад',
        callback_data=MenuCallBack(level=level - 1, menu_name=stockmarket_name, stockmarket_id=stockmarket_id).pack()
    ))

    keyboard.add(InlineKeyboardButton(
        text='🔙Назад в главное меню',
        callback_data=MenuCallBack(level=level - 4, menu_name='main').pack()
    ))

    keyboard.adjust(*sizes)

    return keyboard.as_markup()


def get_shares_btns(
        *,
        level: int,
        pagination_btns: dict | None,
        stockmarket_id: int | None,
        stockmarket_name: str | None,
        share_id: int | None,
        page: int | None,
        sizes: tuple[int] = (2, 1, 2, 1)
):
    keyboard = InlineKeyboardBuilder()

    row = []
    for text, menu_name in pagination_btns.items():
        if menu_name == 'next':
            row.append(InlineKeyboardButton(text=text,
                                            callback_data=MenuCallBack(
                                                level=level,
                                                menu_name='Акции',
                                                stockmarket_id=stockmarket_id,
                                                page=page + 1).pack()))

        elif menu_name == 'previous':
            row.append(InlineKeyboardButton(text=text,
                                            callback_data=MenuCallBack(
                                                level=level,
                                                menu_name='Акции',
                                                stockmarket_id=stockmarket_id,
                                                page=page - 1).pack()))

    if row:
        keyboard.row(*row)

    keyboard.add(InlineKeyboardButton(
        text='➕Добавить акцию',
        callback_data=f'add_share:{stockmarket_id}')
    )
    if share_id:
        keyboard.add(InlineKeyboardButton(
            text='🔄Изменить акцию',
            callback_data=f'change_share:{share_id}'
        ))
        keyboard.add(InlineKeyboardButton(
            text='❌Удалить',
            callback_data=MenuCallBack(level=level, menu_name='delete_share', stockmarket_id=stockmarket_id,
                                       page=page).pack()
        ))

    keyboard.add(InlineKeyboardButton(
        text='🔙Назад',
        callback_data=MenuCallBack(level=level - 1, menu_name=stockmarket_name, stockmarket_id=stockmarket_id).pack()
    ))

    keyboard.add(InlineKeyboardButton(
        text='🔙Назад в главное меню',
        callback_data=MenuCallBack(level=level - 4, menu_name='main').pack()
    ))

    keyboard.adjust(*sizes)

    return keyboard.as_markup()


def get_callback_btns(
        *,
        btns: dict[str, str],
        sizes: tuple[int] = (2,)
):
    keyboard = InlineKeyboardBuilder()
    for text, data in btns.items():
        keyboard.add(InlineKeyboardButton(text=text, callback_data=data))

    return keyboard.adjust(*sizes).as_markup()
