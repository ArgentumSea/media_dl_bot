from aiogram import Router, types
from aiogram.filters import Command
from bot.database import get_pool
import structlog

router = Router()
logger = structlog.get_logger()

def is_admin_or_assistant(role: str) -> bool:
    return role in ("admin", "assistant")

@router.message(Command("stat"))
async def cmd_stat(message: types.Message, user_role: str = "user"):
    if not is_admin_or_assistant(user_role):
        await message.answer("Отказ — нет прав.")
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                u.tg_id,
                COUNT(CASE WHEN r.created_at >= NOW() - INTERVAL '1 day' THEN 1 END) as today,
                COUNT(r.id) as total
            FROM users u
            LEFT JOIN request_logs r ON u.tg_id = r.user_id
            GROUP BY u.tg_id
            ORDER BY total DESC
        """)

    if not rows:
        await message.answer("Статистика пуста.")
        return

    lines = ["user_id — сегодня — всего"]
    for r in rows:
        lines.append(f"{r['tg_id']} — {r['today']} — {r['total']}")

    await message.answer("
".join(lines))
