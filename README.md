# Media DL Bot

Telegram-бот для скачивания и AI-анализа медиаконтента.

## Возможности

- Скачивание контента по ссылкам (YouTube, Instagram, TikTok и 1700+ сайтов через yt-dlp)
- Анализ фото, видео, аудио, документов через Google Gemini API
- Распознавание голосовых сообщений через Vosk (офлайн)
- Каскадный fallback между моделями Gemini с exponential backoff
- Система ролей: Администратор, Ассистент, Пользователь
- Статистика использования
- Полная изоляция данных между пользователями

## Стек

- Python 3.11+
- aiogram 3.30.0
- PostgreSQL 15+
- yt-dlp, Vosk, Google GenAI SDK

## Установка

```bash
bash deploy.sh
```

Затем отредактируй `.env` и запусти:

```bash
systemctl enable --now media_dl_bot
```

## Обновление

```bash
bash update.sh
```

## Переменные окружения (.env)

| Переменная | Описание | Пример |
|---|---|---|
| BOT_TOKEN | Токен бота от @BotFather | 123456:ABC... |
| ADMIN_ID | Telegram ID первого администратора | 123456789 |
| DATABASE_URL | URL подключения к PostgreSQL | postgresql://user:pass@localhost/db |
| LOG_LEVEL | Уровень логирования | INFO |
| GEMINI_API_KEY | Ключ Google Gemini API | AIza... |
| GEMINI_MODELS | Список моделей через запятую | gemini-3.1-flash,gemini-2.5-pro... |

## Команды

- `/start` — запуск и регистрация
- `/help` — справка
- `/admin` — панель управления (админ/ассистент)
- `/stat` — статистика (админ/ассистент)

## Изменение промпта

Отредактируй `prompts/default.txt`, затем выполни:

```bash
cd /opt/media_dl_bot
source venv/bin/activate
python3 -c "
import asyncio
from bot.database import get_pool
async def update():
    with open('prompts/default.txt') as f:
        text = f.read()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(\"UPDATE system_prompts SET content = $1 WHERE name = 'default'\", text)
asyncio.run(update())
"
```

## Vosk модель

Скачай модель для русского языка:

```bash
mkdir -p /opt/media_dl_bot/models
cd /opt/media_dl_bot/models
wget https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip
unzip vosk-model-small-ru-0.22.zip
```

## Мониторинг

- Health-check: `curl http://localhost:8080/health`
- Логи: `journalctl -u media_dl_bot -f`
