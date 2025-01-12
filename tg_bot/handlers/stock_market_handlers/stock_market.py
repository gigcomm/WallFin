from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import (
    orm_add_stock_market,
    orm_delete_stock_market,
    orm_update_cryptomarket,
    orm_get_stock_market_by_id,
    orm_update_stock_market)

from tg_bot.handlers.common_imports import *
from tg_bot.handlers.stock_market_handlers.fund import fund_router
from tg_bot.handlers.stock_market_handlers.share import share_router
from tg_bot.keyboards.inline import get_callback_btns

stock_market_router = Router()
stock_market_router.include_router(share_router)
stock_market_router.include_router(fund_router)


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
        text="Выберете действие, предоставляемое финбиржей:",
        reply_markup=get_callback_btns(btns=buttons_stockmarket)
    )
    await callback_query.answer()


class AddStockMarket(StatesGroup):
    name = State()

    stock_market_for_change = None
    texts = {
        'AddStockMarket:name': 'Введите новое название для финбиржи',
    }


# НАПИСАТЬ ДОПОЛНИТЕЛЬНОЕ ПОДВЕРЖДЕНИЕ НА УДАЛЕНИЕ
@stock_market_router.callback_query(F.data.startswith('delete_stockmarket'))
async def delete_stock_market(callback: types.CallbackQuery, session: AsyncSession):
    stock_market_id = callback.data.split(":")[-1]
    await orm_delete_stock_market(session, int(stock_market_id))

    await callback.answer("Криптобиржа удалена")
    await callback.message.answer("Криптобиржа удалена")


@stock_market_router.callback_query(StateFilter(None), F.data.startswith('change_stockmarket'))
async def change_stock_market(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    stock_market_id = callback.data.split(":")[-1]
    stock_market_for_change = await orm_get_stock_market_by_id(session, int(stock_market_id))

    AddStockMarket.stock_market_for_change = stock_market_for_change

    await callback.answer()
    await callback.message.answer("Введите название финбиржи")
    await state.set_state(AddStockMarket.name)


@stock_market_router.callback_query(StateFilter(None), F.data.startswith('add_stockmarket'))
async def add_stock_market(message: types.Message, state: FSMContext):
    await message.answer("Введите название финбиржи")
    await state.set_state(AddStockMarket.name)


@stock_market_router.message(StateFilter('*'), Command('отмена финбиржи'))
@stock_market_router.message(StateFilter('*'), F.text.casefold() == 'отмена финбиржи')
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()
    await message.answer("Действия отменены")


@stock_market_router.message(AddStockMarket.name, or_f(F.text))
async def add_name(message: types.Message, state: FSMContext, session: AsyncSession):
    if message.text == '.' and AddStockMarket.stock_market_for_change:
        await state.update_data(name=AddStockMarket.stock_market_for_change.name)
    else:
        if len(message.text) >= 150:
            await message.answer(
                "Название финбиржи не должно превышать 150 символов. \n Введите заново"
            )
            return
        await state.update_data(name=message.text)

    data = await state.get_data()
    try:
        if AddStockMarket.stock_market_for_change:
            await orm_update_stock_market(session, AddStockMarket.stock_market_for_change.id, data)
        else:
            await orm_add_stock_market(session, data, message)
        await message.answer("Финбиржа добавлена")
        await state.clear()

    except Exception as e:
        await message.answer(f"Ошибка {e}, обратитесь к @gigcomm, чтобы исправить ее!")
        await state.clear()

    AddStockMarket.stock_market_for_change = None
