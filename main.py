# Main entry point - запускает оба бота (Клиенты + Менеджеры)
import asyncio
import logging
import sys
import io

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import BOT_TOKEN, MANAGER_BOT_TOKEN, MANAGER_CHAT_ID
from bot.handlers import router
from bot.handlers_extended import router_extended
from bot.handlers_new_features import router_features
from bot.manager_handlers import router as manager_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_client_bot():
    """БОТ #1 - для клиентов"""
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Include all router sets
    dp.include_router(router)
    dp.include_router(router_extended)
    dp.include_router(router_features)
    
    logger.info("=" * 60)
    logger.info("🤖 БОТ #1 - КЛИЕНТЫ")
    logger.info("=" * 60)
    logger.info("✅ Основной бот запущен")
    logger.info("📖 Клиенты могут создавать заказы")
    logger.info("=" * 60)
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка БОТ #1: {e}")
        raise
    finally:
        await bot.session.close()


async def run_manager_bot():
    """БОТ #2 - для менеджеров"""
    
    # Проверка конфигурации
    if not MANAGER_BOT_TOKEN:
        logger.warning("⚠️  MANAGER_BOT_TOKEN не настроен - менеджер бот не запущен")
        return
    
    if not MANAGER_CHAT_ID:
        logger.warning("⚠️  MANAGER_CHAT_ID не настроен - менеджер бот не запустится")
        return
    
    bot = Bot(token=MANAGER_BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Include manager router
    dp.include_router(manager_router)
    
    logger.info("=" * 60)
    logger.info("🤖 БОТ #2 - МЕНЕДЖЕРЫ")
    logger.info("=" * 60)
    logger.info("✅ Менеджер бот запущен")
    logger.info(f"📬 Chat ID: {MANAGER_CHAT_ID}")
    logger.info("📋 Менеджеры получают уведомления о заказах")
    logger.info("=" * 60)
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка БОТ #2: {e}")
        raise
    finally:
        await bot.session.close()


async def main():
    """Запустить оба бота одновременно"""
    logger.info("\n" + "=" * 60)
    logger.info("🚀 ЗАПУСК СИСТЕМЫ BOTОВ")
    logger.info("=" * 60 + "\n")
    
    # Запустить оба бота параллельно
    try:
        await asyncio.gather(
            run_client_bot(),
            run_manager_bot()
        )
    except KeyboardInterrupt:
        logger.info("\n\n" + "=" * 60)
        logger.info("⛔ СИСТЕМА ОСТАНОВЛЕНА ПОЛЬЗОВАТЕЛЕМ")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Завершение...")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        raise
