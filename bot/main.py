import asyncio
import logging
import signal
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from bot.config import BOT_TOKEN, LOG_LEVEL
from bot.database import migrate, close_pool
from bot.handlers import common, content, media, admin, stats
from bot.middlewares.auth import AuthMiddleware
import structlog

_shutting_down = False

def setup_logging():
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(level=level)

async def health_check(request):
    return web.Response(text="OK", status=200)

async def start_health_server():
    app = web.Application()
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    return runner

async def main():
    global _shutting_down
    setup_logging()
    logger = structlog.get_logger()
    logger.info("Starting bot")

    await migrate()
    runner = await start_health_server()

    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()

    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    dp.include_router(common.router)
    dp.include_router(content.router)
    dp.include_router(media.router)
    dp.include_router(admin.router)
    dp.include_router(stats.router)

    async def shutdown():
        global _shutting_down
        if _shutting_down:
            return
        _shutting_down = True
        logger.info("Shutting down...")
        await close_pool()
        await runner.cleanup()
        await bot.session.close()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))

    try:
        await dp.start_polling(bot)
    finally:
        await shutdown()

if __name__ == "__main__":
    asyncio.run(main())
