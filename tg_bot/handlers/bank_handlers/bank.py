from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import (
    orm_add_bank,
    orm_get_bank,
    orm_update_bank,
    orm_get_bank_by_id, check_existing_bank, orm_get_user)
from tg_bot.logger import logger

from tg_bot.handlers.common_imports import *
from tg_bot.handlers.bank_handlers.account import account_router
from tg_bot.handlers.bank_handlers.currency import currency_router
from tg_bot.handlers.bank_handlers.deposit import deposit_router
from tg_bot.keyboards.inline import get_callback_btns
from tg_bot.keyboards.reply import get_keyboard
from utils.message_utils import delete_regular_messages, delete_bot_and_user_messages

user_bank = {}

bank_router = Router()
bank_router.include_router(account_router)
bank_router.include_router(currency_router)
bank_router.include_router(deposit_router)

BANK_CANCEL_FSM = get_keyboard(
    "Отменить действие с банком",
    placeholder="Нажмите на кнопку ниже, чтобы отменить добавление/изменение",
)


# @bank_router.message(F.text == "Банки")
# async def starting_at_bank(message: types.Message, session: AsyncSession):
#     try:
#         banks = await orm_get_bank(session, message.from_user.id)
#         logger.info(f"Пользователь {message.from_user.id} запросил список банков. Найдено: {len(banks)} банков.")
#
#         buttons_bank = {bank.name: "bank_" + str(bank.id) for bank in banks}
#         await message.answer(
#             text="Выберите банк:",
#             reply_markup=get_callback_btns(btns=buttons_bank)
#         )
#
#     except Exception as e:
#         logger.error(f"Ошибка при получении списка банков для пользователя {message.from_user.id}: {e}")
#         await message.answer("Ошибка при загрузке банков. Пожалуйста, попробуйте позже.")


@bank_router.callback_query(lambda callback_query: callback_query.data.startswith("bank_"))
async def process_bank_selection(callback_query: CallbackQuery):
    bank_id = int(callback_query.data.split('_')[-1])
    logger.info(f"Пользователь {callback_query.from_user.id} выбрал банк с ID: {bank_id}.")

    buttons = {
        "Вклады": f"deposits_{bank_id}",
        "Счета": f"accounts_{bank_id}",
        "Валюты": f"currencies_{bank_id}"
    }
    await callback_query.message.edit_text(
        "Выберете действие, предоставляемое банком:",
        reply_markup=get_callback_btns(btns=buttons)
    )
    await callback_query.answer()



class AddBank(StatesGroup):
    name = State()

    bank_for_change = None
    texts = {
        'AddBank:name': 'Введите новое название для банка',
    }


@bank_router.callback_query(StateFilter(None), F.data.startswith('change_bank'))
async def change_bank(callback_query: CallbackQuery, state: FSMContext, session: AsyncSession):
    logger.info(f"Пользователь {callback_query.from_user.id} начал изменение банка.")
    bank_id = int(callback_query.data.split(":")[-1])
    bank_for_change = await orm_get_bank_by_id(session, bank_id)

    AddBank.bank_for_change = bank_for_change

    keyboard_message = await callback_query.message.answer(
        "В режиме изменения, если поставить точку, данное поле будет прежним,"
        "а процесс перейдет к следующему полю объекта.\nИзмените данные:",
        reply_markup=BANK_CANCEL_FSM)

    bot_message = await callback_query.message.answer("Введите название банка")
    await state.update_data(keyboard_message_id=[keyboard_message.message_id], message_ids=[bot_message.message_id])

    await state.set_state(AddBank.name)


@bank_router.callback_query(StateFilter(None), F.data.startswith('add_bank'))
async def add_bank(callback_query: CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь {callback_query.from_user.id} начал добавление банка.")
    keyboard_message = await callback_query.message.answer("Заполните данные:", reply_markup=BANK_CANCEL_FSM)

    bot_message = await callback_query.message.answer("Введите название банка")
    await state.update_data(keyboard_message_id=[keyboard_message.message_id], message_ids=[bot_message.message_id])

    await state.set_state(AddBank.name)


@bank_router.message(StateFilter('*'), Command('Отменить действие с банком'))
@bank_router.message(StateFilter('*'), F.text.casefold() == 'отменить действие с банком')
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    logger.info(f"Пользователь {message.from_user.id} отменил действие с банком.")
    data = await state.get_data()

    await delete_regular_messages(data, message)

    current_state = await state.get_state()
    if current_state is None:
        return
    await state.clear()

    bot_message = await message.answer("Действия отменены", reply_markup=types.ReplyKeyboardRemove())
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await delete_bot_and_user_messages(data, message, bot_message)


@bank_router.message(AddBank.name, or_f(F.text))
async def add_name(message: types.Message, state: FSMContext, session: AsyncSession):
    logger.info(f"Пользователь {message.from_user.id} вводит название банка.")
    user_tg_id = message.from_user.id
    user_id = await orm_get_user(session, user_tg_id)

    data = await state.get_data()

    await delete_regular_messages(data, message)

    if message.text == '.' and AddBank.bank_for_change:
        await state.update_data(name=AddBank.bank_for_change.name)
    else:
        if len(message.text) > 50:
            bot_message = await message.answer("Название банка не должно превышать 50 символов.\nВведите заново")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return

        try:
            name = message.text

            if AddBank.bank_for_change and AddBank.bank_for_change.name == name:
                await state.update_data(name=name)
            else:
                check_name = await check_existing_bank(session, name, user_id)
                if check_name:
                    raise ValueError(f"Банк с именем '{name}' уже существует")

                await state.update_data(name=name)

        except ValueError as e:
            logger.error(f"Ошибка при вводе названия банка: {e}")
            bot_message = await message.answer("Ошибка. Пожалуйста, введите другое название:")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return

    data = await state.get_data()
    try:
        if AddBank.bank_for_change:
            await orm_update_bank(session, AddBank.bank_for_change.id, data)
        else:
            await orm_add_bank(session, data, message)

        bot_message = await message.answer("Банк добавлен", reply_markup=types.ReplyKeyboardRemove())
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
        await state.clear()

        await delete_bot_and_user_messages(data, message, bot_message)

    except Exception as e:
        logger.error(f"Ошибка при вводе названия банка: {e}")
        await message.answer("Ошибка, обратитесь к @gigcomm, чтобы исправить ее!")
        await state.clear()

    AddBank.bank_for_change = None
