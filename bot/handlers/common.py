from aiogram import Router, types
from aiogram.filters import Command
from bot.database import get_pool
import structlog

router = Router()
logger = structlog.get_logger()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    pool = await get_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE tg_id = $1", message.from_user.id
        )
        if not user:
            await conn.execute(
                "INSERT INTO users (tg_id, username, role) VALUES ($1, $2, $3)",
                message.from_user.id,
                message.from_user.username,
                "user"
            )
            logger.info("New user registered", tg_id=message.from_user.id)
            admins = await conn.fetch(
                "SELECT tg_id FROM users WHERE role IN ('admin', 'assistant')"
            )
            for admin in admins:
                try:
                    await message.bot.send_message(
                        admin["tg_id"],
                        f"Новый пользователь — {message.from_user.id} "
                        f"(@{message.from_user.username or 'no_username'})"
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to notify admin",
                        admin_id=admin["tg_id"],
                        error=str(e)
                    )
        else:
            await conn.execute(
                "UPDATE users SET username = $1 WHERE tg_id = $2",
                message.from_user.username,
                message.from_user.id
            )

    text = (
        "Привет! Я бот для анализа медиаконтента.\n"
        "Отправь мне ссылку на пост или файл (фото, видео, аудио, документ).\n"
        "Я проанализирую его и сделаю конспект.\n"
        "Можешь прислать голосовое — распознаю текст и обработаю.\n"
        "Пересылай сообщения из других чатов."
    )
    await message.answer(text)

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    text = (
        "Возможности:\n"
        "• Отправь ссылку — скачаю и проанализирую контент\n"
        "• Отправь фото, видео, аудио, документ — проанализирую\n"
        "• Отправь голосовое — распознаю речь и проанализирую\n"
        "• Перешли сообщение из другого чата — обработаю текст\n\n"
        "Команды:\n"
        "/start — запуск\n"
        "/help — помощь\n"
        "/admin — панель управления (админ/ассистент)\n"
        "/stat — статистика (админ/ассистент)"
    )
    await message.answer(text)
