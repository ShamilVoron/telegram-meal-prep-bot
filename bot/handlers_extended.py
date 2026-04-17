# Extended handlers for full webapp functionality in chat
import logging
from datetime import date, datetime, timedelta
from collections import defaultdict

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ContentType

from bot.states import States
from bot.config import RATIONS, DEFAULT_ORDER_DAYS, BASE_PRICES, ADD_ON_PRICES
from bot.data import DISHES, BASE_MENU, BASE_SWAP_MAPPING
from bot.translations import TRANSLATIONS
from bot.utils import (
    get_available_meal_dates, get_current_dish, get_current_dish_name,
    get_mods_for_meal, add_modification, format_date_display, user_carts
)
from bot.keyboards import (
    get_days_count_keyboard, get_calendar_keyboard, get_payment_method_keyboard,
    get_cash_change_keyboard, get_cash_bills_keyboard, get_ration_keyboard,
    get_meals_keyboard, get_cart_keyboard, get_restart_keyboard, get_actions_keyboard
)

router_extended = Router()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== DAYS COUNT ====================
@router_extended.callback_query(F.data.startswith("DAYS_COUNT|"))
async def select_days_count(callback: CallbackQuery, state: FSMContext):
     days_count = int(callback.data.split("|")[1])
     await state.update_data(days_count=days_count, selected_dates=[])
     
     data = await state.get_data()
     lang = data.get("lang", "ru")
     texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
     
     calendar_texts = {
         "ru": "📅 **Выберите {days} дней доставки:**",
         "en": "📅 **Select {days} delivery days:**",
         "es": "📅 **Selecciona {days} días de entrega:**"
     }
     calendar_text = calendar_texts.get(lang, calendar_texts["ru"]).format(days=days_count)
     
     keyboard = get_calendar_keyboard(days_count, lang, [])
     await callback.message.edit_text(
         calendar_text,
         reply_markup=keyboard,
         parse_mode="Markdown"
     )
     await state.set_state(States.calendar_selection)
     await callback.answer()

@router_extended.callback_query(F.data == "BACK_TO_DAYS_COUNT")
async def back_to_days_count(callback: CallbackQuery, state: FSMContext):
     data = await state.get_data()
     lang = data.get("lang", "ru")
     texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
     
     back_texts = {
         "ru": "**Сколько дней?** (рацион: {ration})",
         "en": "**How many days?** (plan: {ration})",
         "es": "**¿Cuántos días?** (plan: {ration})"
     }
     back_text = back_texts.get(lang, back_texts["ru"]).format(ration=data.get('ration'))
     
     keyboard = get_days_count_keyboard(lang)
     await callback.message.edit_text(
         back_text,
         reply_markup=keyboard,
         parse_mode="Markdown"
     )
     await state.set_state(States.days_count_selection)
     await callback.answer()

# ==================== CALENDAR SELECTION ====================
# Валидированный выбор календаря находится в handlers_new_features.py
# Здесь оставляем версию для обратной совместимости если нужна
@router_extended.callback_query(F.data.startswith("CALENDAR|"))
async def select_calendar_date(callback: CallbackQuery, state: FSMContext):
    """Выбор даты (обработчик из handlers_new_features переопределяет этот)"""
    date_str = callback.data.split("|")[1]
    data = await state.get_data()
    days_count = data.get("days_count", 2)
    selected_dates = data.get("selected_dates", [])
    
    # Prevent duplicate selection
    if date_str in selected_dates:
         # Show notification instead of error
         dup_texts = {
             "ru": "📅 Этот день уже выбран!",
             "en": "📅 This day is already selected!",
             "es": "📅 ¡Este día ya está seleccionado!"
         }
         dup_text = dup_texts.get(lang, dup_texts["ru"])
         await callback.answer(dup_text, show_alert=False)
         return
    
    selected_dates.append(date_str)
    await state.update_data(selected_dates=selected_dates)
    
    lang = data.get("lang", "ru")
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    
    if len(selected_dates) == days_count:
        # All dates selected, show first meal
        await state.update_data(current_date_index=0)
        await show_meals(callback.message, callback.from_user.id, state)
        await state.set_state(States.day_selected)
    else:
         # Show calendar again with selected dates marked
         selected_texts = {
             "ru": "📅 **Выбрано: {selected}/{total}**\n\n✅ отмечены выбранные дни",
             "en": "📅 **Selected: {selected}/{total}**\n\n✅ marked selected days",
             "es": "📅 **Seleccionado: {selected}/{total}**\n\n✅ días seleccionados marcados"
         }
         selected_text = selected_texts.get(lang, selected_texts["ru"]).format(
             selected=len(selected_dates), total=days_count
         )
         keyboard = get_calendar_keyboard(days_count, lang, selected_dates)
         await callback.message.edit_text(
             selected_text,
             reply_markup=keyboard,
             parse_mode="Markdown"
         )
         
         await callback.answer()

# ==================== SHOW MEALS (from calendar) ====================
async def show_meals(message, user_id: int, state: FSMContext):
    from bot.utils import calculate_day_kcal
    
    data = await state.get_data()
    ration = data.get("ration", "STANDART")
    selected_dates = data.get("selected_dates", [])
    current_date_index = data.get("current_date_index", 0)
    
    if current_date_index >= len(selected_dates):
        await show_cart(message, state)
        return
    
    date_str = selected_dates[current_date_index]
    await state.update_data(current_date=date_str)
    
    meals = RATIONS.get(ration, [])
    lang = data.get("lang", "ru")
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    
    meal_date = date.fromisoformat(date_str)
    date_display = format_date_display(meal_date, lang)
    day_number = current_date_index + 1
    
    # Рассчитываем ккал за день
    day_kcal = calculate_day_kcal(user_id, date_str, lang)
    
    # Show meal summary
    day_texts = {
        "ru": "🍽️ **День {day}/{total}** — {date}\n**Рацион:** {ration} | 📊 {kcal} ккал\n\n**Ваше меню на этот день:**\n\n",
        "en": "🍽️ **Day {day}/{total}** — {date}\n**Plan:** {ration} | 📊 {kcal} kcal\n\n**Your menu for this day:**\n\n",
        "es": "🍽️ **Día {day}/{total}** — {date}\n**Plan:** {ration} | 📊 {kcal} kcal\n\n**Tu menú para este día:**\n\n"
    }
    day_text = day_texts.get(lang, day_texts["ru"]).format(
        day=day_number, total=len(selected_dates), date=date_display, ration=ration, kcal=day_kcal
    )
    text = day_text
    
    for meal in meals:
        if meal in BASE_MENU.get(date_str, {}):
            dish_name = get_current_dish_name(user_id, date_str, meal, lang)
            mods = get_mods_for_meal(user_id, date_str, meal)
            mod_text = ""
            
            if "SWAP" in mods:
                mod_text += " 🔄"
            elif "BASE_SWAP" in mods:
                mod_text += " 🔄"
            
            addon_quantity = sum(m['quantity'] for m in user_carts[user_id]
                                if m['order_date'] == date_str and
                                   m['meal_category'] == meal and
                                   m['operation_type'] == 'ADD_ON')
            if addon_quantity > 0:
                mod_text += f" ➕×{addon_quantity}"
            
            meal_name = texts.get("meals", {}).get(meal, meal)
            text += f"  • **{meal_name}:** {dish_name}{mod_text}\n"
    
    text += f"\n{texts['choose_meal']}"
    
    keyboard = get_meals_keyboard(ration, lang)
    await message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

@router_extended.callback_query(F.data.startswith("MEAL|"))
async def select_meal_extended(callback: CallbackQuery, state: FSMContext):
    meal = callback.data.split("|")[1]
    await state.update_data(meal=meal)
    
    data = await state.get_data()
    date_str = data.get("current_date")
    user_id = callback.from_user.id
    
    # Ensure menu cart entry exists
    from bot.keyboards import get_actions_keyboard
    
    current_id = get_current_dish(user_id, date_str, meal)
    has_base = DISHES.get(current_id, {}).get("has_base", False) and current_id in BASE_SWAP_MAPPING
    lang = data.get("lang", "ru")
    
    keyboard = get_actions_keyboard(meal, has_base, lang)
    
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    current_texts = {
        "ru": "🍽️ **{meal}**\n\n**Текущее блюдо:** {dish}\n\n**Что хотите сделать?**",
        "en": "🍽️ **{meal}**\n\n**Current dish:** {dish}\n\n**What would you like to do?**",
        "es": "🍽️ **{meal}**\n\n**Plato actual:** {dish}\n\n**¿Qué le gustaría hacer?**"
    }
    meal_name = texts.get("meals", {}).get(meal, meal)
    current_text = current_texts.get(lang, current_texts["ru"]).format(
        meal=meal_name, dish=get_current_dish_name(user_id, date_str, meal, lang)
    )
    text = current_text
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await state.set_state(States.meal_action_selection)
    await callback.answer()

# ==================== BACK BUTTON ====================
@router_extended.callback_query(F.data == "BACK_TO_DAYS")
async def back_to_days_extended(callback: CallbackQuery, state: FSMContext):
     """Back from calendar selection - show days count"""
     data = await state.get_data()
     lang = data.get("lang", "ru")
     
     back_days_texts = {
         "ru": "**Выбранный рацион:** {ration}\n**Сколько дней?**",
         "en": "**Selected plan:** {ration}\n**How many days?**",
         "es": "**Plan seleccionado:** {ration}\n**¿Cuántos días?**"
     }
     back_days_text = back_days_texts.get(lang, back_days_texts["ru"]).format(ration=data.get('ration'))
     
     keyboard = get_days_count_keyboard(lang)
     await callback.message.edit_text(
         back_days_text,
         reply_markup=keyboard,
         parse_mode="Markdown"
     )
     await state.set_state(States.days_count_selection)
     await callback.answer()

@router_extended.callback_query(F.data == "BACK_TO_CART")
async def back_to_cart(callback: CallbackQuery, state: FSMContext):
    """Back from payment/details to cart"""
    await show_cart(callback.message, state)
    await state.set_state(States.cart_review)
    await callback.answer()

# ==================== NEXT DAY ====================
@router_extended.callback_query(F.data == "NEXT_DAY")
async def next_day(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_date_index = data.get("current_date_index", 0)
    selected_dates = data.get("selected_dates", [])
    
    current_date_index += 1
    await state.update_data(current_date_index=current_date_index)
    
    if current_date_index < len(selected_dates):
        await show_meals(callback.message, callback.from_user.id, state)
        await state.set_state(States.day_selected)
    else:
        await show_cart(callback.message, state)
        await state.set_state(States.cart_review)
    
    await callback.answer()

# ==================== CART FROM MENU ====================
@router_extended.callback_query(F.data == "CART")
async def view_cart_from_menu(callback: CallbackQuery, state: FSMContext):
    await show_cart(callback.message, state)
    await state.set_state(States.cart_review)
    await callback.answer()

# ==================== CART ====================
async def show_cart(message, state: FSMContext):
    from bot.utils import calculate_day_kcal, get_daily_ration_kcal
    
    user_id = message.chat.id
    data = await state.get_data()
    ration = data.get("ration", "STANDART")
    meals = RATIONS.get(ration, [])
    lang = data.get("lang", "ru")
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    selected_dates = data.get("selected_dates", [])
    
    cart_titles = {
        "ru": "🛒 **Корзина:**\n\n",
        "en": "🛒 **Cart:**\n\n",
        "es": "🛒 **Cesta:**\n\n"
    }
    text = cart_titles.get(lang, cart_titles["ru"])
    total = 0.0
    base_price = BASE_PRICES.get(ration, 50)
    ration_kcal = get_daily_ration_kcal(ration)
    
    # Show base plan price with kcal info
    plan_texts = {
        "ru": "**План {ration}:** {price} €/день ({kcal} ккал) × {days} дней = {total} €\n\n",
        "en": "**Plan {ration}:** {price} €/day ({kcal} kcal) × {days} days = {total} €\n\n",
        "es": "**Plan {ration}:** {price} €/día ({kcal} kcal) × {days} días = {total} €\n\n"
    }
    plan_text = plan_texts.get(lang, plan_texts["ru"]).format(
        ration=ration, price=base_price, kcal=int(ration_kcal), days=len(selected_dates), total=base_price * len(selected_dates)
    )
    text += plan_text
    total += base_price * len(selected_dates)
    
    # Show each day
    for date_str in sorted(selected_dates):
        meal_date = date.fromisoformat(date_str)
        date_display = format_date_display(meal_date, lang)
        
        text += f"📅 **{date_display}:**\n"
        day_extras = 0.0
        
        for meal in meals:
            if meal in BASE_MENU.get(date_str, {}):
                mods = get_mods_for_meal(user_id, date_str, meal)
                if "SWAP" in mods:
                    day_extras += mods["SWAP"]["price_impact"]
                    text += f"  🔄 {meal}: +€{mods['SWAP']['price_impact']:.2f}\n"
                elif "BASE_SWAP" in mods:
                    day_extras += mods["BASE_SWAP"]["price_impact"]
                    base_swap_texts = {
                        "ru": "  🔄 {meal} (основа): +€{price:.2f}\n",
                        "en": "  🔄 {meal} (base): +€{price:.2f}\n",
                        "es": "  🔄 {meal} (base): +€{price:.2f}\n"
                    }
                    base_swap_text = base_swap_texts.get(lang, base_swap_texts["ru"]).format(meal=meal, price=mods['BASE_SWAP']['price_impact'])
                    text += base_swap_text
                
                if "ADD_ON" in mods:
                    addon_price = ADD_ON_PRICES.get(meal, 0.0)
                    addon_quantity = sum(m['quantity'] for m in user_carts[user_id]
                                        if m['order_date'] == date_str and
                                           m['meal_category'] == meal and
                                           m['operation_type'] == 'ADD_ON')
                    addon_cost = addon_price * addon_quantity
                    day_extras += addon_cost
                    text += f"  ➕ {meal}: ×{addon_quantity} = +€{addon_cost:.2f}\n"
        
        if day_extras > 0:
            text += f"  Дополнительно: +€{day_extras:.2f}\n"
        text += "\n"
        total += day_extras
    
    text += f"\n💰 **ИТОГО: €{total:.2f}**"
    
    keyboard = get_cart_keyboard(lang)
    await message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

# ==================== ORDER DETAILS ====================
@router_extended.callback_query(F.data == "CONFIRM")
async def confirm_order_extended(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    
    # Ask for customer details
    await callback.message.edit_text(
        "📝 **Введите ваше имя:**",
        parse_mode="Markdown"
    )
    await state.set_state(States.order_details_input)
    await state.update_data(detail_step="name")
    await callback.answer()

# ==================== CONTACT INFO HANDLERS (for chat mode) ====================
# Check for saved contact info on first entry
async def ask_for_first_name(message_or_callback, state: FSMContext, user_id: int):
    """Ask for first name, with option to use saved data"""
    from bot.database import get_user_contact
    from bot.keyboards import InlineKeyboardMarkup, InlineKeyboardButton
    
    saved_contact = get_user_contact(user_id)
    
    if saved_contact and saved_contact.get('firstName'):
        # Show saved data with option to use it
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Использовать сохранённые данные", callback_data="USE_SAVED_CONTACT")],
            [InlineKeyboardButton(text="✏️ Ввести новые данные", callback_data="ENTER_NEW_CONTACT")]
        ])
        text = f"📝 **У вас есть сохранённые данные:**\n\n{saved_contact['firstName']} {saved_contact['lastName']}\n📱 {saved_contact['phone']}\n\nХотите их использовать?"
    else:
        keyboard = None
        text = "📝 **Введите ваше имя:**"
    
    if hasattr(message_or_callback, 'edit_text'):
        await message_or_callback.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await message_or_callback.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@router_extended.callback_query(F.data == "USE_SAVED_CONTACT")
async def use_saved_contact(callback: CallbackQuery, state: FSMContext):
    """Load saved contact and go to confirmation"""
    from bot.database import get_user_contact
    
    user_id = callback.from_user.id
    saved_contact = get_user_contact(user_id)
    
    if saved_contact:
        await state.update_data(
            contact_first_name=saved_contact.get('firstName', ''),
            contact_last_name=saved_contact.get('lastName', ''),
            contact_phone=saved_contact.get('phone', ''),
            contact_address=saved_contact.get('address', ''),
            contact_postcode=saved_contact.get('postcode', ''),
            contact_entrance=saved_contact.get('entrance', ''),
            contact_floor=saved_contact.get('floor', ''),
            contact_apartment=saved_contact.get('apartment', ''),
            contact_comment=saved_contact.get('comment', '')
        )
        
        # Show confirmation
        data = await state.get_data()
        first_name = data.get("contact_first_name", "")
        last_name = data.get("contact_last_name", "")
        phone = data.get("contact_phone", "")
        address = data.get("contact_address", "")
        postcode = data.get("contact_postcode", "")
        entrance = data.get("contact_entrance", "")
        floor = data.get("contact_floor", "")
        apartment = data.get("contact_apartment", "")
        comment = data.get("contact_comment", "")
        
        confirm_text = f"""
✅ **Проверьте ваши данные:**

👤 **Имя:** {first_name} {last_name}
📱 **Телефон:** {phone}
📍 **Адрес:** {address}
📮 **Почтовый код:** {postcode}
🚪 **Подъезд:** {entrance}
📊 **Этаж:** {floor}
🔑 **Квартира:** {apartment}
💬 **Комментарий:** {comment if comment else '(без комментария)'}

Данные верны?
"""
        
        from bot.keyboards import get_confirm_contact_keyboard
        keyboard = get_confirm_contact_keyboard()
        await callback.message.edit_text(confirm_text, reply_markup=keyboard, parse_mode="Markdown")
        await state.set_state(States.contact_confirm)
    
    await callback.answer()

@router_extended.callback_query(F.data == "ENTER_NEW_CONTACT")
async def enter_new_contact(callback: CallbackQuery, state: FSMContext):
    """Start entering new contact info"""
    await callback.message.edit_text(
        "📝 **Введите ваше имя:**",
        parse_mode="Markdown"
    )
    await state.set_state(States.contact_first_name)
    await callback.answer()

# These handle the sequential contact input when coming from cart confirmation
@router_extended.message(States.contact_first_name)
async def input_contact_first_name(message: Message, state: FSMContext):
    await state.update_data(contact_first_name=message.text)
    await message.answer("👤 Введите вашу фамилию:", parse_mode="Markdown")
    await state.set_state(States.contact_last_name)

@router_extended.message(States.contact_last_name)
async def input_contact_last_name(message: Message, state: FSMContext):
    await state.update_data(contact_last_name=message.text)
    await message.answer("📱 Введите номер телефона (+34 600 123 456):", parse_mode="Markdown")
    await state.set_state(States.contact_phone)

@router_extended.message(States.contact_phone)
async def input_contact_phone(message: Message, state: FSMContext):
    await state.update_data(contact_phone=message.text)
    await message.answer("🏠 Введите адрес доставки:", parse_mode="Markdown")
    await state.set_state(States.contact_address)

@router_extended.message(States.contact_address)
async def input_contact_address(message: Message, state: FSMContext):
    await state.update_data(contact_address=message.text)
    await message.answer("📮 Введите почтовый код:", parse_mode="Markdown")
    await state.set_state(States.contact_postcode)

@router_extended.message(States.contact_postcode)
async def input_contact_postcode(message: Message, state: FSMContext):
    await state.update_data(contact_postcode=message.text)
    await message.answer("🚪 Введите подъезд (номер или букву):", parse_mode="Markdown")
    await state.set_state(States.contact_entrance)

@router_extended.message(States.contact_entrance)
async def input_contact_entrance(message: Message, state: FSMContext):
    await state.update_data(contact_entrance=message.text)
    await message.answer("📍 Введите этаж:", parse_mode="Markdown")
    await state.set_state(States.contact_floor)

@router_extended.message(States.contact_floor)
async def input_contact_floor(message: Message, state: FSMContext):
    await state.update_data(contact_floor=message.text)
    await message.answer("🔑 Введите номер квартиры:", parse_mode="Markdown")
    await state.set_state(States.contact_apartment)

@router_extended.message(States.contact_apartment)
async def input_contact_apartment(message: Message, state: FSMContext):
    await state.update_data(contact_apartment=message.text)
    await message.answer("💬 Есть ли комментарии к заказу? (опционально, можно просто отправить ничего):", parse_mode="Markdown")
    await state.set_state(States.contact_comment)

@router_extended.message(States.contact_comment)
async def input_contact_comment(message: Message, state: FSMContext):
    # Comment is optional, save it (even if empty)
    comment = message.text if message.text and message.text.strip() else ""
    await state.update_data(contact_comment=comment)
    
    # Show contact confirmation
    await state.set_state(States.contact_confirm)
    await show_contact_confirmation(message, message.from_user.id, state)

async def show_contact_confirmation(message_or_callback, user_id: int, state: FSMContext):
    """Render contact confirmation summary with confirm/change keyboard."""
    data = await state.get_data()
    first_name = data.get("contact_first_name", "")
    last_name = data.get("contact_last_name", "")
    phone = data.get("contact_phone", "")
    address = data.get("contact_address", "")
    postcode = data.get("contact_postcode", "")
    entrance = data.get("contact_entrance", "")
    floor = data.get("contact_floor", "")
    apartment = data.get("contact_apartment", "")
    comment = data.get("contact_comment", "")

    confirm_text = f"""
✅ **Проверьте ваши данные:**

👤 **Имя:** {first_name} {last_name}
📱 **Телефон:** {phone}
📍 **Адрес:** {address}
📮 **Почтовый код:** {postcode}
🚪 **Подъезд:** {entrance}
📊 **Этаж:** {floor}
🔑 **Квартира:** {apartment}
💬 **Комментарий:** {comment if comment else '(без комментария)'}

Данные верны?
"""
    from bot.keyboards import get_confirm_contact_keyboard
    keyboard = get_confirm_contact_keyboard()

    # Prefer editing if possible (callback or previously sent message), otherwise send a new one
    if hasattr(message_or_callback, 'edit_text') and callable(getattr(message_or_callback, 'edit_text')):
        try:
            await message_or_callback.edit_text(confirm_text, reply_markup=keyboard, parse_mode="Markdown")
        except Exception:
            await message_or_callback.answer(confirm_text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await message_or_callback.answer(confirm_text, reply_markup=keyboard, parse_mode="Markdown")

@router_extended.message(States.cash_bill_input)
async def input_cash_bill(message: Message, state: FSMContext):
    """Handle custom cash bill input"""
    try:
        bill = float(message.text.replace(',', '.'))
        if bill <= 0:
            await message.answer("❌ Номинал должен быть больше нуля. Попробуйте ещё раз:")
            return
        await state.update_data(cash_bill=bill)
        await finalize_order(message, message.from_user.id, state)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректное число (например: 20 или 30.50)")

@router_extended.callback_query(F.data == "CONTACT_CONFIRM_YES")
async def confirm_contact_yes(callback: CallbackQuery, state: FSMContext):
    """Proceed to payment after contact info confirmed"""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    user_id = callback.from_user.id
    
    # Build customer info dict
    customer_info = {
        "firstName": data.get("contact_first_name", ""),
        "lastName": data.get("contact_last_name", ""),
        "phone": data.get("contact_phone", ""),
        "address": data.get("contact_address", ""),
        "postcode": data.get("contact_postcode", ""),
        "entrance": data.get("contact_entrance", ""),
        "floor": data.get("contact_floor", ""),
        "apartment": data.get("contact_apartment", ""),
        "comment": data.get("contact_comment", "")
    }
    
    # Save to database
    from bot.database import save_user_contact
    save_user_contact(user_id, customer_info)
    
    await state.update_data(customer_info=customer_info)
    
    # Show payment method
    from bot.keyboards import get_payment_method_keyboard
    keyboard = get_payment_method_keyboard(lang)
    await callback.message.edit_text(
        "💳 **Выберите способ оплаты:**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(States.payment_method_selection)
    await callback.answer()

@router_extended.callback_query(F.data == "CONTACT_CONFIRM_NO")
async def confirm_contact_no(callback: CallbackQuery, state: FSMContext):
    """Go back to edit contact info"""
    # Start over from first name
    await callback.message.edit_text(
        "📝 **Введите ваше имя:**",
        parse_mode="Markdown"
    )
    await state.set_state(States.contact_first_name)
    await callback.answer()

@router_extended.message(States.order_details_input)
async def input_order_details(message: Message, state: FSMContext):
    data = await state.get_data()
    detail_step = data.get("detail_step", "name")
    lang = data.get("lang", "ru")
    customer_info = data.get("customer_info", {})
    
    if detail_step == "name":
        customer_info["firstName"] = message.text
        next_step = "Введите вашу фамилию:"
        next_detail = "lastname"
    elif detail_step == "lastname":
        customer_info["lastName"] = message.text
        next_step = "Введите номер телефона (+34 600 123 456):"
        next_detail = "phone"
    elif detail_step == "phone":
        customer_info["phone"] = message.text
        next_step = "Введите адрес доставки:"
        next_detail = "address"
    elif detail_step == "address":
        customer_info["address"] = message.text
        # Store customer info and proceed to payment
        await state.update_data(customer_info=customer_info)
        
        # Show payment method
        from bot.keyboards import get_payment_method_keyboard
        keyboard = get_payment_method_keyboard(lang)
        await message.answer(
            "💳 **Выберите способ оплаты:**",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await state.set_state(States.payment_method_selection)
        return
    
    await state.update_data(customer_info=customer_info, detail_step=next_detail)
    await message.answer(f"📝 **{next_step}**", parse_mode="Markdown")

# ==================== PAYMENT METHOD ====================
@router_extended.callback_query(F.data.startswith("PAYMENT|"))
async def select_payment_method(callback: CallbackQuery, state: FSMContext):
    payment_method = callback.data.split("|")[1]
    await state.update_data(payment_method=payment_method)
    
    data = await state.get_data()
    lang = data.get("lang", "ru")
    
    if payment_method == "cash":
        keyboard = get_cash_change_keyboard(lang)
        await callback.message.edit_text(
            "💵 **Как с наличными?**",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await state.set_state(States.cash_change_selection)
    else:
        # Terminal or transfer - confirm directly
        await finalize_order(callback.message, callback.from_user.id, state)
    
    await callback.answer()

@router_extended.callback_query(F.data.startswith("CASH_CHANGE|"))
async def select_cash_change(callback: CallbackQuery, state: FSMContext):
    change_type = callback.data.split("|")[1]
    data = await state.get_data()
    lang = data.get("lang", "ru")
    
    if change_type == "exact":
        await state.update_data(cash_bill=None)
        await finalize_order(callback.message, callback.from_user.id, state)
    else:
        keyboard = get_cash_bills_keyboard(lang)
        await callback.message.edit_text(
            "💶 **С какой купюры сдача?**",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    await callback.answer()

@router_extended.callback_query(F.data == "BACK_TO_PAYMENT")
async def back_to_payment(callback: CallbackQuery, state: FSMContext):
    """Back from cash bills to payment method selection"""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    
    keyboard = get_payment_method_keyboard(lang)
    await callback.message.edit_text(
        "💳 **Выберите способ оплаты:**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(States.payment_method_selection)
    await callback.answer()

@router_extended.callback_query(F.data.startswith("BILL|"))
async def select_bill(callback: CallbackQuery, state: FSMContext):
    bill_str = callback.data.split("|")[1]
    
    if bill_str == "custom":
        # Ask user to enter custom bill amount
        await callback.message.edit_text(
            "💶 **Введите номинал купюры (в €):**\n\n(например: 20, 30, 50)",
            parse_mode="Markdown"
        )
        await state.set_state(States.cash_bill_input)
    else:
        bill = int(bill_str)
        await state.update_data(cash_bill=bill)
        await finalize_order(callback.message, callback.from_user.id, state)
    
    await callback.answer()

# ==================== FINALIZE ORDER ====================
async def finalize_order(message, user_id: int, state: FSMContext):
    data = await state.get_data()
    ration = data.get("ration")
    selected_dates = data.get("selected_dates", [])
    customer_info = data.get("customer_info", {})
    payment_method = data.get("payment_method")
    cash_bill = data.get("cash_bill")
    lang = data.get("lang", "ru")
    
    # Calculate total
    base_price = BASE_PRICES.get(ration, 50)
    total = base_price * len(selected_dates)
    
    # Add extras
    for date_str in selected_dates:
        meals = RATIONS.get(ration, [])
        for meal in meals:
            mods = get_mods_for_meal(user_id, date_str, meal)
            if "SWAP" in mods:
                total += mods["SWAP"]["price_impact"]
            
            if "ADD_ON" in mods:
                addon_price = ADD_ON_PRICES.get(meal, 0.0)
                addon_quantity = sum(m['quantity'] for m in user_carts[user_id]
                                    if m['order_date'] == date_str and
                                       m['meal_category'] == meal and
                                       m['operation_type'] == 'ADD_ON')
                total += addon_price * addon_quantity
    
    # Build order data (same structure as webapp)
    order_data = {
        "lang": lang,
        "ration": ration,
        "days": selected_dates,
        "menuCart": build_menu_cart_for_order(user_id, ration, selected_dates),
        "customer": customer_info,
        "payment": {
            "method": payment_method,
            "cashBill": cash_bill,
            "needChange": cash_bill is not None
        },
        "total": total,
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id
    }
    
    # Save and process order (same as webapp handler)
    from bot.database import save_order as save_order_to_db, get_all_managers
    
    try:
        from bot.gsheets import save_order_to_gsheet
        from bot.config import GSPREAD_AVAILABLE
    except:
        save_order_to_gsheet = None
        GSPREAD_AVAILABLE = False
    
    # Save to database
    order_id = save_order_to_db(order_data)
    
    # Send notifications to all managers
    if order_id:
        from bot.manager_notifications import send_order_notification
        from bot.config import MANAGER_BOT_TOKEN
        
        managers = get_all_managers()
        if managers and MANAGER_BOT_TOKEN:
            for manager_chat_id in managers:
                try:
                    await send_order_notification(
                        order_data=order_data,
                        order_id=order_id,
                        manager_chat_id=manager_chat_id,
                        user_id=user_id
                    )
                except Exception as e:
                    logger.error(f"Failed to send notification to manager {manager_chat_id}: {e}")
    
    # Build order items summary
    response = f"""
✅ **Заказ подтвережден!**

**Номер заказа:** #{order_id}
💰 **Итого:** €{total:.2f}

👤 **Клиент:** {customer_info.get('firstName')} {customer_info.get('lastName')}
📱 {customer_info.get('phone')}

📍 **Адрес:** {customer_info.get('address')}
📮 {customer_info.get('postcode')}
🚪 Подъезд {customer_info.get('entrance')} | Этаж {customer_info.get('floor')} | Кв. {customer_info.get('apartment')}

🍽️ **Рацион:** {ration}
📅 **Дней:** {len(selected_dates)}

"""
    
    # Add meal details
    response += "📋 **Состав заказа:**\n"
    meals = RATIONS.get(ration, [])
    for date_str in sorted(selected_dates):
        meal_date = date.fromisoformat(date_str)
        date_display = format_date_display(meal_date, lang)
        response += f"\n{date_display}:\n"
        
        for meal in meals:
            if meal in BASE_MENU.get(date_str, {}):
                dish_name = get_current_dish_name(user_id, date_str, meal, lang)
                mods = get_mods_for_meal(user_id, date_str, meal)
                
                # Base dish
                meal_name = TRANSLATIONS.get(lang, TRANSLATIONS["ru"]).get("meals", {}).get(meal, meal)
                response += f"  • {meal_name}: {dish_name}"
                
                # Swaps
                if "SWAP" in mods:
                    response += f" (🔄 +€{mods['SWAP']['price_impact']:.2f})"
                
                # Add-ons
                if "ADD_ON" in mods:
                    addon_quantity = sum(m['quantity'] for m in user_carts[user_id]
                                        if m['order_date'] == date_str and
                                           m['meal_category'] == meal and
                                           m['operation_type'] == 'ADD_ON')
                    if addon_quantity > 0:
                        response += f" (➕ ×{addon_quantity})"
                
                response += "\n"
    
    response += f"\n💳 **Оплата:** {payment_method}\n"
    
    if customer_info.get('comment'):
        response += f"💬 **Комментарий:** {customer_info.get('comment')}\n"
    
    if payment_method == "cash" and cash_bill:
        response += f"Купюра: {cash_bill} €\n"
    
    response += "\n✨ Спасибо за заказ! Подтверждение будет отправлено в течение нескольких минут."
    
    keyboard = get_restart_keyboard(lang)
    
    # Check if message has edit_text method (from callback) or use answer (from regular message)
    if hasattr(message, 'edit_text') and callable(getattr(message, 'edit_text')):
        try:
            await message.edit_text(response, reply_markup=keyboard, parse_mode="Markdown")
        except:
            # If edit fails, send as new message
            await message.answer(response, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await message.answer(response, reply_markup=keyboard, parse_mode="Markdown")
    
    await state.clear()

def build_menu_cart_for_order(user_id: int, ration: str, selected_dates: list):
    """Build menuCart structure like in webapp"""
    meals = RATIONS.get(ration, [])
    menu_cart = {}
    
    for date_str in selected_dates:
        menu_cart[date_str] = {}
        for meal in meals:
            current_id = get_current_dish(user_id, date_str, meal)
            mods = get_mods_for_meal(user_id, date_str, meal)
            
            swapped_to = None
            extras = []
            
            if "SWAP" in mods:
                swapped_to = mods["SWAP"]["modified_dish_id"]
            
            if "ADD_ON" in mods:
                addon_meals = [m for m in user_carts[user_id]
                              if m['order_date'] == date_str and
                                 m['meal_category'] == meal and
                                 m['operation_type'] == 'ADD_ON']
                for addon in addon_meals:
                    extras.append({
                        "meal": meal,
                        "dish": addon["modified_dish_id"]
                    })
            
            menu_cart[date_str][meal] = {
                "baseDish": current_id,
                "swappedTo": swapped_to,
                "extras": extras
            }
    
    return menu_cart
