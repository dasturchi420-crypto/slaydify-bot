import aiosqlite

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    credits INTEGER NOT NULL DEFAULT 0,
    referrer_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS works (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    topic TEXT NOT NULL,
    file_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


async def init():
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()


async def ensure_user(user_id: int, username: str | None, full_name: str,
                      referrer_id: int | None = None) -> bool:
    """Foydalanuvchini yaratadi. Yangi bo'lsa True qaytaradi."""
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute("SELECT 1 FROM users WHERE id=?", (user_id,))
        if await cur.fetchone():
            return False
        if referrer_id == user_id:
            referrer_id = None
        await db.execute(
            "INSERT INTO users (id, username, full_name, credits, referrer_id) VALUES (?,?,?,?,?)",
            (user_id, username, full_name, config.FREE_CREDITS, referrer_id),
        )
        if referrer_id:
            await db.execute("UPDATE users SET credits = credits + 1 WHERE id=?", (referrer_id,))
        await db.commit()
        return True


async def get_credits(user_id: int) -> int:
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute("SELECT credits FROM users WHERE id=?", (user_id,))
        row = await cur.fetchone()
        return row[0] if row else 0


async def add_credits(user_id: int, n: int):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("UPDATE users SET credits = credits + ? WHERE id=?", (n, user_id))
        await db.commit()


async def spend_credit(user_id: int) -> bool:
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute(
            "UPDATE users SET credits = credits - 1 WHERE id=? AND credits > 0", (user_id,)
        )
        await db.commit()
        return cur.rowcount == 1


async def log_work(user_id: int, kind: str, topic: str, file_id: str | None):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            "INSERT INTO works (user_id, kind, topic, file_id) VALUES (?,?,?,?)",
            (user_id, kind, topic, file_id),
        )
        await db.commit()


async def history(user_id: int, limit: int = 10):
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute(
            "SELECT kind, topic, file_id FROM works WHERE user_id=? AND file_id IS NOT NULL "
            "ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )
        return await cur.fetchall()


async def referral_count(user_id: int) -> int:
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users WHERE referrer_id=?", (user_id,))
        return (await cur.fetchone())[0]


async def stats() -> dict:
    async with aiosqlite.connect(config.DB_PATH) as db:
        users = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        works = (await (await db.execute("SELECT COUNT(*) FROM works")).fetchone())[0]
        today = (await (await db.execute(
            "SELECT COUNT(*) FROM works WHERE date(created_at)=date('now')")).fetchone())[0]
        return {"users": users, "works": works, "today": today}


async def all_user_ids() -> list[int]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute("SELECT id FROM users")
        return [r[0] for r in await cur.fetchall()]
