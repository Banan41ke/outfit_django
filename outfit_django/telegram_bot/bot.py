#!/usr/bin/env python3
"""
ИИ Стилист - Телеграм Бот
Запуск: python -m telegram_bot.bot
"""

import os

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import asyncio
import logging
import sys
from pathlib import Path

# Настройка пути (Django настроится лениво в api_client)
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from telegram_bot.config import BOT_TOKEN
from telegram_bot.handlers import start, photo, callback
from telegram_bot.services.api_client import get_style_api  # ← ИСПРАВЛЕНО: путь

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    """Действия при запуске бота"""
    logger.info("🚀 Бот инициализируется...")


async def on_shutdown(bot: Bot, dispatcher: Dispatcher):
    """Graceful shutdown - закрытие всех ресурсов"""
    logger.info("🛑 Завершение работы бота...")

    # Закрываем StyleAPI (ThreadPoolExecutor)
    try:
        api = await get_style_api()
        await api.close()
        logger.info("✅ StyleAPI закрыт")
    except Exception as e:
        logger.warning(f"⚠️ Ошибка при закрытии StyleAPI: {e}")

    # Закрываем сессию бота
    await bot.session.close()
    logger.info("✅ Сессия бота закрыта")

    # Закрываем storage
    await dispatcher.storage.close()
    logger.info("✅ Storage закрыт")


async def main():
    logger.info("Запуск бота...")

    # Создание бота (aiogram 3.7+)
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрация роутеров
    dp.include_router(start.router)
    dp.include_router(photo.router)
    dp.include_router(callback.router)

    # Регистрация lifecycle хуков
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Удаление вебхука и очистка очереди
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Бот запущен! Нажмите Ctrl+C для остановки.")

    # Запуск поллинга
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен пользователем.")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)