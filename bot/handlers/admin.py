from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.database import get_pool
import structlog

router = Router()
logger = structlog.get_logger()

def is_admin_or_assistant(role: str) -> bool:
    return role in ("admin", "assistant")

def can_manage(actor_role: str, target_role: str) -> bool:
    if actor_role == "admin":
        return True
    if actor_role == "assistant":
        return target_role == "user"
    return False

def display_name(username, tg_id):
    return f"@{username}" if username else str(tg_id)

@router.message(Command("admin"))
async def cmd_admin(message: types.Message, user_role: str = "user"):
    if not is_admin_or_assistant(user_role):
        await message.answer("Отказ — нет прав.")
        return
    pool = await get_pool()
    async with pool.acquire() as conn:
        users = await conn.fetch(
            "SELECT tg_id, username, role, created_at FROM users ORDER BY created_at DESC"
        )
    if not users:
        await message.answer("Пользователей пока нет.")
        return
    lines = []
    buttons = []
    for u in users:
        role_label = "Администратор" if u["role"] == "admin" else "Ассистент" if u["role"] == "assistant" else "Пользователь"
        name = display_name(u["username"], u["tg_id"])
        line = f"{name} — {role_label} — {u['created_at'].strftime('%Y-%m-%d')}"
        lines.append(line)
        buttons.append([InlineKeyboardButton(
            text=f"⚙️ {name}",
            callback_data=f"user:{u['tg_id']}"
        )])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("\n".join(lines), reply_markup=kb)

@router.callback_query(F.data.startswith("user:"))
async def on_user_select(callback: types.CallbackQuery, user_role: str = "user"):
    target_id = int(callback.data.split(":")[1])
    pool = await get_pool()
    async with pool.acquire() as conn:
        target = await conn.fetchrow("SELECT role, username, tg_id FROM users WHERE tg_id = $1", target_id)
    if not target:
        await callback.answer("Пользователь не найден.")
        return
    if not can_manage(user_role, target["role"]):
        await callback.answer("Отказ — нет прав.")
        return
    name = display_name(target["username"], target["tg_id"])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назначить ассистентом", callback_data=f"promote:{target_id}")],
        [InlineKeyboardButton(text="Разжаловать", callback_data=f"demote:{target_id}")],
        [InlineKeyboardButton(text="Заблокировать", callback_data=f"block:{target_id}")],
        [InlineKeyboardButton(text="Разблокировать", callback_data=f"unblock:{target_id}")],
        [InlineKeyboardButton(text="Удалить", callback_data=f"delete:{target_id}")]
    ])
    await callback.message.edit_text(f"Управление: {name}", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("promote:"))
async def on_promote(callback: types.CallbackQuery, user_role: str = "user"):
    target_id = int(callback.data.split(":")[1])
    if user_role != "admin":
        await callback.answer("Отказ — нет прав.")
        return
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET role = 'assistant' WHERE tg_id = $1", target_id)
    await callback.answer("Назначен ассистентом.")
    await callback.message.edit_text("Обновлено.")

@router.callback_query(F.data.startswith("demote:"))
async def on_demote(callback: types.CallbackQuery, user_role: str = "user"):
    target_id = int(callback.data.split(":")[1])
    if user_role != "admin":
        await callback.answer("Отказ — нет прав.")
        return
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET role = 'user' WHERE tg_id = $1", target_id)
    await callback.answer("Разжалован.")
    await callback.message.edit_text("Обновлено.")

@router.callback_query(F.data.startswith("block:"))
async def on_block(callback: types.CallbackQuery, user_role: str = "user"):
    target_id = int(callback.data.split(":")[1])
    if not can_manage(user_role, "user"):
        await callback.answer("Отказ — нет прав.")
        return
    pool = await get_pool()
    async with pool.acquire() as conn:
        target = await conn.fetchrow("SELECT role FROM users WHERE tg_id = $1", target_id)
        if target and not can_manage(user_role, target["role"]):
            await callback.answer("Отказ — нет прав.")
            return
        await conn.execute("UPDATE users SET is_blocked = TRUE WHERE tg_id = $1", target_id)
    await callback.answer("Заблокирован.")

@router.callback_query(F.data.startswith("unblock:"))
async def on_unblock(callback: types.CallbackQuery, user_role: str = "user"):
    target_id = int(callback.data.split(":")[1])
    if not can_manage(user_role, "user"):
        await callback.answer("Отказ — нет прав.")
        return
    pool = await get_pool()
    async with pool.acquire() as conn:
        target = await conn.fetchrow("SELECT role FROM users WHERE tg_id = $1", target_id)
        if target and not can_manage(user_role, target["role"]):
            await callback.answer("Отказ — нет прав.")
            return
        await conn.execute("UPDATE users SET is_blocked = FALSE WHERE tg_id = $1", target_id)
    await callback.answer("Разблокирован.")

@router.callback_query(F.data.startswith("delete:"))
async def on_delete(callback: types.CallbackQuery, user_role: str = "user"):
    target_id = int(callback.data.split(":")[1])
    if not can_manage(user_role, "user"):
        await callback.answer("Отказ — нет прав.")
        return
    pool = await get_pool()
    async with pool.acquire() as conn:
        target = await conn.fetchrow("SELECT role FROM users WHERE tg_id = $1", target_id)
        if target and not can_manage(user_role, target["role"]):
            await callback.answer("Отказ — нет прав.")
            return
        await conn.execute("DELETE FROM users WHERE tg_id = $1", target_id)
    await callback.answer("Удален.")
    await callback.message.edit_text("Пользователь удален.")
