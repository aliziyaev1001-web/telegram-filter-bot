"""
╔══════════════════════════════════════════════════════╗
║           TELEGRAM QUIZ BOT — Викторина              ║
║     Работает в личных сообщениях и в группах         ║
╚══════════════════════════════════════════════════════╝

УСТАНОВКА:
    py -m pip install python-telegram-bot

ЗАПУСК:
    1. Получите токен у @BotFather
    2. Вставьте токен в BOT_TOKEN ниже
    3. py quiz_bot.py

КОМАНДЫ:
    /quiz      — начать викторину (10 вопросов)
    /score     — посмотреть свой рекорд
    /top       — таблица лидеров
    /stop      — остановить викторину
    /help      — справка
"""

import logging
import json
import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ─────────────────────────────────────────────
#   НАСТРОЙКИ
# ─────────────────────────────────────────────

BOT_TOKEN = "8720056848:AAH_qboF7PGGxROqTJ1icoKxlq64n_DB9Qw"
DATA_FILE = "quiz_data.json"
QUESTIONS_PER_GAME = 10  # Вопросов за одну игру

# ─────────────────────────────────────────────
#   ВОПРОСЫ
# ─────────────────────────────────────────────

ALL_QUESTIONS = [
    # 🌍 География
    {"q": "Какая самая длинная река в мире?", "a": "Нил", "opts": ["Амазонка", "Нил", "Янцзы", "Миссисипи"]},
    {"q": "Столица Австралии?", "a": "Канберра", "opts": ["Сидней", "Мельбурн", "Канберра", "Брисбен"]},
    {"q": "Какой океан самый большой?", "a": "Тихий", "opts": ["Атлантический", "Индийский", "Тихий", "Северный Ледовитый"]},
    {"q": "В какой стране находится Эйфелева башня?", "a": "Франция", "opts": ["Италия", "Германия", "Франция", "Испания"]},
    {"q": "Какой континент самый большой?", "a": "Азия", "opts": ["Африка", "Азия", "Северная Америка", "Европа"]},
    {"q": "Столица Японии?", "a": "Токио", "opts": ["Осака", "Токио", "Киото", "Хиросима"]},
    {"q": "Какая гора самая высокая в мире?", "a": "Эверест", "opts": ["К2", "Эверест", "Аконкагуа", "Монблан"]},
    {"q": "Столица Бразилии?", "a": "Бразилиа", "opts": ["Рио-де-Жанейро", "Сан-Паулу", "Бразилиа", "Сальвадор"]},
    {"q": "Сколько стран в Африке?", "a": "54", "opts": ["44", "54", "62", "48"]},
    {"q": "Какой город называют «Вечным городом»?", "a": "Рим", "opts": ["Афины", "Рим", "Иерусалим", "Каир"]},

    # 🔬 Наука
    {"q": "Сколько планет в Солнечной системе?", "a": "8", "opts": ["7", "8", "9", "10"]},
    {"q": "Из чего состоит вода?", "a": "H₂O", "opts": ["CO₂", "H₂O", "O₂", "NaCl"]},
    {"q": "Какой элемент обозначается Au?", "a": "Золото", "opts": ["Серебро", "Медь", "Золото", "Алюминий"]},
    {"q": "Скорость света примерно равна?", "a": "300 000 км/с", "opts": ["150 000 км/с", "300 000 км/с", "500 000 км/с", "1 000 000 км/с"]},
    {"q": "Кто открыл теорию относительности?", "a": "Эйнштейн", "opts": ["Ньютон", "Эйнштейн", "Дарвин", "Галилей"]},
    {"q": "Сколько хромосом у человека?", "a": "46", "opts": ["23", "44", "46", "48"]},
    {"q": "Какой газ растения выделяют при фотосинтезе?", "a": "Кислород", "opts": ["CO₂", "Азот", "Кислород", "Водород"]},
    {"q": "Что изучает орнитология?", "a": "Птицы", "opts": ["Насекомые", "Рыбы", "Птицы", "Рептилии"]},
    {"q": "Самая маленькая планета Солнечной системы?", "a": "Меркурий", "opts": ["Марс", "Венера", "Меркурий", "Плутон"]},
    {"q": "Кто создал таблицу химических элементов?", "a": "Менделеев", "opts": ["Ломоносов", "Менделеев", "Курчатов", "Павлов"]},

    # 📚 История
    {"q": "В каком году началась Вторая мировая война?", "a": "1939", "opts": ["1937", "1938", "1939", "1941"]},
    {"q": "Кто был первым президентом США?", "a": "Вашингтон", "opts": ["Линкольн", "Вашингтон", "Джефферсон", "Адамс"]},
    {"q": "В каком году человек впервые полетел в космос?", "a": "1961", "opts": ["1957", "1959", "1961", "1963"]},
    {"q": "Кто первым полетел в космос?", "a": "Гагарин", "opts": ["Титов", "Гагарин", "Армстронг", "Леонов"]},
    {"q": "В каком году пала Берлинская стена?", "a": "1989", "opts": ["1985", "1987", "1989", "1991"]},
    {"q": "Кто написал «Войну и мир»?", "a": "Толстой", "opts": ["Достоевский", "Толстой", "Тургенев", "Чехов"]},
    {"q": "В каком году была Французская революция?", "a": "1789", "opts": ["1769", "1779", "1789", "1799"]},
    {"q": "Кто был последним российским императором?", "a": "Николай II", "opts": ["Александр III", "Николай II", "Александр II", "Павел I"]},

    # 🎬 Культура и спорт
    {"q": "Сколько колец на олимпийском флаге?", "a": "5", "opts": ["4", "5", "6", "7"]},
    {"q": "Какая страна выиграла ЧМ по футболу больше всего раз?", "a": "Бразилия", "opts": ["Германия", "Аргентина", "Бразилия", "Италия"]},
    {"q": "Кто написал «Ромео и Джульетту»?", "a": "Шекспир", "opts": ["Данте", "Шекспир", "Гёте", "Мольер"]},
    {"q": "В каком городе проходили первые современные Олимпийские игры?", "a": "Афины", "opts": ["Париж", "Лондон", "Афины", "Рим"]},
    {"q": "Кто нарисовал «Мону Лизу»?", "a": "Да Винчи", "opts": ["Микеланджело", "Да Винчи", "Рафаэль", "Боттичелли"]},
    {"q": "Сколько игроков в баскетбольной команде на поле?", "a": "5", "opts": ["4", "5", "6", "7"]},
    {"q": "Из какой страны Моцарт?", "a": "Австрия", "opts": ["Германия", "Австрия", "Италия", "Швейцария"]},

    # 🧠 Разное
    {"q": "Сколько дней в високосном году?", "a": "366", "opts": ["364", "365", "366", "367"]},
    {"q": "Сколько секунд в одном часе?", "a": "3600", "opts": ["600", "1800", "3600", "7200"]},
    {"q": "Какое животное является символом Австралии?", "a": "Кенгуру", "opts": ["Коала", "Кенгуру", "Вомбат", "Динго"]},
    {"q": "Сколько цветов в радуге?", "a": "7", "opts": ["5", "6", "7", "8"]},
    {"q": "Какой металл жидкий при комнатной температуре?", "a": "Ртуть", "opts": ["Свинец", "Ртуть", "Галлий", "Цезий"]},
    {"q": "Сколько букв в русском алфавите?", "a": "33", "opts": ["30", "31", "33", "35"]},
    {"q": "Какое самое большое животное в мире?", "a": "Синий кит", "opts": ["Слон", "Синий кит", "Кашалот", "Белая акула"]},
    {"q": "Столица Узбекистана?", "a": "Ташкент", "opts": ["Самарканд", "Бухара", "Ташкент", "Наманган"]},
]

# ─────────────────────────────────────────────
#   ЛОГИРОВАНИЕ
# ─────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#   ХРАНИЛИЩЕ
# ─────────────────────────────────────────────

def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"scores": {}}  # {user_id: {"name": ..., "best": ..., "total_games": ...}}


def save_data(data: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


data = load_data()

# ─────────────────────────────────────────────
#   ИГРОВЫЕ СЕССИИ {user_id: {...}}
# ─────────────────────────────────────────────

sessions = {}

# ─────────────────────────────────────────────
#   КОМАНДЫ
# ─────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🧠 <b>Бот-Викторина</b>\n\n"
        "Проверь свои знания! Тебя ждут вопросы по географии, науке, истории и не только.\n\n"
        "📋 <b>Команды:</b>\n"
        "  /quiz — начать игру\n"
        "  /score — мой рекорд\n"
        "  /top — таблица лидеров\n"
        "  /stop — остановить игру\n"
        "  /help — справка\n\n"
        "Нажми /quiz чтобы начать! 🚀"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "📖 <b>Как играть:</b>\n\n"
        "1. Напиши /quiz — начнётся викторина\n"
        f"2. Отвечай на {QUESTIONS_PER_GAME} вопросов\n"
        "3. За каждый правильный ответ — 1 очко\n"
        "4. В конце увидишь свой результат\n\n"
        "🏆 Рекорды сохраняются!"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)

    # Начинаем новую сессию
    questions = random.sample(ALL_QUESTIONS, min(QUESTIONS_PER_GAME, len(ALL_QUESTIONS)))
    sessions[user_id] = {
        "questions": questions,
        "current": 0,
        "score": 0,
        "name": user.full_name or user.username or "Игрок",
    }

    await update.message.reply_text(
        f"🎮 Викторина началась!\n"
        f"📝 {QUESTIONS_PER_GAME} вопросов. Удачи, {user.first_name}! 🍀"
    )
    await send_question(update, context, user_id)


async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str) -> None:
    session = sessions.get(user_id)
    if not session:
        return

    idx = session["current"]
    total = len(session["questions"])
    q = session["questions"][idx]

    # Перемешиваем варианты ответов
    options = q["opts"].copy()
    random.shuffle(options)

    keyboard = [
        [InlineKeyboardButton(opt, callback_data=f"ans:{user_id}:{opt}")]
        for opt in options
    ]

    text = (
        f"❓ <b>Вопрос {idx + 1}/{total}</b>\n\n"
        f"{q['q']}"
    )

    if update.callback_query:
        await update.callback_query.message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML"
        )


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":", 2)
    if len(parts) != 3:
        return

    _, user_id, chosen = parts

    # Проверяем что отвечает правильный пользователь
    if str(query.from_user.id) != user_id:
        await query.answer("Это не твоя викторина! Начни свою: /quiz", show_alert=True)
        return

    session = sessions.get(user_id)
    if not session:
        await query.edit_message_text("❌ Сессия устарела. Начни новую: /quiz")
        return

    idx = session["current"]
    q = session["questions"][idx]
    correct = q["a"]

    # Убираем кнопки
    await query.edit_message_reply_markup(reply_markup=None)

    if chosen == correct:
        session["score"] += 1
        result_text = f"✅ <b>Правильно!</b> +1 очко"
    else:
        result_text = f"❌ <b>Неверно!</b>\nПравильный ответ: <b>{correct}</b>"

    score_text = f"📊 Счёт: {session['score']}/{idx + 1}"
    await query.message.reply_text(f"{result_text}\n{score_text}", parse_mode="HTML")

    session["current"] += 1

    if session["current"] >= len(session["questions"]):
        # Игра окончена
        await finish_game(query, user_id)
    else:
        await send_question(update, context, user_id)


async def finish_game(query, user_id: str) -> None:
    session = sessions.pop(user_id, None)
    if not session:
        return

    score = session["score"]
    total = len(session["questions"])
    name = session["name"]
    percent = int(score / total * 100)

    # Сохраняем рекорд
    if user_id not in data["scores"]:
        data["scores"][user_id] = {"name": name, "best": 0, "total_games": 0}

    data["scores"][user_id]["name"] = name
    data["scores"][user_id]["total_games"] += 1
    is_record = False
    if score > data["scores"][user_id]["best"]:
        data["scores"][user_id]["best"] = score
        is_record = True
    save_data(data)

    # Оценка
    if percent == 100:
        grade = "🏆 Идеально! Ты гений!"
    elif percent >= 80:
        grade = "🌟 Отлично!"
    elif percent >= 60:
        grade = "👍 Хорошо!"
    elif percent >= 40:
        grade = "😐 Неплохо, но можно лучше"
    else:
        grade = "😅 Нужно подучиться!"

    record_text = "\n🎉 <b>Новый рекорд!</b>" if is_record else ""

    text = (
        f"🏁 <b>Игра окончена, {name}!</b>\n\n"
        f"✅ Правильных ответов: <b>{score}/{total}</b> ({percent}%)\n"
        f"{grade}{record_text}\n\n"
        f"Сыграть ещё раз: /quiz\n"
        f"Таблица лидеров: /top"
    )
    await query.message.reply_text(text, parse_mode="HTML")


async def cmd_score(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    user_data = data["scores"].get(user_id)

    if not user_data:
        await update.message.reply_text("У тебя пока нет рекордов. Начни игру: /quiz")
        return

    text = (
        f"📊 <b>Твоя статистика:</b>\n\n"
        f"🏆 Рекорд: <b>{user_data['best']}/{QUESTIONS_PER_GAME}</b>\n"
        f"🎮 Игр сыграно: <b>{user_data['total_games']}</b>"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not data["scores"]:
        await update.message.reply_text("Таблица лидеров пуста. Будь первым: /quiz")
        return

    sorted_scores = sorted(
        data["scores"].items(),
        key=lambda x: x[1]["best"],
        reverse=True
    )[:10]

    medals = ["🥇", "🥈", "🥉"] + ["4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    lines = []
    for i, (uid, info) in enumerate(sorted_scores):
        lines.append(f"{medals[i]} {info['name']} — <b>{info['best']}/{QUESTIONS_PER_GAME}</b>")

    text = "🏆 <b>Таблица лидеров:</b>\n\n" + "\n".join(lines)
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id in sessions:
        sessions.pop(user_id)
        await update.message.reply_text("🛑 Викторина остановлена. Начать заново: /quiz")
    else:
        await update.message.reply_text("У тебя нет активной викторины. Начни: /quiz")


# ─────────────────────────────────────────────
#   ЗАПУСК
# ─────────────────────────────────────────────

def main() -> None:
    if BOT_TOKEN == "ВАШ_ТОКЕН_ЗДЕСЬ":
        print("❌ ОШИБКА: Вставьте токен бота в переменную BOT_TOKEN!")
        return

    print("🚀 Запуск Quiz Bot...")
    print(f"   Вопросов в базе: {len(ALL_QUESTIONS)}")
    print(f"   Вопросов за игру: {QUESTIONS_PER_GAME}")
    print("─" * 40)

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("quiz", cmd_quiz))
    app.add_handler(CommandHandler("score", cmd_score))
    app.add_handler(CommandHandler("top", cmd_top))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CallbackQueryHandler(handle_answer, pattern=r"^ans:"))

    print("✅ Бот запущен. Нажмите Ctrl+C для остановки.")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()