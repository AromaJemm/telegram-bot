# products.py
# Реестр товаров Scentori
# Все данные редактируются без изменения main.py

# =========================
# КАТЕГОРИИ
# =========================

CATEGORIES = {
    "essential": "🌿 Эфирные масла",
    "aroma": "🕯 Аромамасла",
    "other": "✨ Другие товары"
}

# =========================
# ТОВАРЫ
# =========================
# product_id — КЛЮЧ. Он же используется в файле остатков.
# image — локальный путь
# allow_preorder — разрешён ли предзаказ при отсутствии

PRODUCTS = {

    # ===== ЭФИРНЫЕ МАСЛА =====

    "orange_10": {
        "name": "Апельсин",
        "subtitle": "Citrus sinensis · 10 мл",
        "category": "essential",
        "image": "images/products/orange.jpg",
        "price": 1300,
        "bot_price": 1040,
        "allow_preorder": True,
        "intro": "Тёплый, солнечный аромат для поднятия настроения и уюта.",
        "sections": {
            "properties": "• Антидепрессивное\n• Расслабляющее\n• Освежающее",
            "usage": "• Диффузор\n• Аромалампа\n• Аромаванны (в разведении)",
            "safety": "⚠️ Фототоксично\nИзбегать солнца после нанесения",
            "tech": "Метод: холодный отжим\nЧасть растения: кожура"
        }
    },

    "bergamot_10": {
        "name": "Бергамот",
        "subtitle": "Citrus bergamia · 10 мл",
        "category": "essential",
        "image": "images/products/bergamot.jpg",
        "price": 1800,
        "bot_price": 1440,
        "allow_preorder": True,
        "intro": "Балансирует эмоции, снимает тревожность.",
        "sections": {
            "properties": "• Антидепрессивное\n• Успокаивающее",
            "usage": "• Диффузор\n• Аромамедальон",
            "safety": "⚠️ Фототоксично",
            "tech": "Метод: холодный отжим"
        }
    },

    "clove_10": {
        "name": "Гвоздика",
        "subtitle": "Syzygium aromaticum · 10 мл",
        "category": "essential",
        "image": "images/products/clove.jpg",
        "price": 1700,
        "bot_price": 1360,
        "allow_preorder": True,
        "intro": "Пряный, тёплый аромат. Сильное масло.",
        "sections": {
            "properties": "• Антисептическое\n• Согревающее",
            "usage": "• В смесях\n• Аромалампа",
            "safety": "⚠️ Использовать только в разведении",
            "tech": "Метод: дистилляция"
        }
    },

    "cedar_10": {
        "name": "Кедр",
        "subtitle": "Cedrus atlantica · 10 мл",
        "category": "essential",
        "image": "images/products/cedar.jpg",
        "price": 1900,
        "bot_price": 1520,
        "allow_preorder": True,
        "intro": "Заземляющий, древесный аромат.",
        "sections": {
            "properties": "• Успокаивающее\n• Антисептическое",
            "usage": "• Медитация\n• Диффузор",
            "safety": "Не применять при беременности",
            "tech": "Метод: дистилляция"
        }
    },

    "cinnamon_10": {
        "name": "Корица",
        "subtitle": "Cinnamomum zeylanicum · 10 мл",
        "category": "essential",
        "image": "images/products/cinnamon.jpg",
        "price": 2000,
        "bot_price": 1600,
        "allow_preorder": True,
        "intro": "Горячее и стимулирующее масло.",
        "sections": {
            "properties": "• Стимулирующее\n• Антисептическое",
            "usage": "• Только в смесях",
            "safety": "⚠️ Высокая концентрация",
            "tech": "Метод: дистилляция"
        }
    },

    "frankincense_10": {
        "name": "Ладан",
        "subtitle": "Boswellia carterii · 10 мл",
        "category": "essential",
        "image": "images/products/frankincense.jpg",
        "price": 2600,
        "bot_price": 2080,
        "allow_preorder": True,
        "intro": "Медитативный, смолистый аромат.",
        "sections": {
            "properties": "• Успокаивающее\n• Восстанавливающее",
            "usage": "• Медитация\n• Уход за кожей",
            "safety": "Подходит для чувствительной кожи",
            "tech": "Метод: дистилляция смолы"
        }
    },

    "lavender_10": {
        "name": "Лаванда",
        "subtitle": "Lavandula angustifolia · 10 мл",
        "category": "essential",
        "image": "images/products/lavender.jpg",
        "price": 1600,
        "bot_price": 1280,
        "allow_preorder": True,
        "intro": "Универсальное масло для расслабления.",
        "sections": {
            "properties": "• Успокаивающее\n• Регенерирующее",
            "usage": "• Сон\n• Стресс",
            "safety": "Без фототоксичности",
            "tech": "Метод: дистилляция"
        }
    },

    "lemongrass_10": {
        "name": "Лемонграсс",
        "subtitle": "Cymbopogon citratus · 10 мл",
        "category": "essential",
        "image": "images/products/lemongrass.jpg",
        "price": 1500,
        "bot_price": 1200,
        "allow_preorder": True,
        "intro": "Свежий, цитрусово-травяной аромат.",
        "sections": {
            "properties": "• Тонизирующее\n• Освежающее",
            "usage": "• Диффузор\n• Рабочее пространство",
            "safety": "Использовать в разведении",
            "tech": "Метод: дистилляция"
        }
    },

    "lemon_10": {
        "name": "Лимон",
        "subtitle": "Citrus limon · 10 мл",
        "category": "essential",
        "image": "images/products/lemon.jpg",
        "price": 1400,
        "bot_price": 1120,
        "allow_preorder": True,
        "intro": "Чистый и бодрящий аромат.",
        "sections": {
            "properties": "• Антисептическое\n• Тонизирующее",
            "usage": "• Утро\n• Концентрация",
            "safety": "⚠️ Фототоксично",
            "tech": "Метод: холодный отжим"
        }
    },

    "mandarin_10": {
        "name": "Мандарин",
        "subtitle": "Citrus reticulata · 10 мл",
        "category": "essential",
        "image": "images/products/mandarin.jpg",
        "price": 1500,
        "bot_price": 1200,
        "allow_preorder": True,
        "intro": "Мягкий, сладкий цитрус.",
        "sections": {
            "properties": "• Успокаивающее",
            "usage": "• Вечер\n• Детские смеси",
            "safety": "⚠️ Фототоксично",
            "tech": "Метод: холодный отжим"
        }
    },

    "almond_10": {
        "name": "Миндаль",
        "subtitle": "Prunus amygdalus · 10 мл",
        "category": "essential",
        "image": "images/products/almond.jpg",
        "price": 1200,
        "bot_price": 960,
        "allow_preorder": True,
        "intro": "Мягкое, нейтральное масло.",
        "sections": {
            "properties": "• Смягчающее",
            "usage": "• База для смесей",
            "safety": "Подходит для чувствительной кожи",
            "tech": "Метод: холодный отжим"
        }
    },

    "juniper_10": {
        "name": "Можжевельник",
        "subtitle": "Juniperus communis · 10 мл",
        "category": "essential",
        "image": "images/products/juniper.jpg",
        "price": 1900,
        "bot_price": 1520,
        "allow_preorder": True,
        "intro": "Свежий, хвойный аромат.",
        "sections": {
            "properties": "• Очищающее",
            "usage": "• Детокс\n• Диффузор",
            "safety": "Не применять при беременности",
            "tech": "Метод: дистилляция"
        }
    },

    "neroli_10": {
        "name": "Нероли",
        "subtitle": "Citrus aurantium · 10 мл",
        "category": "essential",
        "image": "images/products/neroli.jpg",
        "price": 3500,
        "bot_price": 2800,
        "allow_preorder": True,
        "intro": "Элитное масло для глубокого расслабления.",
        "sections": {
            "properties": "• Антистресс",
            "usage": "• Вечер\n• Медитация",
            "safety": "Подходит для чувствительной кожи",
            "tech": "Метод: дистилляция цветков"
        }
    },

    "rosemary_10": {
        "name": "Розмарин",
        "subtitle": "Rosmarinus officinalis · 10 мл",
        "category": "essential",
        "image": "images/products/rosemary.jpg",
        "price": 1500,
        "bot_price": 1200,
        "allow_preorder": True,
        "intro": "Масло ясности и концентрации.",
        "sections": {
            "properties": "• Стимулирующее",
            "usage": "• Работа\n• Учёба",
            "safety": "Не применять при эпилепсии",
            "tech": "Метод: дистилляция"
        }
    },

    "pine_10": {
        "name": "Сосна",
        "subtitle": "Pinus sylvestris · 10 мл",
        "category": "essential",
        "image": "images/products/pine.jpg",
        "price": 1400,
        "bot_price": 1120,
        "allow_preorder": True,
        "intro": "Чистый хвойный аромат.",
        "sections": {
            "properties": "• Очищающее",
            "usage": "• Простуда\n• Диффузор",
            "safety": "Использовать в разведении",
            "tech": "Метод: дистилляция"
        }
    },

    "tea_tree_10": {
        "name": "Чайное дерево",
        "subtitle": "Melaleuca alternifolia · 10 мл",
        "category": "essential",
        "image": "images/products/tea_tree.jpg",
        "price": 1500,
        "bot_price": 1200,
        "allow_preorder": True,
        "intro": "Мощное антисептическое масло.",
        "sections": {
            "properties": "• Антибактериальное",
            "usage": "• Уход\n• Дом",
            "safety": "Использовать в разведении",
            "tech": "Метод: дистилляция"
        }
    },

    "eucalyptus_10": {
        "name": "Эвкалипт",
        "subtitle": "Eucalyptus globulus · 10 мл",
        "category": "essential",
        "image": "images/products/eucalyptus.jpg",
        "price": 1400,
        "bot_price": 1120,
        "allow_preorder": True,
        "intro": "Освежающее дыхательное масло.",
        "sections": {
            "properties": "• Очищающее",
            "usage": "• Простуда\n• Диффузор",
            "safety": "Не применять детям",
            "tech": "Метод: дистилляция"
        }
    },

    "peppermint_10": {
        "name": "Мята перечная",
        "subtitle": "Mentha piperita · 10 мл",
        "category": "essential",
        "image": "images/products/peppermint.jpg",
        "price": 1500,
        "bot_price": 1200,
        "allow_preorder": True,
        "intro": "Охлаждающее и бодрящее масло.",
        "sections": {
            "properties": "• Освежающее\n• Стимулирующее",
            "usage": "• Работа\n• Дорога",
            "safety": "Не применять детям",
            "tech": "Метод: дистилляция"
        }
    },

    # ===== АРОМАМАСЛА =====

    "balance_30": {
        "name": "Balance",
        "subtitle": "Аромамасло Scentori · 30 мл",
        "category": "aroma",
        "image": "images/products/balance.jpg",
        "price": 2200,
        "bot_price": 1760,
        "allow_preorder": True,
        "intro": "Авторская композиция для гармонии.",
        "sections": {
            "properties": "• Балансирующее",
            "usage": "• Диффузор",
            "safety": "Не наносить на кожу",
            "tech": "Производство: Scentori"
        }
    },

    "biskay_30": {
        "name": "Biskay",
        "subtitle": "Аромамасло · 30 мл",
        "category": "aroma",
        "image": "images/products/biskay.jpg",
        "price": 2200,
        "bot_price": 1760,
        "allow_preorder": True,
        "intro": "Глубокий, атмосферный аромат.",
        "sections": {
            "properties": "• Атмосферное",
            "usage": "• Интерьер",
            "safety": "Не наносить на кожу",
            "tech": "Производство: Scentori"
        }
    },

    "festa_30": {
        "name": "Festa",
        "subtitle": "Аромамасло · 30 мл",
        "category": "aroma",
        "image": "images/products/festa.jpg",
        "price": 2200,
        "bot_price": 1760,
        "allow_preorder": True,
        "intro": "Яркая композиция для настроения.",
        "sections": {
            "properties": "• Тонизирующее",
            "usage": "• Пространство",
            "safety": "Не наносить на кожу",
            "tech": "Производство: Scentori"
        }
    },

    "passion_30": {
        "name": "Passion",
        "subtitle": "Аромамасло · 30 мл",
        "category": "aroma",
        "image": "images/products/passion.jpg",
        "price": 2200,
        "bot_price": 1760,
        "allow_preorder": True,
        "intro": "Тёплая, чувственная композиция.",
        "sections": {
            "properties": "• Расслабляющее",
            "usage": "• Вечер",
            "safety": "Не наносить на кожу",
            "tech": "Производство: Scentori"
        }
    },

    "verdi_30": {
        "name": "Verdi",
        "subtitle": "Аромамасло · 30 мл",
        "category": "aroma",
        "image": "images/products/verdi.jpg",
        "price": 2200,
        "bot_price": 1760,
        "allow_preorder": True,
        "intro": "Свежая, зелёная композиция.",
        "sections": {
            "properties": "• Освежающее",
            "usage": "• День",
            "safety": "Не наносить на кожу",
            "tech": "Производство: Scentori"
        }
    },

    # ===== ДРУГИЕ ТОВАРЫ =====

    "flacon_10": {
        "name": "Флакон с пипеткой",
        "subtitle": "10 мл",
        "category": "other",
        "image": "images/products/flacon_10.jpg",
        "price": 150,
        "bot_price": 120,
        "allow_preorder": False,
        "intro": "Стеклянный флакон с крышкой-пипеткой.",
        "sections": {
            "properties": "• Стекло\n• Пипетка",
            "usage": "• Для масел",
            "safety": "Хрупкое изделие",
            "tech": "Объём: 10 мл"
        }
    },

    "flacon_30": {
        "name": "Флакон с пипеткой",
        "subtitle": "30 мл",
        "category": "other",
        "image": "images/products/flacon_30.jpg",
        "price": 200,
        "bot_price": 160,
        "allow_preorder": False,
        "intro": "Стеклянный флакон с крышкой-пипеткой.",
        "sections": {
            "properties": "• Стекло\n• Пипетка",
            "usage": "• Для масел",
            "safety": "Хрупкое изделие",
            "tech": "Объём: 30 мл"
        }
    },

    "flacon_100": {
        "name": "Флакон с пипеткой",
        "subtitle": "100 мл",
        "category": "other",
        "image": "images/products/flacon_100.jpg",
        "price": 350,
        "bot_price": 280,
        "allow_preorder": False,
        "intro": "Стеклянный флакон с крышкой-пипеткой.",
        "sections": {
            "properties": "• Стекло\n• Пипетка",
            "usage": "• Для масел",
            "safety": "Хрупкое изделие",
            "tech": "Объём: 100 мл"
        }
    },

    "diffuser_basic": {
        "name": "Ультразвуковой диффузор",
        "subtitle": "Для эфирных масел",
        "category": "other",
        "image": "images/products/diffuser.jpg",
        "price": 4500,
        "bot_price": 3900,
        "allow_preorder": True,
        "intro": "Минималистичный диффузор для дома.",
        "sections": {
            "properties": "• Тихая работа\n• Подсветка",
            "usage": "• Дом\n• Спальня",
            "safety": "Использовать с водой",
            "tech": "Питание: USB"
        }
    }
}
