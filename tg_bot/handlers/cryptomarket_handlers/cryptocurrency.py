from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import (
    orm_add_cryptocurrency,
    orm_get_cryptocurrency_by_cryptomarket_id,
    orm_update_cryptocurrency)

from tg_bot.handlers.common_imports import *
from parsers.Bybit_API import get_price_cryptocurrency

cryptocurrency_router = Router()


class AddСryptocurrency(StatesGroup):
    cryptocurrency_id = State()
    cryptomarket_id = State()
    name = State()
    balance = State()
    purchase_price = State()
    selling_price = State()
    market_price = State()

    cryptocurrency_for_change = None
    texts = {
        'AddСryptocurrency:name': 'Введите название заново',
        'AddСryptocurrency:balance': 'Введите баланс заново',
        'AddСryptocurrency:purchase_price': 'Введите цену покупки заново',
        'AddСryptocurrency:selling_price': 'Введите цену продажи заново',
        'AddСryptocurrency:market_price': 'Это последний стейт...',
    }


@cryptocurrency_router.callback_query(StateFilter(None), F.data.startswith("change_cryptocurrency"))
async def change_cryptocurrency(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    cryptocurrency_id = callback.data.split(":")[-1]
    cryptocurrency_for_change = await orm_get_cryptocurrency_by_cryptomarket_id(session, int(cryptocurrency_id))
    await state.update_data(cryptocurrency_id=cryptocurrency_id)
    AddСryptocurrency.cryptocurrency_for_change = cryptocurrency_for_change

    await callback.answer()
    await callback.message.answer("Введите название криптовалюты")
    await state.set_state(AddСryptocurrency.name)


@cryptocurrency_router.callback_query(StateFilter(None), F.data.startswith("add_cryptocurrency"))
async def add_cryptomarket(callback_query: CallbackQuery, state: FSMContext):
    cryptomarket_id = int(callback_query.data.split(":")[-1])
    await state.update_data(cryptomarket_id=cryptomarket_id)
    await callback_query.message.answer(
        "Введите название криптовалюты в сокращенном виде, например BTC")
    await state.set_state(AddСryptocurrency.name)


@cryptocurrency_router.message(StateFilter('*'), Command("отмена криптовалюты"))
@cryptocurrency_router.message(StateFilter('*'), F.text.casefold() == "отмена криптовалюты")
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return
    if AddСryptocurrency.cryptocurrency_for_change:
        AddСryptocurrency.cryptocurrency_for_change = None
    await state.clear()
    await message.answer("Действия отменены")


@cryptocurrency_router.message(StateFilter('*'), Command("назад криптовалюты"))
@cryptocurrency_router.message(StateFilter('*'), F.text.casefold() == "назад криптовалюты")
async def back_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()

    if current_state is None:
        await message.answer("Предыдущего шага нет, введите название счета или напишите 'отмена'")
        return

    previous = None
    for step in AddСryptocurrency.__all_states__:
        if step.state == current_state:
            await state.set_state(previous)
            await message.answer(f"Вы вернулись к прошлому шагу \n {AddСryptocurrency.texts[previous.state]}")
            return
        previous = step


@cryptocurrency_router.message(AddСryptocurrency.name, F.text)
async def add_name(message: types.Message, state: FSMContext):
    if message.text == '.' and AddСryptocurrency.cryptocurrency_for_change:
        await state.update_data(name=AddСryptocurrency.cryptocurrency_for_change.name)
    else:
        if len(message.text) >= 5:
            await message.answer(
                "Название криптовалюты не должно превышать 5 символов. \n Введите заново"
            )
            return
        await state.update_data(name=message.text.upper())
    await message.answer("Введите количество криптовалюты")
    await state.set_state(AddСryptocurrency.balance)


@cryptocurrency_router.message(AddСryptocurrency.balance, F.text)
async def add_balance(message: types.Message, state: FSMContext):
    if message.text == '.' and AddСryptocurrency.cryptocurrency_for_change:
        await state.update_data(balance=AddСryptocurrency.cryptocurrency_for_change.balance)
    else:
        try:
            cryptocurrency_balance = float(message.text)
            await state.update_data(balance=cryptocurrency_balance)
        except ValueError:
            await message.answer("Некорректное значение баланса, введите число.")
            return

    await message.answer("Введите цену покупки криптовалюты")
    await state.set_state(AddСryptocurrency.purchase_price)


@cryptocurrency_router.message(AddСryptocurrency.purchase_price, F.text)
async def add_purchase_price(message: types.Message, state: FSMContext):
    if message.text == '.' and AddСryptocurrency.cryptocurrency_for_change:
        await state.update_data(purchase_price=AddСryptocurrency.cryptocurrency_for_change.purchase_price)
    else:
        await state.update_data(purchase_price=message.text)
    await message.answer("Введите цену продажи криптовалюты")
    await state.set_state(AddСryptocurrency.selling_price)


@cryptocurrency_router.message(AddСryptocurrency.selling_price, F.text)
async def add_selling_price(message: types.Message, state: FSMContext):
    if message.text == '.' and AddСryptocurrency.cryptocurrency_for_change:
        await state.update_data(selling_price=AddСryptocurrency.cryptocurrency_for_change.selling_price)
    else:
        await state.update_data(selling_price=message.text)
    await message.answer(
        "Введите цену криптовалюты на криптобирже или введите слово 'авто' для автоматического определения "
        "текущей цены криптовалюты")
    await state.set_state(AddСryptocurrency.market_price)


@cryptocurrency_router.message(AddСryptocurrency.market_price, F.text)
async def add_market_price(message: types.Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    cryptocur_name = data['name'] + "USDT"

    if message.text == '.' and AddСryptocurrency.cryptocurrency_for_change:
        await state.update_data(market_price=AddСryptocurrency.cryptocurrency_for_change.market_price)
    else:
        market_price = message.text
        if market_price.casefold() == 'авто':
            try:
                auto_market_price = get_price_cryptocurrency(cryptocur_name)
                if auto_market_price is None:
                    await message.answer("Введите корректное числовое значение для цены криптовалюты")
                    return
                await state.update_data(market_price=auto_market_price)
                await message.answer(
                    f"Курс {cryptocur_name} на криптобирже автоматически установлен: {auto_market_price}")
            except Exception as e:
                await message.answer(f"Не удалось получить цену криптовалюты: {e}")
                return
        else:
            try:
                market_price = float(market_price)
                await state.update_data(market_price=market_price)
            except ValueError:
                await message.answer("Введите корректное числовое значение для цены криптовалюты")
                return

    data = await state.get_data()
    try:
        if AddСryptocurrency.cryptocurrency_for_change:
            await orm_update_cryptocurrency(session, data["cryptocurrency_id"], data)
        else:
            await orm_add_cryptocurrency(session, data)
        await message.answer(f"Криптовалюта {cryptocur_name} добавлена")
        await state.clear()

    except Exception as e:
        await message.answer(f"Ошибка {e}, обратитесь к @gigcomm, чтобы исправить ее!")
        await state.clear()

    AddСryptocurrency.cryptocurrency_for_change = None
