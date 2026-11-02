import os
import sqlite3
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)

TOKEN = os.getenv("BOT_TOKEN")
DB_PATH = "colors.sqlite3"

COLORS = [
    ("Червоний", "❤️", "#FF0000"),
    ("Помаранчевий", "🧡", "#FF8C00"),
    ("Жовтий", "💛", "#FFD700"),
    ("Зелений", "💚", "#00A000"),
    ("Бірюзовий", "🩵", "#40E0D0"),
    ("Синій", "💙", "#0000FF"),
    ("Фіолетовий", "💜", "#8000FF"),
    ("Рожевий", "🩷", "#FF69B4"),
    ("Коричневий", "🤎", "#8B4513"),
    ("Чорний", "🖤", "#222222"),
    ("Білий", "🤍", "#FFFFFF"),
    ("Сірий", "🩶", "#808080"),
]

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS members (
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            username TEXT,
            PRIMARY KEY (chat_id, user_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            color TEXT NOT NULL,
            emoji TEXT NOT NULL,
            hex TEXT NOT NULL,
            PRIMARY KEY (chat_id, user_id)
        )
    """)
    return conn

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привіт! Додай мене в групу та запусти там /start_colors.\n"
        "Учасники зможуть натиснути кнопку реєстрації, а я роздам їм різні кольори."
    )

async def start_colors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text("Цю команду потрібно запускати в групі.")
        return
    keyboard = [[InlineKeyboardButton("🙋‍♀️ Записатися на колір", callback_data="join_colors")]]
    await update.message.reply_text(
        "🎨 Розподіл кольорів!\n"
        "Натисніть кнопку нижче, щоб взяти участь. Коли всі запишуться, "
        "адміністратор запускає /draw_colors.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def join_colors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    chat_id = query.message.chat_id
    name = user.full_name
    conn = db()
    conn.execute(
        "INSERT OR REPLACE INTO members(chat_id,user_id,name,username) VALUES(?,?,?,?)",
        (chat_id, user.id, name, user.username)
    )
    conn.commit()
    conn.close()
    await query.answer("Ти в списку! 💖", show_alert=True)

async def draw_colors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conn = db()
    members = conn.execute(
        "SELECT user_id,name FROM members WHERE chat_id=? ORDER BY name",
        (chat_id,)
    ).fetchall()
    if not members:
        conn.close()
        await update.message.reply_text(
            "Поки ніхто не зареєструвався. Спочатку запусти /start_colors."
        )
        return
    if len(members) > len(COLORS):
        conn.close()
        await update.message.reply_text(
            f"Зареєструвалося {len(members)} людей, а в наборі лише {len(COLORS)} різних кольорів. "
            "Додай більше кольорів у список COLORS у коді."
        )
        return

    chosen = random.sample(COLORS, len(members))
    conn.execute("DELETE FROM assignments WHERE chat_id=?", (chat_id,))
    lines = ["🌈 **Ваші випадкові кольори:**", ""]
    for (user_id, name), (color, emoji, hex_code) in zip(members, chosen):
        conn.execute(
            "INSERT INTO assignments(chat_id,user_id,color,emoji,hex) VALUES(?,?,?,?,?)",
            (chat_id, user_id, color, emoji, hex_code)
        )
        lines.append(f"{emoji} {name} — **{color}** (`{hex_code}`)")
    conn.commit()
    conn.close()
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def reroll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await draw_colors(update, context)

async def list_colors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conn = db()
    rows = conn.execute(
        "SELECT name,color,emoji,hex FROM assignments WHERE chat_id=? ORDER BY name",
        (chat_id,)
    ).fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text("Ще немає розподілу. Запусти /draw_colors.")
        return
    lines = ["🌈 **Поточний розподіл:**", ""]
    lines.extend(f"{emoji} {name} — **{color}** (`{hex_code}`)" for name, color, emoji, hex_code in rows)
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

def main():
    if not TOKEN:
        raise RuntimeError("Задай токен бота у змінній середовища BOT_TOKEN.")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("start_colors", start_colors))
    app.add_handler(CommandHandler("draw_colors", draw_colors))
    app.add_handler(CommandHandler("reroll", reroll))
    app.add_handler(CommandHandler("colors", list_colors))
    app.add_handler(CallbackQueryHandler(join_colors, pattern="^join_colors$"))
    app.run_polling()

if __name__ == "__main__":
    main()
