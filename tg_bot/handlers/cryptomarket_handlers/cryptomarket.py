from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import CryptoMarket
from database.orm_query import (
    orm_add_cryptomarket,
    orm_delete_cryptomarket,
    orm_update_cryptomarket,
    orm_get_cryptomarket_by_id, check_existing_cryptomarket)

from tg_bot.handlers.common_imports import *
from tg_bot.handlers.cryptomarket_handlers.cryptocurrency import cryptocurrency_router
from tg_bot.keyboards.inline import get_callback_btns
from tg_bot.keyboards.reply import get_keyboard

cryptomarket_router = Router()
cryptomarket_router.include_router(cryptocurrency_router)

CRYPTOMARKET_CANCEL_FSM = get_keyboard(
    "Отменить действие с криптобиржей",
    placeholder="Нажмите на кнопку ниже, чтобы отменить добавление/изменение",
)

# @cryptomarket_router.message(F.text == 'Криптобиржи')
# async def starting_at_cryptomarket(message: types.Message, session: AsyncSession):
#     cryptomarkets = await orm_get_cryptomarkets(session)
#
#     buttons_cryptomarket = {cryptomarket.name: "cryptomarket_" + str(cryptomarket.id) for cryptomarket in cryptomarkets}
#     await message.answer(
#         text="Выберете криптобиржу:",
#         reply_markup=get_callback_btns(btns=buttons_cryptomarket)
#     )


@cryptomarket_router.callback_query(lambda callback_query: callback_query.data.startswith("cryptomarket_"))
async def process_cryptomarket_selection(callback_query: CallbackQuery):
    cryptomarkets_id = int(callback_query.data.split(':')[-1].split('_')[-1])

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


# НАПИСАТЬ ДОПОЛНИТЕЛЬНОЕ ПОДВЕРЖДЕНИЕ НА УДАЛЕНИЕ
# @cryptomarket_router.callback_query(F.data.startswith('delete_cryptomarket'))
# async def delete_cryptomarket(callback: types.CallbackQuery, session: AsyncSession):
#     cryptomarket_id = callback.data.split(":")[-1]
#     await orm_delete_cryptomarket(session, int(cryptomarket_id))
#
#     await callback.answer("Криптобиржа удалена")
#     await callback.message.answer("Криптобиржа удалена")


@cryptomarket_router.callback_query(StateFilter(None), F.data.startswith('change_cryptomarket'))
async def change_cryptomarket(callback_query: CallbackQuery, state: FSMContext, session: AsyncSession):
    cryptomarket_id = int(callback_query.data.split(":")[-1])
    cryptomarket_for_change = await orm_get_cryptomarket_by_id(session, cryptomarket_id)

    AddCryptomarket.cryptomarket_for_change = cryptomarket_for_change

    await callback_query.answer()
    await callback_query.message.answer("Введите название криптобиржи", reply_markup=CRYPTOMARKET_CANCEL_FSM)
    await state.set_state(AddCryptomarket.name)


@cryptomarket_router.callback_query(StateFilter(None), F.data.startswith('add_cryptomarket'))
async def add_cryptomarket(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer("Введите название криптобиржи", reply_markup=CRYPTOMARKET_CANCEL_FSM)
    await state.set_state(AddCryptomarket.name)


@cryptomarket_router.message(StateFilter('*'), Command('Отменить действие с криптобиржей'))
@cryptomarket_router.message(StateFilter('*'), F.text.casefold() == 'отменить действие с криптобиржей')
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()
    await message.answer("Действия отменены", reply_markup=types.ReplyKeyboardRemove())


@cryptomarket_router.message(AddCryptomarket.name, or_f(F.text))
async def add_balance(message: types.Message, state: FSMContext, session: AsyncSession):
    if message.text == '.' and AddCryptomarket.cryptomarket_for_change:
        await state.update_data(name=AddCryptomarket.cryptomarket_for_change.name)
    else:
        if len(message.text) >= 150:
            await message.answer(
                "Название криптобиржи не должно превышать 150 символов. \n Введите заново"
            )
            return

        try:
            name = message.text

            if AddCryptomarket.cryptomarket_for_change and AddCryptomarket.cryptomarket_for_change.name == name:
                await state.update_data(name=name)
            else:
                check_name = await check_existing_cryptomarket(session, name)
                if check_name:
                    raise ValueError(f"Криптобиржа с именем '{name}' уже существует")

                await state.update_data(name=name)

        except ValueError as e:
            await message.answer(f"Ошибка: {e}. Пожалуйста, введите другое название:")
            return

    data = await state.get_data()
    try:
        if AddCryptomarket.cryptomarket_for_change:
            await orm_update_cryptomarket(session, AddCryptomarket.cryptomarket_for_change.id, data)
        else:
            await orm_add_cryptomarket(session, data, message)
        await message.answer("Криптобиржа добавлена", reply_markup=types.ReplyKeyboardRemove())
        await state.clear()

    except Exception as e:
        await message.answer(f"Ошибка, обратитесь к @gigcomm, чтобы исправить ее!")
        await state.clear()

    AddCryptomarket.cryptomarket_for_change = None
