from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import orm_add_share, orm_delete_share, orm_get_share, orm_update_share, check_existing_share, \
    orm_get_user
from tg_bot.handlers.common_imports import *
from tg_bot.keyboards.reply import get_keyboard
from parsers.tinkoff_invest_API import get_price_share
from utils.message_utils import delete_regular_messages, delete_bot_and_user_messages

share_router = Router()

SHARE_CANCEL_FSM = get_keyboard(
    "Отменить действие с акцией",
    placeholder="Используйте кнопки ниже для отмены",
)

SHARE_CANCEL_AND_BACK_FSM = get_keyboard(
"Отменить действие с акцией",
    "Назад к предыдущему шагу для акции",
    placeholder="Используйте кнопки ниже для действий",
)


# @share_router.callback_query(lambda callback_query: callback_query.data.startswith("share_"))
# async def process_deposit_selection(callback_query: CallbackQuery, session: AsyncSession):
#     stockmarket_id = int(callback_query.data.split("_")[-1])
#
#     shares = await orm_get_share(session, stockmarket_id)
#
#     buttons = {share.name: str(share.id) for share in shares}
#     buttons["Добавить акцию"] = f"add_share_{stockmarket_id}"
#     await callback_query.message.edit_text(
#         "Выберете акцию:",
#         reply_markup=get_callback_btns(btns=buttons)
#     )
#     await callback_query.answer()


class AddShare(StatesGroup):
    stockmarket_id = State()
    name = State()
    purchase_price = State()
    selling_price = State()
    market_price = State()
    currency = State()
    quantity = State()

    share_for_change = None
    texts = {
        'AddShare:name': 'Введите название заново',
        'AddShare:purchase_price': 'Введите цена покупки заново',
        'AddShare:selling_price': 'Введите цену продажи заново',
        'AddShare:market_price': 'Введите цену на бирже заново',
        'AddShare:currency': 'Введите наименование валюты для акции (например, RUB, USD, EUR):',
        'AddShare:quantity': 'Это последний стейт...',
    }


# @share_router.callback_query(F.data.startswith('delete_share'))
# async def delete_share(callback: types.CallbackQuery, session: AsyncSession):
#     share_id = callback.data.split("_")[-1]
#     await orm_delete_share(session, int(share_id))
#
#     await callback.answer("Криптобиржа удалена")
#     await callback.message.answer("Криптобиржа удалена")


@share_router.callback_query(StateFilter(None), F.data.startswith('change_share'))
async def change_share(callback_query: CallbackQuery, state: FSMContext, session: AsyncSession):
    share_id = int(callback_query.data.split(":")[-1])
    await state.update_data(share_id=share_id)
    share_for_change = await orm_get_share(session, share_id)
    AddShare.share_for_change = share_for_change

    keyboard_message = await callback_query.answer("В режиме изменения, если поставить точку, данное поле будет прежним,"
        "а процесс перейдет к следующему полю объекта.\nИзмените данные:",
        reply_markup=SHARE_CANCEL_AND_BACK_FSM)
    bot_message = await callback_query.message.answer("Введите тикер акции, например: SBER, AAPL...", reply_markup=SHARE_CANCEL_AND_BACK_FSM)
    await state.update_data(keyboard_message_id=[keyboard_message.message_id], message_ids=[bot_message.message_id])

    await state.set_state(AddShare.name)


@share_router.callback_query(StateFilter(None), F.data.startswith('add_share'))
async def add_cryptomarket(callback_query: CallbackQuery, state: FSMContext):
    stockmarket_id = int(callback_query.data.split(":")[-1])
    await state.update_data(stockmarket_id=stockmarket_id)

    keyboard_message = await callback_query.message.answer("Заполните данные:", reply_markup=SHARE_CANCEL_FSM)
    bot_message = await callback_query.message.answer("Введите тикер акции, например: SBER, AAPL...")
    await state.update_data(keyboard_message_id=[keyboard_message.message_id], message_ids=[bot_message.message_id])

    await state.set_state(AddShare.name)


@share_router.message(StateFilter('*'), Command('Отменить действие с акцией'))
@share_router.message(StateFilter('*'), F.text.casefold() == 'отменить действие с акцией')
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()

    await delete_regular_messages(data, message)

    current_state = await state.get_state()
    if current_state is None:
        return
    if AddShare.share_for_change:
        AddShare.share_for_change = None
    await state.clear()
    bot_message = await message.answer("Действия отменены", reply_markup=types.ReplyKeyboardRemove())
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await delete_bot_and_user_messages(data, message, bot_message)


@share_router.message(StateFilter('*'), Command('Назад к предыдущему шагу для акции'))
@share_router.message(StateFilter('*'), F.text.casefold() == "назад к предыдущему шагу для акции")
async def back_handler(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()

    await delete_regular_messages(data, message)

    current_state = await state.get_state()

    if current_state == AddShare.name:
        bot_message = await message.answer("Предыдущего шага нет, введите название акции или нажмите ниже на кнопку отмены")
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
        return

    previous = None
    for step in AddShare.__all_states__:
        if step.state == current_state:
            await state.set_state(previous)
            bot_message = await message.answer(f"Вы вернулись к прошлому шагу \n {AddShare.texts[previous.state]}")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return
        previous = step


@share_router.message(AddShare.name, F.text)
async def add_name(message: types.Message, state: FSMContext, session: AsyncSession):
    user_tg_id = message.from_user.id
    user_id = await orm_get_user(session, user_tg_id)

    if message.text == '.' and AddShare.share_for_change:
        await state.update_data(name=AddShare.share_for_change.name)
    else:
        if len(message.text) >= 50:
            bot_message = await message.answer("Название акции не должно превышать 50 символов. \n Введите заново")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return

        try:
            name = message.text

            if AddShare.share_for_change and AddShare.share_for_change.name == name:
                await state.update_data(name=name.upper())
            else:
                check_name = await check_existing_share(session, name, user_id)
                if check_name:
                    raise ValueError(f"Акция с именем '{name}' уже существует")

                await state.update_data(name=name.upper())

        except ValueError as e:
            await message.answer(f"Ошибка: {e}. Пожалуйста, введите другое название:")
            return

    bot_message = await message.answer("Введите цену покупки акции")
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await state.set_state(AddShare.purchase_price)


@share_router.message(AddShare.purchase_price, F.text)
async def add_purchase_price(message: types.Message, state: FSMContext):
    if message.text == '.' and AddShare.share_for_change:
        await state.update_data(purchase_price=AddShare.share_for_change.purchase_price)
    else:
        await state.update_data(purchase_price=message.text)

    bot_message = await message.answer("Введите цену продажи акции")
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await state.set_state(AddShare.selling_price)


@share_router.message(AddShare.selling_price, F.text)
async def add_selling_price(message: types.Message, state: FSMContext):
    if message.text == '.' and AddShare.share_for_change:
        await state.update_data(selling_price=AddShare.share_for_change.selling_price)
    else:
        await state.update_data(selling_price=message.text)

    bot_message = await message.answer(
        "Введите цену акции на фондовой бирже или напишите слово 'авто' для автоматического определения текущей цены акции")
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await state.set_state(AddShare.market_price)


@share_router.message(AddShare.market_price, F.text)
async def add_market_price(message: types.Message, state: FSMContext):
    data = await state.get_data()
    share_name = data['name']

    if message.text == '.' and AddShare.share_for_change:
        await state.update_data(market_price=AddShare.share_for_change.market_price)
    else:
        market_price = message.text
        if market_price.casefold() == 'авто':
            try:
                auto_market_price, currency = await get_price_share(share_name)
                if auto_market_price is None:
                    bot_message = await message.answer("Введите корректное числовое значение для цены акции")
                    await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                    return

                await state.update_data(market_price=auto_market_price, currency=currency)
                bot_message = await message.answer(f"Курс {share_name} на финбирже автоматически установлен: {auto_market_price}")
                await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            except Exception as e:
                await message.answer(f"Не удалось получить цену акции: {e}")
                return
        else:
            try:
                market_price = float(market_price)
                await state.update_data(market_price=market_price)

                currency = data.get('currency')
                if not currency:
                    bot_message = await message.answer("Введите валюту для акции (например, RUB, USD, EUR):")
                    await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                    await state.set_state(AddShare.currency)
                    return

            except ValueError:
                await message.answer("Введите корректное числовое значение для цены акции")
                return

    bot_message = await message.answer("Введите валюту для акции (например, RUB, USD, EUR):")
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])
    await state.set_state(AddShare.currency)


@share_router.message(AddShare.currency, F.text)
async def add_currency(message: types.Message, state: FSMContext):
    if message.text == '.' and AddShare.share_for_change:
        await state.update_data(currency=AddShare.share_for_change.currency)
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

    await state.set_state(AddShare.quantity)


@share_router.message(AddShare.quantity, F.text)
async def add_quantity(message: types.Message, state: FSMContext, session: AsyncSession):
    if message.text == '.' and AddShare.share_for_change:
        await state.update_data(quantity=AddShare.share_for_change.quantity)
    else:
        await state.update_data(quantity=message.text)

    data = await state.get_data()
    try:
        if AddShare.share_for_change:
            await orm_update_share(session, AddShare.share_for_change.id, data)
        else:
            await orm_add_share(session, data)
        bot_message = await message.answer("Бумага акции добавлена", reply_markup=types.ReplyKeyboardRemove())
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
        await state.clear()

        await delete_bot_and_user_messages(data, message, bot_message)

    except Exception as e:
        print(e)
        await message.answer(f"Ошибка, обратитесь к @gigcomm, чтобы исправить ее!")
        await state.clear()

    AddShare.share_for_change = None
