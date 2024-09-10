
import asyncio
import logging
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot_send.config_reader import bot, on_startup, on_shutdown
from bot_send.middlewares.db import DataBaseSession

from bot_send.datadase.engine import session_maker
from bot_send.app.handlers import router


async def main():
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(DataBaseSession(session_pool=session_maker))
    dp.include_router(router)
    # Регистрация функций on_startup и on_shutdown
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    # Запуск polling
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Бот остановлен')
