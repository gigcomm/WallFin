from decimal import Decimal

from aiogram import types, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import CallbackQuery, InputMediaPhoto, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import orm_add_user, orm_delete_bank, orm_delete_stock_market, orm_delete_cryptomarket
from tg_bot.handlers.menu_processing import get_menu_content
from tg_bot.keyboards.inline import MenuCallBack
from finance.total_balance import calculate_total_balance
from tg_bot.logger import logger

user_private_router = Router()


@user_private_router.message(CommandStart())
async def start_cmd(message: types.Message, session: AsyncSession):
    await orm_add_user(session, message)
    media, reply_markup = await get_menu_content(session, level=0, menu_name="main")
    await message.answer_photo(media.media, caption=media.caption, reply_markup=reply_markup)


@user_private_router.callback_query(MenuCallBack.filter())
async def menu_command(callback_query: CallbackQuery, callback_data: MenuCallBack, session: AsyncSession):
    menu_name = callback_data.menu_name

    if callback_data.action == "confirm_delete" and callback_data.bank_id:
        bank_id = int(callback_data.bank_id)
        await orm_delete_bank(session, bank_id)
        await callback_query.answer("Банк удален")

    elif callback_data.action == "confirm_delete" and callback_data.stockmarket_id:
        stock_market_id = callback_data.stockmarket_id
        await orm_delete_stock_market(session, int(stock_market_id))
        await callback_query.answer("Финбиржа удалена")

    elif callback_data.action == "confirm_delete" and callback_data.cryptomarket_id:
        cryptomarket_id = callback_data.cryptomarket_id
        await orm_delete_cryptomarket(session, int(cryptomarket_id))
        await callback_query.answer("Криптобиржа удалена")

    if menu_name == "total_balance":
        user_tg_id = int(callback_data.user_tg_id)

        try:
            await calculate_total_balance(session, user_tg_id)
        except Exception as e:
            logger.exception(f"Ошибка при вычислении баланса: {e}")
            await callback_query.answer("Ошибка при вычислении баланса. Попробуйте позже.")
            return

    media_or_caption, reply_markup = await get_menu_content(
        session,
        level=callback_data.level,
        menu_name=callback_data.menu_name,
        user_tg_id=callback_query.from_user.id,
        bank_id=callback_data.bank_id,
        cryptomarket_id=callback_data.cryptomarket_id,
        stockmarket_id=callback_data.stockmarket_id,
        page=callback_data.page,
    )
    if isinstance(media_or_caption, InputMediaPhoto):
        await callback_query.message.edit_media(media=media_or_caption, reply_markup=reply_markup)
    else:
        await callback_query.message.edit_caption(caption=media_or_caption, reply_markup=reply_markup)

    await callback_query.answer()
