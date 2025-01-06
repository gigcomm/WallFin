from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import orm_add_fund, orm_get_fund, orm_update_fund
from tg_bot.handlers.common_imports import *
from parsers.tinkoff_invest_API import get_price_fund
from tg_bot.keyboards.inline import get_callback_btns

fund_router = Router()


# @fund_router.callback_query(lambda callback_query: callback_query.data.startswith("fund_"))
# async def process_account_selection(callback_query: CallbackQuery, session: AsyncSession):
#     stockmarket_id = int(callback_query.data.split("_")[-1])
#
#     funds = await orm_get_fund(session, stockmarket_id)
#
#     buttons = {fund.name: str(fund.id) for fund in funds}
#     buttons["Добавить фонд"] = f"add_fund_{stockmarket_id}"
#     await callback_query.message.edit_text(
#         "Выберете фонд:",
#         reply_markup=get_callback_btns(btns=buttons),
#     )
#     await callback_query.answer()


class AddFund(StatesGroup):
    stockmarket_id = State()
    name = State()
    purchase_price = State()
    selling_price = State()
    market_price = State()
    currency = State()
    quantity = State()

    fund_for_change = None
    texts = {
        'AddFund:name': 'Введите название заново',
        'AddFund:purchase_price': 'Введите цена покупки заново',
        'AddFund:selling_price': 'Введите цену продажи заново',
        'AddFund:market_price': 'Введите цену на бирже заново',
        'AddFund: currency': 'Введите наименование валюты для акции(например, RUB, USD, EUR):',
        'AddFund:quantity': 'Это последний стейт...',
    }


# @fund_router.callback_query(F.data.startswith('delete_'))
# async def delete_fund(callback: types.CallbackQuery, session: AsyncSession):
#     fund_id = callback.data.split("_")[-1]
#     await orm_delete_fund(session, int(fund_id))
#
#     await callback.answer("Бумага фонда удалена")
#     await callback.message.answer("Бумага фонда удалена")


@fund_router.callback_query(StateFilter(None), F.data.startswith('change_fund'))
async def change_fund(callback_query: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    fund_id = callback_query.data.split(":")[-1]
    await state.update_data(fund_id=fund_id)
    fund_for_change = await orm_get_fund(session, int(fund_id))
    AddFund.fund_for_change = None

    AddFund.fund_for_change = fund_for_change

    await callback_query.answer()
    await callback_query.message.answer("Введите тикер фонда, например, TITR")
    await state.set_state(AddFund.name)


@fund_router.callback_query(StateFilter(None), F.data.startswith('add_fund'))
async def add_cryptomarket(callback_query: CallbackQuery, state: FSMContext):
    stockmarket_id = int(callback_query.data.split(":")[-1])
    await state.update_data(stockmarket_id=stockmarket_id)
    await callback_query.message.answer(
        "Введите тикер фонда, например, TITR", reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(AddFund.name)


@fund_router.message(StateFilter('*'), Command('отмена фонда'))
@fund_router.message(StateFilter('*'), F.text.casefold() == 'отмена фонда')
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return
    if AddFund.fund_for_change:
        AddFund.fund_for_change = None
    await state.clear()
    await message.answer("Действия отменены")


@fund_router.message(StateFilter('*'), Command('назад фонда'))
@fund_router.message(StateFilter('*'), F.text.casefold() == "назад фонда")
async def back_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()

    if current_state is None:
        await message.answer("Предыдущего шага нет, введите название счета или напишите 'отмена'")
        return

    previous = None
    for step in AddFund.__all_states__:
        if step.state == current_state:
            await state.set_state(previous)
            await message.answer(f"Вы вернулись к прошлому шагу \n {AddFund.texts[previous.state]}")
            return
        previous = step


@fund_router.message(AddFund.name, F.text)
async def add_name(message: types.Message, state: FSMContext):
    if message.text == '.' and AddFund.fund_for_change:
        await state.update_data(name=AddFund.fund_for_change.name)
    else:
        if len(message.text) >= 150:
            await message.answer(
                "Название фонда не должно превышать 150 символов. \n Введите заново"
            )
            return
        await state.update_data(name=message.text.upper())
    await message.answer("Введите цену покупки фонда")
    await state.set_state(AddFund.purchase_price)


@fund_router.message(AddFund.purchase_price, F.text)
async def add_purchase_price(message: types.Message, state: FSMContext):
    if message.text == '.' and AddFund.fund_for_change:
        await state.update_data(purchase_price=AddFund.fund_for_change.purchase_price)
    else:
        await state.update_data(purchase_price=message.text)
    await message.answer("Введите цену продажи фонда")
    await state.set_state(AddFund.selling_price)


@fund_router.message(AddFund.selling_price, F.text)
async def add_selling_price(message: types.Message, state: FSMContext):
    if message.text == '.' and AddFund.fund_for_change:
        await state.update_data(selling_price=AddFund.fund_for_change.selling_price)
    else:
        await state.update_data(selling_price=message.text)
    await message.answer(
        "Введите цену фонда на финбирже или введите слово 'авто' для автоматического определения текущей цены фонда")
    await state.set_state(AddFund.market_price)


@fund_router.message(AddFund.market_price, F.text)
async def add_market_price(message: types.Message, state: FSMContext):
    data = await state.get_data()
    name_fund = data['name']

    if message.text == '.' and AddFund.fund_for_change:
        await state.update_data(market_price=AddFund.fund_for_change.market_price)
    else:
        market_price = message.text
        if market_price.casefold() == 'авто':
            try:
                auto_market_price, currency = await get_price_fund(name_fund)
                if auto_market_price is None:
                    await message.answer("Введите корректное числовое значение для цены фонда")
                    return

                await state.update_data(market_price=auto_market_price, currency=currency)
                await message.answer(f"Курс {name_fund} на финбирже автоматически установлен: {auto_market_price}")
            except Exception as e:
                await message.answer(f"Не удалось получить цену фонда: {e}")
                return
        else:
            try:
                market_price = float(market_price)
                await state.update_data(market_price=market_price)

                currency = data.get('currency')
                if not currency:
                    await message.answer("Введите валюту для фонда (например, RUB, USD, EUR):")
                    await state.set_state(AddFund.currency)
                    return
            except ValueError:
                await message.answer("Введите корректное числовое значение для цены фонда")
                return

        await message.answer("Введите количество купленных бумаг фонда")
        await state.set_state(AddFund.quantity)


@fund_router.message(AddFund.currency, F.text)
async def add_currency(message: types.Message, state: FSMContext):
    if message.text == '.' and AddFund.fund_for_change:
        await state.update_data(currency=AddFund.fund_for_change.currency)
    else:
        currency = message.text.upper().strip()

        valid_currencies = ['RUB', 'USD', 'EUR']
        if currency not in valid_currencies:
            await message.answer("Введите корректный код валюты (например, RUB, USD, EUR):")
            return

        await state.update_data(currency=currency)
        updated_data = await state.get_data()
        print(f"Обновленные данные после ввода валюты: {updated_data}")

    await message.answer("Введите количество бумаг акции:")
    await state.set_state(AddFund.quantity)


@fund_router.message(AddFund.quantity, F.text)
async def add_quantity(message: types.Message, state: FSMContext, session: AsyncSession):
    if message.text == '.' and AddFund.fund_for_change:
        await state.update_data(quantity=AddFund.fund_for_change.quantity)
    else:
        await state.update_data(quantity=message.text)

    data = await state.get_data()
    try:
        if AddFund.fund_for_change:
            await orm_update_fund(session, AddFund.fund_for_change.id, data)
        else:
            await orm_add_fund(session, data)
        await message.answer("Бумага фонда добавлены")
        await state.clear()

    except Exception as e:
        await message.answer(f"Ошибка {e}, обратитесь к @gigcomm, чтобы исправить ее!")
        await state.clear()

    AddFund.fund_for_change = None
