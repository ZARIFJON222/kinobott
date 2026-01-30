import os
import re
import asyncio
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
import aiosqlite

load_dotenv()

# TOKEN TO'G'RIDAN-TO'G'RI YOZILDI
BOT_TOKEN = "8252174899:AAFceWh6aWmI6-LmpuAnz7iOtty69TAw30s"
# Agar .env faylingizda CHANNEL_ID bo'lsa o'shani oladi, bo'lmasa pastdagi ID ni ishlatadi
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1003762590246"))

HASHTAG_RE = re.compile(r"#(\d+)\b")
DB_PATH = "movies.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                code TEXT PRIMARY KEY,
                message_id INTEGER NOT NULL
            )
        """)
        await db.commit()

async def save_code(code: str, message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO movies(code, message_id) VALUES(?, ?) "
            "ON CONFLICT(code) DO UPDATE SET message_id=excluded.message_id",
            (code, message_id)
        )
        await db.commit()

async def get_message_id(code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT message_id FROM movies WHERE code=?", (code,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

def extract_code_from_text(text: str | None) -> str | None:
    if not text:
        return None
    m = HASHTAG_RE.search(text)
    if not m:
        return None
    return m.group(1)

def normalize_user_code(text: str) -> str | None:
    t = text.strip()
    if t.startswith("#"):
        t = t[1:].strip()
    if t.isdigit():
        return t
    return None

dp = Dispatcher()

@dp.channel_post()
async def on_channel_post(message: Message, bot: Bot):
    code = extract_code_from_text(message.text) or extract_code_from_text(message.caption)
    if not code:
        return
    await save_code(code, message.message_id)

@dp.edited_channel_post()
async def on_edited_channel_post(message: Message, bot: Bot):
    code = extract_code_from_text(message.text) or extract_code_from_text(message.caption)
    if not code:
        return
    await save_code(code, message.message_id)

@dp.message(F.chat.type.in_({"private"}))
async def on_user_message(message: Message, bot: Bot):
    code = normalize_user_code(message.text or "")
    if not code:
        await message.answer("Raqam yuboring. Masalan: 1 yoki #1")
        return

    mid = await get_message_id(code)
    if not mid:
        await message.answer(f"#{code} topilmadi. Kanalda o‘sha film postida #{code} yozilganiga ishonch hosil qiling.")
        return

    try:
        await bot.copy_message(
            chat_id=message.chat.id,
            from_chat_id=CHANNEL_ID,
            message_id=mid
        )
    except Exception as e:
        await message.answer(
            "Yuborib bo‘lmadi. Tekshirib ko‘ring:\n"
            "1) Bot kanalga ADMIN qilinganmi?\n"
            "2) Botda postlarni o‘qish huquqi bormi?"
        )

async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())