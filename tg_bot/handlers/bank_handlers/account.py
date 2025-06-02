from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import orm_add_account, orm_update_account, orm_get_account, check_existing_account, \
    orm_get_user
from tg_bot.logger import logger
from tg_bot.handlers.common_imports import *
from tg_bot.keyboards.reply import get_keyboard
from utils.message_utils import delete_regular_messages, delete_bot_and_user_messages

account_router = Router()

ACCOUNT_CANCEL_FSM = get_keyboard(
    "Отменить действие со счетом",
    placeholder="Используйте кнопки ниже для отмены",
)

ACCOUNT_CANCEL_AND_BACK_FSM = get_keyboard(
    "Отменить действие со счетом",
    "Назад к предыдущему шагу",
    placeholder="Используйте кнопки ниже для действий",
)


class AddAccount(StatesGroup):
    account_id = State()
    bank_id = State()
    name = State()
    balance = State()

    account_for_change = None
    texts = {
        'AddAccount:name': 'Введите название заново',
        'AddAccount:balance': 'Это последний стейт...'
    }


@account_router.callback_query(StateFilter(None), F.data.startswith('change_account'))
async def change_account(callback_query: CallbackQuery, state: FSMContext, session: AsyncSession):
    logger.info(f"Пользователь {callback_query.from_user.id} начал изменение счета.")
    account_id = int(callback_query.data.split(":")[-2])
    bank_id = int(callback_query.data.split(":")[-1])
    await state.update_data(account_id=account_id, bank_id=bank_id)
    account_for_change = await orm_get_account(session, account_id)

    AddAccount.account_for_change = account_for_change

    keyboard_message = await callback_query.message.answer(
        "Вы находитесь в режиме изменения.\n"
        "Чтобы оставить поле без изменений, введите точку (.) — тогда будет сохранено текущее значение, "
        "и вы перейдёте к следующему полю.",
        reply_markup=ACCOUNT_CANCEL_AND_BACK_FSM)
    bot_message = await callback_query.message.answer(
        "Введите новое название счета."
    )

    await state.update_data(keyboard_message_id=[keyboard_message.message_id], message_ids=[bot_message.message_id])

    await state.set_state(AddAccount.name)


@account_router.callback_query(StateFilter(None), F.data.startswith('add_account'))
async def add_account(callback_query: CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь {callback_query.from_user.id} начал добавление счета.")
    bank_id = int(callback_query.data.split(':')[-1])
    await state.update_data(bank_id=bank_id, message_ids=[], keyboard_message_id=[])

    keyboard_message = await callback_query.message.answer("Заполните данные:", reply_markup=ACCOUNT_CANCEL_FSM)

    bot_message = await callback_query.message.answer("Введите название счета")
    await state.update_data(keyboard_message_id=[keyboard_message.message_id], message_ids=[bot_message.message_id])

    await state.set_state(AddAccount.name)


@account_router.message(StateFilter('*'), Command('Отменить действие со счетом'))
@account_router.message(StateFilter('*'), F.text.casefold() == 'отменить действие со счетом')
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    logger.info(f"Пользователь {message.from_user.id} отменил действие со счетом.")
    data = await state.get_data()
    await delete_regular_messages(data, message)

    current_state = await state.get_state()
    if current_state is None:
        return
    if AddAccount.account_for_change:
        AddAccount.account_for_change = None
    await state.clear()

    bot_message = await message.answer("Действия отменены", reply_markup=types.ReplyKeyboardRemove())
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await delete_bot_and_user_messages(data, message, bot_message)


@account_router.message(StateFilter('*'), Command('Назад к предыдущему шагу'))
@account_router.message(StateFilter('*'), F.text.casefold() == "назад к предыдущему шагу")
async def back_handler(message: types.Message, state: FSMContext) -> None:
    logger.info(f"Пользователь {message.from_user.id} вернулся к предыдущему шагу для изменения валюты.")
    data = await state.get_data()
    await delete_regular_messages(data, message)

    current_state = await state.get_state()

    if current_state == AddAccount.name:
        bot_message = await message.answer(
             "Предыдущего шага нет. Введите название счета или нажмите кнопку «Отмена» ниже."
        )
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
        return

    previous = None
    for step in AddAccount.__all_states__:
        if step.state == current_state:
            await state.set_state(previous)
            bot_message = await message.answer(f"Вы вернулись к прошлому шагу \n {AddAccount.texts[previous.state]}")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return
        previous = step


@account_router.message(AddAccount.name, F.text)
async def add_name(message: types.Message, state: FSMContext, session: AsyncSession):
    logger.info(f"Пользователь {message.from_user.id} вводит название счета.")
    user_tg_id = message.from_user.id
    user_id = await orm_get_user(session, user_tg_id)

    data = await state.get_data()
    bank_id = data['bank_id']
    await delete_regular_messages(data, message)

    if message.text == '.' and AddAccount.account_for_change:
        await state.update_data(name=AddAccount.account_for_change.name)
    else:
        if len(message.text) > 50:
            bot_message = await message.answer("Название счета не должно превышать 50 символов.\nВведите заново")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return
        try:
            name = message.text

            if AddAccount.account_for_change and AddAccount.account_for_change.name == name:
                await state.update_data(name=name)
            else:
                check_name = await check_existing_account(session, name, user_id, bank_id)
                if check_name:
                    raise ValueError(f"Счет с именем '{name}' уже существует")

                await state.update_data(name=name)

        except ValueError as e:
            logger.error(f"Ошибка при вводе названия счета: {e}")
            bot_message = await message.answer("Ошибка. Пожалуйста, введите другое название:")
            await state.update_data(message_ids=[bot_message.message_id, message.message_id])
            return

    data = await state.get_data()
    account_name = data['name']

    bot_message = await message.answer(f'Введите баланс счета <b>"{account_name}"</b>')
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await state.set_state(AddAccount.balance)


@account_router.message(AddAccount.balance, F.text)
async def add_balance(message: types.Message, state: FSMContext, session: AsyncSession):
    logger.info(f"Пользователь {message.from_user.id} вводит баланс счета.")
    data = await state.get_data()
    await delete_regular_messages(data, message)

    if message.text == '.' and AddAccount.account_for_change:
        await state.update_data(balance=AddAccount.account_for_change.balance)
    else:
        try:
            if len(message.text) > 20:
                bot_message = await message.answer(
                    "Количество символов баланса счета не должно превышать 10 символов.\nВведите заново")
                await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                return

            await state.update_data(balance=float(message.text))

        except ValueError:
            logger.warning(f"Некорректное значение баланса счета: {message.text}")
            bot_message = await message.answer("Некорректное значение баланса, введите число, например, 123.45")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return

    data = await state.get_data()
    try:
        if AddAccount.account_for_change:
            await orm_update_account(session, data["account_id"], data)
        else:
            await orm_add_account(session, data)

        bot_message = await message.answer("Счет добавлен", reply_markup=types.ReplyKeyboardRemove())
        logger.info("Счет успешно добавлен.")
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
        await state.clear()

        await delete_bot_and_user_messages(data, message, bot_message)

    except Exception as e:
        logger.error(f"Ошибка при добавлении счета: {e}")
        await message.answer("Ошибка, обратитесь к @gigcomm, чтобы исправить ее!")
        await state.clear()

    AddAccount.account_for_change = None
