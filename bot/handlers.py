# Bot handlers
import logging
from datetime import date, datetime
from collections import defaultdict

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.enums import ContentType

from bot.states import States
from bot.config import RATIONS, DEFAULT_ORDER_DAYS
from bot.data import DISHES, BASE_MENU, BASE_SWAP_MAPPING
from bot.translations import TRANSLATIONS
from bot.utils import (
    get_available_meal_dates, get_current_dish, get_current_dish_name,
    get_mods_for_meal, add_modification, format_date_display, user_carts
)
from bot.keyboards import (
    get_language_keyboard, get_mode_keyboard, get_ration_keyboard, get_dates_keyboard,
    get_meals_keyboard, get_actions_keyboard, get_swap_keyboard,
    get_base_swap_keyboard, get_quantity_keyboard, get_cart_keyboard,
    get_restart_keyboard, get_contact_keyboard, get_ration_selection_keyboard
)

router = Router()

# Database (simple SQLite for demo)
import sqlite3
conn = sqlite3.connect('users.db')
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, phone TEXT)")
conn.commit()

# ==================== START ====================
@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
     keyboard = get_language_keyboard()
     start_msg = "Choose language / Выберите язык / Elige idioma:"
     await message.answer(start_msg, reply_markup=keyboard)
     await state.set_state(States.start)

@router.callback_query(F.data.startswith("LANG|"))
async def select_lang(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split("|")[1]
    await state.update_data(lang=lang)
    await callback.answer()
    
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    
    # Skip mode selection, go directly to ration selection (Chat Mode)
    keyboard = get_ration_selection_keyboard(lang)
    await callback.message.edit_text(texts["choose_ration"], reply_markup=keyboard, parse_mode="Markdown")
    await state.set_state(States.start)

# ==================== MODE SELECTION (Deprecated/Skipped) ====================
@router.callback_query(F.data.startswith("MODE|"))
async def select_mode(callback: CallbackQuery, state: FSMContext):
    # ... (Keep for compatibility if needed, but mostly unused now)
    pass

# ==================== RATION ====================
@router.callback_query(F.data.startswith("RATION|"))
async def select_ration(callback: CallbackQuery, state: FSMContext):
    ration_key = callback.data.split("|")[1]
    await state.update_data(ration=ration_key)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    
    # NEW: Show days count selection with Preamble
    from bot.keyboards import get_days_count_keyboard
    keyboard = get_days_count_keyboard(lang, ration=ration_key)
    
    preamble = texts.get("days_selection_preamble", "")
    text = f"✅ **{texts['selected_ration'].format(ration=ration_key)}**\n\n{preamble}"
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboard, parse_mode="Markdown"
    )
    await state.set_state(States.days_count_selection)
    await callback.answer()

@router.callback_query(F.data == "CHANGE_RATION")
async def change_ration(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    keyboard = get_ration_selection_keyboard(lang)
    await callback.message.edit_text(texts["choose_ration"], reply_markup=keyboard, parse_mode="Markdown")
    await state.set_state(States.start)
    await callback.answer(texts["choose_other_ration"])

# ==================== DATE SELECTION ====================
@router.callback_query(F.data.startswith("DATE|"))
async def select_day(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.split("|")[1]
    data = await state.get_data()
    selected = data.get("selected_dates", [])
    if date_str not in selected:
        selected.append(date_str)
    await state.update_data(current_date=date_str, selected_dates=selected)
    await show_meals(callback.message, callback.from_user.id, state)
    await state.set_state(States.day_selected)
    await callback.answer()

async def show_meals(message, user_id: int, state: FSMContext):
    data = await state.get_data()
    ration = data.get("ration", "STANDART")
    date_str = data.get("current_date")
    meals = RATIONS.get(ration, [])
    lang = data.get("lang", "ru")
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    
    if not date_str:
        logging.error(f"show_meals: current_date not set in state")
        return
    
    meal_date = date.fromisoformat(date_str)
    date_display = format_date_display(meal_date, lang)
    
    text = f"📅 **{date_display}** | {texts['plan']}: **{ration}**\n\n"
    day_has_changes = False
    changes_texts = {
        "ru": {"yes": "✏️ Изменения на этот день сохранены.", "no": "ℹ️ Изменений нет."},
        "en": {"yes": "✏️ Changes saved for this day.", "no": "ℹ️ No changes."},
        "es": {"yes": "✏️ Cambios guardados para este día.", "no": "ℹ️ Sin cambios."}
    }
    changes_opts = changes_texts.get(lang, changes_texts["ru"])
    for meal in meals:
        if meal not in BASE_MENU.get(date_str, {}):
            continue
        dish_name = get_current_dish_name(user_id, date_str, meal, lang)
        mod_text = ""
        mods = get_mods_for_meal(user_id, date_str, meal)
        if "SWAP" in mods:
            mod_text += f" (🔄 +€{mods['SWAP']['price_impact']:.2f})"
        total_addon_quantity = sum(m['quantity'] for m in user_carts[user_id]
                                   if m['order_date'] == date_str and
                                      m['meal_category'] == meal and
                                      m['operation_type'] == 'ADD_ON')
        if total_addon_quantity > 0:
            mod_text += f" (➕ x{total_addon_quantity})"
        has_changes = ("SWAP" in mods) or (total_addon_quantity > 0)
        if has_changes:
            day_has_changes = True
        edited_flag = "✏️ " if has_changes else ""
        meal_name = texts.get("meals", {}).get(meal, meal)
        text += f"{edited_flag}**{meal_name}:** {dish_name}{mod_text}\n"
    status_line = changes_opts["yes"] if day_has_changes else changes_opts["no"]
    text += f"\n{status_line}\n\n{texts['choose_meal']}"
    
    keyboard = get_meals_keyboard(ration, lang)
    await message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

# ==================== MEAL SELECTION ====================
@router.callback_query(F.data.startswith("MEAL|"))
async def select_meal(callback: CallbackQuery, state: FSMContext):
    meal = callback.data.split("|")[1]
    await state.update_data(meal=meal)
    await show_actions(callback, callback.from_user.id, state)
    await state.set_state(States.meal_action_selection)
    await callback.answer()

async def show_actions(callback, user_id: int, state: FSMContext):
    data = await state.get_data()
    meal = data["meal"]
    date_str = data["current_date"]
    current_id = get_current_dish(user_id, date_str, meal)
    has_base = DISHES.get(current_id, {}).get("has_base", False) and current_id in BASE_SWAP_MAPPING
    lang = data.get("lang", "ru")
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    
    keyboard = get_actions_keyboard(meal, has_base, lang)
    
    meal_name = texts.get("meals", {}).get(meal, meal)
    text = (f"🍽️ **{meal_name}**\n\n"
            f"**{texts['current_dish']}:** {get_current_dish_name(user_id, date_str, meal, lang)}\n\n"
            f"**{texts['choose_action']}:**")
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

# ==================== ACTIONS ====================
@router.callback_query(F.data == "KEEP_DEFAULT")
async def keep_default(callback: CallbackQuery, state: FSMContext):
    await show_meals(callback.message, callback.from_user.id, state)
    await state.set_state(States.day_selected)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    await callback.answer(texts['keep_default_ok'])

@router.callback_query(F.data.startswith("ACTION|"))
async def handle_action(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split("|")[1]
    data = await state.get_data()
    lang = data.get("lang", "ru")
    
    if action == "SWAP":
        texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
        meal = data["meal"]
        date_str = data["current_date"]
        user_id = callback.from_user.id
        
        # Get original dish ID to calculate prices
        original_id = BASE_MENU.get(date_str, {}).get(meal)
        if not original_id:
             # Fallback if meal not in base menu (should not happen usually)
             original_id = get_current_dish(user_id, date_str, meal)
             
        keyboard = get_swap_keyboard(meal, lang, original_id=original_id)
        text = texts['swap_prompt'].replace('{meal}', meal)
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        await state.set_state(States.swap_selection)
    elif action == "ADD_ON":
        texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
        keyboard = get_quantity_keyboard(lang)
        await callback.message.edit_text(texts['add_on_prompt'], reply_markup=keyboard, parse_mode="Markdown")
        await state.set_state(States.add_on_quantity_input)
    await callback.answer()

@router.callback_query(F.data.startswith("SWAP|"))
async def select_swap(callback: CallbackQuery, state: FSMContext):
    new_id = int(callback.data.split("|")[1])
    data = await state.get_data()
    date_str = data["current_date"]
    meal = data["meal"]
    user_id = callback.from_user.id
    original_id = BASE_MENU.get(date_str, {}).get(meal)
    
    # If not found in base menu, fallback
    if not original_id:
        original_id = get_current_dish(user_id, date_str, meal)
        
    add_modification(user_id, date_str, meal, "SWAP", original_id, new_id)
    await show_meals(callback.message, user_id, state)
    await state.set_state(States.day_selected)
    lang = data.get("lang", "ru")
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    await callback.answer(texts['swap_added'])

# BASE_SWAP handlers removed


@router.callback_query(F.data.startswith("QUANTITY|"))
async def select_quantity(callback: CallbackQuery, state: FSMContext):
    quantity = int(callback.data.split("|")[1])
    data = await state.get_data()
    date_str = data["current_date"]
    meal = data["meal"]
    user_id = callback.from_user.id
    current_id = get_current_dish(user_id, date_str, meal)
    add_modification(user_id, date_str, meal, "ADD_ON", current_id, current_id, quantity)
    await show_meals(callback.message, user_id, state)
    await state.set_state(States.day_selected)
    lang = data.get("lang", "ru")
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    await callback.answer(texts['add_on_added'].format(quantity=quantity))

# ==================== NAVIGATION ====================
@router.callback_query(F.data.in_(["BACK_TO_DAYS", "BACK_TO_MEALS", "BACK_TO_ACTIONS"]))
async def handle_back(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = await state.get_data()
    lang = data.get("lang", "ru")
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    
    if callback.data == "BACK_TO_DAYS":
        available_dates = data.get("available_dates", [])
        keyboard = get_dates_keyboard(available_dates, lang)
        await callback.message.edit_text(
            f"{texts['selected_ration'].format(ration=data.get('ration', 'STANDART'))}\n\n{texts['choose_day_prompt']}",
            reply_markup=keyboard, parse_mode="Markdown"
        )
        await state.set_state(States.ration_selected)
    elif callback.data == "BACK_TO_MEALS":
        await show_meals(callback.message, user_id, state)
        await state.set_state(States.day_selected)
    elif callback.data == "BACK_TO_ACTIONS":
        await show_actions(callback, user_id, state)
        await state.set_state(States.meal_action_selection)
    await callback.answer()

# ==================== CART ====================
@router.callback_query(F.data == "CART")
async def view_cart(callback: CallbackQuery, state: FSMContext):
    await show_cart(callback, state)
    await callback.answer()

async def show_cart(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = await state.get_data()
    ration = data.get("ration", "STANDART")
    meals = RATIONS.get(ration, [])
    lang = data.get("lang", "ru")
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    
    text = f"{texts['cart_title']}\n\n"
    total = 0.0
    grouped_mods = defaultdict(list)
    for mod in user_carts[user_id]:
        grouped_mods[mod["order_date"]].append(mod)
    
    selected_dates = data.get("selected_dates", [])
    for date_str in sorted(selected_dates):
        meal_date = date.fromisoformat(date_str)
        date_display = format_date_display(meal_date, lang)
        
        text += f"📅 **{date_display}:**\n"
        text += f"📋 **{texts['your_order']}**\n"
        day_total_cost = 0.0
        
        for meal in meals:
            if meal in BASE_MENU.get(date_str, {}):
                dish_name = get_current_dish_name(user_id, date_str, meal, lang)
                mods = get_mods_for_meal(user_id, date_str, meal)
                mod_text = ""
                if "SWAP" in mods:
                    mod_text += f" (🔄 +€{mods['SWAP']['price_impact']:.2f})"
                    day_total_cost += mods['SWAP']['price_impact']
                if "ADD_ON" in mods:
                    addon_mods = [m for m in grouped_mods.get(date_str, []) if m['meal_category'] == meal and m['operation_type'] == 'ADD_ON']
                    addon_cost = sum(m['total_cost'] for m in addon_mods)
                    addon_quantity = sum(m['quantity'] for m in addon_mods)
                    mod_text += f" (➕ x{addon_quantity})"
                    day_total_cost += addon_cost
                meal_name = texts.get("meals", {}).get(meal, meal)
                text += f"  • **{meal_name}:** {dish_name}{mod_text}\n"
        
        mods = grouped_mods.get(date_str, [])
        if mods:
            text += f"\n🔄 **{texts['changes_details']}**\n"
            for mod in mods:
                if mod["operation_type"] == "SWAP":
                    orig_name = DISHES[mod["original_dish_id"]][f"name_{lang}"]
                    mod_name = DISHES[mod["modified_dish_id"]][f"name_{lang}"]
                    text += f"  ➤ {mod['meal_category']}: {orig_name} → {mod_name} | +€{mod['price_impact']:.2f}\n"
                elif mod["operation_type"] == "ADD_ON":
                    dish_name = DISHES[mod["modified_dish_id"]][f"name_{lang}"]
                    text += f"  ➕ {mod['meal_category']}: {dish_name} ×{mod['quantity']} | +€{mod['total_cost']:.2f}\n"
        else:
            text += f"\n💚 **{texts['default_set']}**\n"
        total += day_total_cost
        text += "\n"
    
    text += f"💰 **{texts['total_due']} €{total:.2f}**"
    keyboard = get_cart_keyboard(lang)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await state.set_state(States.cart_review)

@router.callback_query(F.data == "CONFIRM")
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    # Proceed to sequential contact info collection instead of finishing
    user_id = callback.from_user.id
    data = await state.get_data()
    lang = data.get("lang", "ru")
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    await state.update_data(contact={})
    
    # Check for saved contact info and show option to use it
    from bot.handlers_extended import ask_for_first_name
    await ask_for_first_name(callback.message, state, user_id)
    await state.set_state(States.contact_first_name)
    await callback.answer()

#

@router.callback_query(F.data == "START")
async def restart_order(callback: CallbackQuery, state: FSMContext):
    keyboard = get_language_keyboard()
    await callback.message.edit_text(TRANSLATIONS['ru']['choose_language'], reply_markup=keyboard)
    await state.set_state(States.start)
    await callback.answer()

# ==================== PROFILE ====================
@router.message(Command("profile"))
async def profile_handler(message: Message, state: FSMContext):
    from bot.database import get_user_rations
    from bot.keyboards import get_profile_extended_keyboard
    
    data = await state.get_data()
    lang = data.get("lang", "ru")
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    user_id = message.from_user.id
    cursor.execute("SELECT name, phone FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    if row is None:
        kb = get_contact_keyboard(lang)
        await message.answer(texts['send_contact'], reply_markup=kb)
    else:
        name, phone = row
        
        # Получаем дополнительные рационы
        additional_rations = get_user_rations(user_id)
        
        profile_text = (f"👤 **{texts['profile_title']}**\n\n"
                        f"{name}\n"
                        f"{texts['profile_phone'].format(phone=phone)}\n"
                        f"{texts['profile_no_sub']}")
        
        # Добавляем информацию о доп рационах
        if additional_rations:
            profile_text += f"\n\n{texts.get('profile_additional', '📋 Ваши рационы:')}\n"
            for ration in additional_rations:
                profile_text += f"  • {ration}\n"
        else:
            profile_text += f"\n\n{texts.get('profile_no_additional', 'Нет дополнительных рационов')}"
        
        # Показываем клавиатуру с опцией добавить рацион
        keyboard = get_profile_extended_keyboard(lang)
        await message.answer(profile_text, reply_markup=keyboard, parse_mode="Markdown")

@router.message(F.contact)
async def handle_contact(message: Message, state: FSMContext):
    contact = message.contact
    user_id = message.from_user.id
    name = message.from_user.full_name
    phone = contact.phone_number
    cursor.execute("REPLACE INTO users (id, name, phone) VALUES (?, ?, ?)", (user_id, name, phone))
    conn.commit()
    data = await state.get_data()
    lang = data.get("lang", "ru")
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    await message.answer(texts['contact_saved'], reply_markup=ReplyKeyboardRemove())

# ==================== WEBAPP DATA ====================
@router.message(F.content_type == ContentType.WEB_APP_DATA)
async def handle_webapp_data(message: Message, state: FSMContext):
    """Handle data sent from WebApp"""
    import json
    
    logging.info("[WEBAPP] Handler triggered!")
    logging.info(f"[WEBAPP] Data length: {len(message.web_app_data.data) if message.web_app_data else 0}")
    
    # Always use SQLite as backup
    from bot.database import save_order as save_order_to_db
    
    try:
        from bot.gsheets import save_order_to_gsheet, GSPREAD_AVAILABLE
    except ImportError:
        GSPREAD_AVAILABLE = False
        
    try:
        from bot.manager_bot import send_order_to_manager
    except ImportError:
        send_order_to_manager = None
    
    try:
        from bot.config import MANAGER_BOT_TOKEN, MANAGER_CHAT_ID
    except Exception:
        MANAGER_BOT_TOKEN, MANAGER_CHAT_ID = None, None
    
    try:
        data = json.loads(message.web_app_data.data)
        user_id = message.from_user.id
        lang = data.get('lang', 'ru')
        texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
        
        logging.info(f"WebApp data received from user {user_id}: {data.keys()}")
        
        # This is a complete order from WebApp
        if 'customer' in data and 'payment' in data:
            customer = data.get('customer', {})
            payment = data.get('payment', {})
            ration = data.get('ration', '')
            days = data.get('days', [])
            total = data.get('total', 0)
            
            # Format order summary for customer
            order_summary = f"""
🎉 **Новый заказ через WebApp!**

👤 **Клиент:**
{customer.get('firstName')} {customer.get('lastName')}
📱 {customer.get('phone')}

📍 **Адрес:**
{customer.get('address')}
{customer.get('postcode')} {customer.get('building')}-{customer.get('floor')}-{customer.get('apartment')}

🍽️ **Заказ:**
Рацион: {ration}
Дней: {len(days)}
Даты: {', '.join(days)}

💳 **Оплата:**
Способ: {payment.get('method')}
"""
            
            if payment.get('method') == 'cash' and payment.get('needChange'):
                order_summary += f"Купюра: {payment.get('cashBill')} €\n"
            
            order_summary += f"\n💰 **Итого: {total:.2f} €**"
            
            # IMMEDIATE response to customer
            await message.answer(
                "⏳ **Ожидайте подтверждения заказа**\n\n"
                "Ваш заказ получен и передан менеджерам.\n"
                "Подтверждение придёт в течение нескольких минут.",
                parse_mode="Markdown"
            )
            
            # Save to local database FIRST (always works)
            results = []
            order_id = save_order_to_db(data)
            if order_id:
                results.append(f"💾 Заказ #{order_id} сохранён локально")
                logging.info(f"Order #{order_id} saved to local database")
                
                # Send notification to all registered managers
                try:
                    from bot.manager_notifications import send_order_notification
                    from bot.database import mark_order_notified, get_all_managers
                    
                    # Get all registered managers from database
                    manager_chat_ids = get_all_managers()
                    
                    if manager_chat_ids:
                        sent_count = 0
                        failed_count = 0
                        
                        for manager_chat_id in manager_chat_ids:
                            try:
                                logging.info(f"📬 Отправка уведомления менеджеру chat_id={manager_chat_id}")
                                success = await send_order_notification(
                                    order_data=data,
                                    order_id=order_id,
                                    manager_chat_id=manager_chat_id,
                                    user_id=user_id
                                )
                                if success:
                                    sent_count += 1
                                    logging.info(f"✅ Уведомление отправлено менеджеру {manager_chat_id}")
                                else:
                                    failed_count += 1
                                    logging.error(f"❌ Ошибка отправки менеджеру {manager_chat_id}")
                            except Exception as e:
                                failed_count += 1
                                logging.error(f"Exception sending to manager {manager_chat_id}: {e}")
                        
                        if sent_count > 0:
                            mark_order_notified(order_id)
                            results.append(f"📬 Уведомлены {sent_count} менеджеров")
                            logging.info(f"Order #{order_id} notified to {sent_count} managers")
                        
                        if failed_count > 0:
                            results.append(f"⚠️ Ошибка у {failed_count} менеджеров")
                    else:
                        logging.warning("❌ Менеджеры не зарегистрированы! Попросите менеджеров написать /start боту менеджера")
                        results.append("⚠️ Менеджеры не зарегистрированы")
                except Exception as e:
                    logging.error(f"Failed to notify managers: {e}")
                    results.append(f"⚠️ Ошибка уведомления: {e}")
            else:
                results.append("⚠️ Ошибка сохранения")
            
            # Try to save to Google Sheets (optional)
            saved_to_gsheet = False
            if GSPREAD_AVAILABLE:
                try:
                    saved_to_gsheet = save_order_to_gsheet(data)
                    if saved_to_gsheet:
                        results.append("📊 Дублировано в Google Sheets")
                        logging.info("Order also saved to Google Sheets")
                except Exception as e:
                    logging.error(f"Google Sheets error: {e}")
                    # Don't add to results - not critical
            else:
                logging.warning("Google Sheets not available - using local DB only")
            
            # Send detailed summary to customer
            await message.answer(order_summary, parse_mode="Markdown")
            
            # Status for admin/debug
            if results:
                logging.info("Order processing results: " + ", ".join(results))
        
        else:
            # Old format or other actions
            logging.info(f"Received WebApp data: {data}")
            await message.answer("✅ Данные получены!")
            
    except Exception as e:
        logging.error(f"Error handling WebApp data: {e}")
        await message.answer("❌ Ошибка обработки данных")
