import importlib
import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from html import escape as escape_md

# --------------------------
# ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ
# --------------------------
BOT_TOKEN = os.environ["BOT_TOKEN"]
WAREHOUSE_FILE_LINK = os.environ["WAREHOUSE_FILE_LINK"]
OPERATOR_ID = int(os.environ["OPERATOR_ID"])  # Telegram ID оператора

# --------------------------
# CATALOG
# --------------------------
CATALOG = {  
    "essential_oils": {  
        "title": "Эфирные масла",  
        "items": [  
            "products.essential.lavender",  
            "products.essential.peppermint",  
            "products.essential.eucalyptus",  
        ]  
    },  
    "aroma_oils": {  
        "title": "Парфюмерные композиции",  
        "items": [  
            "products.aroma.biskay",  
            "products.aroma.balance",  
        ]  
    },  
    "other_goods": {  
        "title": "Другие товары",  
        "items": [  
            "products.other.diffuser",  
        ]  
    }  
}

# --------------------------
# SQLite база
# --------------------------
DB_FILE = "orders.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS carts (
    user_id INTEGER,
    product_id TEXT,
    quantity INTEGER,
    PRIMARY KEY(user_id, product_id)
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    product_id TEXT,
    quantity INTEGER,
    phone TEXT,
    address TEXT,
    delivery_method TEXT
)
""")
conn.commit()

# --------------------------
# Функции для работы с продуктами
# --------------------------
def get_product(module_path: str):
    module = importlib.import_module(module_path)
    return module.PRODUCT

def get_fallback_photo(photo_path: str):
    if not os.path.exists(photo_path):
        return "images/fallback.jpg"
    return photo_path

# --------------------------
# Функции для корзины
# --------------------------
def add_to_cart(user_id: int, product_id: str):
    cursor.execute("SELECT quantity FROM carts WHERE user_id=? AND product_id=?", (user_id, product_id))
    row = cursor.fetchone()
    if row:
        cursor.execute("UPDATE carts SET quantity=? WHERE user_id=? AND product_id=?", (row[0]+1, user_id, product_id))
    else:
        cursor.execute("INSERT INTO carts (user_id, product_id, quantity) VALUES (?, ?, ?)", (user_id, product_id, 1))
    conn.commit()

def remove_from_cart(user_id: int, product_id: str):
    cursor.execute("DELETE FROM carts WHERE user_id=? AND product_id=?", (user_id, product_id))
    conn.commit()

def get_cart(user_id: int):
    cursor.execute("SELECT product_id, quantity FROM carts WHERE user_id=?", (user_id,))
    return cursor.fetchall()

# --------------------------
# START / ПРИВЕТСТВИЕ
# --------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    images_folder = "images"
    welcome_photo = os.path.join(images_folder, "welcome.jpg")
    keyboard = [
        [InlineKeyboardButton("Каталог", callback_data="catalog")],
        [InlineKeyboardButton("Корзина", callback_data="cart")],
        [InlineKeyboardButton("Прошлые заказы", callback_data="orders")],
        [InlineKeyboardButton("Интерактивный помощник", callback_data="helper")]
    ]
    caption = (
        "Добро пожаловать в Scentori! 🕯️\n\n"
        "Интерактивный помощник поможет вам выбрать аромат или собрать персональную композицию под ваше настроение. "
        "Корзина показывает текущие товары и бонусы, которые вы накопили."
    )
    if os.path.exists(welcome_photo):
        await update.message.reply_photo(open(welcome_photo, "rb"), caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(keyboard))

# --------------------------
# ОТКРЫТИЕ КАРТОЧКИ ТОВАРА
# --------------------------
async def open_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    module_path = query.data.split(":")[1]
    product = get_product(module_path)
    context.user_data["current_product"] = module_path

    text_main = (
        f"*{escape_md(product['name'])}*\n\n"
        f"{escape_md(product['properties'][:200])}...\n\n"
        f"💡 Бонус: 1% от суммы заказа начисляется на ваш бонусный счёт.\n\n"
        f"_Если хотите изучить глубже, для вас работает интерактивный помощник 24/7. "
        f"Он поможет выбрать аромат или сделать персональную композицию ароматов под ваш запрос. "
        f"Для перехода в интерактивный бот перейдите в главное меню и выберите «интерактивный помощник». "
        f"Также доступна запись к ароматерапевту через связь с оператором._"
    )
    keyboard_main = [
        [InlineKeyboardButton("Свойства", callback_data="prod_prop")],
        [InlineKeyboardButton("Применение", callback_data="prod_usage")],
        [InlineKeyboardButton("Добавить в корзину", callback_data=f"add:{module_path}")],
        [InlineKeyboardButton("На главную", callback_data="start")]
    ]
    photo_path = get_fallback_photo(product["photo"])
    await query.edit_message_media(
        media=InputMediaPhoto(open(photo_path, "rb"), caption=text_main, parse_mode="Markdown"),
        reply_markup=InlineKeyboardMarkup(keyboard_main)
    )

async def product_step_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    module_path = context.user_data.get("current_product")
    if not module_path:
        await query.edit_message_text("Ошибка: продукт не найден. Вернитесь в главное меню.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("На главную", callback_data="start")]]))
        return
    product = get_product(module_path)
    step_map = {
        "prod_prop": ("Свойства", product["properties"]),
        "prod_usage": ("Применение", product["usage"]),
        "prod_safety": ("Безопасность", product["safety"]),
        "prod_tech": ("Характеристики", product["tech"])
    }
    step = query.data
    if step not in step_map:
        return
    title, text_content = step_map[step]
    text = f"*{title}*\n\n{escape_md(text_content)}\n\n" \
           f"_Если хотите изучить глубже, для вас работает интерактивный помощник 24/7. " \
           f"Он поможет выбрать аромат или сделать персональную композицию ароматов под ваш запрос. " \
           f"Для перехода в интерактивный бот перейдите в главное меню и выберите «интерактивный помощник». " \
           f"Также доступна запись к ароматерапевту через связь с оператором._"
    keyboard = [
        [InlineKeyboardButton("Следующий блок", callback_data={
            "Свойства": "prod_usage",
            "Применение": "prod_safety",
            "Безопасность": "prod_tech",
            "Характеристики": "prod_prop"
        }[title])],
        [InlineKeyboardButton("Назад", callback_data="prod_main")],
        [InlineKeyboardButton("На главную", callback_data="start")],
        [InlineKeyboardButton("Добавить в корзину", callback_data=f"add:{module_path}")]
    ]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def product_main_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await open_product(update, context)

# --------------------------
# Callback добавления в корзину
# --------------------------
async def add_to_cart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    module_path = query.data.split(":")[1]
    product = get_product(module_path)
    add_to_cart(query.from_user.id, product["id"])
    await query.edit_message_caption(query.message.caption + "\n\n✅ Товар добавлен в корзину!", reply_markup=query.message.reply_markup)

# --------------------------
# Регистрация handler'ов
# --------------------------
def register_handlers(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(open_product, pattern=r"^product:"))
    app.add_handler(CallbackQueryHandler(product_step_callback, pattern=r"^prod_"))
    app.add_handler(CallbackQueryHandler(product_main_callback, pattern=r"^prod_main$"))
    app.add_handler(CallbackQueryHandler(add_to_cart_callback, pattern=r"^add:"))

# --------------------------
# Scheduler обновления склада
# --------------------------
def update_warehouse():
    # Здесь можно добавить код загрузки файла с Google Drive или другого источника
    pass

scheduler = BackgroundScheduler()
scheduler.add_job(update_warehouse, "interval", hours=12)
scheduler.start()

# --------------------------
# Запуск бота
# --------------------------
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    register_handlers(app)
    app.run_polling()
