# Обработчики для новых функций: расчетник ккал, менеджер, доставка, профиль
import logging
from datetime import date

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.states import States
from bot.config import BASE_PRICES, RATIONS
from bot.translations import TRANSLATIONS
from bot.utils import (
    calculate_bmr, calculate_tdee, adjust_kcal_for_goal, get_ration_by_kcal,
    validate_delivery_days, get_delivery_info, get_delivery_group, 
    calculate_day_kcal, get_daily_ration_kcal, format_date_display
)
from bot.keyboards import (
    get_calculator_gender_keyboard, get_calculator_activity_keyboard,
    get_calculator_goal_keyboard, get_calculator_confirm_keyboard,
    get_manager_consultation_keyboard, get_ration_selection_keyboard,
    get_dates_keyboard, get_profile_extended_keyboard
)

router_features = Router()

logger = logging.getLogger(__name__)

# ==================== РАСЧЕТНИК ККАЛ ====================

@router_features.callback_query(F.data == "CALC|START")
async def calculator_start(callback: CallbackQuery, state: FSMContext):
    """Начало расчета ккал"""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    
    keyboard = get_calculator_gender_keyboard(lang)
    await callback.message.edit_text(
        texts["calculator_start"],
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(States.calculator_gender)
    await callback.answer()

@router_features.callback_query(F.data.startswith("CALC|GENDER|"))
async def calculator_gender(callback: CallbackQuery, state: FSMContext):
    """Сохраняем пол и просим возраст"""
    gender = callback.data.split("|")[2]
    await state.update_data(calc_gender=gender)
    
    data = await state.get_data()
    lang = data.get("lang", "ru")
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    
    await callback.message.edit_text(
        texts["calculator_age"],
        parse_mode="Markdown"
    )
    await state.set_state(States.calculator_age)
    await callback.answer()

@router_features.message(States.calculator_age)
async def calculator_age_input(message: Message, state: FSMContext):
    """Получаем возраст"""
    try:
        age = int(message.text)
        if age < 13 or age > 120:
            await message.answer("❌ Пожалуйста, введите корректный возраст (13-120 лет)")
            return
        
        await state.update_data(calc_age=age)
        
        data = await state.get_data()
        lang = data.get("lang", "ru")
        texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
        
        await message.answer(texts["calculator_height"], parse_mode="Markdown")
        await state.set_state(States.calculator_height)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число")

@router_features.message(States.calculator_height)
async def calculator_height_input(message: Message, state: FSMContext):
    """Получаем рост"""
    try:
        height = int(message.text)
        if height < 140 or height > 250:
            await message.answer("❌ Пожалуйста, введите корректный рост в сантиметрах (140-250)")
            return
        
        await state.update_data(calc_height=height)
        
        data = await state.get_data()
        lang = data.get("lang", "ru")
        texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
        
        await message.answer(texts["calculator_weight"], parse_mode="Markdown")
        await state.set_state(States.calculator_weight)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число")

@router_features.message(States.calculator_weight)
async def calculator_weight_input(message: Message, state: FSMContext):
    """Получаем вес"""
    try:
        weight = float(message.text.replace(',', '.'))
        if weight < 40 or weight > 300:
            await message.answer("❌ Пожалуйста, введите корректный вес в кг (40-300)")
            return
        
        await state.update_data(calc_weight=weight)
        
        data = await state.get_data()
        lang = data.get("lang", "ru")
        texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
        
        keyboard = get_calculator_activity_keyboard(lang)
        await message.answer(
            texts["calculator_activity"],
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await state.set_state(States.calculator_activity)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректное число")

@router_features.callback_query(F.data.startswith("CALC|ACTIVITY|"))
async def calculator_activity(callback: CallbackQuery, state: FSMContext):
    """Получаем уровень активности"""
    activity_level = float(callback.data.split("|")[2])
    await state.update_data(calc_activity=activity_level)
    
    data = await state.get_data()
    lang = data.get("lang", "ru")
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    
    keyboard = get_calculator_goal_keyboard(lang)
    await callback.message.edit_text(
        texts["calculator_goal"],
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(States.calculator_goal)
    await callback.answer()

@router_features.callback_query(F.data.startswith("CALC|GOAL|"))
async def calculator_goal(callback: CallbackQuery, state: FSMContext):
    """Получаем цель и рассчитываем результаты"""
    goal = callback.data.split("|")[2]
    
    data = await state.get_data()
    lang = data.get("lang", "ru")
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    
    # Извлекаем данные
    gender = data.get("calc_gender", "M")
    age = data.get("calc_age", 30)
    height = data.get("calc_height", 170)
    weight = data.get("calc_weight", 70)
    activity_level = data.get("calc_activity", 1.55)
    
    # Рассчитываем
    bmr = calculate_bmr(gender, age, height, weight)
    tdee = calculate_tdee(bmr, activity_level)
    adjusted_kcal = adjust_kcal_for_goal(tdee, goal)
    
    # Определяем рацион
    recommended_ration, ration_kcal = get_ration_by_kcal(adjusted_kcal)
    
    await state.update_data(
        calc_goal=goal,
        calc_bmr=bmr,
        calc_tdee=tdee,
        calc_adjusted_kcal=adjusted_kcal,
        calc_recommended_ration=recommended_ration,
        calc_recommended_kcal=ration_kcal
    )
    
    # Показываем результаты
    result_text = f"""
{texts['calculator_confirm']}

📊 **{texts['calculator_daily_kcal']}:** {int(adjusted_kcal)} ккал
💪 **БМР:** {int(bmr)} ккал
🏃 **TDEE:** {int(tdee)} ккал

🎯 **{texts['calculator_recommended']}:** **{recommended_ration}** ({int(ration_kcal)} ккал)

**{texts['ration_buttons'][['SLIM', 'LIGHT', 'STANDART', 'MEDIUM', 'STRONG'].index(recommended_ration)]}**
"""
    
    keyboard = get_calculator_confirm_keyboard(lang)
    await callback.message.edit_text(
        result_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(States.calculator_confirm)
    await callback.answer()

@router_features.callback_query(F.data == "CALC|CONFIRM_RATION")
async def calculator_confirm_ration(callback: CallbackQuery, state: FSMContext):
    """Подтверждаем рацион и переходим к выбору дней"""
    data = await state.get_data()
    recommended_ration = data.get("calc_recommended_ration", "STANDART")
    lang = data.get("lang", "ru")
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    
    await state.update_data(ration=recommended_ration)
    
    # Переходим к выбору кол-ва дней
    from bot.keyboards import get_days_count_keyboard
    keyboard = get_days_count_keyboard(lang)
    
    await callback.message.edit_text(
        f"✅ **{texts['selected_ration'].format(ration=recommended_ration)}**\n\n**Сколько дней?**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(States.days_count_selection)
    await callback.answer()

@router_features.callback_query(F.data == "CALC|RECALCULATE")
async def calculator_recalculate(callback: CallbackQuery, state: FSMContext):
    """Пересчитываем ккал сначала"""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    
    keyboard = get_calculator_gender_keyboard(lang)
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    
    await state.clear()
    await state.update_data(lang=lang)
    
    await callback.message.edit_text(
        texts["calculator_start"],
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(States.calculator_gender)
    await callback.answer()

# ==================== КОНСУЛЬТАЦИЯ С МЕНЕДЖЕРОМ ====================

@router_features.callback_query(F.data == "MANAGER|START")
async def manager_consultation_start(callback: CallbackQuery, state: FSMContext):
    """Показываем описание консультации"""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    
    keyboard = get_manager_consultation_keyboard(lang)
    await callback.message.edit_text(
        texts["manager_description"],
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(States.manager_consultation)
    await callback.answer()

@router_features.callback_query(F.data == "MANAGER|ACCEPT")
async def manager_accept(callback: CallbackQuery, state: FSMContext):
    """Клиент согласился на консультацию"""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    
    user_id = callback.from_user.id
    user_name = callback.from_user.full_name or "Unknown"
    
    # Отправляем уведомление менеджеру
    try:
        from bot.manager_bot import send_consultation_request
        await send_consultation_request(user_id, user_name, lang)
    except Exception as e:
        logger.error(f"Error sending manager notification: {e}")
    
    response = f"""
✅ **Спасибо за обращение!**

Наш менеджер скоро свяжется с вами для персональной консультации.

💬 Вы можете уточнить:
• Состав рациона
• Особенности диеты
• Индивидуальные пожелания
• Способ доставки

Ожидайте сообщения от менеджера в течение 30 минут.
"""
    
    from bot.keyboards import get_restart_keyboard
    keyboard = get_restart_keyboard(lang)
    await callback.message.edit_text(
        response,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.clear()
    await callback.answer()

@router_features.callback_query(F.data == "MANAGER|CANCEL")
async def manager_cancel(callback: CallbackQuery, state: FSMContext):
    """Отказ от консультации, возвращаемся к выбору рациона"""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    
    keyboard = get_ration_selection_keyboard(lang)
    await callback.message.edit_text(
        texts["choose_ration"],
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(States.start)
    await callback.answer()

# ==================== ВАЛИДАЦИЯ ДОСТАВКИ ====================

@router_features.callback_query(F.data.startswith("CALENDAR|"))
async def select_calendar_date_validated(callback: CallbackQuery, state: FSMContext):
    """Выбор даты с валидацией группы доставки"""
    date_str = callback.data.split("|")[1]
    data = await state.get_data()
    days_count = data.get("days_count", 2)
    selected_dates = data.get("selected_dates", [])
    lang = data.get("lang", "ru")
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    
    # Добавляем дату
    if date_str not in selected_dates:
        selected_dates.append(date_str)
    
    # Проверяем валидность группы доставки
    if not validate_delivery_days(selected_dates):
        # Ошибка - удаляем последнюю добавленную дату
        selected_dates.remove(date_str)
        await callback.answer(texts.get("delivery_group_error", "Ошибка выбора дней"), show_alert=True)
        
        from bot.keyboards import get_calendar_keyboard
        keyboard = get_calendar_keyboard(days_count, lang)
        await callback.message.edit_text(
            f"📅 **Выбрано: {len(selected_dates)}/{days_count}**",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        return
    
    await state.update_data(selected_dates=selected_dates)
    
    if len(selected_dates) == days_count:
        # Все даты выбраны, показываем информацию о доставке
        delivery_info = get_delivery_info(selected_dates, lang)
        
        from bot.handlers_extended import show_meals
        await callback.message.edit_text(
            f"✅ **{len(selected_dates)} дней выбрано**\n\n{delivery_info}\n\n⏳ Загрузка меню...",
            parse_mode="Markdown"
        )
        
        # Переходим к показу меню
        await state.update_data(current_date_index=0)
        await show_meals(callback.message, callback.from_user.id, state)
        await state.set_state(States.day_selected)
    else:
        # Еще нужны даты, показываем информацию о группе доставки
        from bot.keyboards import get_calendar_keyboard
        keyboard = get_calendar_keyboard(days_count, lang)
        
        selected_group_days = get_delivery_group(date.fromisoformat(selected_dates[0]).weekday())[0]
        weekday_names = TRANSLATIONS[lang]["weekdays"]
        group_days_str = ", ".join([weekday_names[d] for d in selected_group_days])
        
        await callback.message.edit_text(
            f"📅 **Выбрано: {len(selected_dates)}/{days_count}**\n\n"
            f"📦 Доступные дни группы: {group_days_str}\n\n"
            f"Выберите ещё {days_count - len(selected_dates)} дня/дней:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    await callback.answer()

# ==================== ОТОБРАЖЕНИЕ ККАЛ ====================

@router_features.callback_query(F.data == "SHOW_KCAL")
async def show_kcal_info(callback: CallbackQuery, state: FSMContext):
    """Показываем информацию о ккал для рациона"""
    data = await state.get_data()
    ration = data.get("ration", "STANDART")
    lang = data.get("lang", "ru")
    
    ration_kcal = get_daily_ration_kcal(ration)
    
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    
    kcal_text = f"""
📊 **Информация о ккал**

**Рацион:** {ration}
**Ккал в день:** ~{int(ration_kcal)} ккал
**Статус:** Сбалансированное питание

Этот рацион рассчитан на среднего взрослого человека с умеренной активностью.

💡 Точное количество ккал может варьироваться в зависимости от выбранных блюд.
"""
    
    from bot.keyboards import get_restart_keyboard
    keyboard = get_restart_keyboard(lang)
    await callback.message.edit_text(
        kcal_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()

# ==================== РАСШИРЕННЫЙ ПРОФИЛЬ ====================

@router_features.callback_query(F.data == "PROFILE|ADD_RATION")
async def profile_add_ration(callback: CallbackQuery, state: FSMContext):
    """Добавляем дополнительный рацион"""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    
    keyboard = get_ration_selection_keyboard(lang)
    
    await callback.message.edit_text(
        f"{texts['choose_ration']}\n\n*(для добавления к основному заказу)*",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    
    await state.set_state(States.profile_additional_ration)
    await callback.answer()

@router_features.callback_query(F.data.startswith("RATION|"), States.profile_additional_ration)
async def profile_ration_selected(callback: CallbackQuery, state: FSMContext):
    """Рацион выбран для профиля"""
    ration_key = callback.data.split("|")[1]
    data = await state.get_data()
    lang = data.get("lang", "ru")
    texts = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    
    # Сохраняем дополнительный рацион
    additional_rations = data.get("additional_rations", [])
    additional_rations.append({
        "ration": ration_key,
        "added_date": str(date.today())
    })
    
    from bot.database import save_additional_ration
    user_id = callback.from_user.id
    save_additional_ration(user_id, ration_key)
    
    response = f"""
✅ **{ration_key} добавлен к вашему профилю!**

Теперь вы можете заказать этот рацион когда захотите.

📝 Ваши рационы:
• {ration_key}

Хотите добавить ещё один?
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить ещё", callback_data="PROFILE|ADD_RATION")],
        [InlineKeyboardButton(text="🏠 Вернуться в профиль", callback_data="PROFILE|BACK")],
    ])
    
    await callback.message.edit_text(
        response,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()

@router_features.callback_query(F.data == "PROFILE|BACK")
async def profile_back(callback: CallbackQuery, state: FSMContext):
    """Возвращаемся в профиль"""
    await callback.message.delete()
    await callback.answer()
    # Profile отображается в основном handlers.py

# Импорт для InlineKeyboardMarkup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
