from aiogram.types import CallbackQuery
from requests import session
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import (
    orm_add_currency,
    orm_delete_currency,
    orm_get_currency,
    orm_update_currency,
    check_existing_currency)

from tg_bot.handlers.common_imports import *
from parsers.parser_currency_rate import get_exchange_rate
from tg_bot.keyboards.inline import get_callback_btns
from tg_bot.keyboards.reply import get_keyboard

currency_router = Router()

CURRENCY_CANCEL_FSM = get_keyboard(
    "Отменить действие с валютой",
    placeholder="Используйте кнопки ниже для отмены",
)

CURRENCY_CANCEL_AND_BACK_FSM = get_keyboard(
"Отменить действие с валютой",
    "Назад к предыдущему шагу для валюты",
    placeholder="Используйте кнопки ниже для действий",
)


# @currency_router.callback_query(lambda callback_query: callback_query.data.startswith("currencies_"))
# async def process_currency_action(callback_query: CallbackQuery, session: AsyncSession):
#     bank_id = int(callback_query.data.split("_")[-1])
#
#     currencies = await orm_get_currency(session, bank_id)
#     # if not currencies:
#     #     await callback_query.message.edit_text(
#     #         "В этом банке пока нет валют. Добавьте валюту:",
#     #         reply_markup=get_callback_btns(btns={"Добавить валюту": f"add_currency:{bank_id}"})
#     #     )
#     # else:
#     buttons = {currency.name: str(currency.id) for currency in currencies}
#     buttons["Добавить валюту"] = f"add_currency_{bank_id}"
#
#     await callback_query.message.edit_text(
#         "Выберете валюту:",
#         reply_markup=get_callback_btns(btns=buttons)
#     )
#
#     await callback_query.answer()


class AddCurrency(StatesGroup):
    currency_id = State()
    bank_id = State()
    name = State()
    balance = State()
    market_price = State()

    currency_for_change = None
    texts = {
        'AddCurrency:name': 'Введите название заново',
        'AddCurrency:balance': 'Введите баланс заново',
        'AddCurrency:market_price': 'Это последний стейт...'
    }


# @currency_router.callback_query(F.data.startswith('delete_'))
# async def delete_currency(callback: types.CallbackQuery, session: AsyncSession):
#     currency_id = callback.data.split("_")[-1]
#     await orm_delete_currency(session, int(currency_id))
#
#     await callback.answer("Валюта удалена")
#     await callback.message.answer("Валюта удалена")


@currency_router.callback_query(StateFilter(None), F.data.startswith("change_currency"))
async def change_currency(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    currency_id = int(callback.data.split(":")[-1])
    await state.update_data(currency_id=currency_id)
    currency_for_change = await orm_get_currency(session, currency_id)

    AddCurrency.currency_for_change = currency_for_change

    await callback.answer()
    await callback.message.answer("Введите название валюты, например USD", reply_markup=CURRENCY_CANCEL_AND_BACK_FSM)
    await state.set_state(AddCurrency.name)


@currency_router.callback_query(StateFilter(None), F.data.startswith("add_currency"))
async def add_currency(callback_query: CallbackQuery, state: FSMContext):
    bank_id = int(callback_query.data.split(':')[-1])
    await state.update_data(bank_id=bank_id)
    await (callback_query.message.answer("Введите название валюты, например USD", reply_markup=CURRENCY_CANCEL_FSM))
    await state.set_state(AddCurrency.name)


@currency_router.message(StateFilter('*'), Command("Отменить действие с валютой"))
@currency_router.message(StateFilter('*'), F.text.casefold() == "отменить действие с валютой")
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return
    if AddCurrency.currency_for_change:
        AddCurrency.currency_for_change = None
    await state.clear()
    await message.answer("Действия отменены", reply_markup=types.ReplyKeyboardRemove())


@currency_router.message(StateFilter('*'), Command("Назад к предыдущему шагу для валюты"))
@currency_router.message(StateFilter('*'), F.text.casefold() == "назад к предыдущему шагу для валюты")
async def back_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()

    if current_state == AddCurrency.name:
        await message.answer("Предыдущего шага нет, введите название валюты или нажмите ниже на кнопку отмены")
        return

    previous = None
    for step in AddCurrency.__all_states__:

        if step.state == current_state:
            await state.set_state(previous)
            await message.answer(f"Вы вернулись к прошлому шагу \n {AddCurrency.texts[previous.state]}")
            return
        previous = step


@currency_router.message(AddCurrency.name, F.text)
async def add_name(message: types.Message, state: FSMContext, session: AsyncSession):
    if message.text == '.' and AddCurrency.currency_for_change:
        await state.update_data(name=AddCurrency.currency_for_change.name)
    else:
        if len(message.text) >= 150:
            await message.answer(
                "Название валюты не должно превышать 150 символов. \n Введите заново"
            )
            return

        try:
            name = message.text

            if AddCurrency.currency_for_change and AddCurrency.currency_for_change.name == name:
                await state.update_data(name=name)
            else:
                check_name = await check_existing_currency(session, name)
                if check_name:
                    raise ValueError(f"Валюта с именем '{name}' уже существует")

                await state.update_data(name=name)

        except ValueError as e:
            await message.answer(f"Ошибка: {e}. Пожалуйста, введите другое название:")
            return

    data = await state.get_data()
    currency_name = data['name']
    await message.answer(f"Введите количество валюты {currency_name} на балансе")
    await state.set_state(AddCurrency.balance)


@currency_router.message(AddCurrency.balance, F.text)
async def add_balance(message: types.Message, state: FSMContext):
    if message.text == '.' and AddCurrency.currency_for_change:
        await state.update_data(balance=AddCurrency.currency_for_change.balance)
    else:
        await state.update_data(balance=message.text)
    await message.answer(
        "Введите курс данной валюты или определите его автоматичекси, написав слово 'авто' в поле ввода")
    await state.set_state(AddCurrency.market_price)


@currency_router.message(AddCurrency.market_price, F.text)
async def add_market_price(message: types.Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    currency_name = data['name']

    if message.text == '.' and AddCurrency.currency_for_change:
        await state.update_data(market_price=AddCurrency.currency_for_change.market_price)
    else:
        market_price = message.text
        if market_price.casefold() == 'авто':
            try:
                auto_market_price = get_exchange_rate(currency_name, 'RUB')
                await state.update_data(market_price=auto_market_price)
                await message.answer(f"Курс {currency_name} к RUB автоматически установлен: {auto_market_price}")
            except Exception as e:
                await message.answer(f"Не удалось получить курс валюты: {e}")
                return
        else:
            try:
                market_price = float(market_price)
                await state.update_data(market_price=market_price)
            except ValueError:
                await message.answer("Введите корректное числовое значение для курса валюты.")
                return

    data = await state.get_data()
    try:
        if AddCurrency.currency_for_change:
            await orm_update_currency(session, data["currency_id"], data)
        else:
            await orm_add_currency(session, data)
        await message.answer("Валюта добалена/изменена", reply_markup=types.ReplyKeyboardRemove())
        await state.clear()

    except Exception as e:
        await message.answer(f"Ошибка {e}, обратитесь к @gigcomm, чтобы исправить ее!")
        await state.clear()

    AddCurrency.currency_for_change = None
