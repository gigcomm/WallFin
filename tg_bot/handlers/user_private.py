from aiogram import types, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InputMediaPhoto
from sqlalchemy.ext.asyncio import AsyncSession

from tg_bot.handlers.menu_processing import get_menu_content, cryptomarkets, stockmarkets
from tg_bot.keyboards.inline import MenuCallBack

user_private_router = Router()


@user_private_router.message(CommandStart())
async def start_cmd(message: types.Message, session: AsyncSession):
    media, reply_markup = await get_menu_content(session, level=0, menu_name="main")
    await message.answer_photo(media.media, caption=media.caption, reply_markup=reply_markup)


@user_private_router.callback_query(MenuCallBack.filter())
async def menu_command(callback_query: CallbackQuery, callback_data: MenuCallBack, session: AsyncSession):
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
