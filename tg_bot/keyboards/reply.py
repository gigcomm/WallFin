from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder

def get_keyboard(
        *btns: str,
        placeholder: str = None,
        sizes: tuple[int] = (2, ),
):
    keyboard = ReplyKeyboardBuilder()

    for index, text in enumerate(btns, start=0):
        keyboard.add(KeyboardButton(text=text))

    return keyboard.adjust(*sizes).as_markup(
        resize_keyboard=True, input_field_placeholder=placeholder)