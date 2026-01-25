import os
import time
import threading
import sqlite3
from datetime import datetime
from telebot import TeleBot, types

from products import PRODUCTS, CATEGORIES

# ======================================================
# НАСТРОЙКИ (ТОЛЬКО ЧЕРЕЗ ENV)
# ======================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")                 # ← обязательно
OPERATOR_CHAT_ID = os.getenv("OPERATOR_CHAT_ID")   # ← твой chat_id
TIMEZONE = "Europe/Moscow"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан")

bot = TeleBot(BOT_TOKEN, parse_mode="HTML")

# ======================================================
# БАЗА ДАННЫХ (SQLite)
# ======================================================

DB_PATH = "bot.db"

def db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    with db() as conn:
        c = conn.cursor()

        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_seen TEXT
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS cart (
            user_id INTEGER,
            product_id TEXT,
            qty INTEGER,
            PRIMARY KEY (user_id, product_id)
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            data TEXT,
            created_at TEXT
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS stock (
            product_id TEXT PRIMARY KEY,
            qty INTEGER,
            updated_at TEXT
        )
        """)

        conn.commit()

init_db()

# ======================================================
# СКЛАД (обновление 2 раза в сутки)
# ======================================================

STOCK_CACHE = {}

def load_stock_from_file():
    """
    Здесь позже будет чтение Excel/CSV с Google Drive.
    Пока заглушка.
    """
    # ← сюда вставь чтение файла остатков
    # формат: {"lavender_10": 12, ...}
    pass

def stock_scheduler():
    while True:
        now = datetime.now()
        if now.hour in (6, 14):
            try:
                load_stock_from_file()
            except Exception as e:
                print("Ошибка обновления склада:", e)
            time.sleep(3600)
        time.sleep(300)

threading.Thread(target=stock_scheduler, daemon=True).start()

def get_stock(product_id):
    return STOCK_CACHE.get(product_id, 0)

# ======================================================
# ВСПОМОГАТЕЛЬНЫЕ
# ======================================================

def save_user(message):
    with db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users VALUES (?, ?, ?)",
            (message.from_user.id,
             message.from_user.username,
             datetime.now().isoformat())
        )

def cart_count(user_id):
    with db() as conn:
        cur = conn.execute(
            "SELECT SUM(qty) FROM cart WHERE user_id=?",
            (user_id,)
        )
        return cur.fetchone()[0] or 0

# ======================================================
# МЕНЮ
# ======================================================

def main_menu(user_id):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        "📚 Каталог и инструкции", callback_data="catalog"
    ))
    kb.add(types.InlineKeyboardButton(
        f"🛒 Корзина ({cart_count(user_id)})", callback_data="cart"
    ))
    kb.add(types.InlineKeyboardButton(
        "💬 Интерактивный помощник", url="https://t.me/ТУТ_ССЫЛКА"
    ))
    kb.add(types.InlineKeyboardButton(
        "📣 Канал", url="https://t.me/ТУТ_КАНАЛ"
    ))
    kb.add(types.InlineKeyboardButton(
        "🌐 Сайт", url="https://ТУТ_САЙТ"
    ))
    kb.add(types.InlineKeyboardButton(
        "📞 Задать вопрос", callback_data="contact"
    ))
    return kb

# ======================================================
# СТАРТ
# ======================================================

@bot.message_handler(commands=["start"])
def start(message):
    save_user(message)
    bot.send_message(
        message.chat.id,
        "Добро пожаловать в <b>Scentori</b> 🌿\n\n"
        "Каталог ароматов, инструкции и удобный заказ.",
        reply_markup=main_menu(message.from_user.id)
    )

# ======================================================
# КАТАЛОГ
# ======================================================

@bot.callback_query_handler(func=lambda c: c.data == "catalog")
def catalog(call):
    kb = types.InlineKeyboardMarkup()
    for cid, title in CATEGORIES.items():
        kb.add(types.InlineKeyboardButton(title, callback_data=f"cat:{cid}"))
    kb.add(types.InlineKeyboardButton("⬅️ Главное меню", callback_data="home"))
    bot.edit_message_text(
        "Выберите категорию:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("cat:"))
def category(call):
    cat = call.data.split(":")[1]
    kb = types.InlineKeyboardMarkup()
    for pid, p in PRODUCTS.items():
        if p["category"] == cat:
            kb.add(types.InlineKeyboardButton(p["name"], callback_data=f"product:{pid}"))
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="catalog"))
    bot.edit_message_text(
        "Выберите товар:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

# ======================================================
# КАРТОЧКА ТОВАРА
# ======================================================

@bot.callback_query_handler(func=lambda c: c.data.startswith("product:"))
def product_card(call):
    pid = call.data.split(":")[1]
    p = PRODUCTS[pid]

    text = (
        f"<b>{p['name']}</b>\n"
        f"{p['subtitle']}\n\n"
        f"{p['intro']}\n\n"
        f"<b>Свойства</b>\n{p['sections']['properties']}\n\n"
        f"<b>Применение</b>\n{p['sections']['usage']}\n\n"
        f"<b>Безопасность</b>\n{p['sections']['safety']}\n\n"
        f"<b>Технические данные</b>\n{p['sections']['tech']}\n\n"
        f"Цена: <s>{p['price']} ₽</s>\n"
        f"<b>{p['bot_price']} ₽ через бот</b>"
    )

    kb = types.InlineKeyboardMarkup()

    stock = get_stock(pid)

    if stock > 0:
        kb.add(types.InlineKeyboardButton(
            "🛒 Добавить в корзину", callback_data=f"add:{pid}"
        ))
    elif p.get("allow_preorder"):
        kb.add(types.InlineKeyboardButton(
            "📦 Предзаказ", callback_data=f"preorder:{pid}"
        ))

    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"cat:{p['category']}"))

    with open(p["image"], "rb") as img:
        bot.send_photo(
            call.message.chat.id,
            img,
            caption=text,
            reply_markup=kb
        )

# ======================================================
# ДОБАВЛЕНИЕ В КОРЗИНУ
# ======================================================

@bot.callback_query_handler(func=lambda c: c.data.startswith("add:"))
def add_to_cart(call):
    pid = call.data.split(":")[1]
    uid = call.from_user.id

    stock = get_stock(pid)

    with db() as conn:
        cur = conn.execute(
            "SELECT qty FROM cart WHERE user_id=? AND product_id=?",
            (uid, pid)
        )
        current = cur.fetchone()
        current_qty = current[0] if current else 0

        if current_qty >= stock:
            bot.answer_callback_query(call.id, "Больше добавить нельзя")
            return

        if current:
            conn.execute(
                "UPDATE cart SET qty=qty+1 WHERE user_id=? AND product_id=?",
                (uid, pid)
            )
        else:
            conn.execute(
                "INSERT INTO cart VALUES (?, ?, 1)",
                (uid, pid)
            )

    bot.answer_callback_query(call.id, "Добавлено в корзину")

# ======================================================
# КОНТАКТ
# ======================================================

@bot.callback_query_handler(func=lambda c: c.data == "contact")
def contact(call):
    bot.send_message(
        call.message.chat.id,
"Перевожу ваше сообщение оператору 😊\n"
        "Специалист уже спешит к вам!"
    )

# ======================================================
# НАВИГАЦИЯ
# ======================================================

@bot.callback_query_handler(func=lambda c: c.data == "home")
def home(call):
    bot.edit_message_text(
        "Главное меню:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=main_menu(call.from_user.id)
    )

# ======================================================
# ЗАПУСК
# ======================================================

print("Scentori bot started")
bot.infinity_polling()
