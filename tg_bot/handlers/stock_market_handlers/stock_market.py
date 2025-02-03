from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import (
    orm_add_stock_market,
    orm_get_stock_market_by_id,
    orm_update_stock_market,
    check_existing_stock_market,
    orm_get_user)

from tg_bot.handlers.common_imports import *
from tg_bot.handlers.stock_market_handlers.fund import fund_router
from tg_bot.handlers.stock_market_handlers.share import share_router
from tg_bot.keyboards.inline import get_callback_btns
from tg_bot.keyboards.reply import get_keyboard
from utils.message_utils import delete_regular_messages, delete_bot_and_user_messages

stock_market_router = Router()
stock_market_router.include_router(share_router)
stock_market_router.include_router(fund_router)

STOCKMARKET_CANCEL_FSM = get_keyboard(
    "Отменить действие с фодовой биржей",
    placeholder="Нажмите на кнопку ниже, чтобы отменить добавление/изменение",
)

# @stock_market_router.message(F.text == 'Финбиржи')
# async def starting_at_stockmarket(message: types.Message, session: AsyncSession):
#     stockmarkets = await orm_get_stock_markets(session)
#
#     buttons_stockmarket = {stockmarket.name: "stockmarket_" + str(stockmarket.id) for stockmarket in stockmarkets}
#     await message.answer(
#         text="Выберете финбиржу:",
#         reply_markup=get_callback_btns(btns=buttons_stockmarket)
#     )


@stock_market_router.callback_query(lambda callback_query: callback_query.data.startswith("stockmarket_"))
async def process_stockmarket_selection(callback_query: CallbackQuery):
    stockmarket_id = int(callback_query.data.split(':')[-1].split('_')[-1])
    buttons_stockmarket = {
        "Ваши акции": f"share_{stockmarket_id}",
        "Ваши фонды": f"fund_{stockmarket_id}"
    }

    await callback_query.message.edit_text(
        text="Выберете действие, предоставляемое фодовой биржей:",
        reply_markup=get_callback_btns(btns=buttons_stockmarket)
    )
    await callback_query.answer()


class AddStockMarket(StatesGroup):
    name = State()

    stock_market_for_change = None
    texts = {
        'AddStockMarket:name': 'Введите новое название для фодовой биржи',
    }


# НАПИСАТЬ ДОПОЛНИТЕЛЬНОЕ ПОДВЕРЖДЕНИЕ НА УДАЛЕНИЕ
# @stock_market_router.callback_query(F.data.startswith('delete_stockmarket'))
# async def delete_stock_market(callback: types.CallbackQuery, session: AsyncSession):
#     stock_market_id = callback.data.split(":")[-1]
#     await orm_delete_stock_market(session, int(stock_market_id))
#
#     await callback.answer("Криптобиржа удалена")
#     await callback.message.answer("Криптобиржа удалена")


@stock_market_router.callback_query(StateFilter(None), F.data.startswith('change_stockmarket'))
async def change_stock_market(callback_query: CallbackQuery, state: FSMContext, session: AsyncSession):
    stock_market_id = int(callback_query.data.split(":")[-1])
    stock_market_for_change = await orm_get_stock_market_by_id(session, stock_market_id)

    AddStockMarket.stock_market_for_change = stock_market_for_change

    keyboard_message = await callback_query.message.answer(
        "В режиме изменения, если поставить точку, данное поле будет прежним,"
        "а процесс перейдет к следующему полю объекта.\nИзмените данные:",
        reply_markup=STOCKMARKET_CANCEL_FSM)
    bot_message = await callback_query.message.answer("Введите название фодовой биржи")
    await state.update_data(keyboard_message_id=[keyboard_message.message_id], message_ids=[bot_message.message_id])

    await state.set_state(AddStockMarket.name)


@stock_market_router.callback_query(StateFilter(None), F.data.startswith('add_stockmarket'))
async def add_stock_market(callback_query: CallbackQuery, state: FSMContext):
    keyboard_message = await callback_query.message.answer("Заполните данные:", reply_markup=STOCKMARKET_CANCEL_FSM)
    bot_message = await callback_query.message.answer("Введите название фодовой биржи")
    await state.update_data(keyboard_message_id=[keyboard_message.message_id], message_ids=[bot_message.message_id])

    await state.set_state(AddStockMarket.name)


@stock_market_router.message(StateFilter('*'), Command('Отменить действие с фодовой биржей'))
@stock_market_router.message(StateFilter('*'), F.text.casefold() == 'отменить действие с фодовой биржей')
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()

    await delete_regular_messages(data, message)

    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()
    bot_message = await message.answer("Действия отменены", reply_markup=types.ReplyKeyboardRemove())
    await state.update_data(message_ids=[message.message_id, bot_message.message_id])

    await delete_bot_and_user_messages(data, message, bot_message)

@stock_market_router.message(AddStockMarket.name, or_f(F.text))
async def add_name(message: types.Message, state: FSMContext, session: AsyncSession):
    user_tg_id = message.from_user.id
    user_id = await orm_get_user(session, user_tg_id)

    data = await state.get_data()

    await delete_regular_messages(data, message)

    if message.text == '.' and AddStockMarket.stock_market_for_change:
        await state.update_data(name=AddStockMarket.stock_market_for_change.name)
    else:
        if len(message.text) >= 50:
            bot_message = await message.answer("Название финбиржи не должно превышать 50 символов. \n Введите заново")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return

        try:
            name = message.text

            if AddStockMarket.stock_market_for_change and AddStockMarket.stock_market_for_change.name == name:
                await state.update_data(name=name)
            else:
                check_name = await check_existing_stock_market(session, name, user_id)
                if check_name:
                    raise ValueError(f"Фондовая биржа с именем '{name}' уже существует")

                await state.update_data(name=name)

        except ValueError as e:
            bot_message = await message.answer(f"Ошибка: {e}. Пожалуйста, введите другое название:")
            await state.update_data(message_ids=[message.message_id, bot_message.message_id])
            return

    data = await state.get_data()
    try:
        if AddStockMarket.stock_market_for_change:
            await orm_update_stock_market(session, AddStockMarket.stock_market_for_change.id, data)
        else:
            await orm_add_stock_market(session, data, message)

        bot_message = await message.answer("Фондовая биржа добавлена", reply_markup=types.ReplyKeyboardRemove())
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
        await state.clear()

        await delete_bot_and_user_messages(data, message, bot_message)

    except Exception as e:
        print(f"Ошибка {e}")
        await message.answer(f"Ошибка, обратитесь к @gigcomm, чтобы исправить ее!")
        await state.clear()

    AddStockMarket.stock_market_for_change = None
