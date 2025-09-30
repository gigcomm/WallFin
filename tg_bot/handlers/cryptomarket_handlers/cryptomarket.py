from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import (
    orm_add_cryptomarket,
    orm_update_cryptomarket,
    orm_get_cryptomarket_by_id,
    check_existing_cryptomarket,
    orm_get_user)

from tg_bot.handlers.common_imports import *
from tg_bot.handlers.cryptomarket_handlers.cryptocurrency import cryptocurrency_router
from tg_bot.keyboards.inline import get_callback_btns
from tg_bot.keyboards.reply import get_keyboard
from tg_bot.logger import logger
from utils.message_utils import delete_regular_messages, delete_bot_and_user_messages

cryptomarket_router = Router()
cryptomarket_router.include_router(cryptocurrency_router)

CRYPTOMARKET_CANCEL_FSM = get_keyboard(
    "Отменить действие с криптобиржей",
    placeholder="Нажмите на кнопку ниже, чтобы отменить добавление/изменение",
)


@cryptomarket_router.callback_query(lambda callback_query: callback_query.data.startswith("cryptomarket_"))
async def process_cryptomarket_selection(callback_query: CallbackQuery):
    cryptomarkets_id = int(callback_query.data.split(':')[-1].split('_')[-1])
    logger.info(f"Пользователь {callback_query.from_user.id} выбрал банк с ID: {cryptomarkets_id}.")

    button_cryptomarket = {
        "Криптовалюта": f"cryptocurrency_{cryptomarkets_id}"
    }

    await callback_query.message.edit_text(
        text="Выберете действие, предоставляемое криптобиржей:",
        reply_markup=get_callback_btns(btns=button_cryptomarket)
    )
    await callback_query.answer()


class AddCryptomarket(StatesGroup):
    name = State()

    cryptomarket_for_change = None
    texts = {
        'AddCryptomarket:name': 'Введите новое название для криптобиржи',
    }


@cryptomarket_router.callback_query(StateFilter(None), F.data.startswith('change_cryptomarket'))
async def change_cryptomarket(callback_query: CallbackQuery, state: FSMContext, session: AsyncSession):
    logger.info(f"Пользователь {callback_query.from_user.id} начал изменение криптобиржи.")
    cryptomarket_id = int(callback_query.data.split(":")[-1])
    cryptomarket_for_change = await orm_get_cryptomarket_by_id(session, cryptomarket_id)

    AddCryptomarket.cryptomarket_for_change = cryptomarket_for_change

    keyboard_message = await callback_query.message.answer(
        "В режиме изменения, если поставить точку, данное поле будет прежним,"
        "а процесс перейдет к следующему полю объекта.\nИзмените данные:",
        reply_markup=CRYPTOMARKET_CANCEL_FSM)
    bot_message = await callback_query.message.answer("Введите название криптобиржи")
    await state.update_data(keyboard_message_id=[keyboard_message.message_id], message_ids=[bot_message.message_id])

    await state.set_state(AddCryptomarket.name)


@cryptomarket_router.callback_query(StateFilter(None), F.data.startswith('add_cryptomarket'))
async def add_cryptomarket(callback_query: CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь {callback_query.from_user.id} начал добавление криптобиржи.")
    keyboard_message = await callback_query.message.answer("Заполните данные:", reply_markup=CRYPTOMARKET_CANCEL_FSM)
    bot_message = await callback_query.message.answer("Введите название криптобиржи", reply_markup=CRYPTOMARKET_CANCEL_FSM)
    await state.update_data(keyboard_message_id=[keyboard_message.message_id], message_ids=[bot_message.message_id])

    await state.set_state(AddCryptomarket.name)


@cryptomarket_router.message(StateFilter('*'), Command('Отменить действие с криптобиржей'))
@cryptomarket_router.message(StateFilter('*'), F.text.casefold() == 'отменить действие с криптобиржей')
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    logger.info(f"Пользователь {message.from_user.id} отменил действие с криптобиржой.")
    data = await state.get_data()

    await delete_regular_messages(data, message)

    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()

    bot_message = await message.answer("Действия отменены", reply_markup=types.ReplyKeyboardRemove())
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await delete_bot_and_user_messages(data, message, bot_message)


@cryptomarket_router.message(AddCryptomarket.name, or_f(F.text))
async def add_name(message: types.Message, state: FSMContext, session: AsyncSession):
    logger.info(f"Пользователь {message.from_user.id} вводит название криптобиржи.")
    user_tg_id = message.from_user.id
    user_id = await orm_get_user(session, user_tg_id)

    data = await state.get_data()

    await delete_regular_messages(data, message)

    if message.text == '.' and AddCryptomarket.cryptomarket_for_change:
        await state.update_data(name=AddCryptomarket.cryptomarket_for_change.name)
    else:
        if len(message.text) > 50:
            bot_message = await message.answer("Название криптобиржи не должно превышать 50 символов.\nВведите заново")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return

        try:
            name = message.text

            if AddCryptomarket.cryptomarket_for_change and AddCryptomarket.cryptomarket_for_change.name == name:
                await state.update_data(name=name)
            else:
                check_name = await check_existing_cryptomarket(session, name, user_id)
                if check_name:
                    raise ValueError(f"Криптобиржа с именем '{name}' уже существует!")

                await state.update_data(name=name)

        except ValueError as e:
            logger.error(f"Ошибка при вводе названия криптобиржи: {e}")
            bot_message = await message.answer(f"{e} Пожалуйста, введите другое название:")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return

    data = await state.get_data()
    try:
        if AddCryptomarket.cryptomarket_for_change:
            await orm_update_cryptomarket(session, AddCryptomarket.cryptomarket_for_change.id, data)
        else:
            await orm_add_cryptomarket(session, data, message)

        bot_message = await message.answer("Криптобиржа добавлена", reply_markup=types.ReplyKeyboardRemove())
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
        await state.clear()

        await delete_bot_and_user_messages(data, message, bot_message)

    except Exception as e:
        logger.error(f"Ошибка при вводе названия криптобиржи: {e}")
        await message.answer("Ошибка, обратитесь к @gigcomm, чтобы исправить ее!")
        await state.clear()

    AddCryptomarket.cryptomarket_for_change = None
