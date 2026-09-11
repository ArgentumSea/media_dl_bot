import os
import asyncio
import structlog
from google import genai
from google.genai import types
from bot.config import GEMINI_API_KEY, GEMINI_MODELS
from bot.database import get_pool

logger = structlog.get_logger()

class GeminiService:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.models = [m.strip() for m in GEMINI_MODELS if m.strip()]
        self.backoff_delays = [1, 2, 4, 8, 60]

    async def analyze(self, text: str = None, file_path: str = None, mime_type: str = None) -> str:
        pool = await get_pool()
        async with pool.acquire() as conn:
            prompt_row = await conn.fetchrow(
                "SELECT content FROM system_prompts WHERE name = 'default'"
            )
        system_prompt = prompt_row["content"] if prompt_row else "Проанализируй контент."

        contents = []
        if text:
            contents.append(text)

        uploaded_file = None
        if file_path and os.path.exists(file_path):
            uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path)
            contents.append(uploaded_file)

        for model_name in self.models:
            for attempt, delay in enumerate(self.backoff_delays):
                try:
                    logger.info("Gemini request", model=model_name, attempt=attempt + 1)
                    response = await asyncio.to_thread(
                        self.client.models.generate_content,
                        model=model_name,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=system_prompt
                        )
                    )

                    if uploaded_file:
                        try:
                            await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                        except Exception:
                            pass

                    if response.text:
                        return response.text
                    else:
                        logger.warning("Empty response from model", model=model_name)
                        raise Exception("Модель вернула пустой ответ")

                except Exception as e:
                    error_str = str(e).lower()
                    if "quota" in error_str or "rate limit" in error_str or "429" in error_str:
                        logger.warning(
                            "Gemini rate limit",
                            model=model_name,
                            attempt=attempt + 1,
                            delay=delay
                        )
                        if attempt < len(self.backoff_delays) - 1:
                            await asyncio.sleep(delay)
                            continue
                    logger.error("Gemini error", model=model_name, error=str(e))
                    break

        if uploaded_file:
            try:
                await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
            except Exception:
                pass
        raise Exception("Лимит API иссяк — попробуйте позже")
