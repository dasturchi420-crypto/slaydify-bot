import asyncio
import html
import logging
import os
import re
import uuid

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (CallbackQuery, FSInputFile, InlineKeyboardButton,
                           InlineKeyboardMarkup, KeyboardButton, Message,
                           ReplyKeyboardMarkup)
from aiogram.utils.keyboard import InlineKeyboardBuilder

import ai
import config
import db
import pptx_builder

logging.basicConfig(level=logging.INFO)
router = Router()
gate = asyncio.Semaphore(config.MAX_PARALLEL)  # bir vaqtda faqat shuncha ish; qolgani navbatda

BTN_PRES = "🎓 Taqdimot yaratish"
BTN_ANIM = "✨ Animatsion slayd"
BTN_TEST = "📝 Test yaratish"
BTN_REF = "📚 Referat"
BTN_IND = "📘 Mustaqil ish"
BTN_BAL = "💰 Hisobim"
BTN_HIST = "🗂 Ishlarim"
BTN_INV = "🎁 Do'st taklif qilish"

MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN_PRES)],
        [KeyboardButton(text=BTN_ANIM)],
        [KeyboardButton(text=BTN_TEST)],
        [KeyboardButton(text=BTN_REF), KeyboardButton(text=BTN_IND)],
        [KeyboardButton(text=BTN_BAL), KeyboardButton(text=BTN_HIST)],
        [KeyboardButton(text=BTN_INV)],
    ],
    resize_keyboard=True,
)

CANCEL_KB = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")]]
)


class Pres(StatesGroup):
    topic = State()
    count = State()
    lang = State()
    theme = State()


def e(s: str) -> str:
    return html.escape(s)


# ---------------------------------------------------------------- start / menyu
@router.message(CommandStart())
async def start(m: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    ref = int(command.args) if command.args and command.args.isdigit() else None
    new = await db.ensure_user(m.from_user.id, m.from_user.username, m.from_user.full_name, ref)
    if new and ref:
        try:
            await m.bot.send_message(ref, "🎉 Siz taklif qilgan do'st botga qo'shildi! +1 bepul ish.")
        except Exception:
            pass
    await m.answer(
        f"👋 Assalomu alaykum, <b>{e(m.from_user.full_name)}</b>!\n\n"
        "Men juda yuqori darajada <b>taqdimotlar</b> va <b>testlar</b> tayyorlab beruvchi botman.\n"
        f"🎁 Sizga <b>{await db.get_credits(m.from_user.id)} ta bepul ish</b> berildi.\n\n"
        "Kerakli bo'limni tanlang 👇",
        reply_markup=MENU,
    )


@router.callback_query(F.data == "cancel")
async def cancel(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.edit_text("❌ Bekor qilindi.")
    await c.answer()


@router.message(Command("cancel"))
async def cancel_cmd(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("❌ Bekor qilindi.", reply_markup=MENU)


@router.message(F.text.in_({BTN_ANIM, BTN_TEST, BTN_REF, BTN_IND}))
async def soon(m: Message):
    await m.answer("🛠 Bu bo'lim tez orada ishga tushadi. Hozircha <b>Taqdimot yaratish</b> ishlaydi.")


@router.message(F.text == BTN_BAL)
async def balance(m: Message):
    await m.answer(f"💰 Qolgan ishlaringiz: <b>{await db.get_credits(m.from_user.id)}</b>")


@router.message(F.text == BTN_INV)
async def invite(m: Message):
    me = await m.bot.get_me()
    n = await db.referral_count(m.from_user.id)
    await m.answer(
        "🎁 Har bir taklif qilgan do'stingiz uchun <b>+1 bepul ish</b> olasiz.\n\n"
        f"Sizning havolangiz:\nhttps://t.me/{me.username}?start={m.from_user.id}\n\n"
        f"Taklif qilinganlar: <b>{n}</b>"
    )


@router.message(F.text == BTN_HIST)
async def my_works(m: Message):
    rows = await db.history(m.from_user.id)
    if not rows:
        await m.answer("Hali ishlaringiz yo'q.")
        return
    await m.answer("🗂 So'nggi ishlaringiz yuborilmoqda...")
    for kind, topic, file_id in reversed(rows):
        await m.answer_document(file_id, caption=f"{e(kind)}: {e(topic)}")


# ---------------------------------------------------------------- taqdimot oqimi
@router.message(F.text == BTN_PRES)
async def pres_start(m: Message, state: FSMContext):
    await db.ensure_user(m.from_user.id, m.from_user.username, m.from_user.full_name)
    if await db.get_credits(m.from_user.id) < 1:
        await m.answer("😔 Bepul ishlaringiz tugadi. Do'st taklif qilib yangi ish oling: "
                       f"<b>{BTN_INV}</b>")
        return
    await state.set_state(Pres.topic)
    await m.answer("📝 Taqdimot <b>mavzusini</b> yozing:\n<i>Masalan: Amir Temur va Temuriylar davri</i>",
                   reply_markup=CANCEL_KB)


@router.message(Pres.topic, F.text)
async def pres_topic(m: Message, state: FSMContext):
    topic = m.text.strip()
    if len(topic) < 3 or len(topic) > 200:
        await m.answer("Mavzu 3 tadan 200 tagacha belgi bo'lishi kerak. Qayta yozing:")
        return
    await state.update_data(topic=topic)
    await state.set_state(Pres.count)
    kb = InlineKeyboardBuilder()
    for n in (6, 8, 10, 12, 15, 20):
        kb.button(text=f"{n} slayd", callback_data=f"cnt:{n}")
    kb.adjust(3)
    await m.answer("📊 Nechta slayd bo'lsin?", reply_markup=kb.as_markup())


@router.callback_query(Pres.count, F.data.startswith("cnt:"))
async def pres_count(c: CallbackQuery, state: FSMContext):
    await state.update_data(count=int(c.data.split(":")[1]))
    await state.set_state(Pres.lang)
    kb = InlineKeyboardBuilder()
    kb.button(text="🇺🇿 O'zbekcha", callback_data="lng:uz")
    kb.button(text="🇷🇺 Русский", callback_data="lng:ru")
    kb.button(text="🇬🇧 English", callback_data="lng:en")
    kb.adjust(3)
    await c.message.edit_text("🌐 Qaysi tilda bo'lsin?", reply_markup=kb.as_markup())
    await c.answer()


@router.callback_query(Pres.lang, F.data.startswith("lng:"))
async def pres_lang(c: CallbackQuery, state: FSMContext):
    await state.update_data(lang=c.data.split(":")[1])
    await state.set_state(Pres.theme)
    kb = InlineKeyboardBuilder()
    for key, t in pptx_builder.THEMES.items():
        kb.button(text=t["name"], callback_data=f"thm:{key}")
    kb.adjust(2)
    await c.message.edit_text("🎨 Dizaynni tanlang:", reply_markup=kb.as_markup())
    await c.answer()


@router.callback_query(Pres.theme, F.data.startswith("thm:"))
async def pres_theme(c: CallbackQuery, state: FSMContext):
    theme = c.data.split(":")[1]
    data = await state.get_data()
    await state.clear()
    await c.answer()

    if not await db.spend_credit(c.from_user.id):
        await c.message.edit_text("😔 Bepul ishlaringiz tugadi.")
        return

    status = await c.message.edit_text(
        f"⏳ <b>{e(data['topic'])}</b> bo'yicha taqdimot tayyorlanmoqda...\n"
        "Odatda 20-60 soniya oladi. Navbat bo'lsa biroz kutish mumkin.")
    os.makedirs(config.OUT_DIR, exist_ok=True)
    path = os.path.join(config.OUT_DIR, f"{uuid.uuid4().hex}.pptx")
    ok = False
    try:
        async with gate:
            content = await ai.generate_presentation(data["topic"], data["count"], data["lang"])
            await asyncio.to_thread(pptx_builder.build, content, theme, path, data["lang"])
        safe = re.sub(r"[^\w\- ]", "", data["topic"], flags=re.U).strip()[:40] or "taqdimot"
        sent = await c.message.answer_document(
            FSInputFile(path, filename=f"{safe}.pptx"),
            caption=f"✅ Tayyor! <b>{e(content.get('title', data['topic']))}</b>\n"
                    f"Slaydlar: {len(content['slides']) + 2}",
            reply_markup=MENU,
        )
        await db.log_work(c.from_user.id, "Taqdimot", data["topic"], sent.document.file_id)
        ok = True
        await status.delete()
    except Exception:
        logging.exception("Taqdimot yaratishda xato")
        await status.edit_text("😔 Xatolik yuz berdi. Ish hisobingizdan yechilmadi, qayta urinib ko'ring.")
    finally:
        if not ok:
            await db.add_credits(c.from_user.id, 1)
        if os.path.exists(path):
            os.remove(path)


# ---------------------------------------------------------------- admin
def admin_only(m: Message) -> bool:
    return m.from_user.id in config.ADMIN_IDS


@router.message(Command("stats"), admin_only)
async def stats(m: Message):
    s = await db.stats()
    await m.answer(f"👥 Foydalanuvchilar: <b>{s['users']}</b>\n"
                   f"📄 Jami ishlar: <b>{s['works']}</b>\n📅 Bugun: <b>{s['today']}</b>")


@router.message(Command("addcredit"), admin_only)
async def addcredit(m: Message, command: CommandObject):
    try:
        uid, n = (int(x) for x in command.args.split())
    except Exception:
        await m.answer("Format: /addcredit <user_id> <soni>")
        return
    await db.add_credits(uid, n)
    await m.answer("✅ Qo'shildi.")


@router.message(Command("broadcast"), admin_only)
async def broadcast(m: Message, command: CommandObject):
    if not command.args:
        await m.answer("Format: /broadcast <matn>")
        return
    sent = 0
    for uid in await db.all_user_ids():
        try:
            await m.bot.send_message(uid, command.args)
            sent += 1
        except Exception:
            pass
        await asyncio.sleep(0.05)  # Telegram limitiga tushmaslik uchun
    await m.answer(f"📣 Yuborildi: {sent}")


async def main():
    if not config.BOT_TOKEN:
        raise SystemExit("BOT_TOKEN kiritilmagan. .env faylni to'ldiring.")
    await db.init()
    bot = Bot(config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
