import os
import telebot
from flask import Flask, request
from threading import Thread
import time
import requests
import logging

# --- Настройка логов ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

app = Flask(__name__)
token = os.getenv("TELEGRAM_TOKEN")

if not token:
    logging.error("❌ TELEGRAM_TOKEN не найден. Добавьте его в Environment Variables на Render!")
    exit(1)

bot = telebot.TeleBot(token)
WEBHOOK_URL = f"https://{os.getenv('RENDER_SERVICE_NAME')}.onrender.com/{token}"

# --- Автопробуждение ---
def ping_server():
    while True:
        try:
            requests.get(f"https://{os.getenv('RENDER_SERVICE_NAME')}.onrender.com")
            logging.info("🔄 Пинг отправлен")
        except Exception as e:
            logging.error(f"❌ Ошибка пинга: {e}")
        time.sleep(300)

# --- Вебхуки ---
@app.route("/")
def home():
    return "Бот активен! Мониторинг: UptimeRobot + Render"

@app.route(f"/{token}", methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_data = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_data)
        bot.process_new_updates([update])
        return "OK", 200
    return "Forbidden", 403

# --- Обработчики команд ---
@bot.message_handler(commands=["start"])
def start(message):
    try:
        markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        buttons = ["Каталог", "Инструкции к товарам", "ИИ-помощник", "Консультация"]
        markup.add(*[telebot.types.KeyboardButton(btn) for btn in buttons])
        bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)
    except Exception as e:
        logging.error(f"❌ Ошибка в /start: {e}")

@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    try:
        if message.text == "Каталог":
            bot.send_message(message.chat.id, "🔗 Ссылка на каталог: [ваш_сайт]")

        elif message.text == "Инструкции к товарам":
            markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
            items = ["ЛАВАНДА", "БЕРГАМОТ", "МЯТА", "МИКС", "Назад"]
            markup.add(*[telebot.types.KeyboardButton(item) for item in items])
            bot.send_message(message.chat.id, "Выберите товар:", reply_markup=markup)

        elif message.text == "ИИ-помощник":
            bot.send_message(message.chat.id, "Напишите вопрос (пример: 'Как использовать масло чайного дерева?')")

        elif message.text == "Консультация":
            bot.send_message(message.chat.id, "💬 Опишите вопрос, специалист ответит в течение 30 минут")

        elif message.text == "ЛАВАНДА":
            instructions = "🌿 Инструкция для лаванды..."

🔹 <u>Основные способы применения</u>:
1. <b>Ароматерапия</b>:
   • Аромалампа: 3-5 капель на 15 м²
   • Ингаляции: 1-2 капли в горячую воду (5 мин)

2. <b>Косметика</b>:
   • Обогащение кремов: 2-3 капли на 10 мл
   • Массаж: 5 капель на 10 мл основы
   • Ванна: 5-7 капель + 1 ст.л. соли

3. <b>Бытовое применение</b>:
   • Аромасаше: 2-3 капли
   • Антисептик: 10 капель + 100 мл воды

⚠️ <b>Меры предосторожности</b>:
   • Тест на аллергию обязателен
   • Хранить при +15...+20°C
   • Запрещено:
     - Беременным (I триместр)
     - Детям до 7 лет
     - При эпилепсии

💡 <b>Лайфхаки</b>:
   • Для сна: 2 капли на салфетку у подушки
   • Репеллент: смесь с цитронеллой
   • СПА для волос: 3 капли + репейное масло

📌 <b>Почему выбирают нас</b>:
   • Холодный отжим
   • Сертификаты ECOCERT
   • Отчеты по каждой партии
"""

            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(telebot.types.KeyboardButton("Назад к инструкциям"))
            bot.send_message(message.chat.id, instructions, reply_markup=markup)

        elif message.text == "Назад к инструкциям":
            markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
            markup.add(*[telebot.types.KeyboardButton(item) for item in ["ЛАВАНДА", "БЕРГАМОТ", "МЯТА", "МИКС", "Назад в главное меню"]])
            bot.send_message(message.chat.id, "Выберите товар:", reply_markup=markup)

        elif message.text == "Назад в главное меню":
            markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
            markup.add(*[telebot.types.KeyboardButton(btn) for btn in ["Каталог", "Инструкции к товарам", "ИИ-помощник", "Консультация"]])
            bot.send_message(message.chat.id, "Главное меню:", reply_markup=markup)

    except Exception as e:
        logging.error(f"❌ Ошибка обработки кнопки: {e}")

def run_flask():
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=WEBHOOK_URL)
        
        Thread(target=ping_server, daemon=True).start()
        run_flask()

    except Exception as e:
        logging.critical(f"💥 Критическая ошибка: {e}")
