import asyncio
import logging
import os
import random
import sys
import sqlite3
from datetime import date

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

# ==========================================
# 1. DATA QISMI (Darslar va so'zlar)
# ==========================================
LEVELS = {
    "A1": {
        "emoji": "🌱",
        "label": "Boshlang'ich",
        "lessons": [
            {
                "id": "a1_l1",
                "emoji": "👋",
                "title": "Tanishuv va Salomlashish",
                "title_de": "Begrüßung und Kennenlernen",
                "grammar": "<b>Nemis tilida kishilik olmoshlari (Personalpronomen):</b>\nich - men, du - sen, er/sie/es - u, wir - biz, ihr - sizlar, sie/Sie - ular/Siz.\n\n<b>Sein (bo'lmoq) fe'lining hozirgi zamonda tuslanishi:</b>\nich bin, du bist, er/sie/es ist, wir sind, ihr seid, sie/Sie sind.",
                "words": [
                    {"de": "Hallo", "uz": "Salom", "example": "Hallo! Wie geht es dir?", "ex_uz": "Salom! Ishlaring qalay?"},
                    {"de": "Guten Tag", "uz": "Xayrli kun", "example": "Guten Tag, Herr Schmidt.", "ex_uz": "Xayrli kun, janob Shmidt."},
                    {"de": "Wie heißt du?", "uz": "Isming nima?", "example": "Wie heißt du? - Ich heiße Ali.", "ex_uz": "Isming nima? - Ismim Ali."},
                    {"de": "Auf Wiedersehen", "uz": "Xayr, ko'rishguncha", "example": "Auf Wiedersehen, bis morgen!", "ex_uz": "Xayr, ertagacha!"},
                ]
            },
            {
                "id": "a1_l2",
                "emoji": "🔢",
                "title": "Sonlar va Ranglar",
                "title_de": "Zahlen und Farben",
                "grammar": "<b>Nemis tilida sonlar (Zahlen):</b>\neins - 1, zwei - 2, drei - 3, vier - 4, fünf - 5\nsechs - 6, sieben - 7, acht - 8, neun - 9, zehn - 10\n\n<b>Ranglar (Farben):</b>\nrot - qizil, blau - ko'k, grün - yashil, gelb - sariq, schwarz - qora, weiß - oq",
                "words": [
                    {"de": "eins", "uz": "bir", "example": "Ich habe eins.", "ex_uz": "Menda bitta bor."},
                    {"de": "zwei", "uz": "ikki", "example": "Ich habe zwei Bücher.", "ex_uz": "Menda ikki kitob bor."},
                    {"de": "rot", "uz": "qizil", "example": "Das Auto ist rot.", "ex_uz": "Mashina qizil."},
                    {"de": "blau", "uz": "ko'k", "example": "Der Himmel ist blau.", "ex_uz": "Osmon ko'k."},
                ]
            }
        ]
    },
    "A2": {
        "emoji": "🌿",
        "label": "Boshlang'ichdan yuqori",
        "lessons": [
            {
                "id": "a2_l1",
                "emoji": "🏠",
                "title": "Uy va Oila",
                "title_de": "Haus und Familie",
                "grammar": "<b>Ega kelishigi (Nominativ):</b>\nder (erkak) - die (urg'ochi) - das (neytral) - die (ko'plik)\n\n<b>Tushum kelishigi (Akkusativ):</b>\nden (erkak) - die (urg'ochi) - das (neytral) - die (ko'plik)",
                "words": [
                    {"de": "die Familie", "uz": "oila", "example": "Meine Familie ist groß.", "ex_uz": "Mening oilam katta."},
                    {"de": "das Haus", "uz": "uy", "example": "Das Haus ist schön.", "ex_uz": "Uy chiroyli."},
                    {"de": "die Mutter", "uz": "ona", "example": "Meine Mutter kocht.", "ex_uz": "Mening onam pishiradi."},
                    {"de": "der Vater", "uz": "ota", "example": "Mein Vater arbeitet.", "ex_uz": "Mening otam ishlaydi."},
                ]
            }
        ]
    }
}

ACHIEVEMENTS = [
    {"id": "first_lesson", "emoji": "🎓", "title": "Birinchi dars", "desc": "Birinchi darsni tugallang", "xp": 10},
    {"id": "five_lessons", "emoji": "📚", "title": "Talaba", "desc": "5 ta darsni tugallang", "xp": 50},
    {"id": "first_quiz", "emoji": "🎯", "title": "Imtihonchi", "desc": "Birinchi viktorinani o'ynang", "xp": 15},
    {"id": "perfect_quiz", "emoji": "💯", "title": "Mukammal", "desc": "Viktorinada 100% to'plang", "xp": 100},
    {"id": "streak_3", "emoji": "🔥", "title": "3 kunlik seria", "desc": "3 kun ketma-ket o'rganish", "xp": 30},
    {"id": "streak_7", "emoji": "⚡", "title": "Haftalik seria", "desc": "7 kun ketma-ket o'rganish", "xp": 70},
    {"id": "level_5", "emoji": "⭐", "title": "5-daraja", "desc": "5-darajaga yeting", "xp": 50},
    {"id": "xp_100", "emoji": "💎", "title": "100 XP", "desc": "100 XP to'plang", "xp": 20},
]

ALL_WORDS = []
for lv_data in LEVELS.values():
    for les in lv_data["lessons"]:
        ALL_WORDS.extend(les["words"])

def get_lesson_by_id(lesson_id):
    for lv, ldata in LEVELS.items():
        for les in ldata["lessons"]:
            if les["id"] == lesson_id:
                return lv, les
    return None, None

def get_level_lessons(level_name):
    return LEVELS.get(level_name, {}).get("lessons", [])

# ==========================================
# 2. TOKEN VA LOGGING
# ==========================================
BOT_TOKEN = "8420045976:AAHnAEvxZu7WuznXMimKhRvB19YzlUCbYSA"
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class LessonState(StatesGroup):
    viewing = State()

class QuizState(StatesGroup):
    active = State()

router = Router()

# ==========================================
# 3. KEYBOARDS (Tugmalar)
# ==========================================
def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 Darslar"), KeyboardButton(text="🎯 Viktorina")],
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="🏆 Mukofotlar")],
            [KeyboardButton(text="📖 Bugungi so'z"), KeyboardButton(text="ℹ️ Yordam")],
        ],
        resize_keyboard=True
    )

def levels_kb():
    buttons = []
    for lv, ldata in LEVELS.items():
        buttons.append([InlineKeyboardButton(
            text=f"{ldata['emoji']} {lv} — {ldata['label']}",
            callback_data=f"level:{lv}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def lessons_kb(level_name, completed_ids):
    lessons = get_level_lessons(level_name)
    buttons = []
    for les in lessons:
        done = "✅ " if completed_ids and les["id"] in completed_ids else ""
        buttons.append([InlineKeyboardButton(
            text=f"{done}{les['emoji']} {les['title']}",
            callback_data=f"lesson:{les['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back:levels")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def lesson_menu_kb(lesson_id, level_name):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📖 So'zlarni o'rganish", callback_data=f"study:{lesson_id}:0"),
            InlineKeyboardButton(text="📝 Grammatika", callback_data=f"grammar:{lesson_id}"),
        ],
        [InlineKeyboardButton(text="⬅️ Darslar", callback_data=f"level:{level_name}")],
    ])

def word_nav_kb(lesson_id, idx, total, lesson_level):
    buttons = []
    nav_row = []
    if idx > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"study:{lesson_id}:{idx-1}"))
    nav_row.append(InlineKeyboardButton(text=f"{idx+1}/{total}", callback_data="noop"))
    if idx < total - 1:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"study:{lesson_id}:{idx+1}"))
    buttons.append(nav_row)
    if idx == total - 1:
        buttons.append([InlineKeyboardButton(
            text="✅ Darsni tugatish", callback_data=f"finish:{lesson_id}:{lesson_level}"
        )])
    else:
        buttons.append([InlineKeyboardButton(
            text="📝 Grammatika", callback_data=f"grammar:{lesson_id}"
        )])
    buttons.append([InlineKeyboardButton(
        text="⬅️ Dars menyusi", callback_data=f"lesson:{lesson_id}"
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def quiz_level_kb():
    buttons = []
    for lv, ldata in LEVELS.items():
        buttons.append([InlineKeyboardButton(
            text=f"{ldata['emoji']} {lv} — {ldata['label']}",
            callback_data=f"quiz_level:{lv}"
        )])
    buttons.append([InlineKeyboardButton(
        text="🔀 Aralash (barcha darajalar)", callback_data="quiz_level:ALL"
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def quiz_options_kb(options, q_idx):
    buttons = []
    for i, opt in enumerate(options):
        buttons.append([InlineKeyboardButton(
            text=opt, callback_data=f"quiz_ans:{q_idx}:{i}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def quiz_next_kb(q_idx):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="➡️ Keyingi savol", callback_data=f"quiz_next:{q_idx+1}")
    ]])

def quiz_finish_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔄 Qayta o'ynash", callback_data="quiz_replay"),
        InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back:home"),
    ]])

def ach_text(new_ach):
    if not new_ach:
        return ""
    lines = ["\n\n🎊 <b>Yangi mukofotlar:</b>"]
    for a in new_ach:
        lines.append(f"{a['emoji']} <b>{a['title']}</b> — {a['desc']} (+{a['xp']} XP)")
    return "\n".join(lines)

def level_up_text(leveled, new_level):
    if leveled:
        return f"\n\n⬆️ <b>Tabriklaymiz! Daraja {new_level} ga o'tdingiz!</b>"
    return ""

# ==========================================
# 4. HANDLERS (Bot logikasi)
# ==========================================
@router.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    get_user(msg.from_user.id, msg.from_user.username)
    name = msg.from_user.first_name or "Do'stim"
    await msg.answer(
        f"🇩🇪 <b>DeutschUz Botiga xush kelibsiz, {name}!</b>\n\n"
        f"Bu bot sizga nemis tilini o'rgatadi.\n\n"
        f"Boshlash uchun pastdagi tugmalardan foydalaning! 👇",
        parse_mode=ParseMode.HTML,
        reply_markup=main_kb()
    )

@router.message(Command("help"))
@router.message(F.text == "ℹ️ Yordam")
async def cmd_help(msg: Message):
    await msg.answer(
        "💡 <b>Yordam bo'limi</b>\n\n"
        "📚 <b>Darslar</b> — Nemischa so'zlarni o'rganing\n"
        "🎯 <b>Viktorina</b> — Bilimingizni sinab ko'ring\n"
        "📊 <b>Statistika</b> — Progressingizni kuzating\n"
        "🏆 <b>Mukofotlar</b> — Yutuqlaringizni ko'ring\n"
        "📖 <b>Bugungi so'z</b> — Kunlik yangi so'z\n\n"
        "Har kuni o'rganib boring va streak yig'ing! 🔥",
        parse_mode=ParseMode.HTML
    )

@router.message(F.text == "📚 Darslar")
async def show_levels(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("📚 <b>Daraja tanlang:</b>", parse_mode=ParseMode.HTML, reply_markup=levels_kb())

@router.callback_query(F.data.startswith("level:"))
async def show_lessons(cb: CallbackQuery):
    try:
        level_name = cb.data.split(":")[1]
        if level_name not in LEVELS:
            await cb.answer("Daraja topilmadi!")
            return
        ldata = LEVELS[level_name]
        completed = get_completed(cb.from_user.id) or []
        lessons = ldata["lessons"]
        done_count = sum(1 for l in lessons if l["id"] in completed)
        await cb.message.edit_text(
            f"{ldata['emoji']} <b>{level_name} — {ldata['label']}</b>\n\n"
            f"📊 Tugallangan: {done_count}/{len(lessons)} dars\n\nDars tanlang:",
            parse_mode=ParseMode.HTML,
            reply_markup=lessons_kb(level_name, completed)
        )
    except Exception as e:
        logging.error(f"Xatolik show_lessons ichida: {e}")
    await cb.answer()

@router.callback_query(F.data.startswith("lesson:"))
async def show_lesson_menu(cb: CallbackQuery):
    lesson_id = cb.data.split(":")[1]
    level_name, lesson = get_lesson_by_id(lesson_id)
    if not lesson:
        await cb.answer("Dars topilmadi!")
        return
    completed = get_completed(cb.from_user.id) or []
    done = "✅ " if lesson_id in completed else ""
    await cb.message.edit_text(
        f"{lesson['emoji']} <b>{done}{lesson['title']}</b>\n<i>{lesson['title_de']}</i>\n\n"
        f"📝 So'zlar soni: {len(lesson['words'])}\n\nQuyidagi tugmalardan birini tanlang:",
        parse_mode=ParseMode.HTML,
        reply_markup=lesson_menu_kb(lesson_id, level_name)
    )
    await cb.answer()

@router.callback_query(F.data.startswith("study:"))
async def study_word(cb: CallbackQuery):
    parts = cb.data.split(":")
    lesson_id = parts[1]
    idx = int(parts[2])
    level_name, lesson = get_lesson_by_id(lesson_id)
    if not lesson:
        await cb.answer("Dars topilmadi!")
        return
    words = lesson["words"]
    idx = min(idx, len(words) - 1)
    w = words[idx]
    await cb.message.edit_text(
        f"📖 <b>{lesson['emoji']} {lesson['title']}</b> — so'z {idx+1}/{len(words)}\n\n"
        f"🇩🇪 <b>{w['de']}</b>\n🇺🇿 {w['uz']}\n\n"
        f"📝 <b>Misol:</b>\n<i>{w['example']}</i>\n<i>{w['ex_uz']}</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=word_nav_kb(lesson_id, idx, len(words), level_name)
    )
    await cb.answer()

@router.callback_query(F.data.startswith("grammar:"))
async def show_grammar(cb: CallbackQuery):
    lesson_id = cb.data.split(":")[1]
    level_name, lesson = get_lesson_by_id(lesson_id)
    if not lesson:
        await cb.answer("Dars topilmadi!")
        return
    gram = lesson.get("grammar", "Grammatika mavjud emas.")
    await cb.message.edit_text(
        f"📖 <b>Grammatika</b> — {lesson['title']}\n\n{gram}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ Dars menyusi", callback_data=f"lesson:{lesson_id}")
        ]])
    )
    await cb.answer()

@router.callback_query(F.data.startswith("finish:"))
async def finish_lesson(cb: CallbackQuery):
    parts = cb.data.split(":")
    lesson_id = parts[1]
    level_name = parts[2]
    user_id = cb.from_user.id
    newly = complete_lesson(user_id, lesson_id)
    xp_gain = 20 if newly else 5
    new_xp, new_level, leveled = add_xp(user_id, xp_gain)
    completed = get_completed(user_id) or []
    stats = get_stats(user_id)
    new_ach = check_and_award(user_id, completed, stats)
    cur, nxt = xp_for_next(new_xp)
    text = (
        f"🎉 <b>Dars tugadi!</b>\n\n"
        f"{'✨ Yangi dars yakunlandi!' if newly else '🔄 Dars qayta o\'tildi.'}\n"
        f"+{xp_gain} XP qo'shildi!\n\n"
        f"💎 Jami XP: {new_xp}\n"
        f"⭐ Daraja: {new_level} ({cur}/{nxt})"
    )
    text += level_up_text(leveled, new_level)
    text += ach_text(new_ach)
    await cb.message.edit_text(
        text, parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📚 Darslarga qaytish", callback_data=f"level:{level_name}")],
            [InlineKeyboardButton(text="🎯 Viktorina", callback_data=f"quiz_level:{level_name}")],
        ])
    )
    await cb.answer("✅ Dars yakunlandi!")

@router.callback_query(F.data == "back:levels")
async def back_to_levels(cb: CallbackQuery):
    await cb.message.edit_text("📚 <b>Daraja tanlang:</b>", parse_mode=ParseMode.HTML, reply_markup=levels_kb())
    await cb.answer()

@router.callback_query(F.data == "back:home")
async def back_home(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.delete()
    await cb.message.answer("🏠 Bosh menyu:", reply_markup=main_kb())
    await cb.answer()

# ==========================================
# 5. VIKTORINA QISMI
# ==========================================
@router.message(F.text == "🎯 Viktorina")
async def quiz_menu(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("🎯 <b>Viktorina</b>\n\nQaysi darajadan o'ynaysiz?", parse_mode=ParseMode.HTML, reply_markup=quiz_level_kb())

@router.callback_query(F.data.startswith("quiz_level:"))
async def start_quiz(cb: CallbackQuery, state: FSMContext):
    level = cb.data.split(":")[1]
    if level == "ALL":
        pool = list({w["de"]: w for w in ALL_WORDS}.values())
        level_label = "Aralash"
    else:
        pool = []
        for les in get_level_lessons(level):
            pool.extend(les["words"])
        pool = list({w["de"]: w for w in pool}.values())
        level_label = f"{level} — {LEVELS[level]['label']}"
    if len(pool) < 4:
        await cb.answer("Bu darajada savollar kam!", show_alert=True)
        return
    random.shuffle(pool)
    selected = pool[:10]
    questions = []
    for w in selected:
        others = [o for o in pool if o["de"] != w["de"]]
        wrongs = random.sample(others, min(3, len(others)))
        opts = random.sample([w["uz"]] + [x["uz"] for x in wrongs], len(wrongs) + 1)
        questions.append({"de": w["de"], "correct": w["uz"], "opts": opts})
    await state.update_data(questions=questions, q_idx=0, score=0, level=level, level_label=level_label)
    q = questions[0]
    await cb.message.edit_text(
        f"🎯 <b>Viktorina</b> — {level_label}\n\nSavol 1/{len(questions)}\n\n"
        f"🇩🇪 <b>{q['de']}</b> — O'zbekcha tarjimasi nima?",
        parse_mode=ParseMode.HTML,
        reply_markup=quiz_options_kb(q["opts"], 0)
    )
    await state.set_state(QuizState.active)
    await cb.answer()

@router.callback_query(QuizState.active, F.data.startswith("quiz_ans:"))
async def quiz_answer(cb: CallbackQuery, state: FSMContext):
    parts = cb.data.split(":")
    q_idx = int(parts[1])
    opt_idx = int(parts[2])
    data = await state.get_data()
    questions = data["questions"]
    if q_idx >= len(questions):
        await cb.answer()
        return
    q = questions[q_idx]
    chosen = q["opts"][opt_idx]
    correct = q["correct"]
    is_correct = chosen == correct
    score = data["score"] + (1 if is_correct else 0)
    await state.update_data(score=score)
    feedback = f"✅ <b>To'g'ri!</b> {chosen}" if is_correct else f"❌ <b>Noto'g'ri.</b>\nTo'g'ri javob: <b>{correct}</b>"
    total = len(questions)
    text = (
        f"🎯 <b>Viktorina</b> — {data['level_label']}\n\n"
        f"Savol {q_idx+1}/{total}\n\n"
        f"🇩🇪 <b>{q['de']}</b>\n\n{feedback}\n\nBall: {score}/{q_idx+1}"
    )
    if q_idx + 1 >= total:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="📊 Natijani ko'rish", callback_data="quiz_result")
        ]])
    else:
        keyboard = quiz_next_kb(q_idx)
    await cb.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    await cb.answer("✅" if is_correct else "❌")

@router.callback_query(QuizState.active, F.data.startswith("quiz_next:"))
async def quiz_next(cb: CallbackQuery, state: FSMContext):
    q_idx = int(cb.data.split(":")[1])
    data = await state.get_data()
    questions = data["questions"]
    if q_idx >= len(questions):
        await cb.answer()
        return
    q = questions[q_idx]
    await cb.message.edit_text(
        f"🎯 <b>Viktorina</b> — {data['level_label']}\n\nSavol {q_idx+1}/{len(questions)}\n\n"
        f"🇩🇪 <b>{q['de']}</b> — O'zbekcha tarjimasi nima?",
        parse_mode=ParseMode.HTML,
        reply_markup=quiz_options_kb(q["opts"], q_idx)
    )
    await cb.answer()

@router.callback_query(F.data == "quiz_result")
async def quiz_result(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    score = data["score"]
    total = len(data["questions"])
    level = data["level"]
    level_label = data["level_label"]
    pct = round(score / total * 100) if total else 0
    xp_gain = score * 10
    user_id = cb.from_user.id
    save_quiz(user_id, level, score, total)
    new_xp, new_level, leveled = add_xp(user_id, xp_gain)
    completed = get_completed(user_id) or []
    stats = get_stats(user_id)
    new_ach = check_and_award(user_id, completed, stats, quiz_pct=pct)
    if pct >= 90:   emoji, msg2 = "🏆", "Ajoyib natija!"
    elif pct >= 70: emoji, msg2 = "⭐", "Yaxshi natija!"
    elif pct >= 50: emoji, msg2 = "👍", "Davom eting!"
    else:           emoji, msg2 = "💪", "Ko'proq mashq qiling!"
    cur, nxt = xp_for_next(new_xp)
    text = (
        f"{emoji} <b>Viktorina yakunlandi!</b>\n\n"
        f"📊 Daraja: {level_label}\n"
        f"✅ To'g'ri: {score}/{total} ({pct}%)\n"
        f"💰 +{xp_gain} XP\n\n"
        f"⭐ Daraja: {new_level} ({cur}/{nxt} XP)\n\n{msg2}"
    )
    text += level_up_text(leveled, new_level)
    text += ach_text(new_ach)
    await state.clear()
    await cb.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=quiz_finish_kb())
    await cb.answer()

@router.callback_query(F.data == "quiz_replay")
async def quiz_replay(cb: CallbackQuery):
    await cb.message.edit_text("🎯 <b>Viktorina</b>\n\nQaysi darajadan o'ynaysiz?", parse_mode=ParseMode.HTML, reply_markup=quiz_level_kb())
    await cb.answer()

@router.message(F.text == "📊 Statistika")
@router.message(Command("stats"))
async def show_stats(msg: Message):
    get_user(msg.from_user.id, msg.from_user.username)
    s = get_stats(msg.from_user.id)
    total_lessons = sum(len(ldata["lessons"]) for ldata in LEVELS.values())
    cur, nxt = xp_for_next(s["xp"])
    bar = "█" * int(cur / nxt * 10) + "░" * (10 - int(cur / nxt * 10))
    await msg.answer(
        f"📊 <b>Sizning statistikangiz</b>\n\n"
        f"⭐ Daraja: <b>{s['level']}</b>\n"
        f"💎 Jami XP: <b>{s['xp']}</b>\n"
        f"[{bar}] {cur}/{nxt}\n\n"
        f"🔥 Streak: <b>{s['streak']} kun</b>\n"
        f"📚 Darslar: <b>{s['completed']}/{total_lessons}</b>\n"
        f"🎯 Viktorinalar: <b>{s['quizzes']}</b>\n"
        f"📈 O'rtacha ball: <b>{s['avg_score']}%</b>\n"
        f"🏆 Mukofotlar: <b>{s['achievements']}/{len(ACHIEVEMENTS)}</b>\n\n"
        f"{'✅ Bugungi maqsad bajarildi!' if s['daily_done'] else '⏳ Bugungi maqsad: 1 dars o\'rgan'}",
        parse_mode=ParseMode.HTML
    )

@router.message(F.text == "🏆 Mukofotlar")
@router.message(Command("achievements"))
async def show_achievements(msg: Message):
    conn = get_db()
    c = conn.cursor()
    earned = [r["ach_id"] for r in c.execute("SELECT ach_id FROM achievements WHERE user_id=?", (msg.from_user.id,)).fetchall()]
    conn.close()
    lines = ["🏆 <b>Mukofotlar</b>\n"]
    for a in ACHIEVEMENTS:
        if a["id"] in earned:
            lines.append(f"{a['emoji']} <b>{a['title']}</b> — {a['desc']}")
        else:
            lines.append(f"🔒 <i>{a['title']}</i> — {a['desc']}")
    lines.append(f"\n✅ Earned: {len(earned)}/{len(ACHIEVEMENTS)}")
    await msg.answer("\n".join(lines), parse_mode=ParseMode.HTML)

@router.message(F.text == "📖 Bugungi so'z")
@router.message(Command("word"))
async def daily_word(msg: Message):
    seed = int(date.today().strftime("%Y%m%d"))
    random.seed(seed)
    word = random.choice(ALL_WORDS)
    random.seed()
    await msg.answer(
        f"📖 <b>Bugungi so'z</b>\n\n"
        f"🇩🇪 <b>{word['de']}</b>\n🇺🇿 {word['uz']}\n\n"
        f"📝 <b>Misol:</b>\n<i>{word['example']}</i>\n<i>{word['ex_uz']}</i>",
        parse_mode=ParseMode.HTML
    )

@router.message(Command("reset"))
async def reset_progress(msg: Message):
    await msg.answer(
        "⚠️ <b>Haqiqatan ham barcha progressingizni o'chirmoqchimisiz?</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Ha, o'chir", callback_data="confirm_reset"),
            InlineKeyboardButton(text="❌ Yo'q", callback_data="back:home"),
        ]])
    )

@router.callback_query(F.data == "confirm_reset")
async def confirm_reset(cb: CallbackQuery, state: FSMContext):
    conn = get_db()
    c = conn.cursor()
    uid = cb.from_user.id
    c.execute("DELETE FROM progress WHERE user_id=?", (uid,))
    c.execute("DELETE FROM quiz_history WHERE user_id=?", (uid,))
    c.execute("DELETE FROM achievements WHERE user_id=?", (uid,))
    c.execute("UPDATE users SET xp=0, level=1, streak=0, daily_done=0 WHERE user_id=?", (uid,))
    conn.commit()
    conn.close()
    await state.clear()
    await cb.message.edit_text("🗑️ Barcha progress o'chirildi.\n\n/start bilan qayta boshlang.")
    await cb.answer()

@router.callback_query(F.data == "noop")
async def noop(cb: CallbackQuery):
    await cb.answer()

# ==========================================
# 6. DATABASE LOGIKASI (sqlite3)
# ==========================================
DB_PATH = "users.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            xp          INTEGER DEFAULT 0,
            level       INTEGER DEFAULT 1,
            streak      INTEGER DEFAULT 0,
            last_active TEXT DEFAULT '',
            daily_done  INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS progress (
            user_id     INTEGER,
            lesson_id   TEXT,
            completed   INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, lesson_id)
        );
        CREATE TABLE IF NOT EXISTS quiz_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            level_name  TEXT,
            score       INTEGER,
            total       INTEGER,
            percent     INTEGER,
            played_at   TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS achievements (
            user_id     INTEGER,
            ach_id      TEXT,
            earned_at   TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, ach_id)
        );
    """)
    conn.commit()
    conn.close()

def get_user(user_id, username=None):
    conn = get_db()
    c = conn.cursor()
    user = c.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not user:
        c.execute("INSERT INTO users (user_id, username) VALUES (?, ?)", (user_id, username or ""))
        conn.commit()
        user = c.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    today = str(date.today())
    if user["last_active"] != today:
        last = user["last_active"]
        new_streak = user["streak"]
        if last:
            try:
                diff = (date.today() - date.fromisoformat(last)).days
                new_streak = new_streak + 1 if diff == 1 else 1
            except Exception:
                new_streak = 1
        else:
            new_streak = 1
        c.execute("UPDATE users SET last_active=?, streak=?, daily_done=0 WHERE user_id=?", (today, new_streak, user_id))
        conn.commit()
        user = c.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return dict(user)

def xp_to_level(xp):
    level = 1
    needed = 100
    while xp >= needed:
        xp -= needed
        level += 1
        needed = int(needed * 1.2)
    return level

def xp_for_next(total_xp):
    xp = total_xp
    needed = 100
    while xp >= needed:
        xp -= needed
        needed = int(needed * 1.2)
    return xp, needed

def add_xp(user_id, amount):
    conn = get_db()
    c = conn.cursor()
    user = c.execute("SELECT xp, level FROM users WHERE user_id=?", (user_id,)).fetchone()
    new_xp = (user["xp"] or 0) + amount
    new_level = xp_to_level(new_xp)
    leveled = new_level > (user["level"] or 1)
    daily_done = 1
    c.execute("UPDATE users SET xp=?, level=?, daily_done=? WHERE user_id=?",
              (new_xp, new_level, daily_done, user_id))
    conn.commit()
    conn.close()
    return new_xp, new_level, leveled

def complete_lesson(user_id, lesson_id):
    conn = get_db()
    c = conn.cursor()
    existing = c.execute("SELECT completed FROM progress WHERE user_id=? AND lesson_id=?",
                         (user_id, lesson_id)).fetchone()
    if existing:
        conn.close()
        return False
    c.execute("INSERT INTO progress (user_id, lesson_id, completed) VALUES (?, ?, 1)",
              (user_id, lesson_id))
    conn.commit()
    conn.close()
    return True

def get_completed(user_id):
    conn = get_db()
    c = conn.cursor()
    rows = c.execute("SELECT lesson_id FROM progress WHERE user_id=? AND completed=1",
                     (user_id,)).fetchall()
    conn.close()
    return [r["lesson_id"] for r in rows]

def save_quiz(user_id, level_name, score, total):
    pct = round(score / total * 100) if total else 0
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO quiz_history (user_id, level_name, score, total, percent) VALUES (?, ?, ?, ?, ?)",
              (user_id, level_name, score, total, pct))
    conn.commit()
    conn.close()

def get_stats(user_id):
    conn = get_db()
    c = conn.cursor()
    user = c.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not user:
        conn.close()
        return {"xp": 0, "level": 1, "streak": 0, "completed": 0,
                "quizzes": 0, "avg_score": 0, "achievements": 0, "daily_done": 0}
    completed = c.execute("SELECT COUNT(*) as cnt FROM progress WHERE user_id=? AND completed=1",
                          (user_id,)).fetchone()["cnt"]
    quizzes = c.execute("SELECT COUNT(*) as cnt FROM quiz_history WHERE user_id=?",
                        (user_id,)).fetchone()["cnt"]
    avg_row = c.execute("SELECT AVG(percent) as avg FROM quiz_history WHERE user_id=?",
                        (user_id,)).fetchone()
    avg_score = round(avg_row["avg"] or 0)
    achievements = c.execute("SELECT COUNT(*) as cnt FROM achievements WHERE user_id=?",
                              (user_id,)).fetchone()["cnt"]
    conn.close()
    return {
        "xp": user["xp"] or 0,
        "level": user["level"] or 1,
        "streak": user["streak"] or 0,
        "completed": completed,
        "quizzes": quizzes,
        "avg_score": avg_score,
        "achievements": achievements,
        "daily_done": user["daily_done"] or 0,
    }

def check_and_award(user_id, completed, stats, quiz_pct=None):
    conn = get_db()
    c = conn.cursor()
    earned = [r["ach_id"] for r in c.execute("SELECT ach_id FROM achievements WHERE user_id=?",
                                              (user_id,)).fetchall()]
    new_ach = []
    def award(ach_id):
        if ach_id not in earned:
            a = next((x for x in ACHIEVEMENTS if x["id"] == ach_id), None)
            if a:
                c.execute("INSERT INTO achievements (user_id, ach_id) VALUES (?, ?)", (user_id, ach_id))
                new_ach.append(a)

    if len(completed) >= 1:    award("first_lesson")
    if len(completed) >= 5:    award("five_lessons")
    if stats["quizzes"] >= 1:  award("first_quiz")
    if quiz_pct == 100:        award("perfect_quiz")
    if stats["streak"] >= 3:   award("streak_3")
    if stats["streak"] >= 7:   award("streak_7")
    if stats["level"] >= 5:    award("level_5")
    if stats["xp"] >= 100:     award("xp_100")

    conn.commit()
    conn.close()
    return new_ach

# ==========================================
# 7. MAIN RUNNER
# ==========================================
async def main():
    try:
        init_db()
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        dp = Dispatcher(storage=MemoryStorage())
        dp.include_router(router)
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Bot muvaffaqiyatli ishga tushdi!")
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ Xatolik yuz berdi: {e}")

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
