import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_STR = os.getenv("ADMIN_ID", "0")
try:
    ADMIN_ID = int(ADMIN_ID_STR)
except ValueError:
    ADMIN_ID = 0
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODELS = os.getenv(
    "GEMINI_MODELS",
    "gemini-3.1-flash,gemini-3.1-flash-lite,gemini-2.5-pro,gemini-2.5-flash,gemini-2.0-flash,gemini-2.0-flash-lite"
).split(",")
