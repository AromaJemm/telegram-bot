import os
import time
import threading
import sqlite3
import requests
import pandas as pd
from datetime import datetime
from telebot import TeleBot, types

# ================== ENV ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPERATOR_CHAT_ID = int(os.getenv("OPERATOR_CHAT_ID"))
ASSISTANT_LINK = os.getenv("ASSISTANT_LINK")
INVENTORY_FILE_URL = os.getenv("INVENTORY_FILE_URL")

bot = TeleBot(BOT_TOKEN, threaded=True)

# ================== DB ==================
conn = sqlite3.connect("shop.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    created_at TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    data TEXT,
    status TEXT,
    created_at TEXT
)
""")

conn.commit()

# ================== INVENTORY ==================
inventory_cache = {}
inventory_last_update = None

def load_inventory():
    global inventory_cache, inventory_last_update
    try:
        df = pd.read_excel(INVENTORY_FILE_URL)
        inventory_cache = {
            row["product_id"]: {
                "name": row["name"],
                "quantity": int(row["quantity"]),
                "active": int(row["active"])
            }
            for _, row in df.iterrows()
        }
        inventory_last_update = datetime.now()
        print("Inventory updated")
    except Exception as e:
        print("Inventory load error:", e)

def inventory_scheduler():
    while True:
        now = datetime.now().strftime("%H:%M")
        if now in ("06:00", "14:00"):
            load_inventory()
            time.sleep(61)
        time.sleep(20)

threading.Thread(target=inventory_scheduler, daemon=True).start()
load_inventory()

# ================== STATE ==================
user_state = {}
user_cart = {}

# ================== START ==================
@bot.message_handler(commands=["start"])
def start(msg):
    user_id = msg.from_user.id
    cur.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?)",
                (user_id, msg.from_user.username, msg.from_user.first_name, datetime.now().isoformat()))
    conn.commit()

    user_cart[user_id] = {}

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("🛍 Каталог и инструкции", callback_data="catalog"),
        types.InlineKeyboardButton("🛒 Корзина (0)", callback_data="cart")
    )
    kb.add(
        types.InlineKeyboardButton("🤖 Интерактивный помощник", url=ASSISTANT_LINK),
        types.InlineKeyboardButton("📞 Поддержка", callback_data="support")
    )

    bot.send_photo(
        user_id,
        photo=open("media/welcome.jpg", "rb"),
        caption=(
            "✨ Добро пожаловать в *Scentori!*\n\n"
            "🛍 *Каталог* — масла, диффузоры и инструкции\n"
            "🛒 *Корзина* — оформление заказа\n"
            "🤖 *Интерактивный помощник* — поможет подобрать аромат под ваше настроение\n\n"
            "Мы рядом 🌿"
        ),
        reply_markup=kb,
        parse_mode="Markdown"
    )

# ================== CALLBACKS ==================
@bot.callback_query_handler(func=lambda c: True)
def callbacks(c):
    uid = c.from_user.id

    if c.data == "catalog":
        show_catalog(uid)

    elif c.data.startswith("product_"):
        show_product(uid, c.data.split("_", 1)[1])

    elif c.data.startswith("add_"):
        add_to_cart(uid, c.data.split("_", 1)[1])

    elif c.data == "cart":
        show_cart(uid)

    elif c.data == "order":
        request_phone(uid)

    elif c.data == "support":
        bot.send_message(uid, "💬 Перевожу вас на оператора, он уже спешит к вам!")
        bot.send_message(OPERATOR_CHAT_ID, f"Сообщение от @{c.from_user.username}")

# ================== CATALOG ==================
def show_catalog(uid):
    kb = types.InlineKeyboardMarkup()
    for pid, item in inventory_cache.items():
        if item["active"] == 1:
            kb.add(types.InlineKeyboardButton(item["name"], callback_data=f"product_{pid}"))
    kb.add(types.InlineKeyboardButton("⬅ Назад", callback_data="start"))
    bot.edit_message_text("🛍 *Каталог*", uid, bot.get_updates()[-1].message.message_id,
                          reply_markup=kb, parse_mode="Markdown")

# ================== PRODUCT ==================
def show_product(uid, pid):
    item = inventory_cache.get(pid)
    if not item:
        bot.send_message(uid, "Товар не найден")
        return

    text = f"*{item['name']}*\n\n"
    if item["quantity"] > 0:
        text += f"✅ В наличии: {item['quantity']} шт\n"
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("➕ Добавить в корзину", callback_data=f"add_{pid}"))
    else:
        text += "⏳ Сейчас нет в наличии\nДоступен *предзаказ*\n"
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📞 Связаться с оператором", callback_data="support"))

    kb.add(types.InlineKeyboardButton("⬅ Назад", callback_data="catalog"))

    bot.send_photo(uid, open(f"media/{pid}.jpg", "rb"),
                   caption=text,
                   reply_markup=kb,
                   parse_mode="Markdown")

# ================== CART ==================
def add_to_cart(uid, pid):
    cart = user_cart.setdefault(uid, {})
    available = inventory_cache[pid]["quantity"]

    current = cart.get(pid, 0)
    if current + 1 > available:
        bot.answer_callback_query(bot.get_updates()[-1].callback_query.id,
                                  "❌ Больше добавить нельзя — ограничение склада")
        return

    cart[pid] = current + 1
    bot.answer_callback_query(bot.get_updates()[-1].callback_query.id,
                              "✅ Добавлено в корзину")

def show_cart(uid):
    cart = user_cart.get(uid, {})
    if not cart:
        bot.send_message(uid, "🛒 Корзина пуста")
        return

    text = "🛒 *Ваша корзина:*\n\n"
    total = 0
    for pid, qty in cart.items():
        name = inventory_cache[pid]["name"]
        text += f"• {name} × {qty}\n"
        total += qty

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(f"✅ Оформить заказ ({total})", callback_data="order"))
    kb.add(types.InlineKeyboardButton("⬅ Назад", callback_data="catalog"))

    bot.send_message(uid, text, reply_markup=kb, parse_mode="Markdown")

# ================== ORDER ==================
def request_phone(uid):
    user_state[uid] = "phone"
    bot.send_message(uid, "📞 Введите номер телефона\nФормат: +7XXXXXXXXXX")

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "phone")
def receive_phone(msg):
    if not msg.text.startswith("+7") or len(msg.text) != 12:
        bot.send_message(msg.chat.id, "❌ Неверный формат. Попробуйте ещё раз")
        return

    user_state[msg.chat.id] = None
    bot.send_message(msg.chat.id, "✅ Номер принят\n\nВыберите способ получения:")
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("📦 Доставка в ПВЗ Яндекс", callback_data="support"),
        types.InlineKeyboardButton("🏬 Самовывоз (Москва)", callback_data="support")
    )
    bot.send_message(msg.chat.id, "👇", reply_markup=kb)

# ================== RUN ==================
bot.infinity_polling()
