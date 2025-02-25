from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import (
    orm_add_currency,
    orm_get_currency,
    orm_update_currency,
    check_existing_currency, orm_get_user)

from tg_bot.handlers.common_imports import *
from parsers.parser_currency_rate import get_exchange_rate
from tg_bot.keyboards.reply import get_keyboard
from utils.message_utils import delete_regular_messages, delete_bot_and_user_messages

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
async def change_currency(callback_query: CallbackQuery, state: FSMContext, session: AsyncSession):
    currency_id = int(callback_query.data.split(":")[-1])
    await state.update_data(currency_id=currency_id)
    currency_for_change = await orm_get_currency(session, currency_id)

    AddCurrency.currency_for_change = currency_for_change

    keyboard_message = await callback_query.message.answer(
        "В режиме изменения, если поставить точку, данное поле будет прежним,"
        "а процесс перейдет к следующему полю объекта.\nИзмените данные:",
        reply_markup=CURRENCY_CANCEL_AND_BACK_FSM)
    bot_message = await callback_query.message.answer("Введите название валюты, например USD")
    await state.update_data(keyboard_message_id=[keyboard_message.message_id], message_ids=[bot_message.message_id])

    await state.set_state(AddCurrency.name)


@currency_router.callback_query(StateFilter(None), F.data.startswith("add_currency"))
async def add_currency(callback_query: CallbackQuery, state: FSMContext):
    bank_id = int(callback_query.data.split(':')[-1])
    await state.update_data(bank_id=bank_id)

    keyboard_message = await callback_query.message.answer("Заполните данные:", reply_markup=CURRENCY_CANCEL_FSM)
    bot_message = await (callback_query.message.answer("Введите название валюты, например USD"))
    await state.update_data(keyboard_message_id=[keyboard_message.message_id], message_ids=[bot_message.message_id])

    await state.set_state(AddCurrency.name)


@currency_router.message(StateFilter('*'), Command("Отменить действие с валютой"))
@currency_router.message(StateFilter('*'), F.text.casefold() == "отменить действие с валютой")
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()

    await delete_regular_messages(data, message)

    current_state = await state.get_state()
    if current_state is None:
        return
    if AddCurrency.currency_for_change:
        AddCurrency.currency_for_change = None
    await state.clear()
    bot_message = await message.answer("Действия отменены", reply_markup=types.ReplyKeyboardRemove())
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await delete_bot_and_user_messages(data, message, bot_message)


@currency_router.message(StateFilter('*'), Command("Назад к предыдущему шагу для валюты"))
@currency_router.message(StateFilter('*'), F.text.casefold() == "назад к предыдущему шагу для валюты")
async def back_handler(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()

    await delete_regular_messages(data, message)

    current_state = await state.get_state()

    if current_state == AddCurrency.name:
        bot_message = await message.answer("Предыдущего шага нет, введите название валюты или нажмите ниже на кнопку отмены")
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
        return

    previous = None
    for step in AddCurrency.__all_states__:

        if step.state == current_state:
            await state.set_state(previous)
            bot_message = await message.answer(f"Вы вернулись к прошлому шагу \n {AddCurrency.texts[previous.state]}")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return
        previous = step


@currency_router.message(AddCurrency.name, F.text)
async def add_name(message: types.Message, state: FSMContext, session: AsyncSession):
    user_tg_id = message.from_user.id
    user_id = await orm_get_user(session, user_tg_id)

    data = await state.get_data()
    await delete_regular_messages(data, message)

    if message.text == '.' and AddCurrency.currency_for_change:
        await state.update_data(name=AddCurrency.currency_for_change.name)
    else:
        if len(message.text) >= 50:
            bot_message = await message.answer("Название валюты не должно превышать 50 символов. \n Введите заново")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return

        try:
            name = message.text

            if AddCurrency.currency_for_change and AddCurrency.currency_for_change.name == name:
                await state.update_data(name=name)
            else:
                check_name = await check_existing_currency(session, name, user_id)
                if check_name:
                    raise ValueError(f"Валюта с именем '{name}' уже существует")

                await state.update_data(name=name)

        except ValueError as e:
            bot_message = await message.answer(f"Ошибка: {e}. Пожалуйста, введите другое название:")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return

    data = await state.get_data()
    currency_name = data['name']
    bot_message = await message.answer(f"Введите количество валюты {currency_name} на балансе")
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await state.set_state(AddCurrency.balance)


@currency_router.message(AddCurrency.balance, F.text)
async def add_balance(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await delete_regular_messages(data, message)

    if message.text == '.' and AddCurrency.currency_for_change:
        await state.update_data(balance=AddCurrency.currency_for_change.balance)
    else:
        await state.update_data(balance=message.text)
    bot_message = await message.answer(
        "Введите курс данной валюты или определите его автоматичекси, написав слово 'авто' в поле ввода")
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await state.set_state(AddCurrency.market_price)


@currency_router.message(AddCurrency.market_price, F.text)
async def add_market_price(message: types.Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    await delete_regular_messages(data, message)
    currency_name = data['name']

    if message.text == '.' and AddCurrency.currency_for_change:
        await state.update_data(market_price=AddCurrency.currency_for_change.market_price)
    else:
        market_price = message.text
        if market_price.casefold() == 'авто':
            try:
                auto_market_price = get_exchange_rate(currency_name, 'RUB')
                await state.update_data(market_price=auto_market_price)
                bot_message = await message.answer(f"Курс {currency_name} к RUB автоматически установлен: {auto_market_price}")
                await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            except Exception as e:
                bot_message = await message.answer(f"Не удалось получить курс валюты: {e}")
                await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                return
        else:
            try:
                market_price = float(market_price)
                await state.update_data(market_price=market_price)
            except ValueError:
                bot_message = await message.answer("Введите корректное числовое значение для курса валюты.")
                await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                return

    data = await state.get_data()
    try:
        if AddCurrency.currency_for_change:
            await orm_update_currency(session, data["currency_id"], data)
        else:
            await orm_add_currency(session, data)

        bot_message = await message.answer("Валюта добалена/изменена", reply_markup=types.ReplyKeyboardRemove())
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
        await state.clear()

        await delete_bot_and_user_messages(data, message, bot_message)

    except Exception as e:
        await message.answer(f"Ошибка {e}, обратитесь к @gigcomm, чтобы исправить ее!")
        await state.clear()

    AddCurrency.currency_for_change = None
