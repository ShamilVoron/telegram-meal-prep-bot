# Utility functions
from datetime import date, timedelta
from collections import defaultdict
import uuid
from bot.config import DELIVERY_DAYS, ADD_ON_PRICES, SWAP_PRICE_MAIN, SWAP_PRICE_SNACK
from bot.data import DISHES, BASE_MENU
from bot.translations import TRANSLATIONS

# In-memory storage
user_carts = defaultdict(list)

def get_next_delivery_date(from_date: date) -> date:
    """Find next delivery date from given date"""
    weekday = from_date.weekday()
    
    if weekday < 1:
        days_ahead = 1 - weekday
    elif weekday < 3:
        days_ahead = 3 - weekday
    elif weekday < 6:
        days_ahead = 6 - weekday
    else:
        days_ahead = 2
    
    return from_date + timedelta(days=days_ahead)

def get_available_meal_dates(order_date: date, num_days: int = 6) -> list:
    """Get list of available meal dates based on delivery schedule"""
    meal_dates = []
    current_delivery = get_next_delivery_date(order_date)
    
    while len(meal_dates) < num_days:
        delivery_weekday = current_delivery.weekday()
        if delivery_weekday in DELIVERY_DAYS:
            for day_offset in DELIVERY_DAYS[delivery_weekday]:
                meal_date = current_delivery + timedelta(days=(day_offset - delivery_weekday))
                if meal_date not in meal_dates:
                    meal_dates.append(meal_date)
                    if len(meal_dates) >= num_days:
                        break
        
        current_delivery = get_next_delivery_date(current_delivery + timedelta(days=1))
    
    return sorted(meal_dates[:num_days])

def is_snack(category: str) -> bool:
    return "Snack" in category

def calculate_swap_price(original_id: int, modified_id: int) -> float:
    """Calculate price for swapping dishes based on ingredients"""
    from bot.config import SWAP_PRICE_PREMIUM
    
    if original_id == modified_id:
        return 0.0
        
    d1 = DISHES.get(original_id, {})
    d2 = DISHES.get(modified_id, {})
    
    # If basic info missing, assume free
    if not d1 or not d2:
        return 0.0
        
    type1 = d1.get('meat_type')
    type2 = d2.get('meat_type')
    
    # Same type = free (e.g. chicken to chicken)
    if type1 == type2:
        return 0.0
        
    # Check for premium swaps
    # Any change involving Fish, Beef (Red Meat), Pork costs money
    premium_types = ['fish', 'beef', 'pork']
    
    if type1 in premium_types or type2 in premium_types:
        return SWAP_PRICE_PREMIUM
        
    return 0.0

def get_price(operation: str, category: str, original_id: int = None, modified_id: int = None) -> float:
    if operation == "SWAP":
        if is_snack(category):
            return SWAP_PRICE_SNACK
        # For main dishes, calculate based on content
        if original_id and modified_id:
            return calculate_swap_price(original_id, modified_id)
        return SWAP_PRICE_MAIN
    elif operation == "ADD_ON":
        return ADD_ON_PRICES.get(category, 0.0)
    return 0.0

def format_dish_with_kbju(dish_id: int, lang: str = 'ru') -> str:
    d = DISHES.get(dish_id)
    if not d:
        return "Неизвестное блюдо"
    name = d.get(f"name_{lang}", d.get("name_ru", ""))
    
    # Add price info if swap is not free
    # We need original context to know price, but here we just formatting list item
    # So we can't show price here easily unless we pass original_id to this function too.
    # For now just show dish info.
    
    kbju = f" — {d.get('kcal', '?')}kcal"
    return f"{name}{kbju}"

def get_current_dish(user_id: int, date_str: str, category: str) -> int:
    original_id = BASE_MENU.get(date_str, {}).get(category, 1)
    modified_id = original_id
    
    for mod in user_carts[user_id]:
        if (mod["order_date"] == date_str and mod["meal_category"] == category and
                mod["operation_type"] == "SWAP"):
            modified_id = mod["modified_dish_id"]
            break

    if modified_id == original_id:
        for mod in user_carts[user_id]:
            if (mod["order_date"] == date_str and mod["meal_category"] == category and
                    mod["operation_type"] == "BASE_SWAP"):
                modified_id = mod["modified_dish_id"]
                break

    return modified_id

def get_current_dish_name(user_id: int, date_str: str, category: str, lang: str = 'ru') -> str:
    dish_id = get_current_dish(user_id, date_str, category)
    dish = DISHES.get(dish_id, {})
    dish_name = dish.get(f"name_{lang}", dish.get("name_ru", "Неизвестное блюдо"))
    return dish_name

def get_mods_for_meal(user_id: int, date_str: str, category: str) -> dict:
    mods = {}
    for mod in user_carts[user_id]:
        if mod["order_date"] == date_str and mod["meal_category"] == category:
            mods[mod["operation_type"]] = mod
    return mods

def add_modification(user_id: int, date_str: str, category: str,
                     operation_type: str, original_id: int, modified_id, quantity: int = 1):
    price_impact = get_price(operation_type, category, original_id, modified_id)
    total_cost = price_impact * quantity
    mod = {
        "modification_id": str(uuid.uuid4()),
        "user_id": user_id,
        "order_date": date_str,
        "meal_category": category,
        "operation_type": operation_type,
        "original_dish_id": original_id,
        "modified_dish_id": modified_id,
        "quantity": quantity,
        "price_impact": price_impact,
        "total_cost": total_cost
    }

    if operation_type == "SWAP":
        user_carts[user_id] = [
            m for m in user_carts[user_id]
            if not (m["order_date"] == date_str and m["meal_category"] == category and
                    m["operation_type"] == operation_type)
        ]

    user_carts[user_id].append(mod)

def format_date_display(date_obj: date, lang: str) -> str:
    """Format date for display: 'Пн 18.11' or 'Mon 11/18'"""
    weekday_names = TRANSLATIONS[lang]["weekdays"]
    weekday = weekday_names[date_obj.weekday()]
    if lang == "en":
        return f"{weekday} {date_obj.strftime('%m/%d')}"
    else:
        return f"{weekday} {date_obj.strftime('%d.%m')}"

# ==================== КАЛЬКУЛЯТОР ККАЛ ====================
def calculate_bmr(gender: str, age: int, height: int, weight: int) -> float:
    """
    Формула Харриса-Бенедикта для расчета базального метаболизма
    gender: 'M' или 'F'
    age: возраст в годах
    height: рост в сантиметрах
    weight: вес в килограммах
    Возвращает калории в покое
    """
    if gender == 'M':
        bmr = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
    else:  # F
        bmr = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)
    return bmr

def calculate_tdee(bmr: float, activity_level: float) -> float:
    """
    Расчет суточного расхода энергии (TDEE)
    activity_level: коэффициент активности (1.2-1.9)
    """
    return bmr * activity_level

def get_ration_by_kcal(daily_kcal: float) -> tuple:
    """
    Определяет рекомендуемый рацион по количеству ккал
    Возвращает (ration_name, recommended_kcal)
    """
    from bot.config import BASE_PRICES, RATIONS
    
    # Примерные ккал для каждого рациона (вычисленные на основе типичного меню)
    ration_kcals = {
        "SLIM": 1400,       # Завтрак + обед + ужин (без перекусов)
        "LIGHT": 1700,      # + 1 перекус
        "STANDART": 2000,   # + 2 перекуса
        "MEDIUM": 2200,     # + 2 перекуса + большие порции
        "STRONG": 2500,     # + 2 перекуса + максимальные порции
    }
    
    # Выбираем рацион, ближайший к рассчитанному
    best_ration = "STANDART"
    min_diff = abs(daily_kcal - ration_kcals["STANDART"])
    
    for ration, kcal in ration_kcals.items():
        diff = abs(daily_kcal - kcal)
        if diff < min_diff:
            min_diff = diff
            best_ration = ration
    
    return best_ration, ration_kcals[best_ration]

def adjust_kcal_for_goal(daily_kcal: float, goal: str) -> float:
    """
    Корректирует калории в зависимости от цели
    goal: 'lose', 'maintain', 'gain'
    """
    if goal == "lose":
        return daily_kcal - 500  # Дефицит 500 ккал
    elif goal == "gain":
        return daily_kcal + 500  # Профицит 500 ккал
    else:  # maintain
        return daily_kcal

def get_daily_ration_kcal(ration: str) -> float:
    """Получить примерное кол-во ккал для рациона"""
    ration_kcals = {
        "SLIM": 1400,
        "LIGHT": 1700,
        "STANDART": 2000,
        "MEDIUM": 2200,
        "STRONG": 2500,
    }
    return ration_kcals.get(ration, 2000)

# ==================== ВАЛИДАЦИЯ ДОСТАВКИ ====================
def get_delivery_group(weekday: int) -> tuple:
    """
    Возвращает группу доставки и информацию о доставке
    weekday: день недели (0-6, где 0=понедельник)
    Возвращает (group_days, delivery_day, delivery_time_ru)
    """
    delivery_groups = {
        0: ([0, 1], 6, "Воскресенье 19:30-22:30"),      # Пн/Вт - доставка Вс
        1: ([0, 1], 6, "Воскресенье 19:30-22:30"),      # Пн/Вт - доставка Вс
        2: ([2, 3], 1, "Вторник 19:30-22:30"),          # Ср/Чт - доставка Вт
        3: ([2, 3], 1, "Вторник 19:30-22:30"),          # Ср/Чт - доставка Вт
        4: ([4, 5], 3, "Четверг 19:30-22:30"),          # Пт/Сб - доставка Чт
        5: ([4, 5], 3, "Четверг 19:30-22:30"),          # Пт/Сб - доставка Чт
        6: ([0, 1], 6, "Воскресенье 19:30-22:30"),      # Вс - доставка Вс (на Пн/Вт)
    }
    return delivery_groups.get(weekday, ([0, 1], 6, "Воскресенье 19:30-22:30"))

def validate_delivery_days(selected_dates: list) -> bool:
    """
    Проверяет, что все выбранные дни соответствуют одной группе доставки
    selected_dates: список дат в формате YYYY-MM-DD
    """
    if len(selected_dates) == 0:
        return True
    
    # Преобразуем в даты
    dates = [date.fromisoformat(d) for d in selected_dates]
    
    # Получаем группы доставки для каждого дня
    groups = set()
    for d in dates:
        group, _, _ = get_delivery_group(d.weekday())
        groups.add(tuple(group))
    
    # Все дни должны относиться к одной группе
    return len(groups) == 1

def get_delivery_info(selected_dates: list, lang: str = "ru") -> str:
    """
    Возвращает информацию о доставке для выбранных дат
    """
    if not selected_dates:
        return ""
    
    dates = [date.fromisoformat(d) for d in selected_dates]
    first_date = dates[0]
    group_days, delivery_weekday, delivery_time = get_delivery_group(first_date.weekday())
    
    # Формируем список дней
    weekday_names = TRANSLATIONS[lang]["weekdays"]
    days_str = ", ".join([weekday_names[d] for d in group_days])
    
    # Формируем дату доставки
    days_until_delivery = (delivery_weekday - first_date.weekday()) % 7
    if days_until_delivery == 0 and first_date.weekday() != delivery_weekday:
        days_until_delivery = 7
    delivery_date = first_date + timedelta(days=days_until_delivery)
    
    delivery_date_str = format_date_display(delivery_date, lang)
    
    return f"📦 Дни: {days_str}\n📅 Доставка: {delivery_date_str} ({delivery_time})"

def calculate_day_kcal(user_id: int, date_str: str, lang: str = "ru") -> int:
    """
    Рассчитывает суммарные ккал за день с учетом свопов и добавок
    """
    total_kcal = 0
    
    # Получаем все приемы пищи на этот день
    from bot.config import RATIONS
    
    # Подразумеваем стандартный набор приемов пищи
    meals = ["Breakfast", "Snack1", "Lunch", "Snack2", "Dinner"]
    
    for meal in meals:
        # Получаем текущее блюдо (с учетом свопов)
        current_dish_id = get_current_dish(user_id, date_str, meal)
        dish = DISHES.get(current_dish_id, {})
        total_kcal += dish.get("kcal", 0)
    
    return total_kcal
