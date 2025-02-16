import asyncio

from aiogram import types
from core import bot, dp

from middlewares.db import DataBaseSession

from database.engine import create_db, drop_db, session_maker

from handlers.user_private import user_private_router
from command.bot_cmds_list import private
from handlers.admin_private import admin_router
from handlers.bank_handlers.bank import bank_router
from handlers.cryptomarket_handlers.cryptomarket import cryptomarket_router
from handlers.stock_market_handlers.stock_market import stock_market_router
from tasks.update_price_assets import test_task


dp.include_router(user_private_router)
dp.include_router(admin_router)
dp.include_router(bank_router)
dp.include_router(cryptomarket_router)
dp.include_router(stock_market_router)


async def on_startup(bot):
    run_param = False
    if run_param:
        await drop_db()
    await create_db()

    # Запуск задачи update_prices в фоновом режиме
    # test_task.delay()


async def on_shutdown(bot):
    print('Бот упал')


async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    dp.update.middleware(DataBaseSession(session_pool=session_maker))

    await bot.delete_webhook(drop_pending_updates=True)  # все обновления при не работе бота сбрасываются
    # await bot.delete_my_commands(scope=types.BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(commands=private, scope=types.BotCommandScopeAllPrivateChats())
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


asyncio.run(main())
