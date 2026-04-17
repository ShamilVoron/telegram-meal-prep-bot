# Keyboard builders
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from bot.translations import TRANSLATIONS
from bot.config import ADD_ON_PRICES, RATIONS, BASE_PRICES
from bot.data import SUBSTITUTIONS
from bot.utils import format_dish_with_kbju, format_date_display
from datetime import date

def get_language_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="LANG|ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="LANG|en")],
        [InlineKeyboardButton(text="🇪🇸 Español", callback_data="LANG|es")],
    ])

def get_mode_keyboard(lang: str = "ru"):
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    keyboard = [
        [InlineKeyboardButton(text=texts["mode_chat"], callback_data="MODE|chat")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_ration_keyboard(lang: str = "ru"):
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    button_texts = texts["ration_buttons"]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=button_texts[0], callback_data="RATION|SLIM")],
        [InlineKeyboardButton(text=button_texts[1], callback_data="RATION|LIGHT")],
        [InlineKeyboardButton(text=button_texts[2], callback_data="RATION|STANDART")],
        [InlineKeyboardButton(text=button_texts[3], callback_data="RATION|MEDIUM")],
        [InlineKeyboardButton(text=button_texts[4], callback_data="RATION|STRONG")]
    ])

def get_dates_keyboard(available_dates: list, lang: str = "ru"):
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    # Build two-column grid for dates
    rows = []
    row = []
    for idx, date_str in enumerate(available_dates):
        meal_date = date.fromisoformat(date_str)
        display_text = format_date_display(meal_date, lang)
        row.append(InlineKeyboardButton(text=display_text, callback_data=f"DATE|{date_str}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    # Control buttons
    rows.append([InlineKeyboardButton(text=texts["cart_button"], callback_data="CART")])
    rows.append([InlineKeyboardButton(text=texts["change_ration_btn"], callback_data="CHANGE_RATION")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_meals_keyboard(ration: str, lang: str = "ru"):
     texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
     meals = RATIONS.get(ration, [])
     
     return InlineKeyboardMarkup(inline_keyboard=[
         [InlineKeyboardButton(text=f"🍽️ {meal}", callback_data=f"MEAL|{meal}")] for meal in meals
     ] + [
         [InlineKeyboardButton(text=texts['next_day'], callback_data="NEXT_DAY")],
         [InlineKeyboardButton(text=texts['back'], callback_data="BACK_TO_DAYS")]
     ])

def get_actions_keyboard(meal: str, has_base: bool, lang: str = "ru"):
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    keyboard_rows = []
    
    keyboard_rows.append([InlineKeyboardButton(text=texts['keep_default_btn'], callback_data="KEEP_DEFAULT")])
    swap_text = texts['swap_snack_btn'] if "Snack" in meal else texts['swap_main_btn']
    keyboard_rows.append([InlineKeyboardButton(text=swap_text, callback_data="ACTION|SWAP")])
    
    add_on_price = ADD_ON_PRICES.get(meal, 0.0)
    keyboard_rows.append([InlineKeyboardButton(text=f"{texts['add_on_btn']} ({add_on_price:.2f}€/порция)", callback_data="ACTION|ADD_ON")])
    keyboard_rows.append([InlineKeyboardButton(text=texts['back_to_menu'], callback_data="BACK_TO_MEALS")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

def get_swap_keyboard(meal: str, lang: str = "ru", original_id: int = None):
     texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
     options = SUBSTITUTIONS.get(meal, [])
     
     from bot.utils import calculate_swap_price
     
     keyboard = []
     for d_id in options:
         text = format_dish_with_kbju(d_id, lang)
         if original_id:
             price = calculate_swap_price(original_id, d_id)
             if price > 0:
                 text += f" (+{price}€)"
         
         keyboard.append([InlineKeyboardButton(text=text, callback_data=f"SWAP|{d_id}")])
     
     keyboard.append([InlineKeyboardButton(text=texts['back'], callback_data="BACK_TO_ACTIONS")])
     return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_base_swap_keyboard(lang: str = "ru"):
     texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
     return InlineKeyboardMarkup(inline_keyboard=[
         [InlineKeyboardButton(text=texts['yes'], callback_data="BASE_SWAP_YES")],
         [InlineKeyboardButton(text=texts['no'], callback_data="BACK_TO_ACTIONS")]
     ])

def get_quantity_keyboard(lang: str = "ru"):
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1", callback_data="QUANTITY|1"), InlineKeyboardButton(text="2", callback_data="QUANTITY|2")],
        [InlineKeyboardButton(text="3", callback_data="QUANTITY|3"), InlineKeyboardButton(text="4", callback_data="QUANTITY|4")],
        [InlineKeyboardButton(text="5", callback_data="QUANTITY|5")],
        [InlineKeyboardButton(text=texts['back_to_menu'], callback_data="BACK_TO_ACTIONS")]
    ])

def get_cart_keyboard(lang: str = "ru"):
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts['confirm_order_btn'], callback_data="CONFIRM")],
        [InlineKeyboardButton(text=texts['back_to_menu'], callback_data="BACK_TO_DAYS")]
    ])

def get_restart_keyboard(lang: str = "ru"):
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts['new_order_btn'], callback_data="START")]
    ])

def get_contact_keyboard(lang: str = "ru"):
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=texts['send_contact'], request_contact=True)]], 
        resize_keyboard=True, 
        one_time_keyboard=True
    )

def get_days_count_keyboard(lang: str = "ru", ration: str = "STANDART"):
     texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
     base_price = BASE_PRICES.get(ration, 50)
     
     days_options = [2, 4, 5, 6, 30]
     
     keyboard = []
     for d in days_options:
         price = base_price * d
         text = f"{d} дн. - {price}€"
         keyboard.append([InlineKeyboardButton(text=text, callback_data=f"DAYS_COUNT|{d}")])
     
     # Add 30 days weekdays
     # Assuming 30 weekdays is just a different mode, but still 30 days of food? 
     # Or is it a 20 day package? User said "30/30".
     # Let's assume it's 30 food days but with different delivery rules, so same price?
     # Or maybe it's "Subscription for a month (weekdays only)" which is ~22 days.
     # Let's stick to the text "30 (будни)" and same price for now or maybe calculate for 22 days?
     # User said "30/30(без сб и вскр)дней". 
     # If I select 30 weekdays, I pay for 30 days? Or is the label just "30 weekdays"?
     # Let's assume 22 days for "30 days weekdays" equivalent (approx 4.3 weeks * 5 = 21.5). 
     # Actually, let's just put the button and let the logic handle the dates.
     # For price, I'll show it for 30 days if it's "30 days of food".
     
     price_30 = base_price * 30
     keyboard.append([InlineKeyboardButton(text=f"30 дн. (будни) - {price_30}€", callback_data="DAYS_COUNT|30_WORK")])

     keyboard.append([InlineKeyboardButton(text=texts['change_ration_btn'], callback_data="CHANGE_RATION")])
     
     return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_calendar_keyboard(days_count: int, lang: str = "ru", selected_dates: list = None):
     """Generate calendar for delivery date selection in two columns"""
     texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
     from datetime import datetime, timedelta

     if selected_dates is None:
         selected_dates = []

     today = datetime.now().date()
     rows = []
     row = []
     # Get weekday names from translations
     weekdays = texts.get("weekdays", ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
     
     # Generate next 14 days in a 2-column grid
     for i in range(14):
         date_obj = today + timedelta(days=i)
         day_name = weekdays[date_obj.weekday()]
         date_iso = date_obj.isoformat()
         
         # Check if date is already selected
         is_selected = date_iso in selected_dates
         
         if is_selected:
             # Show selected date with checkmark, disable it
             btn = InlineKeyboardButton(
                 text=f"✅ {day_name} {date_obj.day}.{date_obj.month}",
                 callback_data=f"CALENDAR|{date_iso}"
             )
         else:
             # Show unselected date normally
             btn = InlineKeyboardButton(
                 text=f"{day_name} {date_obj.day}.{date_obj.month}",
                 callback_data=f"CALENDAR|{date_iso}"
             )
         row.append(btn)
         if len(row) == 2:
             rows.append(row)
             row = []
     if row:
         rows.append(row)

     rows.append([InlineKeyboardButton(text=texts['back'], callback_data="BACK_TO_DAYS_COUNT")])
     return InlineKeyboardMarkup(inline_keyboard=rows)

def get_payment_method_keyboard(lang: str = "ru"):
     texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
     # Payment methods should be added to translations.py
     payment_texts = {
         "ru": {"cash": "💵 Наличные", "terminal": "💳 По терминалу", "transfer": "🏦 Банковский перевод"},
         "en": {"cash": "💵 Cash", "terminal": "💳 Card Terminal", "transfer": "🏦 Bank Transfer"},
         "es": {"cash": "💵 Efectivo", "terminal": "💳 Terminal de tarjeta", "transfer": "🏦 Transferencia bancaria"}
     }
     payment_opts = payment_texts.get(lang, payment_texts["ru"])
     return InlineKeyboardMarkup(inline_keyboard=[
         [InlineKeyboardButton(text=payment_opts["cash"], callback_data="PAYMENT|cash")],
         [InlineKeyboardButton(text=payment_opts["terminal"], callback_data="PAYMENT|terminal")],
         [InlineKeyboardButton(text=payment_opts["transfer"], callback_data="PAYMENT|transfer")],
         [InlineKeyboardButton(text=texts['back'], callback_data="BACK_TO_CART")]
     ])

def get_cash_change_keyboard(lang: str = "ru"):
     texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
     cash_change_texts = {
         "ru": {"exact": "✅ Без сдачи", "need": "💶 Нужна сдача"},
         "en": {"exact": "✅ No change", "need": "💶 Need change"},
         "es": {"exact": "✅ Sin cambio", "need": "💶 Necesito cambio"}
     }
     cash_opts = cash_change_texts.get(lang, cash_change_texts["ru"])
     return InlineKeyboardMarkup(inline_keyboard=[
         [InlineKeyboardButton(text=cash_opts["exact"], callback_data="CASH_CHANGE|exact")],
         [InlineKeyboardButton(text=cash_opts["need"], callback_data="CASH_CHANGE|need")],
         [InlineKeyboardButton(text=texts['back'], callback_data="BACK_TO_PAYMENT")]
     ])

def get_cash_bills_keyboard(lang: str = "ru"):
     texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
     bill_texts = {
         "ru": {"custom": "✏️ Ввести свой номинал"},
         "en": {"custom": "✏️ Enter custom amount"},
         "es": {"custom": "✏️ Ingresar cantidad personalizada"}
     }
     bill_opts = bill_texts.get(lang, bill_texts["ru"])
     return InlineKeyboardMarkup(inline_keyboard=[
         [InlineKeyboardButton(text="50 €", callback_data="BILL|50")],
         [InlineKeyboardButton(text="100 €", callback_data="BILL|100")],
         [InlineKeyboardButton(text="200 €", callback_data="BILL|200")],
         [InlineKeyboardButton(text="500 €", callback_data="BILL|500")],
         [InlineKeyboardButton(text=bill_opts["custom"], callback_data="BILL|custom")],
         [InlineKeyboardButton(text=texts['back'], callback_data="BACK_TO_PAYMENT")]
     ])

def get_confirm_contact_keyboard(lang: str = "ru"):
     contact_confirm_texts = {
         "ru": {"confirm": "✅ Да, данные верны", "change": "🔄 Изменить данные"},
         "en": {"confirm": "✅ Yes, data is correct", "change": "🔄 Change data"},
         "es": {"confirm": "✅ Sí, datos correctos", "change": "🔄 Cambiar datos"}
     }
     confirm_opts = contact_confirm_texts.get(lang, contact_confirm_texts["ru"])
     return InlineKeyboardMarkup(inline_keyboard=[
         [InlineKeyboardButton(text=confirm_opts["confirm"], callback_data="CONTACT_CONFIRM_YES")],
         [InlineKeyboardButton(text=confirm_opts["change"], callback_data="CONTACT_CONFIRM_NO")]
     ])

def get_ration_selection_keyboard(lang: str = "ru"):
    """Клавиатура с кнопками рациона + калькулятор + менеджер"""
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    button_texts = texts["ration_buttons"]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=button_texts[0], callback_data="RATION|SLIM")],
        [InlineKeyboardButton(text=button_texts[1], callback_data="RATION|LIGHT")],
        [InlineKeyboardButton(text=button_texts[2], callback_data="RATION|STANDART")],
        [InlineKeyboardButton(text=button_texts[3], callback_data="RATION|MEDIUM")],
        [InlineKeyboardButton(text=button_texts[4], callback_data="RATION|STRONG")],
        [InlineKeyboardButton(text="🧮 " + texts.get("calculator_start", "Рассчитать ккал"), callback_data="CALC|START")],
        [InlineKeyboardButton(text="👨‍💼 " + texts.get("manager_consultation", "Консультация"), callback_data="MANAGER|START")]
    ])

def get_calculator_gender_keyboard(lang: str = "ru"):
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts["calculator_male"], callback_data="CALC|GENDER|M")],
        [InlineKeyboardButton(text=texts["calculator_female"], callback_data="CALC|GENDER|F")],
    ])

def get_calculator_activity_keyboard(lang: str = "ru"):
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts["activity_sedentary"], callback_data="CALC|ACTIVITY|1.2")],
        [InlineKeyboardButton(text=texts["activity_light"], callback_data="CALC|ACTIVITY|1.375")],
        [InlineKeyboardButton(text=texts["activity_moderate"], callback_data="CALC|ACTIVITY|1.55")],
        [InlineKeyboardButton(text=texts["activity_active"], callback_data="CALC|ACTIVITY|1.725")],
        [InlineKeyboardButton(text=texts["activity_very_active"], callback_data="CALC|ACTIVITY|1.9")],
    ])

def get_calculator_goal_keyboard(lang: str = "ru"):
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts["goal_lose"], callback_data="CALC|GOAL|lose")],
        [InlineKeyboardButton(text=texts["goal_maintain"], callback_data="CALC|GOAL|maintain")],
        [InlineKeyboardButton(text=texts["goal_gain"], callback_data="CALC|GOAL|gain")],
    ])

def get_calculator_confirm_keyboard(lang: str = "ru"):
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts["calculator_confirm_btn"], callback_data="CALC|CONFIRM_RATION")],
        [InlineKeyboardButton(text=texts["calculator_recalculate"], callback_data="CALC|RECALCULATE")],
    ])

def get_manager_consultation_keyboard(lang: str = "ru"):
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts["manager_accept"], callback_data="MANAGER|ACCEPT")],
        [InlineKeyboardButton(text=texts["manager_back"], callback_data="MANAGER|CANCEL")],
    ])

def get_profile_extended_keyboard(lang: str = "ru"):
    """Клавиатура профиля с опцией добавить ещё рацион"""
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.get("profile_add_ration", "Добавить рацион"), callback_data="PROFILE|ADD_RATION")],
    ])
