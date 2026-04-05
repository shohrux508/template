from aiogram import Bot, Dispatcher
from app.config import settings
from app.container import Container
from app.telegram.routers import example


async def start_telegram(container: Container):
    if not settings.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is required when RUN_TELEGRAM=true")

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    # Pass the container into the Dispatcher to bypass globals
    dp["container"] = container

    # Include routers
    dp.include_router(example.router)

    try:
        await dp.start_polling(bot, container=container)
    finally:
        await bot.session.close()
