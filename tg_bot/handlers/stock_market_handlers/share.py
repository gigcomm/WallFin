import asyncio
from fileinput import filename

from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import orm_add_share, orm_delete_share, orm_get_share, orm_update_share, check_existing_share, \
    orm_get_user
from tg_bot.handlers.common_imports import *
from tg_bot.keyboards.reply import get_keyboard
from parsers.tinkoff_invest_API import get_price_share
from tg_bot.logger import logger
from utils.message_utils import delete_regular_messages, delete_bot_and_user_messages
from utils.processing_input_number import validate_positive_number

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


@share_router.callback_query(StateFilter(None), F.data.startswith('change_share'))
async def change_share(callback_query: CallbackQuery, state: FSMContext, session: AsyncSession):
    logger.info(f"Пользователь {callback_query.from_user.id} начал изменение акции.")
    share_id = int(callback_query.data.split(":")[-2])
    stockmarket_id = int(callback_query.data.split(":")[-1])
    await state.update_data(share_id=share_id, stockmarket_id=stockmarket_id)
    share_for_change = await orm_get_share(session, share_id)

    AddShare.share_for_change = share_for_change

    keyboard_message = await callback_query.message.answer("Вы находитесь в режиме изменения.\n"
        "Чтобы оставить поле без изменений, введите точку (.) — тогда будет сохранено текущее значение, "
        "и вы перейдёте к следующему полю.",
        reply_markup=SHARE_CANCEL_AND_BACK_FSM)
    bot_message = await callback_query.message.answer(
        "Введите новый тикер акции, например: SBER, AAPL."
    )

    await state.update_data(keyboard_message_id=[keyboard_message.message_id], message_ids=[bot_message.message_id])

    await state.set_state(AddShare.name)


@share_router.callback_query(StateFilter(None), F.data.startswith('add_share'))
async def add_cryptomarket(callback_query: CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь {callback_query.from_user.id} начал добавление акции.")
    stockmarket_id = int(callback_query.data.split(":")[-1])
    await state.update_data(stockmarket_id=stockmarket_id)

    keyboard_message = await callback_query.message.answer("Заполните данные:", reply_markup=SHARE_CANCEL_FSM)

    bot_message = await callback_query.message.answer("Введите тикер акции, например: SBER, AAPL...")
    await state.update_data(keyboard_message_id=[keyboard_message.message_id], message_ids=[bot_message.message_id])

    await state.set_state(AddShare.name)


@share_router.message(StateFilter('*'), Command('Отменить действие с акцией'))
@share_router.message(StateFilter('*'), F.text.casefold() == 'отменить действие с акцией')
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    logger.info(f"Пользователь {message.from_user.id} отменил действие с акцией.")
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
    logger.info(f"Пользователь {message.from_user.id} вернулся к предыдущему шагу для изменения акции.")
    data = await state.get_data()
    await delete_regular_messages(data, message)

    current_state = await state.get_state()

    if current_state == AddShare.name:
        bot_message = await message.answer(
            "Предыдущего шага нет. Введите название акции или нажмите кнопку «Отмена» ниже."
        )
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
    logger.info(f"Пользователь {message.from_user.id} вводит название акции.")
    user_tg_id = message.from_user.id
    user_id = await orm_get_user(session, user_tg_id)

    data = await state.get_data()
    stockmarket_id = data['stockmarket_id']
    name = message.text.strip().upper()
    await delete_regular_messages(data, message)

    if name == '.' and AddShare.share_for_change:
        await state.update_data(name=AddShare.share_for_change.name)
    else:
        if len(name) > 50:
            bot_message = await message.answer("Название акции не должно превышать 50 символов.\nВведите заново")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return

        try:
            if AddShare.share_for_change and AddShare.share_for_change.name == name:
                await state.update_data(name=name)
            else:
                check_name = await check_existing_share(session, name, user_id, stockmarket_id)
                if check_name:
                    raise ValueError(f"Акция с именем '{name}' уже существует!")

                await state.update_data(name=name)

        except ValueError as e:
            logger.error(f"Ошибка при вводе названия акции: {e}")
            bot_message = await message.answer(f"{e} Пожалуйста, введите другое название:")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return

    data = await state.get_data()
    share_name = data['name']

    bot_message = await message.answer(f'Введите цену покупки акции <b>"{share_name}"</b>')
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await state.set_state(AddShare.purchase_price)


@share_router.message(AddShare.purchase_price, F.text)
async def add_purchase_price(message: types.Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} вводит цену покупки акции.")
    data = await state.get_data()
    await delete_regular_messages(data, message)

    try:
        if message.text == '.' and AddShare.share_for_change:
            await state.update_data(purchase_price=AddShare.share_for_change.purchase_price)
        else:
            if len(message.text) > 20:
                bot_message = await message.answer(
                    "Количество символов для цены покупки акции не должно превышать 20 символов.\nВведите заново")
                await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                return

            value = await validate_positive_number(message, state, scale=6, field_name="цены покупки")
            if value is None:
                return

            value = float(message.text)
            if value == 0:
                bot_message = await message.answer(
                    "Цена покупки акции не должна быть равная 0.\nВведите заново")
                await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                return

            await state.update_data(purchase_price=float(message.text))

    except ValueError:
        logger.warning(f"Некорректное значение цены покупки акции: {message.text}")
        bot_message = await message.answer("Некорректное значение цены покупки акции, введите число, например, 123.45")
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
        return

    except Exception as e:
        logger.error(f"Ошибка при обновлении цены покупки акции: {e}")
        bot_message = await message.answer("Введите корректное числовое значение для цены покупки акции.")
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
        return

    bot_message = await message.answer("Введите цену продажи акции")
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await state.set_state(AddShare.selling_price)


@share_router.message(AddShare.selling_price, F.text)
async def add_selling_price(message: types.Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} вводит цену продажи акции.")
    data = await state.get_data()
    await delete_regular_messages(data, message)

    try:
        if message.text == '.' and AddShare.share_for_change:
            await state.update_data(selling_price=AddShare.share_for_change.selling_price)
        else:
            if len(message.text) > 20:
                bot_message = await message.answer(
                    "Количество символов для цены продажи акции не должно превышать 20 символов.\nВведите заново")
                await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                return

            value = await validate_positive_number(message, state, scale=6, field_name="цены продажи")
            if value is None:
                return

            await state.update_data(selling_price=float(message.text))

    except ValueError:
        logger.warning(f"Некорректное значение цены продажи акции: {message.text}")
        bot_message = await message.answer("Некорректное значение цены продажи акции, введите число, например, 123.45")
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
        return

    except Exception as e:
        logger.error(f"Ошибка при обновлении цены продажи акции: {e}")
        bot_message = await message.answer("Введите корректное числовое значение для цены продажи акции.")
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
        return

    bot_message = await message.answer(
        "Введите цену акции на фондовой бирже или напишите слово 'авто' для автоматического определения текущей цены акции")
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await state.set_state(AddShare.market_price)


@share_router.message(AddShare.market_price, F.text)
async def add_market_price(message: types.Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} вводит/получает рыночную цену акции.")
    data = await state.get_data()
    share_name = data['name']

    await delete_regular_messages(data, message)

    if message.text == '.' and AddShare.share_for_change:
        await state.update_data(market_price=AddShare.share_for_change.market_price)
    else:
        market_price = message.text
        if market_price.casefold() == 'авто':
            try:
                auto_market_price, currency = await get_price_share(share_name)
                if auto_market_price is None:
                    bot_message = await message.answer(f"Данная акция {share_name} не найдена! Введите корректное числовое значение для цены акции:")
                    await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                    return

                await state.update_data(market_price=auto_market_price, currency=currency)
                bot_message = await message.answer(f"Курс {share_name} на финбирже автоматически установлен: {auto_market_price}")

                await asyncio.sleep(2)
                await bot_message.delete()

            except (ConnectionError, TimeoutError) as e:
                logger.error(f"Ошибка подключения при получении рыночной цены акции {share_name} для пользователя {message.from_user.id}: {e}")
                bot_message = await message.answer("Ошибка подключения к сервису получения цены акции. Введите цену с клавиатуры!")
                await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                return

            except Exception as e:
                logger.exception(
                    f"Ошибка при определении рыночной цены акции {share_name} для пользователя {message.from_user.id}: {e}")
                bot_message = await message.answer("Не удалось получить цену акции, введите цену акции с клавиатуры!")
                await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                return
        else:
            try:
                if len(message.text) > 10:
                    bot_message = await message.answer(
                        "Количество символов для рыночной цены акции не должно превышать 10 символов.\nВведите заново")
                    await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                    return

                value = await validate_positive_number(message, state, scale=6, field_name="рыночной цены", allow_auto=True)
                if value is None:
                    return

                await state.update_data(market_price=float(market_price))

                currency = data.get('currency')
                if not currency:
                    bot_message = await message.answer("Введите валюту для акции (например, RUB, USD, EUR):")
                    await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                    await state.set_state(AddShare.currency)
                    return

            except ValueError:
                logger.warning(f"Некорректное значение рыночной цены акции: {message.text}")
                bot_message = await message.answer("Введите корректное числовое значение цены акции, например: 123.45, "
                    "или введите 'авто' для автоматического определения текущей цены."
                )
                await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                return

    bot_message = await message.answer("Введите валюту для акции (например, RUB, USD, EUR):")
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await state.set_state(AddShare.currency)


@share_router.message(AddShare.currency, F.text)
async def add_currency(message: types.Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} вводит валюту акции.")
    data = await state.get_data()
    await delete_regular_messages(data, message)

    try:
        if message.text == '.' and AddShare.share_for_change:
            await state.update_data(currency=AddShare.share_for_change.currency)
        else:
            currency = message.text.upper().strip()

            valid_currencies = ['RUB', 'USD', 'EUR']
            if currency not in valid_currencies:
                bot_message = await message.answer("Введите корректный код валюты (RUB, USD, EUR):")
                await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                return

            await state.update_data(currency=currency)
            updated_data = await state.get_data()
            print(f"Обновленные данные после ввода валюты: {updated_data}")

    except Exception as e:
        logger.error(f"Ошибка при обновлении валюты акции: {e}")
        bot_message = await message.answer("Введите корректное значение для валюты (USD, EUR, RUB) акции.")
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
        return

    bot_message = await message.answer("Введите количество бумаг акции:")
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await state.set_state(AddShare.quantity)


@share_router.message(AddShare.quantity, F.text)
async def add_quantity(message: types.Message, state: FSMContext, session: AsyncSession):
    logger.info(f"Пользователь {message.from_user.id} вводит количество бумаг акций.")
    data = await state.get_data()
    await delete_regular_messages(data, message)

    if message.text == '.' and AddShare.share_for_change:
        await state.update_data(quantity=AddShare.share_for_change.quantity)
    else:
        try:
            if len(message.text) > 7:
                bot_message = await message.answer(
                    "Количество символов для количества бумаг акции не должно превышать 7 символов.\nВведите заново")
                await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                return

            value = await validate_positive_number(message, state, scale=6, field_name="количества")
            if value is None:
                return

            await state.update_data(quantity=float(message.text))

        except ValueError:
            logger.warning(f"Некорректное значение количество бумаг акции: {message.text}")
            bot_message = await message.answer("Некорректное значение количество бумаг акции, введите число, например, 12")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return

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
        logger.error(f"Ошибка при добавлении акции: {e}")
        await message.answer("Ошибка, обратитесь к @gigcomm, чтобы исправить ее!")
        await state.clear()

    AddShare.share_for_change = None
