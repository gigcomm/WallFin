from datetime import datetime

from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import orm_add_deposit, orm_update_deposit, orm_get_deposit, check_existing_deposit, \
    orm_get_user
from tg_bot.handlers.common_imports import *
from tg_bot.keyboards.reply import get_keyboard
from tg_bot.logger import logger
from utils.message_utils import delete_regular_messages, delete_bot_and_user_messages

deposit_router = Router()

DEPOSIT_CANCEL_FSM = get_keyboard(
    "Отменить действие с вкладом",
    placeholder="Используйте кнопки ниже для отмены",
)

DEPOSIT_CANCEL_AND_BACK_FSM = get_keyboard(
    "Отменить действие с вкладом",
    "Назад к предыдущему шагу для вклада",
    placeholder="Используйте кнопки ниже для действий",
)


class AddDeposit(StatesGroup):
    deposit_id = State()
    bank_id = State()
    name = State()
    start_date = State()
    deposit_term = State()
    interest_rate = State()
    balance = State()

    deposit_for_change = None

    texts = {
        'AddDeposit:name': 'Введите название заново',
        'AddDeposit:start_date': 'Введите дату начала вклада заново',
        'AddDeposit:deposit_term': 'Введите срок вклада заново',
        'AddDeposit:interest_rate': 'Введите процентную ставку по вкладу заново',
        'AddDeposit:balance': 'Это последний стейт...'
    }


@deposit_router.callback_query(StateFilter(None), F.data.startswith("change_deposit"))
async def change_deposit(callback_query: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    logger.info(f"Пользователь {callback_query.from_user.id} начал изменение вклада.")
    deposit_id = int(callback_query.data.split(":")[-1])
    await state.update_data(deposit_id=deposit_id)
    deposit_for_change = await orm_get_deposit(session, deposit_id)

    AddDeposit.deposit_for_change = deposit_for_change

    keyboard_message = await callback_query.message.answer("В режиме изменения, если поставить точку, данное поле будет прежним,"
        "а процесс перейдет к следующему полю объекта.\nИзмените данные:",
        reply_markup=DEPOSIT_CANCEL_AND_BACK_FSM)
    bot_message = await callback_query.message.answer("Введите название вклада:")

    await state.update_data(keyboard_message_id=[keyboard_message.message_id], message_ids=[bot_message.message_id])

    await state.set_state(AddDeposit.name)


@deposit_router.callback_query(StateFilter(None), F.data.startswith("add_deposit"))
async def add_deposit(callback_query: CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь {callback_query.from_user.id} начал добавление вклада.")
    bank_id = int(callback_query.data.split(':')[-1])
    await state.update_data(bank_id=bank_id)

    keyboard_message = await callback_query.message.answer("Заполните данные:", reply_markup=DEPOSIT_CANCEL_FSM)

    bot_message = await callback_query.message.answer("Введите название вклада")
    await state.update_data(keyboard_message_id=[keyboard_message.message_id], message_ids=[bot_message.message_id])

    await state.set_state(AddDeposit.name)


@deposit_router.message(StateFilter('*'), Command('Отменить действие с вкладом'))
@deposit_router.message(StateFilter('*'), F.text.casefold() == 'отменить действие с вкладом')
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    logger.info(f"Пользователь {message.from_user.id} отменил действие со вкладом.")
    data = await state.get_data()
    await delete_regular_messages(data, message)

    current_state = await state.get_state()
    if current_state is None:
        return
    if AddDeposit.deposit_for_change:
        AddDeposit.deposit_for_change = None
    await state.clear()

    bot_message = await message.answer("Действия отменены", reply_markup=types.ReplyKeyboardRemove())
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await delete_bot_and_user_messages(data, message, bot_message)


@deposit_router.message(StateFilter('*'), Command("Назад к предыдущему шагу для вклада"))
@deposit_router.message(StateFilter('*'), F.text.casefold() == "назад к предыдущему шагу для вклада")
async def back_handler(message: types.Message, state: FSMContext) -> None:
    logger.info(f"Пользователь {message.from_user.id} вернулся к предыдущему шагу для изменения вклада.")
    data = await state.get_data()
    await delete_regular_messages(data, message)

    current_state = await state.get_state()

    if current_state == AddDeposit.name:
        bot_message = await message.answer("Предыдущего шага нет, введите название вклада или нажмите ниже на кнопку отмены")
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
        return

    previous = None
    for step in AddDeposit.__all_states__:
        if step.state == current_state:
            await state.set_state(previous)
            bot_message = await message.answer(f"Вы вернулись к прошлому шагу\n {AddDeposit.texts[previous.state]}")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return
        previous = step


@deposit_router.message(AddDeposit.name, F.text)
async def add_name(message: types.Message, state: FSMContext, session: AsyncSession):
    logger.info(f"Пользователь {message.from_user.id} вводит название вклада.")
    user_tg_id = message.from_user.id
    user_id = await orm_get_user(session, user_tg_id)

    data = await state.get_data()
    bank_id = data['bank_id']
    await delete_regular_messages(data, message)

    if message.text == '.' and AddDeposit.deposit_for_change:
        await state.update_data(name=AddDeposit.deposit_for_change.name)
    else:
        if len(message.text) > 50:
            bot_message = await message.answer("Название вклада не должно превышать 50 символов.\nВведите заново")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return

        try:
            name = message.text

            if AddDeposit.deposit_for_change and AddDeposit.deposit_for_change.name == name:
                await state.update_data(name=name)
            else:
                check_name = await check_existing_deposit(session, name, user_id, bank_id)
                if check_name:
                    raise ValueError(f"Вклад с именем '{name}' уже существует")

                await state.update_data(name=name)

        except ValueError as e:
            logger.error(f"Ошибка при вводе названия вклада: {e}")
            bot_message = await message.answer("Ошибка. Пожалуйста, введите другое название:")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return

    bot_message = await message.answer("Введите дату начала вклада в формате ДД.ММ.ГГ.")
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await state.set_state(AddDeposit.start_date)


@deposit_router.message(AddDeposit.name)
async def error(message: types.Message):
    await message.answer("Вы ввели не допустимые данные, введите текст названия вклада")


@deposit_router.message(AddDeposit.start_date, F.text)
async def add_start_date(message: types.Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} вводит дату начала открытия вклада.")
    data = await state.get_data()
    await delete_regular_messages(data, message)

    if message.text == '.' and AddDeposit.deposit_for_change:

        await state.update_data(start_date=AddDeposit.deposit_for_change.start_date)
    else:
        try:
            user_date = datetime.strptime(message.text, '%d.%m.%Y').date()
            current_date = datetime.today().date()
            if user_date > current_date:
                bot_message = await message.answer("Введенная дата не может быть в будущем.\nВведите прошедшую или сегодняшнюю дату.")
                await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                return

        except ValueError as e:
            logger.error(f"Ошибка при вводе даты начала открытия вклада: {e}")
            bot_message = await message.answer("Введенная дата неверного формата.\nВведите заново в формате ДД.ММ.ГГ.")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return

        await state.update_data(start_date=user_date)

    bot_message = await message.answer("Введите срок вклада числом (например ввод числа '6', означает вклад сроком на 6 месяцев)")
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await state.set_state(AddDeposit.deposit_term)


@deposit_router.message(AddDeposit.start_date)
async def error(message: types.Message):
    await message.answer("Вы ввели не допустимые данные, введите дату в формате xx.xx.20xx")


@deposit_router.message(AddDeposit.deposit_term, F.text)
async def add_deposit_term(message: types.Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} вводит срок вклада.")
    data = await state.get_data()
    await delete_regular_messages(data, message)

    try:
        if message.text == '.' and AddDeposit.deposit_for_change:
            await state.update_data(deposit_term=AddDeposit.deposit_for_change.deposit_term)
        else:
            if len(message.text) > 3:
                bot_message = await message.answer(
                    "Количество символов для срока вклада не должно превышать 3 символов.\nВведите заново")
                await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                return

            await state.update_data(deposit_term=int(message.text))

    except ValueError:
        logger.warning(f"Некорректное значение срока вклада: {message.text}")
        bot_message = await message.answer("Некорректное значение срока вклада, введите число, например, 12")
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
        return

    except Exception as e:
        logger.error(f"Ошибка при обновлении срока вклада для пользователя {message.from_user.id}: {e}")
        bot_message = await message.answer("Произошла ошибка при установке срока вклада. Попробуйте еще раз.")
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
        return

    bot_message = await message.answer("Введите процентную ставку")
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await state.set_state(AddDeposit.interest_rate)


@deposit_router.message(AddDeposit.deposit_term)
async def error(message: types.Message):
    await message.answer("Вы ввели не допустимые данные, введите срок вклада числом")


@deposit_router.message(AddDeposit.interest_rate, F.text)
async def add_interest_rate(message: types.Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} вводит процентную ставку вклада.")
    data = await state.get_data()
    await delete_regular_messages(data, message)

    try:
        if message.text == '.' and AddDeposit.deposit_for_change:
            await state.update_data(interest_rate=AddDeposit.deposit_for_change.interest_rate)
        else:
            if len(message.text) > 7:
                bot_message = await message.answer(
                    "Количество символов для процентой ставки вклада не должно превышать 7 символов.\nВведите заново")
                await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                return

            await state.update_data(interest_rate=float(message.text))

    except ValueError:
        logger.warning(f"Некорректное значение процентной ставки вклада: {message.text}")
        bot_message = await message.answer("Некорректное значение процентной ставки, введите число, например, 12.34")
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
        return

    except Exception as e:
        logger.error(f"Ошибка при обновлении процентной ставки вклада для пользователя {message.from_user.id}: {e}")
        bot_message = await message.answer("Произошла ошибка при установке процентной ставки вклада. Попробуйте еще раз.")
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
        return

    bot_message = await message.answer("Введите сумму вклада")
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await state.set_state(AddDeposit.balance)


@deposit_router.message(AddDeposit.interest_rate)
async def error(message: types.Message):
    await message.answer("Вы ввели не допустимые данные, введите процент по вкладу числом")


@deposit_router.message(AddDeposit.balance, F.text)
async def add_balance(message: types.Message, state: FSMContext, session: AsyncSession):
    logger.info(f"Пользователь {message.from_user.id} вводит баланс вклада.")
    data = await state.get_data()
    await delete_regular_messages(data, message)

    if message.text == '.' and AddDeposit.deposit_for_change:
        await state.update_data(balance=AddDeposit.deposit_for_change.balance)
    else:
        try:
            if len(message.text) > 20:
                bot_message = await message.answer(
                    "Количество символов для баланса вклада не должно превышать 20 символов.\nВведите заново")
                await state.update_data(message_ids=[message.message_id, bot_message.message_id])
                return

            await state.update_data(balance=float(message.text))

        except ValueError:
            logger.warning(f"Некорректное значение баланса вклада: {message.text}")
            bot_message = await message.answer("Некорректное значение баланса, введите число, например 123.45.")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return

    data = await state.get_data()
    try:
        if AddDeposit.deposit_for_change:
            await orm_update_deposit(session, int(data["deposit_id"]), data)
        else:
            await orm_add_deposit(session, data)
        bot_message = await message.answer("Вклад добавлен/изменен", reply_markup=types.ReplyKeyboardRemove())
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
        await state.clear()

        await delete_bot_and_user_messages(data, message, bot_message)

    except Exception as e:
        logger.error(f"Ошибка при добавлении вклада: {e}")
        await message.answer("Ошибка, обратитесь к @gigcomm, чтобы исправить ее!")
        await state.clear()

    AddDeposit.deposit_for_change = None


@deposit_router.message(AddDeposit.balance)
async def error(message: types.Message):
    await message.answer("Вы ввели не допустимые данные, введите число (например 50000)")
