import asyncpg
from bot.config import DATABASE_URL, ADMIN_ID
import structlog

logger = structlog.get_logger()

_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    return _pool

async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

async def migrate():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                tg_id BIGINT UNIQUE NOT NULL,
                username TEXT,
                role VARCHAR(20) DEFAULT 'user',
                is_blocked BOOLEAN DEFAULT FALSE,
                subscription_status VARCHAR(50) DEFAULT 'free',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS request_logs (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                request_type VARCHAR(50),
                status VARCHAR(50),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS system_prompts (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                content TEXT NOT NULL
            )
        """)
        await conn.execute("""
            INSERT INTO system_prompts (name, content)
            VALUES ('default', 'Ты — ассистент для анализа медиаконтента. Создай структурированный конспект, максимально близкий к исходнику, но резюмирующий. Упомяни все ссылки и ресурсы из контента.')
            ON CONFLICT (name) DO NOTHING
        """)
        if ADMIN_ID:
            await conn.execute("""
                INSERT INTO users (tg_id, username, role)
                VALUES ($1, 'admin', 'admin')
                ON CONFLICT (tg_id) DO UPDATE SET role = 'admin'
            """, ADMIN_ID)
    logger.info("Migrations completed")
