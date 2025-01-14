import os

from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import orm_get_info_pages, orm_update_banner_image
from tg_bot.handlers.common_imports import *
from tg_bot.keyboards.reply import get_keyboard

admin_router = Router()

ADMIN_KB = get_keyboard(
    "Добавить/Изменить баннер"
)


@admin_router.message(Command("admin"))
async def admin_start(message: types.Message):
    user_id = message.from_user.id
    admin_ids = list(map(int, os.getenv("ADMINS_ID_TG", "").split(",")))
    if user_id in admin_ids:
        await message.answer("Добро пожаловать в админку, что хотите сделать?", reply_markup=ADMIN_KB)


class AddBanner(StatesGroup):
    image = State()


@admin_router.message(StateFilter(None), F.text == "Добавить/Изменить баннер")
async def add_image(message: types.Message, state: FSMContext, session: AsyncSession):
    pages_names = [page.name for page in await orm_get_info_pages(session)]
    await message.answer(f"Отправьте фото баннера. \nВ описании укажите для какой странице:"
                         f"\n{', '.join(pages_names)}")
    await state.set_state(AddBanner.image)


@admin_router.message(AddBanner.image, F.photo)
async def add_banner(message: types.Message, state: FSMContext, session: AsyncSession):
    image_id = message.photo[-1].file_id
    for_page = message.caption.strip()
    pages_names = [page.name for page in await orm_get_info_pages(session)]
    if for_page not in pages_names:
        await message.answer(f"Введите существующее название страницы, напримаер"
                             f"{', '.join(pages_names)}")
        return
    await orm_update_banner_image(session, for_page, image_id)
    await message.answer("Баннер добвален/изменен")
    await state.clear()