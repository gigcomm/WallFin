from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import orm_add_bank, orm_delete_bank, orm_get_bank, orm_update_bank
from tg_bot.handlers.common_imports import *
from tg_bot.handlers.bank_handlers.account import account_router
from tg_bot.handlers.bank_handlers.currency import currency_router
from tg_bot.handlers.bank_handlers.deposit import deposit_router
from tg_bot.handlers.user_private import menu_command
from tg_bot.keyboards.inline import get_callback_btns

user_bank = {}

bank_router = Router()
bank_router.include_router(account_router)
bank_router.include_router(currency_router)
bank_router.include_router(deposit_router)


@bank_router.message(F.text == "Банки")
async def starting_at_bank(message: types.Message, session: AsyncSession):
    banks = await orm_get_bank(session, message.from_user.id)

    buttons_bank = {bank.name: "bank_" + str(bank.id) for bank in banks}
    await message.answer(
        text="Выберите банк:",
        reply_markup=get_callback_btns(btns=buttons_bank)
    )


@bank_router.callback_query(lambda callback_query: callback_query.data.startswith("bank_"))
async def process_bank_selection(callback_query: types.CallbackQuery):
    bank_id = int(callback_query.data.split('_')[-1])
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


# FSM Bank
class AddBank(StatesGroup):
    name = State()

    bank_for_change = None


# НАПИСАТЬ ДОПОЛНИТЕЛЬНОЕ ПОДВЕРЖДЕНИЕ НА УДАЛЕНИЕ
@bank_router.callback_query(F.data.startswith('delete_bank'))
async def delete_bank(callback: types.CallbackQuery, session: AsyncSession):
    bank_id = callback.data.split("_")[-1]
    await orm_delete_bank(session, int(bank_id))

    await callback.answer("Банк удален")
    await callback.message.answer("Банк удален")


@bank_router.callback_query(StateFilter(None), F.data.startswith('change_bank'))
async def change_bank(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    bank_id = callback.data.split("_")[-1]
    bank_for_change = await orm_get_bank(session, int(bank_id))

    AddBank.bank_for_change = bank_for_change

    await callback.answer()
    await callback.message.answer("Введите название банка")
    await state.set_state(AddBank.name)


@bank_router.callback_query(StateFilter(None), F.data.startswith('add_bank'))
async def add_bank(message: types.Message, state: FSMContext):
    await message.answer("Введите название банка")
    await state.set_state(AddBank.name)


@bank_router.message(StateFilter('*'), Command('отмена банка'))
@bank_router.message(StateFilter('*'), F.text.casefold() == 'отмена банка')
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()
    await message.answer("Действия отменены")


@bank_router.message(AddBank.name, or_f(F.text, F.text == '.'))
async def add_name(message: types.Message, state: FSMContext, session: AsyncSession):
    if message.text == '.' and AddBank.bank_for_change:
        await state.update_data(name=AddBank.bank_for_change.name)
    else:
        if len(message.text) >= 150:
            await message.answer(
                "Название банка не должно превышать 150 символов. \n Введите заново"
            )
            return
        await state.update_data(name=message.text)
    data = await state.get_data()
    try:
        if AddBank.bank_for_change:
            await orm_update_bank(session, AddBank.bank_for_change.id, data)
        else:
            await orm_add_bank(session, data, message)
        await message.answer("Товар добавлен")
        await state.clear()

    except Exception as e:
        await message.answer(f"Ошибка {e}, обратитесь к @gigcomm, чтобы исправить ее!")
        await state.clear()

    AddBank.bank_for_change = None
