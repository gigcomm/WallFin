import re
from aiogram.fsm.context import FSMContext
from aiogram import types


async def validate_positive_number(
        message: types.Message,
        state: FSMContext,
        scale: int,
        field_name: str = None,
        allow_auto: bool = False
):

    text = message.text.strip()

    if not re.fullmatch(rf"\d+(\.\d{{1,{scale}}})?", text):
        text = (
                f"Вводимое число для \"{field_name}\" должно быть положительным без дополнительных символов"
                + (" или введите слово 'авто'" if allow_auto else "")
                + ".\nВведите заново, например: 123.45"
        )
        bot_message = await message.answer(text)
        await state.update_data(message_ids=[message.message_id, bot_message.message_id])
        return None

    return float(text)
