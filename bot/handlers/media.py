import asyncio
import os
import tempfile
from aiogram import Router, types, F
from bot.services.gemini import GeminiService
from bot.services.vosk_service import VoskService
from bot.handlers.content import send_split_message, log_request
import structlog

router = Router()
logger = structlog.get_logger()
gemini = GeminiService()

VOSK = None
try:
    VOSK = VoskService()
except Exception as e:
    logger.warning("Vosk not available", error=str(e))

@router.message(F.photo)
async def handle_photo(message: types.Message):
    status_msg = await message.answer("Анализирую информацию...")
    tmp_path = None
    try:
        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        ext = file.file_path.split(".")[-1]
        tmp_path = os.path.join(tempfile.gettempdir(), f"{photo.file_id}.{ext}")
        await message.bot.download_file(file.file_path, tmp_path)

        analysis = await gemini.analyze(file_path=tmp_path, mime_type="image/jpeg")
        await status_msg.delete()
        await send_split_message(message, analysis)
        await log_request(message.from_user.id, "photo", "success")
    except Exception as e:
        logger.error("Photo processing error", error=str(e))
        await status_msg.edit_text(f"Ошибка обработки: {str(e)}")
        await log_request(message.from_user.id, "photo", "error")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

@router.message(F.video)
async def handle_video(message: types.Message):
    status_msg = await message.answer("Анализирую информацию...")
    tmp_path = None
    try:
        video = message.video
        file = await message.bot.get_file(video.file_id)
        ext = video.mime_type.split("/")[-1] if video.mime_type else "mp4"
        tmp_path = os.path.join(tempfile.gettempdir(), f"{video.file_id}.{ext}")
        await message.bot.download_file(file.file_path, tmp_path)

        analysis = await gemini.analyze(file_path=tmp_path, mime_type=video.mime_type or "video/mp4")
        await status_msg.delete()
        await send_split_message(message, analysis)
        await log_request(message.from_user.id, "video", "success")
    except Exception as e:
        logger.error("Video processing error", error=str(e))
        await status_msg.edit_text(f"Ошибка обработки: {str(e)}")
        await log_request(message.from_user.id, "video", "error")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

@router.message(F.audio)
async def handle_audio(message: types.Message):
    status_msg = await message.answer("Анализирую информацию...")
    tmp_path = None
    try:
        audio = message.audio
        file = await message.bot.get_file(audio.file_id)
        ext = audio.mime_type.split("/")[-1] if audio.mime_type else "mp3"
        tmp_path = os.path.join(tempfile.gettempdir(), f"{audio.file_id}.{ext}")
        await message.bot.download_file(file.file_path, tmp_path)

        analysis = await gemini.analyze(file_path=tmp_path, mime_type=audio.mime_type or "audio/mpeg")
        await status_msg.delete()
        await send_split_message(message, analysis)
        await log_request(message.from_user.id, "audio", "success")
    except Exception as e:
        logger.error("Audio processing error", error=str(e))
        await status_msg.edit_text(f"Ошибка обработки: {str(e)}")
        await log_request(message.from_user.id, "audio", "error")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

@router.message(F.voice)
async def handle_voice(message: types.Message):
    status_msg = await message.answer("Распознаю речь...")
    ogg_path = None
    wav_path = None
    try:
        voice = message.voice
        file = await message.bot.get_file(voice.file_id)
        ogg_path = os.path.join(tempfile.gettempdir(), f"{voice.file_id}.ogg")
        wav_path = os.path.join(tempfile.gettempdir(), f"{voice.file_id}.wav")
        await message.bot.download_file(file.file_path, ogg_path)

        ret = await asyncio.to_thread(
            os.system,
            f"ffmpeg -i {ogg_path} -ar 16000 -ac 1 -f wav {wav_path} -y -loglevel error"
        )
        if ret != 0:
            raise RuntimeError("ffmpeg conversion failed")

        if VOSK:
            text = await asyncio.to_thread(VOSK.transcribe, wav_path)
            await status_msg.edit_text("Анализирую информацию...")
            analysis = await gemini.analyze(text=text)
            await status_msg.delete()
            await send_split_message(message, f"<b>Распознанный текст:</b>
{text}

<b>Анализ:</b>
{analysis}")
        else:
            await status_msg.edit_text("Анализирую информацию...")
            analysis = await gemini.analyze(file_path=wav_path, mime_type="audio/wav")
            await status_msg.delete()
            await send_split_message(message, analysis)

        await log_request(message.from_user.id, "voice", "success")
    except Exception as e:
        logger.error("Voice processing error", error=str(e))
        await status_msg.edit_text(f"Ошибка обработки: {str(e)}")
        await log_request(message.from_user.id, "voice", "error")
    finally:
        for p in (ogg_path, wav_path):
            if p and os.path.exists(p):
                os.remove(p)

@router.message(F.document)
async def handle_document(message: types.Message):
    status_msg = await message.answer("Анализирую информацию...")
    tmp_path = None
    try:
        doc = message.document
        file = await message.bot.get_file(doc.file_id)
        ext = doc.file_name.split(".")[-1] if doc.file_name else "bin"
        tmp_path = os.path.join(tempfile.gettempdir(), f"{doc.file_id}.{ext}")
        await message.bot.download_file(file.file_path, tmp_path)

        mime = doc.mime_type or "application/octet-stream"
        analysis = await gemini.analyze(file_path=tmp_path, mime_type=mime)
        await status_msg.delete()
        await send_split_message(message, analysis)
        await log_request(message.from_user.id, "document", "success")
    except Exception as e:
        logger.error("Document processing error", error=str(e))
        await status_msg.edit_text(f"Ошибка обработки: {str(e)}")
        await log_request(message.from_user.id, "document", "error")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
