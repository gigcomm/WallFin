from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import orm_add_account, orm_update_account, orm_get_account, check_existing_account
from tg_bot.handlers.common_imports import *
from tg_bot.keyboards.inline import get_callback_btns
from tg_bot.keyboards.reply import get_keyboard

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


# @account_router.callback_query(lambda callback_query: callback_query.data.startswith("accounts_"))
# async def process_account_selection(callback_query: CallbackQuery, session: AsyncSession):
#     bank_id = int(callback_query.data.split("_")[-1])
#
#     accounts = await orm_get_account(session, bank_id)
#
#     buttons = {account.name: str(account.id) for account in accounts}
#     buttons["Добавить счет"] = f"add_account_{bank_id}"
#     await callback_query.message.edit_text(
#         "Выберете счет:",
#         reply_markup=get_callback_btns(btns=buttons)
#     )
#     await callback_query.answer()


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


# @account_router.callback_query(F.data.startswith('delete_account'))
# async def delete_bank(callback: types.CallbackQuery, session: AsyncSession):
#     account_id = callback.data.split("_")[-1]
#     await orm_delete_account(session, int(account_id))
#
#     await callback.answer("Счет удален")
#     await callback.message.answer("Счет удален")


@account_router.callback_query(StateFilter(None), F.data.startswith('change_account'))
async def change_account(callback_query: CallbackQuery, state: FSMContext, session: AsyncSession):
    account_id = int(callback_query.data.split(":")[-1])
    await state.update_data(account_id=account_id)
    account_for_change = await orm_get_account(session, account_id)
    AddAccount.account_for_change = account_for_change

    await callback_query.answer()
    await callback_query.message.answer("В режиме изменения, если поставить точку, данное поле будет прежним,"
                                        " а процесс перейдет к следующему полю объекта. \n Введите название счета",
                                        reply_markup=ACCOUNT_CANCEL_AND_BACK_FSM)
    await state.set_state(AddAccount.name)


@account_router.callback_query(StateFilter(None), F.data.startswith('add_account'))
async def add_account(callback_query: CallbackQuery, state: FSMContext):
    bank_id = int(callback_query.data.split(':')[-1])
    await state.update_data(bank_id=bank_id)
    await callback_query.message.answer("Введите название счета", reply_markup=ACCOUNT_CANCEL_FSM)
    await state.set_state(AddAccount.name)


@account_router.message(StateFilter('*'), Command('Отменить действие со счетом'))
@account_router.message(StateFilter('*'), F.text.casefold() == 'отменить действие со счетом')
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return
    if AddAccount.account_for_change:
        AddAccount.account_for_change = None
    await state.clear()
    await message.answer("Действия отменены", reply_markup=types.ReplyKeyboardRemove())


@account_router.message(StateFilter('*'), Command('Назад к предыдущему шагу'))
@account_router.message(StateFilter('*'), F.text.casefold() == "назад к предыдущему шагу")
async def back_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()

    if current_state == AddAccount.name:
        await message.answer("Предыдущего шага нет, введите название счета или нажмите ниже на кнопку отмены")
        return

    previous = None
    for step in AddAccount.__all_states__:
        if step.state == current_state:
            await state.set_state(previous)
            await message.answer(f"Вы вернулись к прошлому шагу \n {AddAccount.texts[previous.state]}")
            return
        previous = step


@account_router.message(AddAccount.name, F.text)
async def add_name(message: types.Message, state: FSMContext, session: AsyncSession):
    if message.text == '.' and AddAccount.account_for_change:
        await state.update_data(name=AddAccount.account_for_change.name)
    else:
        if len(message.text) >= 150:
            await message.answer(
                "Название счета не должно превышать 150 символов. \n Введите заново"
            )
            return
        try:
            name = message.text.casefold()

            if AddAccount.account_for_change and AddAccount.account_for_change.name == name:
                await state.update_data(name=name)
            else:
                check_name = await check_existing_account(session, name)
                if check_name:
                    raise ValueError(f"Счет с именем '{name}' уже существует")

                await state.update_data(name=name)

        except ValueError as e:
            await message.answer(f"Ошибка: {e}. Пожалуйста, введите другое название:")
            return

    data = await state.get_state()
    account_name = data['name']
    await message.answer(f"Введите количество денег на балансе счета {account_name}")
    await state.set_state(AddAccount.balance)


@account_router.message(AddAccount.balance, F.text)
async def add_balance(message: types.Message, state: FSMContext, session: AsyncSession):
    if message.text == '.' and AddAccount.account_for_change:
        await state.update_data(balance=AddAccount.account_for_change.balance)
    else:
        try:
            balance = float(message.text)
            await state.update_data(balance=balance)
        except ValueError:
            await message.answer("Некорректное значение баланса, введите число.")
            return

    data = await state.get_data()
    try:
        if AddAccount.account_for_change:
            await orm_update_account(session, data["account_id"], data)
        else:
            await orm_add_account(session, data)
        await message.answer("Счет добавлен")
        await state.clear()

    except Exception as e:
        await message.answer(f"Ошибка {e}, обратитесь к @gigcomm, чтобы исправить ее!")
        await state.clear()

    AddAccount.account_for_change = None
