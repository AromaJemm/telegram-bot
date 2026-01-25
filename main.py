import os
import sqlite3
import telebot
from telebot import types
from dotenv import load_dotenv
from datetime import datetime

# ===== ENV =====
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ORDER_CHAT_ID = os.getenv("ORDER_CHAT_ID")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ===== IMPORT DATA =====
from products import PRODUCTS, CATEGORIES
from config import CONFIG
from texts import TEXTS
from locations import PICKUP_LOCATIONS

DB_NAME = "store.db"

# ===== DB =====
def db():
    return sqlite3.connect(DB_NAME)

def init_db():
    with db() as conn:
        c = conn.cursor()

        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            phone TEXT,
            bonus INTEGER DEFAULT 0
        )""")

        c.execute("""
        CREATE TABLE IF NOT EXISTS cart (
            user_id INTEGER,
            product_id TEXT,
            qty INTEGER
        )""")

        c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            total INTEGER,
            status TEXT,
            created_at TEXT
        )""")

        c.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            order_id INTEGER,
            product_id TEXT,
            qty INTEGER,
            price INTEGER
        )""")

        c.execute("""
        CREATE TABLE IF NOT EXISTS user_state (
            user_id INTEGER PRIMARY KEY,
            state TEXT,
            payload TEXT
        )""")

        c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            user_id INTEGER,
            action TEXT,
            payload TEXT,
            created_at TEXT
        )""")

init_db()

# ===== HELPERS =====
def log(user_id, action, payload=""):
    with db() as conn:
        conn.execute(
            "INSERT INTO logs VALUES (?, ?, ?, ?)",
            (user_id, action, payload, datetime.now().isoformat())
        )

def get_cart_count(user_id):
    with db() as conn:
        res = conn.execute(
            "SELECT SUM(qty) FROM cart WHERE user_id=?",
            (user_id,)
        ).fetchone()[0]
        return res or 0

def set_state(user_id, state, payload=""):
    with db() as conn:
        conn.execute(
            "REPLACE INTO user_state VALUES (?, ?, ?)",
            (user_id, state, payload)
        )

def get_state(user_id):
    with db() as conn:
        row = conn.execute(
            "SELECT state, payload FROM user_state WHERE user_id=?",
            (user_id,)
        ).fetchone()
        return row if row else (None, None)

# ===== MENUS =====
def main_menu(user_id):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🛍 Каталог и инструкции", callback_data="catalog"))
    kb.add(types.InlineKeyboardButton(f"🛒 Корзина ({get_cart_count(user_id)})", callback_data="cart"))
    kb.add(types.InlineKeyboardButton("📞 Задать вопрос", url=CONFIG["CONTACT_PHONE_URL"]))
    kb.add(types.InlineKeyboardButton("📣 Канал", url=CONFIG["CHANNEL_URL"]))
    kb.add(types.InlineKeyboardButton("🌐 Сайт", url=CONFIG["SITE_URL"]))
    return kb

# ===== START =====
@bot.message_handler(commands=["start"])
def start(message):
    with db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
            (message.from_user.id, message.from_user.username, message.from_user.first_name)
        )

    bot.send_message(
        message.chat.id,
        TEXTS["welcome"],
        reply_markup=main_menu(message.from_user.id)
    )
    log(message.from_user.id, "start")

# ===== CATALOG =====
@bot.callback_query_handler(func=lambda c: c.data == "catalog")
def catalog(call):
    kb = types.InlineKeyboardMarkup()
    for k, v in CATEGORIES.items():
        kb.add(types.InlineKeyboardButton(v, callback_data=f"cat:{k}"))
    kb.add(types.InlineKeyboardButton("⬅️ Главное меню", callback_data="main"))

    bot.edit_message_text(
TEXTS["catalog_title"],
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

# ===== CATEGORY =====
@bot.callback_query_handler(func=lambda c: c.data.startswith("cat:"))
def category(call):
    cat = call.data.split(":")[1]
    kb = types.InlineKeyboardMarkup()

    for pid, p in PRODUCTS.items():
        if p["category"] == cat:
            kb.add(types.InlineKeyboardButton(p["name"], callback_data=f"prod:{pid}:intro"))

    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="catalog"))

    bot.edit_message_text(
        TEXTS["choose_product"],
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

# ===== PRODUCT CARD =====
def product_caption(pid, section):
    p = PRODUCTS[pid]
    text = f"<b>{p['name']}</b>\n"
    if p.get("subtitle"):
        text += f"<i>{p['subtitle']}</i>\n\n"

    content = p.get("sections", {}).get(section, p.get("intro", ""))
    text += content + "\n\n"

    text += f"💰 Цена: {p['price']} {CONFIG['CURRENCY']}\n"
    text += f"✨ Цена в боте: <b>{p['bot_price']} {CONFIG['CURRENCY']}</b>"
    return text

def product_keyboard(pid):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📖 Свойства", callback_data=f"prod:{pid}:properties"),
        types.InlineKeyboardButton("🌿 Применение", callback_data=f"prod:{pid}:usage"),
        types.InlineKeyboardButton("⚠️ Безопасность", callback_data=f"prod:{pid}:safety"),
        types.InlineKeyboardButton("⚙️ Тех. данные", callback_data=f"prod:{pid}:tech"),
    )
    kb.add(types.InlineKeyboardButton("➕ Добавить в корзину", callback_data=f"add:{pid}"))
    kb.add(types.InlineKeyboardButton("⬅️ Назад к списку", callback_data=f"cat:{PRODUCTS[pid]['category']}"))
    return kb

@bot.callback_query_handler(func=lambda c: c.data.startswith("prod:"))
def product(call):
    _, pid, section = call.data.split(":")
    set_state(call.from_user.id, "product", f"{pid}:{section}")

    p = PRODUCTS[pid]
    caption = product_caption(pid, section)
    kb = product_keyboard(pid)

    try:
        with open(p["image"], "rb") as img:
            bot.send_photo(
                call.message.chat.id,
                img,
                caption=caption,
                reply_markup=kb
            )
    except:
        bot.send_message(
            call.message.chat.id,
            caption,
            reply_markup=kb
        )

# ===== CART =====
@bot.callback_query_handler(func=lambda c: c.data.startswith("add:"))
def add_cart(call):
    pid = call.data.split(":")[1]
    uid = call.from_user.id

    with db() as conn:
        row = conn.execute(
            "SELECT qty FROM cart WHERE user_id=? AND product_id=?",
            (uid, pid)
        ).fetchone()

        if row:
            conn.execute(
                "UPDATE cart SET qty=qty+1 WHERE user_id=? AND product_id=?",
                (uid, pid)
            )
        else:
            conn.execute(
                "INSERT INTO cart VALUES (?, ?, 1)",
                (uid, pid)
            )

    bot.answer_callback_query(call.id, "Добавлено в корзину 🛒")

# ===== VIEW CART =====
@bot.callback_query_handler(func=lambda c: c.data == "cart")
def cart(call):
    uid = call.from_user.id
    with db() as conn:
        items = conn.execute(
            "SELECT product_id, qty FROM cart WHERE user_id=?",
            (uid,)
        ).fetchall()

    if not items:
        bot.answer_callback_query(call.id, TEXTS["cart_empty"])
        return

    text = "<b>🛒 Ваша корзина</b>\n\n"
    total = 0

    for pid, qty in items:
        p = PRODUCTS[pid]
        subtotal = p["bot_price"] * qty
        total += subtotal
        text += f"{p['name']} × {qty} = {subtotal} {CONFIG['CURRENCY']}\n"

    text += f"\n<b>Итого: {total} {CONFIG['CURRENCY']}</b>"

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Оформить заказ", callback_data="checkout"))
    kb.add(types.InlineKeyboardButton("⬅️ Главное меню", callback_data="main"))

    bot.
edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)

# ===== CHECKOUT =====
@bot.callback_query_handler(func=lambda c: c.data == "checkout")
def checkout(call):
    set_state(call.from_user.id, "await_phone")
    bot.send_message(call.message.chat.id, TEXTS["checkout_start"])

@bot.message_handler(func=lambda m: get_state(m.from_user.id)[0] == "await_phone")
def phone_input(message):
    phone = message.text.strip()
    if not phone.startswith("+7") or len(phone) != 12:
        bot.send_message(message.chat.id, "Введите номер в формате +7XXXXXXXXXX")
        return

    with db() as conn:
        conn.execute(
            "UPDATE users SET phone=? WHERE user_id=?",
            (phone, message.from_user.id)
        )

    set_state(message.from_user.id, None)
    bot.send_message(message.chat.id, TEXTS["order_sent"])
    bot.send_message(ORDER_CHAT_ID, f"🛒 Новый заказ от @{message.from_user.username}\n📞 {phone}")

# ===== BACK =====
@bot.callback_query_handler(func=lambda c: c.data == "main")
def back(call):
    bot.edit_message_text(
        TEXTS["welcome"],
        call.message.chat.id,
        call.message.message_id,
        reply_markup=main_menu(call.from_user.id)
    )

print("Scentori shop bot running...")
bot.infinity_polling(skip_pending=True)
