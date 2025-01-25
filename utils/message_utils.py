import asyncio

from tg_bot.core import bot


async def delete_regular_messages(data, message):
    for msg_id in data.get("message_ids", []):
        try:
            await bot.delete_message(message.chat.id, msg_id)
        except Exception as e:
            print(f"Не удалось удалить сообщение {msg_id}: {e}")


async def delete_keyboard_messages(data, message):
    for kbd_msg_id in data.get("keyboard_message_id", []):
        await bot.delete_message(message.chat.id, kbd_msg_id)


async def delete_bot_and_user_messages(data, message, bot_message):
    try:
        await delete_keyboard_messages(data, message)
        await bot.delete_message(message.chat.id, message.message_id)
        await asyncio.sleep(3)
        await bot.delete_message(message.chat.id, bot_message.message_id)
    except Exception as e:
        print(f"Не удалось удалить сообщение: {e}")
