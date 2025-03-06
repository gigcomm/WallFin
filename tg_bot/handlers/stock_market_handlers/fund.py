import asyncio

from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import orm_add_fund, orm_get_fund, orm_update_fund, check_existing_fund, orm_get_user
from tg_bot.handlers.common_imports import *
from tg_bot.keyboards.reply import get_keyboard
from parsers.tinkoff_invest_API import get_price_fund
from utils.message_utils import delete_regular_messages, delete_bot_and_user_messages

fund_router = Router()

FUND_CANCEL_FSM = get_keyboard(
    "Отменить действие с фондом",
    placeholder="Используйте кнопки ниже для отмены",
)

FUND_CANCEL_AND_BACK_FSM = get_keyboard(
"Отменить действие с фондом",
    "Назад к предыдущему шагу для фонда",
    placeholder="Используйте кнопки ниже для действий",
)

# @fund_router.callback_query(lambda callback_query: callback_query.data.startswith("fund_"))
# async def process_account_selection(callback_query: CallbackQuery, session: AsyncSession):
#     stockmarket_id = int(callback_query.data.split("_")[-1])
#
#     funds = await orm_get_fund(session, stockmarket_id)
#
#     buttons = {fund.name: str(fund.id) for fund in funds}
#     buttons["Добавить фонд"] = f"add_fund_{stockmarket_id}"
#     await callback_query.message.edit_text(
#         "Выберете фонд:",
#         reply_markup=get_callback_btns(btns=buttons),
#     )
#     await callback_query.answer()


class AddFund(StatesGroup):
    stockmarket_id = State()
    name = State()
    purchase_price = State()
    selling_price = State()
    market_price = State()
    currency = State()
    quantity = State()

    fund_for_change = None
    texts = {
        'AddFund:name': 'Введите название заново',
        'AddFund:purchase_price': 'Введите цена покупки заново',
        'AddFund:selling_price': 'Введите цену продажи заново',
        'AddFund:market_price': 'Введите цену на бирже заново',
        'AddFund:currency': 'Введите наименование валюты для акции(например, RUB, USD, EUR):',
        'AddFund:quantity': 'Это последний стейт...',
    }


# @fund_router.callback_query(F.data.startswith('delete_'))
# async def delete_fund(callback: types.CallbackQuery, session: AsyncSession):
#     fund_id = callback.data.split("_")[-1]
#     await orm_delete_fund(session, int(fund_id))
#
#     await callback.answer("Бумага фонда удалена")
#     await callback.message.answer("Бумага фонда удалена")


@fund_router.callback_query(StateFilter(None), F.data.startswith('change_fund'))
async def change_fund(callback_query: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    fund_id = int(callback_query.data.split(":")[-1])
    await state.update_data(fund_id=fund_id)
    fund_for_change = await orm_get_fund(session, fund_id)
    AddFund.fund_for_change = fund_for_change

    keyboard_message = await callback_query.message.answer(
        "В режиме изменения, если поставить точку, данное поле будет прежним,"
        "а процесс перейдет к следующему полю объекта.\nИзмените данные:",
        reply_markup=FUND_CANCEL_AND_BACK_FSM)
    bot_message = await callback_query.message.answer("Введите тикер фонда, например, TITR")
    await state.update_data(keyboard_message_id=[keyboard_message.message_id], message_ids=[bot_message.message_id])

    await state.set_state(AddFund.name)


@fund_router.callback_query(StateFilter(None), F.data.startswith('add_fund'))
async def add_fund(callback_query: CallbackQuery, state: FSMContext):
    stockmarket_id = int(callback_query.data.split(":")[-1])
    await state.update_data(stockmarket_id=stockmarket_id)

    keyboard_message = await callback_query.message.answer("Заполните данные:", reply_markup=FUND_CANCEL_FSM)
    bot_message = await callback_query.message.answer("Введите тикер фонда, например, TITR")
    await state.update_data(keyboard_message_id=[keyboard_message.message_id], message_ids=[bot_message.message_id])

    await state.set_state(AddFund.name)


@fund_router.message(StateFilter('*'), Command('Отменить действие с фондом'))
@fund_router.message(StateFilter('*'), F.text.casefold() == 'отменить действие с фондом')
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    await delete_regular_messages(data, message)

    current_state = await state.get_state()
    if current_state is None:
        return
    if AddFund.fund_for_change:
        AddFund.fund_for_change = None
    await state.clear()
    bot_message = await message.answer("Действия отменены", reply_markup=types.ReplyKeyboardRemove())
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await delete_bot_and_user_messages(data, message, bot_message)


@fund_router.message(StateFilter('*'), Command('Назад к предыдущему шагу для фонда'))
@fund_router.message(StateFilter('*'), F.text.casefold() == "назад к предыдущему шагу для фонда")
async def back_handler(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    await delete_regular_messages(data, message)

    current_state = await state.get_state()

    if current_state == AddFund.name:
        bot_message = await message.answer("Предыдущего шага нет, введите название фонда или нажмите ниже на кнопку отмены")
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
        return

    previous = None
    for step in AddFund.__all_states__:
        if step.state == current_state:
            await state.set_state(previous)
            bot_message = await message.answer(f"Вы вернулись к прошлому шагу \n {AddFund.texts[previous.state]}")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return
        previous = step


@fund_router.message(AddFund.name, F.text)
async def add_name(message: types.Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    await delete_regular_messages(data, message)

    user_tg_id = message.from_user.id
    user_id = await orm_get_user(session, user_tg_id)

    if message.text == '.' and AddFund.fund_for_change:
        await state.update_data(name=AddFund.fund_for_change.name)
    else:
        if len(message.text) >= 50:
            bot_message = await message.answer("Название фонда не должно превышать 50 символов. \n Введите заново")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return

        try:
            name = message.text

            if AddFund.fund_for_change and AddFund.fund_for_change.name == name:
                await state.update_data(name=name.upper())
            else:
                check_name = await check_existing_fund(session, name, user_id)
                if check_name:
                    raise ValueError(f"Фонд с именем '{name}' уже существует")

                await state.update_data(name=name.upper())

        except ValueError as e:
            await message.answer(f"Ошибка: {e}. Пожалуйста, введите другое название:")
            return

    bot_message = await message.answer("Введите цену покупки фонда")
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await state.set_state(AddFund.purchase_price)


@fund_router.message(AddFund.purchase_price, F.text)
async def add_purchase_price(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await delete_regular_messages(data, message)

    if message.text == '.' and AddFund.fund_for_change:
        await state.update_data(purchase_price=AddFund.fund_for_change.purchase_price)
    else:
        await state.update_data(purchase_price=message.text)

    bot_message = await message.answer("Введите цену продажи фонда")
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await state.set_state(AddFund.selling_price)


@fund_router.message(AddFund.selling_price, F.text)
async def add_selling_price(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await delete_regular_messages(data, message)

    if message.text == '.' and AddFund.fund_for_change:
        await state.update_data(selling_price=AddFund.fund_for_change.selling_price)
    else:
        await state.update_data(selling_price=message.text)

    bot_message = await message.answer(
        "Введите цену фонда на фондовой бирже или введите слово 'авто' для автоматического определения текущей цены фонда")
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await state.set_state(AddFund.market_price)


@fund_router.message(AddFund.market_price, F.text)
async def add_market_price(message: types.Message, state: FSMContext):
    data = await state.get_data()
    fund_name = data['name']

    await delete_regular_messages(data, message)

    if message.text == '.' and AddFund.fund_for_change:
        await state.update_data(market_price=AddFund.fund_for_change.market_price)
    else:
        market_price = message.text
        if market_price.casefold() == 'авто':
            try:
                auto_market_price, currency = await get_price_fund(fund_name)
                if auto_market_price is None:
                    bot_message = await message.answer("Введите корректное числовое значение для цены фонда")
                    await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                    return

                await state.update_data(market_price=auto_market_price, currency=currency)
                bot_message = await message.answer(f"Курс {fund_name} на финбирже автоматически установлен: {auto_market_price}")
                await asyncio.sleep(2)
                await bot_message.delete()

            except Exception as e:
                await message.answer(f"Не удалось получить цену фонда: {e}")
                return
        else:
            try:
                market_price = float(market_price)
                await state.update_data(market_price=market_price)

                currency = data.get('currency')
                if not currency:
                    bot_message = await message.answer("Введите валюту для фонда (например, RUB, USD, EUR):")
                    await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                    await state.set_state(AddFund.currency)
                    return
            except ValueError:
                await message.answer("Введите корректное числовое значение для цены фонда")
                return

    bot_message = await message.answer("Введите валюту для фонда (например, RUB, USD, EUR):")
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await state.set_state(AddFund.currency)


@fund_router.message(AddFund.currency, F.text)
async def add_currency(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await delete_regular_messages(data, message)

    if message.text == '.' and AddFund.fund_for_change:
        await state.update_data(currency=AddFund.fund_for_change.currency)
    else:
        currency = message.text.upper().strip()

        valid_currencies = ['RUB', 'USD', 'EUR']
        if currency not in valid_currencies:
            bot_message = await message.answer("Введите корректный код валюты (например, RUB, USD, EUR):")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return

        await state.update_data(currency=currency)
        updated_data = await state.get_data()
        print(f"Обновленные данные после ввода валюты: {updated_data}")

    bot_message = await message.answer("Введите количество бумаг акции:")
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await state.set_state(AddFund.quantity)


@fund_router.message(AddFund.quantity, F.text)
async def add_quantity(message: types.Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    await delete_regular_messages(data, message)

    if message.text == '.' and AddFund.fund_for_change:
        await state.update_data(quantity=AddFund.fund_for_change.quantity)
    else:
        await state.update_data(quantity=message.text)

    data = await state.get_data()
    try:
        if AddFund.fund_for_change:
            await orm_update_fund(session, AddFund.fund_for_change.id, data)
        else:
            await orm_add_fund(session, data)

        bot_message = await message.answer("Бумага фонда добавлены", reply_markup=types.ReplyKeyboardRemove())
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
        await state.clear()

        await delete_bot_and_user_messages(data, message, bot_message)

    except Exception as e:
        await message.answer(f"Ошибка {e}, обратитесь к @gigcomm, чтобы исправить ее!")
        await state.clear()

    AddFund.fund_for_change = None
