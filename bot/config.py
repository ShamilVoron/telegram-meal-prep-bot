# Configuration settings
from datetime import date, timedelta

# Main Bot token
# Get it from @BotFather
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# Manager Bot (для уведомлений менеджерам)
# Optional: create a second bot for manager notifications
MANAGER_BOT_TOKEN = "YOUR_MANAGER_BOT_TOKEN_HERE"
MANAGER_CHAT_ID = 0  # Chat ID менеджера (use @userinfobot to get yours)

# Delivery schedule: {weekday: [covered_days]}
DELIVERY_DAYS = {
    6: [0, 1],      # Sunday delivery → Monday, Tuesday
    1: [2, 3],      # Tuesday delivery → Wednesday, Thursday
    3: [4, 5]       # Thursday delivery → Friday, Saturday
}

# Rations structure
RATIONS = {
    "SLIM": ["Breakfast", "Lunch", "Dinner"],
    "LIGHT": ["Breakfast", "Snack1", "Lunch", "Dinner"],
    "STANDART": ["Breakfast", "Snack1", "Lunch", "Snack2", "Dinner"],
    "MEDIUM": ["Breakfast", "Snack1", "Lunch", "Snack2", "Dinner"],
    "STRONG": ["Breakfast", "Snack1", "Lunch", "Snack2", "Dinner"]
}

# Pricing
ADD_ON_PRICES = {
    "Breakfast": 3.50,
    "Snack1": 3.00,
    "Lunch": 5.50,
    "Snack2": 3.00,
    "Dinner": 5.50
}

BASE_PRICES = {
    "OFFICE": 45,
    "SLIM": 42,
    "LIGHT": 48,
    "STANDART": 55,
    "MEDIUM": 65,
    "STRONG": 75
}

SWAP_PRICE_MAIN = 0.00 # Basic swap is free within 2 days
SWAP_PRICE_SNACK = 0.00
SWAP_PRICE_PREMIUM = 3.00

# Replacement rules prices
REPLACEMENT_PRICES = {
    "FISH_TO_MEAT": 3.00,
    "MEAT_TO_FISH": 3.00,
    "RED_MEAT": 3.00,
    "PORK": 3.00
}

# Default number of days to order
DEFAULT_ORDER_DAYS = 6

# WebApp URL disabled for chat-only flow
# Веб интерфейс отключён, оставляем пустым
# Ранее: ссылка ngrok/webapp. Сейчас не используется.
# Ранее: продакшен веб-приложения. Сейчас не используется.

# WebApp отключён
WEBAPP_URL = ""
