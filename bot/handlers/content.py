import os
import tempfile
from aiogram import Router, types, F
from aiogram.types import FSInputFile
from bot.services.ytdlp import YtDlpService
from bot.services.gemini import GeminiService
from bot.database import get_pool
import structlog

router = Router()
logger = structlog.get_logger()
ytdlp = YtDlpService()
gemini = GeminiService()

URL_PATTERNS = ["http://", "https://", "www."]

VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv"}
AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"}

@router.message(F.text, ~F.text.startswith("/"))
async def handle_text(message: types.Message):
    if not message.text:
        return
    
    is_url = any(message.text.startswith(p) or p in message.text for p in URL_PATTERNS)
    
    if is_url:
        status_msg = await message.answer("Скачиваю контент...")
        file_path = None
        try:
            result = await ytdlp.download(message.text)
            
            if result.get("error"):
                await status_msg.edit_text(f"Ошибка скачивания: {result['error']}")
                await log_request(message.from_user.id, "link", "error")
                return
            
            if result.get("is_too_big"):
                await status_msg.edit_text("Анализирую информацию...")
                context = f"Заголовок: {result['title']}\nОписание: {result['description']}\nСсылка: {message.text}"
                analysis = await gemini.analyze(text=context)
                await status_msg.delete()
                await send_split_message(message, analysis)
                await log_request(message.from_user.id, "link", "success")
                return
            
            file_path = result.get("file_path")
            if file_path and os.path.exists(file_path):
                actual_size = os.path.getsize(file_path)
                if actual_size > 50 * 1024 * 1024:
                    await status_msg.edit_text("Файл слишком большой для Telegram. Анализирую без скачивания...")
                    context = f"Заголовок: {result['title']}\nОписание: {result['description']}\nСсылка: {message.text}"
                    analysis = await gemini.analyze(text=context)
                    await status_msg.delete()
                    await send_split_message(message, analysis)
                    await log_request(message.from_user.id, "link", "success")
                    return
                
                await status_msg.edit_text("Анализирую информацию...")
                analysis = await gemini.analyze(file_path=file_path)
                await status_msg.delete()
                
                caption = f"📹 {result['title']}\n\n{result['description'][:1024] if result['description'] else ''}".strip()
                if len(caption) > 1024:
                    caption = caption[:1021] + "..."
                
                file = FSInputFile(file_path)
                ext = os.path.splitext(file_path)[1].lower()
                
                if ext in VIDEO_EXTS:
                    await message.answer_video(video=file, caption=caption)
                elif ext in AUDIO_EXTS:
                    await message.answer_audio(audio=file, caption=caption)
                else:
                    await message.answer_document(document=file, caption=caption)
                
                await send_split_message(message, analysis)
                await log_request(message.from_user.id, "link", "success")
            else:
                await status_msg.edit_text("Не удалось скачать контент.")
                await log_request(message.from_user.id, "link", "error")
                
        except Exception as e:
            logger.error("Link processing error", error=str(e))
            await status_msg.edit_text(f"Ошибка обработки: {str(e)}")
            await log_request(message.from_user.id, "link", "error")
        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
    else:
        status_msg = await message.answer("Анализирую информацию...")
        try:
            analysis = await gemini.analyze(text=message.text)
            await status_msg.delete()
            await send_split_message(message, analysis)
            await log_request(message.from_user.id, "text", "success")
        except Exception as e:
            logger.error("Text analysis error", error=str(e))
            await status_msg.edit_text(f"Ошибка обработки: {str(e)}")
            await log_request(message.from_user.id, "text", "error")

async def send_split_message(message: types.Message, text: str):
    if not text or not text.strip():
        await message.answer("Анализ завершён, но результат пустой.")
        return
    max_len = 4096
    if len(text) <= max_len:
        await message.answer(text)
        return
    for i in range(0, len(text), max_len):
        await message.answer(text[i:i + max_len])

async def log_request(user_id: int, req_type: str, status: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO request_logs (user_id, request_type, status) VALUES ($1, $2, $3)",
            user_id, req_type, status
        )
