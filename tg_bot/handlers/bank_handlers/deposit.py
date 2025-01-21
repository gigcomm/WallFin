from datetime import datetime

from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import orm_add_deposit, orm_update_deposit, orm_get_deposit, check_existing_deposit
from tg_bot.handlers.common_imports import *
from tg_bot.keyboards.reply import get_keyboard

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


# @deposit_router.callback_query(lambda callback_query: callback_query.data.startswith("deposits_"))
# async def process_deposit_selection(callback_query: CallbackQuery, session: AsyncSession):
#     bank_id = int(callback_query.data.split("_")[-1])
#     print("BANK_ID",bank_id)
#     deposits = await orm_get_deposit(session, bank_id)
#
#     buttons = {deposit.name: str(deposit.id) for deposit in deposits}
#     buttons["Добавить вклад"] = f"add_deposit_{bank_id}"
#     await callback_query.message.edit_text(
#         "Выберете вклад:",
#         reply_markup=get_callback_btns(btns=buttons)
#     )
#     await callback_query.answer()


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


# @deposit_router.callback_query(F.data.startswith("delete_deposit"))
# async def delete_deposit(callback_query: types.CallbackQuery, session: AsyncSession):
#     deposit_id = callback_query.data.split("_")[-1]
#     await orm_delete_deposit(session, int(deposit_id))
#
#     await callback_query.answer("Вклад удален")
#     await callback_query.message.answer("Вклад удален")


@deposit_router.callback_query(StateFilter(None), F.data.startswith("change_deposit"))
async def change_currency(callback_query: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    deposit_id = int(callback_query.data.split(":")[-1])
    await state.update_data(deposit_id=deposit_id)
    deposit_for_change = await orm_get_deposit(session, deposit_id)
    AddDeposit.deposit_for_change = deposit_for_change

    await callback_query.answer()
    await callback_query.message.answer("Введите название вклада:", reply_markup=DEPOSIT_CANCEL_AND_BACK_FSM)
    await state.set_state(AddDeposit.name)


@deposit_router.callback_query(StateFilter(None), F.data.startswith("add_deposit"))
async def add_deposit(callback_query: CallbackQuery, state: FSMContext):
    bank_id = int(callback_query.data.split(':')[-1])
    await state.update_data(bank_id=bank_id)
    await callback_query.message.answer("Введите название вклада", reply_markup=DEPOSIT_CANCEL_FSM)
    await state.set_state(AddDeposit.name)


@deposit_router.message(StateFilter('*'), Command('Отменить действие с вкладом'))
@deposit_router.message(StateFilter('*'), F.text.casefold() == 'отменить действие с вкладом')
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return
    if AddDeposit.deposit_for_change:
        AddDeposit.deposit_for_change = None
    await state.clear()
    await message.answer("Действия отменены", reply_markup=types.ReplyKeyboardRemove())


@deposit_router.message(StateFilter('*'), Command("Назад к предыдущему шагу для вклада"))
@deposit_router.message(StateFilter('*'), F.text.casefold() == "назад к предыдущему шагу для вклада")
async def back_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()

    if current_state == AddDeposit.name:
        await message.answer("Предыдущего шага нет, введите название вклада или нажмите ниже на кнопку отмены")
        return

    previous = None
    for step in AddDeposit.__all_states__:
        if step.state == current_state:
            await state.set_state(previous)
            await message.answer(f"Вы вернулись к прошлому шагу \n {AddDeposit.texts[previous.state]}")
            return
        previous = step


@deposit_router.message(AddDeposit.name, F.text)
async def add_name(message: types.Message, state: FSMContext, session: AsyncSession):
    if message.text == '.' and AddDeposit.deposit_for_change:
        await state.update_data(name=AddDeposit.deposit_for_change.name)
    else:
        if len(message.text) >= 150:
            await message.answer(
                "Название вклада не должно превышать 150 символов. \n Введите заново"
            )
            return

        try:
            name = message.text

            if AddDeposit.deposit_for_change and AddDeposit.deposit_for_change.name == name:
                await state.update_data(name=name)
            else:
                check_name = await check_existing_deposit(session, name)
                if check_name:
                    raise ValueError(f"Вклад с именем '{name}' уже существует")

                await state.update_data(name=name)

        except ValueError as e:
            await message.answer(f"Ошибка: {e}. Пожалуйста, введите другое название:")
            return

    await message.answer(f"Введите дату начала вклада в формате ДД.ММ.ГГ.")
    await state.set_state(AddDeposit.start_date)


@deposit_router.message(AddDeposit.name)
async def error(message: types.Message):
    await message.answer("Вы ввели не допустимые данные, введите текст названия вклада")


@deposit_router.message(AddDeposit.start_date, F.text)
async def add_start_date(message: types.Message, state: FSMContext):
    print(AddDeposit.deposit_for_change)
    if message.text == '.' and AddDeposit.deposit_for_change:

        await state.update_data(start_date=AddDeposit.deposit_for_change.start_date)
    else:
        try:
            user_date = datetime.strptime(message.text, '%d.%m.%Y').date()
            current_date = datetime.today().date()
            if user_date > current_date:
                await message.answer(
                    "Введенная дата не может быть в будущем. \nВведите прошедшую или сегодняшнюю дату."
                )
                return
        except ValueError:
            await message.answer(
                "Введенная дата неверного формата. \nВведите заново в формате ДД.ММ.ГГ."
            )
            return

        await state.update_data(start_date=user_date)
    await message.answer("Введите срок вклада числом (например 6, означает вклад сроком на 6 месяцев)")
    await state.set_state(AddDeposit.deposit_term)


@deposit_router.message(AddDeposit.start_date)
async def error(message: types.Message):
    await message.answer("Вы ввели не допустимые данные, введите дату в формате xx.xx.20xx")


@deposit_router.message(AddDeposit.deposit_term, F.text)
async def add_deposit_term(message: types.Message, state: FSMContext):
    if message.text == '.' and AddDeposit.deposit_for_change:
        await state.update_data(deposit_term=AddDeposit.deposit_for_change.deposit_term)
    else:
        await state.update_data(deposit_term=message.text)
    await message.answer("Введите процентную ставку")
    await state.set_state(AddDeposit.interest_rate)


@deposit_router.message(AddDeposit.deposit_term)
async def error(message: types.Message):
    await message.answer("Вы ввели не допустимые данные, введите срок вклада числом")


@deposit_router.message(AddDeposit.interest_rate, F.text)
async def add_interest_rate(message: types.Message, state: FSMContext):
    if message.text == '.' and AddDeposit.deposit_for_change:
        await state.update_data(interest_rate=AddDeposit.deposit_for_change.interest_rate)
    else:
        await state.update_data(interest_rate=message.text)
    await message.answer("Введите сумму вклада")
    await state.set_state(AddDeposit.balance)


@deposit_router.message(AddDeposit.interest_rate)
async def error(message: types.Message):
    await message.answer("Вы ввели не допустимые данные, введите процент по вкладу числом")


@deposit_router.message(AddDeposit.balance, F.text)
async def add_balance(message: types.Message, state: FSMContext, session: AsyncSession):
    if message.text == '.' and AddDeposit.deposit_for_change:
        await state.update_data(balance=AddDeposit.deposit_for_change.balance)
    else:
        try:
            dep_balance = float(message.text)
            await state.update_data(balance=dep_balance)
        except ValueError:
            await message.answer("Некорректное значение баланса, введите число.")
            return

    data = await state.get_data()
    try:
        if AddDeposit.deposit_for_change:
            await orm_update_deposit(session, int(data["deposit_id"]), data)
        else:
            await orm_add_deposit(session, data)
        await message.answer("Вклад добавлен/изменен", reply_markup=types.ReplyKeyboardRemove())
        await state.clear()

    except Exception as e:
        await message.answer(f"Ошибка {e}, обратитесь к @gigcomm, чтобы исправить ее!")
        await state.clear()

    AddDeposit.deposit_for_change = None


@deposit_router.message(AddDeposit.balance)
async def error(message: types.Message):
    await message.answer("Вы ввели не допустимые данные, введите число (например 50000)")
