import os
import telebot
from flask import Flask, request
from threading import Thread
import time
import requests
import logging
from waitress import serve

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
PORT = int(os.getenv("PORT", 8080))

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
            instructions = """🌿 <b>Инструкция к ЛАВАНДЕ</b>

Спасибо, что выбрали наш продукт! Перед вами 100% натуральное эфирное масло лаванды холодного отжима, полученное методом паровой дистилляции.
Наше масло идеально подходит для ароматерапии, ухода за кожей и создания гармонии атмосферы.

🔹<b>Основные способы применения</b>
1. <b>Ароматерапия</b>
   • Аромалампа/диффузор: 3-5 капель на 15 м².
     Эффект: снятие стресса, улучшение сна.
   • Ингаляции: 1-2 капли в миску с горячей водой (накройте голову полотенцем, 5 минут).
     Есть противопоказания: астма, аллергия.

2. <b>Косметическое использование</b>
   • Обогащение косметических средств: 2-3 капли на 10 мл крема/шампуня.
   • Массажное масло: 5 капель на 10 мл базового масла (персиковое, миндальное, виноградной косточки).
   • Спа-ванна: 5-7 капель + 1 ст.л. эмульгатора (молоко, морская соль).
     <b>Важно!</b> Не наносите чистое масло на кожу – возможен ожог.

3. <b>Бытовое применение</b>
   • Аромасаше: 2-3 капли на деревянную/керамическую подвеску или гипсовое саше.
   • Дезодорация белья: 5 капель на салфетку в шкафу.
   • Антисептик: 10 капель + 100 мл воды в спрее (обработайте дверные ручки, гаджеты).

⚠️ <b>Меры предосторожности</b>
   • Тест на аллергию: нанесите 1 каплю, разведенную в базовом масле, на запястье.
   • Хранение: флакон из темного стекла при +15...+20°С (допустимо +5...+25°С).
     ▸ При замерзании (ниже +5°C) ухудшаются свойства.
     ▸ При перегреве (выше +25°C) происходит резкое окисление.
   • <b>Запрещено</b>:
     ▸ Беременным в I триместре
     ▸ Детям до 7 лет (для 1-7 лет - только 1 капля на 2 ст.л. основы)
     ▸ При эпилепсии и гипотонии

💡 <b>Лайфхаки для максимального эффекта</b>
   • Экспресс-релакс: нанесите пару капель масла на салфетку или ватный диск, вдыхайте аромат в течение 30 секунд.
   • Сон, как у ребенка: положите салфетку с парой капель масла рядом с подушкой. Наслаждайтесь здоровым сном!
   • Аптечка путешественника: смешайте 10 капель лаванды + 10 капель мяты в роллере с маслом-основой (миндальное, персиковое, виноградной косточки).
   • Ароматизатор и антисептик для уборки: 5–7 капель в ведро воды при мытье полов.
   • Экстренная помощь при ожогах: точечно нанесите чистую каплю (только для взрослых!).
   • Репеллент своими руками: 10 капель лаванды + 10 капель цитронеллы на 100 мл воды.
   • СПА для волос: 3 капли + 2 ст.л. репейного масла на корни на 40 минут.

🌐 <b>Мы всегда на связи</b>
   • Хотите персональные рецепты? Пишите на наш Telegram-канал Jemm - еженедельно публикуем авторские смеси масел.
   • Воспользуйтесь нашей библиотекой по ароматерапии получите ответы на свои вопросы в форме вопрос-ответ в боте Aroma_Bot
   • Задайте ваш вопрос, и мы свяжемся с вами, чтобы помочь 🌿

📌 <b>Почему выбирают нас?</b>
   ▸ Холодный отжим – сохраняет максимум полезных свойств.
   ▸ Сертификаты ECOCERT – гарантия чистоты состава.
   ▸ Прозрачность: на сайте - отчет ГХ-МС по каждой партии.

ПС. При покупке от 3-х флаконов - мини-гид по ароматерапии в подарок!
При покупке 2-х флаконов - чек-лист "7 неочевидных способов применения эфирных масел".

Команда Джемм. Ваше здоровье - наша миссия.
"""

            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(telebot.types.KeyboardButton("Назад к инструкциям"))
            bot.send_message(message.chat.id, instructions, parse_mode='HTML', reply_markup=markup)

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
    serve(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=WEBHOOK_URL)
        
        Thread(target=ping_server, daemon=True).start()
        run_flask()

    except Exception as e:
        logging.critical(f"💥 Критическая ошибка: {e}")