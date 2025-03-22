import asyncio

from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import (
    orm_add_cryptocurrency,
    orm_update_cryptocurrency, check_existing_cryptocurrency, orm_get_cryptocurrency, orm_get_user)

from tg_bot.handlers.common_imports import *
from parsers.Bybit_API import get_price_cryptocurrency
from tg_bot.keyboards.reply import get_keyboard
from tg_bot.logger import logger
from utils.message_utils import delete_regular_messages, delete_bot_and_user_messages

cryptocurrency_router = Router()

CRYPTOCURRENCY_CANCEL_FSM = get_keyboard(
    "Отменить действие с криптовалютой",
    placeholder="Используйте кнопки ниже для отмены",
)

CRYPTOCURRENCY_CANCEL_AND_BACK_FSM = get_keyboard(
"Отменить действие с криптовалютой",
    "Назад к предыдущему шагу для криптовалюты",
    placeholder="Используйте кнопки ниже для действий",
)

class AddСryptocurrency(StatesGroup):
    cryptocurrency_id = State()
    cryptomarket_id = State()
    name = State()
    balance = State()
    purchase_price = State()
    selling_price = State()
    market_price = State()

    cryptocurrency_for_change = None
    texts = {
        'AddСryptocurrency:name': 'Введите название заново',
        'AddСryptocurrency:balance': 'Введите баланс заново',
        'AddСryptocurrency:purchase_price': 'Введите цену покупки заново',
        'AddСryptocurrency:selling_price': 'Введите цену продажи заново',
        'AddСryptocurrency:market_price': 'Это последний стейт...',
    }


@cryptocurrency_router.callback_query(StateFilter(None), F.data.startswith("change_cryptocurrency"))
async def change_cryptocurrency(callback_query: CallbackQuery, state: FSMContext, session: AsyncSession):
    logger.info(f"Пользователь {callback_query.from_user.id} начал изменение криптовалюты.")
    cryptocurrency_id = int(callback_query.data.split(":")[-1])
    await state.update_data(cryptocurrency_id=cryptocurrency_id)
    cryptocurrency_for_change = await orm_get_cryptocurrency(session, cryptocurrency_id)
    AddСryptocurrency.cryptocurrency_for_change = cryptocurrency_for_change

    keyboard_message = await callback_query.message.answer(
        "В режиме изменения, если поставить точку, данное поле будет прежним,"
        "а процесс перейдет к следующему полю объекта.\nИзмените данные:",
        reply_markup=CRYPTOCURRENCY_CANCEL_AND_BACK_FSM)
    bot_message = await callback_query.message.answer("Введите название криптовалюты")
    await state.update_data(keyboard_message_id=[keyboard_message.message_id], message_ids=[bot_message.message_id])

    await state.set_state(AddСryptocurrency.name)


@cryptocurrency_router.callback_query(StateFilter(None), F.data.startswith("add_cryptocurrency"))
async def add_cryptomarket(callback_query: CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь {callback_query.from_user.id} начал добавление криптовалюты.")
    cryptomarket_id = int(callback_query.data.split(":")[-1])
    await state.update_data(cryptomarket_id=cryptomarket_id)

    keyboard_message = await callback_query.message.answer("Заполните данные:", reply_markup=CRYPTOCURRENCY_CANCEL_FSM)
    bot_message = await callback_query.message.answer("Введите название криптовалюты в сокращенном виде, например BTC")
    await state.update_data(keyboard_message_id=[keyboard_message.message_id], message_ids=[bot_message.message_id])

    await state.set_state(AddСryptocurrency.name)


@cryptocurrency_router.message(StateFilter('*'), Command("Отменить действие с криптовалютой"))
@cryptocurrency_router.message(StateFilter('*'), F.text.casefold() == "отменить действие с криптовалютой")
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    logger.info(f"Пользователь {message.from_user.id} отменил действие с криптовалюты.")
    data = await state.get_data()
    await delete_regular_messages(data, message)

    current_state = await state.get_state()
    if current_state is None:
        return
    if AddСryptocurrency.cryptocurrency_for_change:
        AddСryptocurrency.cryptocurrency_for_change = None
    await state.clear()
    bot_message = await message.answer("Действия отменены", reply_markup=types.ReplyKeyboardRemove())
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await delete_bot_and_user_messages(data, message, bot_message)


@cryptocurrency_router.message(StateFilter('*'), Command("Назад к предыдущему шагу для криптовалюты"))
@cryptocurrency_router.message(StateFilter('*'), F.text.casefold() == "назад к предыдущему шагу для криптовалюты")
async def back_handler(message: types.Message, state: FSMContext) -> None:
    logger.info(f"Пользователь {message.from_user.id} вернулся к предыдущему шагу для изменения криптовалюты.")
    data = await state.get_data()
    await delete_regular_messages(data, message)

    current_state = await state.get_state()

    if current_state == AddСryptocurrency.name:
        bot_message = await message.answer("Предыдущего шага нет, введите название криптовалюты или нажмите ниже на кнопку отмены")
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
        return

    previous = None
    for step in AddСryptocurrency.__all_states__:
        if step.state == current_state:
            await state.set_state(previous)
            bot_message = await message.answer(f"Вы вернулись к прошлому шагу \n {AddСryptocurrency.texts[previous.state]}")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return
        previous = step


@cryptocurrency_router.message(AddСryptocurrency.name, F.text)
async def add_name(message: types.Message, state: FSMContext, session: AsyncSession):
    logger.info(f"Пользователь {message.from_user.id} вводит название криптовалюты.")
    user_tg_id = message.from_user.id
    user_id = await orm_get_user(session, user_tg_id)

    data = await state.get_data()
    await delete_regular_messages(data, message)

    if message.text == '.' and AddСryptocurrency.cryptocurrency_for_change:
        await state.update_data(name=AddСryptocurrency.cryptocurrency_for_change.name)
    else:
        if len(message.text) > 10:
            bot_message = await message.answer("Название криптовалюты не должно превышать 10 символов.\nВведите заново")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return

        try:
            name = message.text

            if AddСryptocurrency.cryptocurrency_for_change and AddСryptocurrency.cryptocurrency_for_change.name == name:
                await state.update_data(name=name.upper())
            else:
                check_name = await check_existing_cryptocurrency(session, name, user_id)
                if check_name:
                    raise ValueError(f"Криптовалюта с именем '{name}' уже существует")

                await state.update_data(name=name.upper())

        except ValueError as e:
            logger.error(f"Ошибка при вводе названия криптовалюты: {e}")
            bot_message = await message.answer("Ошибка. Пожалуйста, введите другое название:")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return

    bot_message = await message.answer("Введите количество криптовалюты")
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await state.set_state(AddСryptocurrency.balance)


@cryptocurrency_router.message(AddСryptocurrency.balance, F.text)
async def add_balance(message: types.Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} вводит баланс криптовалюты.")
    data = await state.get_data()
    await delete_regular_messages(data, message)

    if message.text == '.' and AddСryptocurrency.cryptocurrency_for_change:
        await state.update_data(balance=AddСryptocurrency.cryptocurrency_for_change.balance)
    else:
        try:
            if len(message.text) > 20:
                bot_message = await message.answer(
                    "Количество символов цены криптовалюты не должно превышать 20 символов.\nВведите заново")
                await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                return

            cryptocurrency_balance = float(message.text)
            await state.update_data(balance=cryptocurrency_balance)
        except ValueError:
            logger.warning(f"Некорректное значение баланса: {message.text}")
            bot_message = await message.answer("Некорректное значение баланса, введите число.")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return

    bot_message = await message.answer("Введите цену покупки криптовалюты")
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await state.set_state(AddСryptocurrency.purchase_price)


@cryptocurrency_router.message(AddСryptocurrency.purchase_price, F.text)
async def add_purchase_price(message: types.Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} вводит цену покупки криптовалюты.")
    data = await state.get_data()
    await delete_regular_messages(data, message)

    try:
        if message.text == '.' and AddСryptocurrency.cryptocurrency_for_change:
            await state.update_data(purchase_price=AddСryptocurrency.cryptocurrency_for_change.purchase_price)
        else:
            if len(message.text) > 20:
                bot_message = await message.answer(
                    "Количество символов цены покупки криптовалюты не должно превышать 20 символов.\nВведите заново")
                await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                return

            await state.update_data(purchase_price=message.text)

        bot_message = await message.answer("Введите цену продажи криптовалюты")
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
    except Exception as e:
        logger.error(f"Ошибка при обновлении цены покупки криптовалюты: {e}")
        bot_message = await message.answer("Введите корректное числовое значение для цены покупки криптовалюты.")
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
        return

    await state.set_state(AddСryptocurrency.selling_price)


@cryptocurrency_router.message(AddСryptocurrency.selling_price, F.text)
async def add_selling_price(message: types.Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} вводит цену продажи криптовалюты.")
    data = await state.get_data()
    await delete_regular_messages(data, message)
    try:
        if message.text == '.' and AddСryptocurrency.cryptocurrency_for_change:
            await state.update_data(selling_price=AddСryptocurrency.cryptocurrency_for_change.selling_price)
        else:
            if len(message.text) > 20:
                bot_message = await message.answer(
                    "Количество символов цены продажи криптовалюты не должно превышать 20 символов.\nВведите заново")
                await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                return

            await state.update_data(selling_price=message.text)

        bot_message = await message.answer(
            "Введите цену криптовалюты на криптобирже или введите слово 'авто' для автоматического определения "
            "текущей цены криптовалюты")
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    except Exception as e:
        logger.error(f"Ошибка при обновлении цены продажи криптовалюты: {e}")
        bot_message = await message.answer("Введите корректное числовое значение для цены продажи криптовалюты.")
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
        return

    await state.set_state(AddСryptocurrency.market_price)


@cryptocurrency_router.message(AddСryptocurrency.market_price, F.text)
async def add_market_price(message: types.Message, state: FSMContext, session: AsyncSession):
    logger.info(f"Пользователь {message.from_user.id} вводит/получает рыночную цену криптовалюты.")
    data = await state.get_data()
    cryptocur_name = data['name'] + "USDT"

    await delete_regular_messages(data, message)

    if message.text == '.' and AddСryptocurrency.cryptocurrency_for_change:
        await state.update_data(market_price=AddСryptocurrency.cryptocurrency_for_change.market_price)
    else:
        market_price = message.text
        if market_price.casefold() == 'авто':
            try:
                auto_market_price = get_price_cryptocurrency(cryptocur_name)
                if auto_market_price is None:
                    bot_message = await message.answer("Введите корректное числовое значение для цены криптовалюты")
                    await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                    return

                await state.update_data(market_price=auto_market_price)
                bot_message = await message.answer(f"Курс {cryptocur_name} на криптобирже автоматически установлен: {auto_market_price}")

                await asyncio.sleep(2)
                await bot_message.delete()

            except (ConnectionError, TimeoutError) as e:
                logger.error(f"Ошибка подключения при получении рыночной цены криптовалюты {cryptocur_name} для пользователя {message.from_user.id}: {e}")
                bot_message = await message.answer("Ошибка подключения к сервису получения цены криптовалюты. Введите цену с клавиатуры!")
                await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                return

            except Exception as e:
                logger.exception(f"Ошибка при определении рыночной цены криптовалюты {cryptocur_name} для пользователя {message.from_user.id}: {e}")
                bot_message = await message.answer("Не удалось получить цену криптовалюты, введите цену с клавиатуры!")
                await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                return
        else:
            try:
                if len(message.text) > 10:
                    bot_message = await message.answer(
                        "Количество символов для рыночной цены криптовалюты не должно превышать 10 символов.\nВведите заново")
                    await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                    return

                market_price = float(market_price)
                await state.update_data(market_price=market_price)

            except ValueError:
                logger.warning(f"Некорректное значение рыночной цены криптовалюты: {message.text}")
                bot_message = await message.answer("Введите корректное числовое значение для рыночной цены криптовалюты")
                await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                return

    data = await state.get_data()
    try:
        if AddСryptocurrency.cryptocurrency_for_change:
            await orm_update_cryptocurrency(session, data["cryptocurrency_id"], data)
        else:
            await orm_add_cryptocurrency(session, data)

        bot_message = await message.answer(f"Криптовалюта {cryptocur_name} добавлена", reply_markup=types.ReplyKeyboardRemove())
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
        await state.clear()

        await delete_bot_and_user_messages(data, message, bot_message)

    except Exception as e:
        logger.error(f"Ошибка при добавлении криптовалюты: {e}")
        await message.answer("Ошибка, обратитесь к @gigcomm, чтобы исправить ее!")
        await state.clear()

    AddСryptocurrency.cryptocurrency_for_change = None
