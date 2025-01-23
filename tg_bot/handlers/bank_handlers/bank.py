from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import (
    orm_add_bank,
    orm_delete_bank,
    orm_get_bank,
    orm_update_bank,
    orm_get_bank_by_id, check_existing_bank, orm_get_user)

from tg_bot.handlers.common_imports import *
from tg_bot.handlers.bank_handlers.account import account_router
from tg_bot.handlers.bank_handlers.currency import currency_router
from tg_bot.handlers.bank_handlers.deposit import deposit_router
from tg_bot.keyboards.delete_confirmation_keyboard import get_delete_confirmation_keyboard
from tg_bot.keyboards.inline import get_callback_btns, MenuCallBack
from tg_bot.keyboards.reply import get_keyboard

user_bank = {}

bank_router = Router()
bank_router.include_router(account_router)
bank_router.include_router(currency_router)
bank_router.include_router(deposit_router)

BANK_CANCEL_FSM = get_keyboard(
    "Отменить действие с банком",
    placeholder="Нажмите на кнопку ниже, чтобы отменить добавление/изменение",
)


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
    texts = {
        'AddBank:name': 'Введите новое название для банка',
    }


# # НАПИСАТЬ ДОПОЛНИТЕЛЬНОЕ ПОДВЕРЖДЕНИЕ НА УДАЛЕНИЕ
# @bank_router.callback_query(F.data.startswith('delete_bank'))
# async def delete_bank(callback: types.CallbackQuery):
#     bank_id = int(callback.data.split(":")[-1])
#     keyboard = get_delete_confirmation_keyboard(bank_id)
#     await callback.message.edit_text(
#         "Вы уверены, что хотите удалить банк? Это действие необратимо.",
#         reply_markup=keyboard
#     )
#     await callback.answer()

# @bank_router.callback_query(MenuCallBack.filter(F.action == "confirm_delete"))
# async def confirm_delete_bank(callback: types.CallbackQuery, session: AsyncSession, callback_data: MenuCallBack):
#     print(callback_data.action)
#     if callback_data.action == "confirm_delete":
#         bank_id = int(callback_data.bank_id)
#         await orm_delete_bank(session, bank_id)
#
#         await callback.answer("Банк удален")
#         await callback.message.answer("Банк удален")


@bank_router.callback_query(StateFilter(None), F.data.startswith('change_bank'))
async def change_bank(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    bank_id = int(callback.data.split(":")[-1])
    bank_for_change = await orm_get_bank_by_id(session, bank_id)

    AddBank.bank_for_change = bank_for_change

    await callback.answer()
    await callback.message.answer("Введите название банка", reply_markup=BANK_CANCEL_FSM)
    await state.set_state(AddBank.name)


@bank_router.callback_query(StateFilter(None), F.data.startswith('add_bank'))
async def add_bank(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите название банка", reply_markup=BANK_CANCEL_FSM)
    await state.set_state(AddBank.name)


@bank_router.message(StateFilter('*'), Command('Отменить действие с банком'))
@bank_router.message(StateFilter('*'), F.text.casefold() == 'отменить действие с банком')
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()
    await message.answer("Действия отменены", reply_markup=types.ReplyKeyboardRemove())


@bank_router.message(AddBank.name, or_f(F.text))
async def add_name(message: types.Message, state: FSMContext, session: AsyncSession):
    user_tg_id = message.from_user.id
    user_id = await orm_get_user(session, user_tg_id)

    if message.text == '.' and AddBank.bank_for_change:
        await state.update_data(name=AddBank.bank_for_change.name)
    else:
        if len(message.text) >= 150:
            await message.answer(
                "Название банка не должно превышать 150 символов. \n Введите заново"
            )
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
            await message.answer(f"Ошибка: {e}. Пожалуйста, введите другое название:")
            return

    data = await state.get_data()
    try:
        if AddBank.bank_for_change:
            await orm_update_bank(session, AddBank.bank_for_change.id, data)
        else:
            await orm_add_bank(session, data, message)
        await message.answer("Товар добавлен", reply_markup=types.ReplyKeyboardRemove())
        await state.clear()

    except Exception as e:
        print(f"Ошибка {e}")
        await message.answer(f"Ошибка, обратитесь к @gigcomm, чтобы исправить ее!")
        await state.clear()

    AddBank.bank_for_change = None
