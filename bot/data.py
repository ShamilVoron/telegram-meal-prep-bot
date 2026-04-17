# Dishes and menu data
from collections import defaultdict
from datetime import date, timedelta

# Test dishes (local data)
DISHES = {
    # Breakfast
    1: {"category": "Breakfast", "name_ru": "Омлет с овощами", "name_en": "Veggie Omelette", "name_es": "Tortilla con verduras", 
        "kcal": 320, "protein": 18, "fat": 22, "carbs": 12, "is_meat": False, "has_base": False},
    2: {"category": "Breakfast", "name_ru": "Овсянка с ягодами", "name_en": "Oatmeal with berries", "name_es": "Avena con bayas",
        "kcal": 280, "protein": 10, "fat": 8, "carbs": 45, "is_meat": False, "has_base": False},
    3: {"category": "Breakfast", "name_ru": "Панкейки с медом", "name_en": "Pancakes with honey", "name_es": "Panqueques con miel",
        "kcal": 350, "protein": 12, "fat": 10, "carbs": 52, "is_meat": False, "has_base": False},
    
    # Lunch
    4: {"category": "Lunch", "name_ru": "Курица с рисом", "name_en": "Chicken with rice", "name_es": "Pollo con arroz",
        "kcal": 520, "protein": 35, "fat": 15, "carbs": 60, "is_meat": True, "meat_type": "chicken", "has_base": True},
    5: {"category": "Lunch", "name_ru": "Рыба с овощами", "name_en": "Fish with vegetables", "name_es": "Pescado con verduras",
        "kcal": 480, "protein": 32, "fat": 18, "carbs": 45, "is_meat": False, "meat_type": "fish", "has_base": True},
    10: {"category": "Lunch", "name_ru": "Говядина с гречкой", "name_en": "Beef with buckwheat", "name_es": "Ternera con trigo sarraceno",
        "kcal": 550, "protein": 38, "fat": 20, "carbs": 55, "is_meat": True, "meat_type": "beef", "has_base": True},
    
    # Snack1
    6: {"category": "Snack1", "name_ru": "Йогурт с орехами", "name_en": "Yogurt with nuts", "name_es": "Yogur con nueces",
        "kcal": 180, "protein": 8, "fat": 10, "carbs": 15, "is_meat": False, "meat_type": None, "has_base": False},
    11: {"category": "Snack1", "name_ru": "Фруктовый салат", "name_en": "Fruit salad", "name_es": "Ensalada de frutas",
        "kcal": 150, "protein": 3, "fat": 2, "carbs": 35, "is_meat": False, "meat_type": None, "has_base": False},
    
    # Snack2
    7: {"category": "Snack2", "name_ru": "Протеиновый батончик", "name_en": "Protein bar", "name_es": "Barra de proteína",
        "kcal": 200, "protein": 15, "fat": 8, "carbs": 20, "is_meat": False, "meat_type": None, "has_base": False},
    12: {"category": "Snack2", "name_ru": "Творог с медом", "name_en": "Cottage cheese with honey", "name_es": "Requesón con miel",
        "kcal": 220, "protein": 18, "fat": 9, "carbs": 18, "is_meat": False, "meat_type": None, "has_base": False},
    
    # Dinner
    8: {"category": "Dinner", "name_ru": "Стейк с овощами", "name_en": "Steak with vegetables", "name_es": "Filete con verduras",
        "kcal": 480, "protein": 40, "fat": 25, "carbs": 20, "is_meat": True, "meat_type": "beef", "has_base": True},
    9: {"category": "Dinner", "name_ru": "Лосось на гриле", "name_en": "Grilled salmon", "name_es": "Salmón a la parrilla",
        "kcal": 450, "protein": 35, "fat": 28, "carbs": 15, "is_meat": False, "meat_type": "fish", "has_base": True},
    13: {"category": "Dinner", "name_ru": "Индейка с киноа", "name_en": "Turkey with quinoa", "name_es": "Pavo con quinua",
        "kcal": 460, "protein": 38, "fat": 18, "carbs": 35, "is_meat": True, "meat_type": "chicken", "has_base": True},
}

# Build substitutions automatically
def get_substitutions():
    substitutions = defaultdict(list)
    for dish_id, dish in DISHES.items():
        substitutions[dish["category"]].append(dish_id)
    return dict(substitutions)

# Build base swap mapping (meat <-> fish for dishes with base)
def get_base_swap_mapping():
    base_swap_mapping = {}
    category_items = defaultdict(list)
    for d_id, d in DISHES.items():
        if d.get("has_base"):
            category_items[d.get("category")].append((d_id, d.get("is_meat")))
    
    for cat, items in category_items.items():
        meats = [i for i, is_m in items if is_m]
        fish = [i for i, is_m in items if not is_m]
        if meats and fish:
            base_swap_mapping[meats[0]] = fish[0]
            base_swap_mapping[fish[0]] = meats[0]
    
    return base_swap_mapping

# Generate menu for specified number of weeks
def generate_menu_for_weeks(weeks: int = 5) -> dict:
    menu = {}
    start_date = date.today()
    
    default_dishes = {
        "Breakfast": 3,
        "Snack1": 6,
        "Lunch": 4,
        "Snack2": 7,
        "Dinner": 8
    }
    
    for day_offset in range(weeks * 7):
        current_date = start_date + timedelta(days=day_offset)
        date_str = current_date.isoformat()
        
        rotation = day_offset % 3
        menu[date_str] = {
            "Breakfast": [1, 2, 3][rotation],
            "Snack1": [6, 11][rotation % 2],
            "Lunch": [4, 5, 10][rotation],
            "Snack2": [7, 12][rotation % 2],
            "Dinner": [8, 9, 13][rotation]
        }
    
    return menu

# Initialize data
SUBSTITUTIONS = get_substitutions()
BASE_SWAP_MAPPING = get_base_swap_mapping()
BASE_MENU = generate_menu_for_weeks(5)
