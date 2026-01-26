import importlib
import os
import sqlite3
import pandas as pd
import io
import requests
import time
import threading
import aiosqlite
from flask import Flask
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from html import escape as escape_md
import logging
import traceback

logging.basicConfig(level=logging.INFO)
app_flask = Flask(__name__)

# -------------------------- ПЕРЕМЕННЫЕ --------------------------
BOT_TOKEN = os.environ["BOT_TOKEN"]
WAREHOUSE_FILE_LINK = os.environ["WAREHOUSE_FILE_LINK"]
DATA_CUST_LINK = os.environ.get("DATA_CUST_LINK", "")
OPERATOR_ID = int(os.environ["OPERATOR_ID"])
DB_FILE = "orders.db"

# -------------------------- ГЛОБАЛЬНЫЕ --------------------------
warehouse_cache = {}
user_states = {}
last_action = {}
CATALOG = {  
    "essential_oils": {"title": "🌱 Эфирные масла", "items": ["products.essential.lavender", "products.essential.peppermint", "products.essential.eucalyptus"]},  
    "aroma_oils": {"title": "💎 Парфюмерные композиции", "items": ["products.aroma.biskay", "products.aroma.balance"]},  
    "other_goods": {"title": "🛋️ Другие товары", "items": ["products.other.diffuser"]}
}

# -------------------------- БАЗА ДАННЫХ --------------------------
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()
cursor.executescript("""
CREATE TABLE IF NOT EXISTS carts (user_id INTEGER, product_id TEXT, quantity INTEGER, PRIMARY KEY(user_id, product_id));
CREATE TABLE IF NOT EXISTS orders (order_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, total INTEGER, phone TEXT, address TEXT, delivery_method TEXT, timestamp DATETIME, bonus_used REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS bonuses (user_id INTEGER PRIMARY KEY, bonus_amount REAL DEFAULT 5.0, welcome_bonus_given INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS customer_actions (user_id INTEGER, action TEXT, timestamp DATETIME);
""")
conn.commit()

# -------------------------- МЕНЮ (ПЕРЕМЕЩЕН ВВЕРХ) --------------------------
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Каталог", callback_data="catalog"), InlineKeyboardButton("🤖 Помощник", callback_data="assistant")],
        [InlineKeyboardButton("👨‍⚕️ Оператор", callback_data="operator"), InlineKeyboardButton("🛍️ Корзина", callback_data="cart")],
        [InlineKeyboardButton("📋 Заказы", callback_data="orders"), InlineKeyboardButton("⭐ Бонусы", callback_data="bonuses")]
    ])

def catalog_menu():
    markup = InlineKeyboardMarkup()
    for cat_id, cat_data in CATALOG.items():
        markup.row(InlineKeyboardButton(cat_data['title'], callback_data=f"cat:{cat_id}"))
    markup.row(InlineKeyboardButton("🏠 Главное меню", callback_data="main"))
    return markup

def delivery_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏪 Самовывоз", callback_data="delivery_self")],
        [InlineKeyboardButton("📦 Доставка до ПВЗ Яндекс", callback_data="delivery_yandex")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main")]
    ])

def self_pickup_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚇 Метро Каширская", callback_data="pickup_kashirskaya")],
        [InlineKeyboardButton("🚇 Метро Перово", callback_data="pickup_perovo")],
        [InlineKeyboardButton("🏠 Назад", callback_data="checkout")]
    ])

# -------------------------- ФУНКЦИИ ТОВАРОВ --------------------------
def get_product_safe(module_path: str):
    try:
        module = importlib.import_module(module_path)
        return module.PRODUCT
    except:
        return {
            'name': 'Ошибка загрузки', 
            'id': module_path, 
            'properties': 'Описание недоступно', 
            'photo': 'images/fallback.jpg',
            'usage': '', 'safety': '', 'tech': ''
        }

def get_fallback_photo(photo_path: str):
    import os
    return photo_path if os.path.exists(photo_path) else "images/fallback.jpg"

def get_product_stock(product_id: str):
    stock = warehouse_cache.get(product_id, {'quantity': 0, 'active': 0, 'price': 0})
    return stock['quantity'], stock['active'], stock.get('price', 0)

# -------------------------- БОНУСЫ (ПЕРЕМЕЩЕН ВВЕРХ) --------------------------
def get_user_bonus(user_id: int):
    cursor.execute("SELECT bonus_amount FROM bonuses WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 5.0

# -------------------------- КОРЗИНА --------------------------
def add_to_cart(user_id: int, product_id: str):
    qty_stock, active, _ = get_product_stock(product_id)
    if qty_stock == 0 or active == 0:
        return False
    cursor.execute("SELECT quantity FROM carts WHERE user_id=? AND product_id=?", (user_id, product_id))
    row = cursor.fetchone()
    if row:
        new_qty = min(row[0]+1, qty_stock)
        cursor.execute("UPDATE carts SET quantity=? WHERE user_id=? AND product_id=?", (new_qty, user_id, product_id))
    else:
        cursor.execute("INSERT INTO carts (user_id, product_id, quantity) VALUES (?, ?, 1)", (user_id, product_id))
    conn.commit()
    save_customer_action(user_id, "cart_add")
    return True

def change_cart_quantity(user_id: int, product_id: str, delta: int):
    cursor.execute("SELECT quantity FROM carts WHERE user_id=? AND product_id=?", (user_id, product_id))
    row = cursor.fetchone()
    if row:
        qty_stock, _, _ = get_product_stock(product_id)
        new_qty = max(1, min(row[0] + delta, qty_stock))
        if new_qty == 1 and delta < 0:
            cursor.execute("DELETE FROM carts WHERE user_id=? AND product_id=?", (user_id, product_id))
        else:
            cursor.execute("UPDATE carts SET quantity=? WHERE user_id=? AND product_id=?", (new_qty, user_id, product_id))
        conn.commit()
        return True
    return False

def get_cart(user_id: int):
    cursor.execute("SELECT product_id, quantity FROM carts WHERE user_id=?", (user_id,))
    return cursor.fetchall()

def get_cart_total(user_id: int):
    cart = get_cart(user_id)
    total = 0
    for product_id, qty in cart:
        _, _, price = get_product_stock(product_id)
        total += price * qty
    return int(total)

def clear_cart(user_id: int):
    cursor.execute("DELETE FROM carts WHERE user_id=?", (user_id,))
    conn.commit()

# -------------------------- КЛИЕНТЫ --------------------------
def save_customer_action(user_id: int, action: str):
    cursor.execute("INSERT INTO customer_actions (user_id, action, timestamp) VALUES (?, ?, ?)", 
                  (user_id, action, datetime.now()))
    conn.commit()
    logging.info(f"👤 Клиент {user_id}: {action}")

def register_new_customer(user_id: int):
    cursor.execute("SELECT 1 FROM customer_actions WHERE user_id=? AND action='new'", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO customer_actions (user_id, action, timestamp) VALUES (?, 'new', ?)", (user_id, datetime.now()))
        cursor.execute("INSERT OR IGNORE INTO bonuses (user_id, bonus_amount, welcome_bonus_given) VALUES (?, 5.0, 1)", (user_id,))
        conn.commit()
        logging.info(f"🆕 Новый клиент: {user_id}")

# -------------------------- СКЛАД --------------------------
def update_warehouse():
    global warehouse_cache
    try:
        url = WAREHOUSE_FILE_LINK.replace('/view?', '/export?format=xlsx').replace('/edit?', '/export?format=xlsx')
        df = pd.read_excel(io.BytesIO(requests.get(url, timeout=30).content))
        warehouse_cache.clear()
        for _, row in df.iterrows():
            pid = str(row['product_id']).strip()
            qty, active, price = int(row.get('quantity', 0)), int(row.get('active', 0)), float(row.get('Price min', 0))
            if qty > 0 and active == 1:
                warehouse_cache[pid] = {'quantity': qty, 'price': price, 'active': 1, 'name': str(row.get('name', pid))}
        logging.info(f"✅ Склад: {len(warehouse_cache)} товаров")
    except Exception as e:
        logging.error(f"❌ Склад: {e}")

# -------------------------- база --------------------------
async def save_customer_action(user_id, action):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        async with aiosqlite.connect("customers.db") as db:
            await db.execute(
                "INSERT INTO customers (user_id, timestamp, action) VALUES (?, ?, ?)",
                (user_id, timestamp, action)
            )
            await db.commit()
        print(f"✅ {user_id} → {action}")
    except:
       pass

# -------------------------- ОПЕРАТОР --------------------------
async def send_operator_notification(context, user_id: int, request_type: str, details: str = ""):
    try:
        text = f"🆕 *НОВЫЙ ЗАПРОС*\n\n👤 ID: `{user_id}`\n📋 Тип: {request_type}"
        if details:
            text += f"\n📝 {details}"
        text += f"\n\n_вам напишет оператор @Scentori_"
        await context.bot.send_message(chat_id=OPERATOR_ID, text=text, parse_mode="Markdown")
    except:
        pass

# -------------------------- ERROR HANDLER --------------------------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)
    try:
        await context.bot.send_message(chat_id=OPERATOR_ID, text=f"🚨 ОШИБКА БОТА\n\n```{tb_string[:4000]}```", parse_mode="Markdown")
    except:
        pass
    logging.error(f"Error: {context.error}")

# -------------------------- HANDLERS --------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_new_customer(user_id)
    
    caption = (
        "🌿 *Приветствуем вас в Scentori*\n\n"
        "Это пространство ароматов и вашего комфорта\n\n"
        "*Каталог* — инструкции по маслам\n"
        "💡 *Помощник* — 24/7 подбор ароматов\n"
        "📞 *Оператор* — запись к терапевту\n"
        "🛒 *Корзина* + _Заказы/Бонусы_"
    )
    try:
        await update.message.reply_photo(open("images/welcome.jpg", "rb"), caption=caption, parse_mode="Markdown", reply_markup=main_menu())
    except:
        await update.message.reply_text(caption, parse_mode="Markdown", reply_markup=main_menu())

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    # Антиспам
    if user_id in last_action and time.time() - last_action[user_id] < 0.3:
        return
    last_action[user_id] = time.time()
    
    # ✅ ФИКС 4: cart_view обработчик
    if query.data.startswith("cart_view:"):
        await query.answer("👁️ Просмотр товара")
        return
    
    # Главное меню
    if query.data == "main":
        await query.edit_message_text("🏠 *Главное меню*", parse_mode="Markdown", reply_markup=main_menu())
        return
    
    # Быстрые кнопки
    if query.data == "catalog":
        save_customer_action(user_id, "catalog")
        await query.edit_message_text("🛒 *Каталог:*", parse_mode="Markdown", reply_markup=catalog_menu())
        return
    
    if query.data == "assistant":
        await query.edit_message_text("🤖 *Интерактивный помощник*\n\nt.me/scentori_helper_bot", parse_mode="Markdown", reply_markup=main_menu())
        return
    
    if query.data == "operator":
        await query.edit_message_text(f"👨‍⚕️ *Оператор*\n\nhttps://t.me/{OPERATOR_ID}", parse_mode="Markdown", reply_markup=main_menu())
        return
    
    # Корзина
    if query.data == "cart":
        await show_cart(query, user_id)
        return
    
    if query.data == "cart_clear":
        clear_cart(user_id)
        await query.edit_message_text("🛒 *Корзина очищена*", parse_mode="Markdown", reply_markup=main_menu())
        return
    
    # Корзина +/-
    if query.data.startswith(("cart_plus:", "cart_minus:")):
        pid = query.data.split(":", 1)[1]
        delta = 1 if "plus" in query.data else -1
        if change_cart_quantity(user_id, pid, delta):
            await query.answer(f"{'➕' if delta > 0 else '➖'} Обновлено")
        await show_cart(query, user_id)
        return
    
    # Оформление заказа
    if query.data == "checkout":
        save_customer_action(user_id, "checkout")
        await query.edit_message_text("📦 *Способ доставки*\n\nВыберите удобный вариант:", parse_mode="Markdown", reply_markup=delivery_menu())
        return
    
    # Доставка
    if query.data == "delivery_self":
        await query.edit_message_text("🏪 *Самовывоз*\n\nВыберите станцию метро:", parse_mode="Markdown", reply_markup=self_pickup_menu())
        return
    
    if query.data == "delivery_yandex":
        user_states[user_id] = {"step": "yandex_address"}  # ✅ ФИКС 1: словарь вместо строки
        await query.edit_message_text(
            "📦 *Доставка до ПВЗ Яндекс*\n\n"
            "Напишите свой адрес,\n"
            "мы найдем ближайший пункт выдачи:",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="main")]])
        )
        return
    
    if query.data in ("pickup_kashirskaya", "pickup_perovo"):
        point = "Каширская" if query.data == "pickup_kashirskaya" else "Перово"
        save_customer_action(user_id, f"purchase_{point}")
        await query.edit_message_text(
            f"✅ *Перевожу на оператора*\n\n"
            f"Он уже спешит к вам обсудить детали.\n\n"
            f"_вам напишет оператор @Scentori_",
            parse_mode="Markdown", reply_markup=main_menu()
        )
        await send_operator_notification(context, user_id, "Самовывоз", point)
        return
    
    # Заказы (6 месяцев)
    if query.data == "orders":
        six_months_ago = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        cursor.execute("SELECT order_id, total, timestamp FROM orders WHERE user_id=? AND timestamp > ? ORDER BY timestamp DESC", (user_id, six_months_ago))
        orders = cursor.fetchall()
        if not orders:
            await query.edit_message_text("📋 *Нет заказов за 6 месяцев*", parse_mode="Markdown", reply_markup=main_menu())
        else:
            text = "📋 *Заказы (6 мес.):*\n\n"
            for oid, total, ts in orders:
                text += f"Заказ #{oid} — {total}₽ ({ts[:10]})\n"
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu())
        return
    
    # Бонусы
    if query.data == "bonuses":
        bonus = get_user_bonus(user_id)
        text = f"⭐ *Бонусы*: {bonus:.1f}₽\n\n1% от покупок + приветственные 5₽"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu())
        return
    
    # КАТАЛОГ
    await handle_catalog(query, context, user_id)

async def show_cart(query, user_id):
    cart = get_cart(user_id)
    if not cart:
        await query.edit_message_text("🛍️ *Корзина пуста*", parse_mode="Markdown", reply_markup=main_menu())
        return
    
    total = get_cart_total(user_id)
    bonus = get_user_bonus(user_id)
    text = f"🛍️ *Корзина* ({len(cart)} товаров)\n\n"
    markup = []
    
    for pid, qty in cart:
        name = warehouse_cache.get(pid, {}).get('name', pid)[:25]
        text += f"• {name}: *{qty}* шт\n"
        markup.append([
            InlineKeyboardButton("➖", callback_data=f"cart_minus:{pid}"),
            InlineKeyboardButton(f"{qty}", callback_data=f"cart_view:{pid}"),  # ✅ ФИКС 4
            InlineKeyboardButton("➕", callback_data=f"cart_plus:{pid}")
        ])
    
    markup += [
        [InlineKeyboardButton("🗑️ Очистить корзину", callback_data="cart_clear")],
        [InlineKeyboardButton("✅ Оформить заказ", callback_data="checkout")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main")]
    ]
    
    text += f"\n💰 *Итого: {total}₽*\n⭐ *Бонусов: {bonus:.1f}₽*"
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(markup))

async def handle_catalog(query, context, user_id):
    data = query.data
    
    # 1. КАТЕГОРИЯ
    if data.startswith("cat:"):
        cat_id = data.split(":")[1]
        cat = CATALOG[cat_id]
        markup = InlineKeyboardMarkup()
        for item_path in sorted(cat['items'], key=lambda x: get_product_safe(x)['name']):
            product = get_product_safe(item_path)
            markup.row(InlineKeyboardButton(product['name'][:30], callback_data=f"product:{item_path}"))
        markup.row(InlineKeyboardButton("🏠 Главное меню", callback_data="main"))
        await query.edit_message_text(f"{cat['title']}:", reply_markup=markup)
        return
    
    # 2. КАРТОЧКА ТОВАРА
    if data.startswith("product:"):
        module_path = data.split(":", 1)[1]
        product = get_product_safe(module_path)
        pid = product['id']
        qty_stock, active, price = get_product_stock(pid)
        
        text = f"*{product['name']}*\n\n{product['properties']}\n\n*Цена: {price}₽*\n*Доступно: {qty_stock} шт.*"
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("ℹ️ Свойства", callback_data=f"prop:{module_path}")],
            [InlineKeyboardButton("📋 Применение", callback_data=f"use:{module_path}")],
            [InlineKeyboardButton("🛡️ Безопасность", callback_data=f"safety:{module_path}")],
            [InlineKeyboardButton("📊 Характеристики", callback_data=f"tech:{module_path}")],
            [InlineKeyboardButton("🛒 В корзину" if qty_stock > 0 else "🛒 Нет в наличии", callback_data=f"add:{module_path}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main")]
        ])
        
        # ✅ ФИКС: Безопасное фото БЕЗ os.path.exists()
        try:
            photo_path = product.get("photo", "images/fallback.jpg")
            await query.edit_message_media(InputMediaPhoto(open(photo_path, "rb"), caption=text, parse_mode="Markdown"), reply_markup=markup)
        except:
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=markup)
        return
    
    # 3. ДЕТАЛИ ТОВАРА
    if data.startswith(("prop:", "use:", "safety:", "tech:")):
        module_path = data.split(":", 1)[1]
        product = get_product_safe(module_path)
        step_map = {
            "prop": "Свойства", 
            "use": "Применение", 
            "safety": "Безопасность",
            "tech": "Характеристики"
        }
        content_map = {
            "prop": product["properties"], 
            "use": product.get("usage", "Информация отсутствует"), 
            "safety": product.get("safety", "Информация отсутствует"),
            "tech": product.get("tech", "Информация отсутствует")
        }
        step = data.split(":")[0]
        text = f"*{step_map[step]}*\n\n{content_map[step]}"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main")], 
            [InlineKeyboardButton("🛒 Корзина", callback_data="cart")]
        ]))
        return
    
    # 4. ДОБАВИТЬ В КОРЗИНУ
    if data.startswith("add:"):
        module_path = data.split(":", 1)[1]
        product = get_product_safe(module_path)
        if add_to_cart(user_id, product['id']):
            await query.answer("✅ Добавлено в корзину!")
        else:
            await query.answer("❌ Нет на складе!")
        return
    
    # 5. ГЛАВНАЯ СТРАНИЦА КАТАЛОГА
    save_customer_action(user_id, "catalog_view")
    await query.edit_message_text("🛒 *Каталог:*", parse_mode="Markdown", reply_markup=catalog_menu())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    # ✅ ФИКС 1: Правильная проверка user_states
    if user_states.get(user_id, {}).get("step") == "yandex_address":
        save_customer_action(user_id, "purchase_yandex")
        await update.message.reply_text(
            "✅ *Перевожу на оператора*\n\n"
            "Он уже спешит к вам обсудить детали.\n\n"
            "_вам напишет оператор @Scentori_",
            parse_mode="Markdown", reply_markup=main_menu()
        )
        await send_operator_notification(context, user_id, "Доставка до ПВЗ Яндекс", text)
        user_states.pop(user_id, None)
        return
    
    await update.message.reply_text("👆 Используйте кнопки меню", reply_markup=main_menu())

# -------------------------- ПИНГ + SCHEDULER (✅ ФИКС 3) --------------------------
def ping_thread():
    while True:
        try:
            requests.get("https://httpbin.org/delay/1", timeout=5)
        except:
            pass
        time.sleep(1800)

@app_flask.route('/')
@app_flask.route('/ping')
def ping():
    return "🤖 Bot OK"

# -------------------------- ЗАПУСК (✅ ФИКС 5) --------------------------
def main():
    # ✅ ФИКС 3: Сначала функции, потом scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_warehouse, 'cron', hour='6,14')
    scheduler.start()
    
    # ✅ ФИКС 6: Правильный Flask для Render
    if os.environ.get('RENDER'):
        flask_thread = threading.Thread(
            target=lambda: app_flask.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)), debug=False), 
            daemon=True
        )
        flask_thread.start()
        threading.Thread(target=ping_thread, daemon=True).start()
    
    # Первое обновление склада
    update_warehouse()
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

