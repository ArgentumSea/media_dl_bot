from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Dict, Any, Awaitable
from bot.database import get_pool

class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if not event.from_user:
            return await handler(event, data)

        pool = await get_pool()
        async with pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT role, is_blocked FROM users WHERE tg_id = $1",
                event.from_user.id
            )
            if user and user["is_blocked"]:
                await event.answer("Вы заблокированы.")
                return None

            data["user_role"] = user["role"] if user else "user"
            data["is_blocked"] = user["is_blocked"] if user else False

        return await handler(event, data)
