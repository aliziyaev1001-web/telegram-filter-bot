"""
╔══════════════════════════════════════════════════════╗
║         TELEGRAM FILTER BOT — Модератор группы       ║
║         Удаляет сообщения с запрещёнными словами      ║
╚══════════════════════════════════════════════════════╝

УСТАНОВКА:
    pip install python-telegram-bot

ЗАПУСК:
    1. Получите токен у @BotFather
    2. Вставьте токен в BOT_TOKEN ниже
    3. Добавьте бота в группу и сделайте его администратором
    4. python telegram_filter_bot.py

КОМАНДЫ БОТА:
    /addword <слово>   — добавить слово в чёрный список
    /delword <слово>   — удалить слово из чёрного списка
    /listwords         — показать все запрещённые слова
    /stats             — статистика удалений
    /help              — справка
    (только для администраторов группы)
"""

import logging
import json
import os
import re
from datetime import datetime
from telegram import Update, ChatPermissions
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ─────────────────────────────────────────────
#   НАСТРОЙКИ — измените под себя
# ─────────────────────────────────────────────

BOT_TOKEN = "8680531928:AAFn_LKJHduBEP-UgSL3awSojvWpRLspV1g"  # Токен от @BotFather

# Файл для хранения данных (слова и статистика)
DATA_FILE = "filter_bot_data.json"

# Предупреждать пользователя перед удалением сообщения?
WARN_USER = True

# Сколько предупреждений до мута (0 = не мутить)
WARNINGS_BEFORE_MUTE = 3

# Длительность мута в секундах (300 = 5 минут)
MUTE_DURATION = 300

# ─────────────────────────────────────────────
#   СТАРТОВЫЙ СПИСОК ЗАПРЕЩЁННЫХ СЛОВ
#   (загружаются только если список в файле пуст)
# ─────────────────────────────────────────────

DEFAULT_FORBIDDEN_WORDS = [
    # 🔞 Русский мат — базовый набор (корни, покрывают большинство форм)
    "блять", "бля", "блядь", "блядина", "блядский",
    "ёбаный", "ёб", "еб", "ёбать", "ебать", "ебал", "ебан", "ебло",
    "пиздец", "пизда", "пиздить", "пизданутый", "пизданул",
    "хуй", "хуйня", "хуёво", "хуево", "хуйло",
    "мудак", "мудила", "мудозвон",
    "сука", "суки", "сучара", "сучка",
    "залупа", "залупон",
    "ёпт", "епт", "ёпта", "епта",
    "пиздюк", "пиздюля",
    "долбоёб", "долбоеб",
    "ублюдок",
    "педик", "педераст",
    "шлюха", "шлюшка",
    "курва",
    "гандон",
    "сволочь",
    "уёбок", "уебок",
    "ёбнутый", "ёбнулся",
    "заебал", "заёбал",
    "выёбываться",
    "хуесос", "хуесёс",
    "пиздёж", "пиздеж",
    "мразь",
    "тварь",
    "ёб твою мать", "еб твою мать",
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
#   ХРАНИЛИЩЕ ДАННЫХ
# ─────────────────────────────────────────────

def load_data() -> dict:
    """Загрузить данные из файла."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            logger.warning("Не удалось загрузить данные, создаю новый файл.")

    # Первый запуск — используем стартовый список слов
    default_data = {
        "forbidden_words": list(DEFAULT_FORBIDDEN_WORDS),
        "stats": {"total_deleted": 0, "by_word": {}},
        "warnings": {},
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(default_data, f, ensure_ascii=False, indent=2)
    return default_data


def save_data(data: dict) -> None:
    """Сохранить данные в файл."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# Глобальное хранилище
data = load_data()

# ─────────────────────────────────────────────
#   ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ─────────────────────────────────────────────

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Проверить, является ли пользователь администратором группы."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # В личных чатах все команды разрешены
    if update.effective_chat.type == "private":
        return True

    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


def contains_forbidden_word(text: str) -> list[str]:
    """Найти запрещённые слова в тексте. Возвращает список найденных слов."""
    if not text:
        return []

    text_lower = text.lower()
    found = []

    for word in data["forbidden_words"]:
        # Ищем слово как отдельное слово (учитываем падежи — по вхождению)
        pattern = re.compile(re.escape(word.lower()))
        if pattern.search(text_lower):
            found.append(word)

    return found


def get_warnings(chat_id: int, user_id: int) -> int:
    """Получить количество предупреждений пользователя."""
    chat_key = str(chat_id)
    user_key = str(user_id)
    return data["warnings"].get(chat_key, {}).get(user_key, 0)


def increment_warnings(chat_id: int, user_id: int) -> int:
    """Увеличить счётчик предупреждений и вернуть новое значение."""
    chat_key = str(chat_id)
    user_key = str(user_id)

    if chat_key not in data["warnings"]:
        data["warnings"][chat_key] = {}

    current = data["warnings"][chat_key].get(user_key, 0) + 1
    data["warnings"][chat_key][user_key] = current
    save_data(data)
    return current


def reset_warnings(chat_id: int, user_id: int) -> None:
    """Сбросить предупреждения пользователя."""
    chat_key = str(chat_id)
    user_key = str(user_id)
    if chat_key in data["warnings"]:
        data["warnings"][chat_key].pop(user_key, None)
        save_data(data)

# ─────────────────────────────────────────────
#   ОБРАБОТЧИКИ КОМАНД
# ─────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start."""
    text = (
        "🤖 <b>Filter Bot</b> — модератор группы\n\n"
        "Я автоматически удаляю сообщения с запрещёнными словами.\n\n"
        "📋 Команды (только для администраторов):\n"
        "  /addword &lt;слово&gt; — добавить слово\n"
        "  /delword &lt;слово&gt; — удалить слово\n"
        "  /listwords — список запрещённых слов\n"
        "  /stats — статистика\n"
        "  /help — справка\n\n"
        "Добавьте меня в группу и назначьте администратором!"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /help."""
    text = (
        "📖 <b>Справка по Filter Bot</b>\n\n"
        "<b>Добавление слова:</b>\n"
        "  <code>/addword мат</code>\n\n"
        "<b>Удаление слова:</b>\n"
        "  <code>/delword мат</code>\n\n"
        "<b>Список слов:</b>\n"
        "  <code>/listwords</code>\n\n"
        "<b>Статистика:</b>\n"
        "  <code>/stats</code>\n\n"
        "⚙️ <b>Как работает:</b>\n"
        f"  • Проверяю каждое сообщение\n"
        f"  • При нарушении — удаляю и предупреждаю\n"
        f"  • После {WARNINGS_BEFORE_MUTE} предупреждений — мут на {MUTE_DURATION//60} мин\n\n"
        "⚠️ Все команды доступны только администраторам."
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_addword(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /addword <слово> — добавить запрещённое слово."""
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Только администраторы могут управлять списком слов.")
        return

    if not context.args:
        await update.message.reply_text(
            "❗ Укажите слово: <code>/addword &lt;слово&gt;</code>",
            parse_mode="HTML",
        )
        return

    word = " ".join(context.args).strip().lower()

    if word in data["forbidden_words"]:
        await update.message.reply_text(f"⚠️ Слово <b>«{word}»</b> уже в списке.", parse_mode="HTML")
        return

    data["forbidden_words"].append(word)
    save_data(data)
    logger.info(f"Добавлено слово: «{word}»")

    await update.message.reply_text(
        f"✅ Слово <b>«{word}»</b> добавлено в чёрный список.\n"
        f"📋 Всего слов: {len(data['forbidden_words'])}",
        parse_mode="HTML",
    )


async def cmd_delword(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /delword <слово> — удалить слово из списка."""
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Только администраторы могут управлять списком слов.")
        return

    if not context.args:
        await update.message.reply_text(
            "❗ Укажите слово: <code>/delword &lt;слово&gt;</code>",
            parse_mode="HTML",
        )
        return

    word = " ".join(context.args).strip().lower()

    if word not in data["forbidden_words"]:
        await update.message.reply_text(f"⚠️ Слово <b>«{word}»</b> не найдено в списке.", parse_mode="HTML")
        return

    data["forbidden_words"].remove(word)
    save_data(data)
    logger.info(f"Удалено слово: «{word}»")

    await update.message.reply_text(
        f"🗑 Слово <b>«{word}»</b> удалено из чёрного списка.\n"
        f"📋 Осталось слов: {len(data['forbidden_words'])}",
        parse_mode="HTML",
    )


async def cmd_listwords(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /listwords — показать все запрещённые слова."""
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Только администраторы могут просматривать список слов.")
        return

    if not data["forbidden_words"]:
        await update.message.reply_text("📋 Список запрещённых слов пуст.\nДобавьте слово: /addword &lt;слово&gt;", parse_mode="HTML")
        return

    words_list = "\n".join(f"  • {w}" for w in sorted(data["forbidden_words"]))
    await update.message.reply_text(
        f"🚫 <b>Запрещённые слова ({len(data['forbidden_words'])}):</b>\n\n{words_list}",
        parse_mode="HTML",
    )


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /stats — статистика удалений."""
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Только администраторы могут просматривать статистику.")
        return

    total = data["stats"]["total_deleted"]
    by_word = data["stats"]["by_word"]

    if not total:
        await update.message.reply_text("📊 Статистика пуста — нарушений пока не было.")
        return

    # Топ-5 слов
    top_words = sorted(by_word.items(), key=lambda x: x[1], reverse=True)[:5]
    top_text = "\n".join(f"  {i+1}. «{w}» — {c} раз" for i, (w, c) in enumerate(top_words))

    await update.message.reply_text(
        f"📊 <b>Статистика модерации</b>\n\n"
        f"🗑 Всего удалено сообщений: <b>{total}</b>\n"
        f"🚫 Слов в чёрном списке: <b>{len(data['forbidden_words'])}</b>\n\n"
        f"🏆 <b>Топ нарушений по словам:</b>\n{top_text}",
        parse_mode="HTML",
    )

# ─────────────────────────────────────────────
#   ФИЛЬТРАЦИЯ СООБЩЕНИЙ
# ─────────────────────────────────────────────

async def filter_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Проверяет каждое сообщение на запрещённые слова."""
    message = update.message
    if not message or not message.text:
        return

    # Не проверяем сообщения в личных чатах
    if update.effective_chat.type == "private":
        return

    # Не проверяем администраторов
    if await is_admin(update, context):
        return

    found_words = contains_forbidden_word(message.text)
    if not found_words:
        return

    user = message.from_user
    chat_id = message.chat_id
    user_id = user.id
    user_name = user.full_name or user.username or str(user_id)

    # Обновляем статистику
    data["stats"]["total_deleted"] += 1
    for word in found_words:
        data["stats"]["by_word"][word] = data["stats"]["by_word"].get(word, 0) + 1
    save_data(data)

    # Удаляем сообщение
    try:
        await message.delete()
        logger.info(
            f"Удалено сообщение от @{user.username or user_id} "
            f"в чате {chat_id} | Слова: {found_words}"
        )
    except Exception as e:
        logger.error(f"Не удалось удалить сообщение: {e}")
        return

    # Предупреждаем пользователя
    if WARN_USER and WARNINGS_BEFORE_MUTE > 0:
        warnings = increment_warnings(chat_id, user_id)
        remaining = WARNINGS_BEFORE_MUTE - warnings

        if remaining > 0:
            warn_text = (
                f"⚠️ <a href='tg://user?id={user_id}'>{user_name}</a>, "
                f"ваше сообщение удалено — оно содержит запрещённые слова.\n"
                f"Предупреждений: <b>{warnings}/{WARNINGS_BEFORE_MUTE}</b>"
            )
            warn_msg = await message.chat.send_message(warn_text, parse_mode="HTML")

            # Удаляем предупреждение через 10 секунд
            context.job_queue.run_once(
                lambda ctx: ctx.bot.delete_message(chat_id, warn_msg.message_id),
                when=10,
            )

        else:
            # Мут пользователя
            try:
                mute_until = datetime.now().timestamp() + MUTE_DURATION
                await context.bot.restrict_chat_member(
                    chat_id,
                    user_id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=int(mute_until),
                )
                reset_warnings(chat_id, user_id)
                logger.info(f"Пользователь {user_id} замучен на {MUTE_DURATION} сек.")

                mute_text = (
                    f"🔇 <a href='tg://user?id={user_id}'>{user_name}</a> "
                    f"замолчан на <b>{MUTE_DURATION // 60} мин</b> "
                    f"за систематическое использование запрещённых слов."
                )
                mute_msg = await message.chat.send_message(mute_text, parse_mode="HTML")

                context.job_queue.run_once(
                    lambda ctx: ctx.bot.delete_message(chat_id, mute_msg.message_id),
                    when=15,
                )
            except Exception as e:
                logger.error(f"Не удалось замутить пользователя: {e}")

    elif WARN_USER:
        # Просто предупреждаем без мута
        warn_text = (
            f"⚠️ <a href='tg://user?id={user_id}'>{user_name}</a>, "
            f"ваше сообщение удалено — оно содержит запрещённые слова."
        )
        warn_msg = await message.chat.send_message(warn_text, parse_mode="HTML")
        context.job_queue.run_once(
            lambda ctx: ctx.bot.delete_message(chat_id, warn_msg.message_id),
            when=10,
        )

# ─────────────────────────────────────────────
#   ЗАПУСК БОТА
# ─────────────────────────────────────────────

def main() -> None:
    if BOT_TOKEN == "ВАШ_ТОКЕН_ЗДЕСЬ":
        print("❌ ОШИБКА: Вставьте токен бота в переменную BOT_TOKEN!")
        print("   Получите токен у @BotFather в Telegram.")
        return

    print("🚀 Запуск Filter Bot...")
    print(f"   Запрещённых слов загружено: {len(data['forbidden_words'])} (мат + спам)")
    print(f"   Предупреждений до мута: {WARNINGS_BEFORE_MUTE}")
    print(f"   Длительность мута: {MUTE_DURATION // 60} мин")
    print("─" * 40)

    app = Application.builder().token(BOT_TOKEN).build()

    # Регистрируем команды
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("addword", cmd_addword))
    app.add_handler(CommandHandler("delword", cmd_delword))
    app.add_handler(CommandHandler("listwords", cmd_listwords))
    app.add_handler(CommandHandler("stats", cmd_stats))

    # Фильтр сообщений
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, filter_message)
    )

    print("✅ Бот запущен. Нажмите Ctrl+C для остановки.")
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()