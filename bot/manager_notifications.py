"""
Manager bot notifications system
Отправляет уведомления менеджерам о новых заказах
"""

import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from bot.config import MANAGER_BOT_TOKEN
from bot.database import get_business_contact

logger = logging.getLogger(__name__)

def format_order_for_manager(order_data: dict, order_id: int = None) -> str:
    """
    Форматирует заказ для отправки менеджеру
    
    Args:
        order_data: словарь с данными заказа
        order_id: ID заказа из БД
    
    Returns:
        Отформатированная строка с информацией
    """
    
    customer = order_data.get('customer', {})
    payment = order_data.get('payment', {})
    days = order_data.get('days', [])
    
    msg = "📋 НОВЫЙ ЗАКАЗ\n"
    msg += "=" * 40 + "\n\n"
    
    if order_id:
        msg += f"🔢 ID заказа: <b>#{order_id}</b>\n"
    
    msg += f"⏰ Время: <b>{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</b>\n\n"
    
    # Customer info
    msg += "👤 КЛИЕНТ:\n"
    msg += f"Имя: <b>{customer.get('firstName', '')} {customer.get('lastName', '')}</b>\n"
    msg += f"📱 Телефон: <b>{customer.get('phone', 'N/A')}</b>\n"
    msg += f"Telegram ID: <code>{order_data.get('user_id', 'N/A')}</code>\n\n"
    
    # Address info
    msg += "📍 АДРЕС ДОСТАВКИ:\n"
    msg += f"{customer.get('address', 'N/A')}, {customer.get('postcode', 'N/A')}\n"
    msg += f"Дом {customer.get('building', 'N/A')}, Этаж {customer.get('floor', 'N/A')}, "
    msg += f"Кв. {customer.get('apartment', 'N/A')}\n\n"
    
    # Order details
    msg += "🍱 ДЕТАЛИ ЗАКАЗА:\n"
    msg += f"Рацион: <b>{order_data.get('ration', 'N/A')}</b>\n"
    msg += f"Дней: <b>{len(days)}</b>\n"
    msg += f"Даты: {', '.join(days)}\n\n"
    
    # Payment info
    msg += "💳 ОПЛАТА:\n"
    msg += f"Способ: <b>{payment.get('method', 'N/A').upper()}</b>\n"
    if payment.get('needChange'):
        msg += f"Сумма купюры: {payment.get('cashBill', 'N/A')} €\n"
    msg += f"Итого: <b>{order_data.get('total', 0):.2f} €</b>\n"
    
    return msg

def create_order_keyboard(order_id: int, user_id: int = None) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопками для менеджера
    
    Args:
        order_id: ID заказа в БД
        user_id: Telegram ID клиента
    
    Returns:
        InlineKeyboardMarkup с кнопками
    """
    
    buttons = [
        [
            InlineKeyboardButton(
                text="✅ ПОДТВЕРДИТЬ",
                callback_data=f"confirm_order:{order_id}"
            ),
            InlineKeyboardButton(
                text="❌ ОТКЛОНИТЬ",
                callback_data=f"reject_order:{order_id}"
            )
        ]
    ]
    
    if user_id:
        buttons.append([
            InlineKeyboardButton(
                text="💬 СВЯЗАТЬСЯ С КЛИЕНТОМ",
                callback_data=f"contact_client:{user_id}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(
            text="📞 ПОЗВОНИТЬ КЛИЕНТУ",
            callback_data=f"call_client:{order_id}"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def send_order_notification(
    order_data: dict,
    order_id: int,
    manager_chat_id: int,
    user_id: int = None
) -> bool:
    """
    Отправляет уведомление менеджеру о новом заказе
    
    Args:
        order_data: данные заказа
        order_id: ID заказа в БД
        manager_chat_id: ID чата менеджера для отправки
        user_id: Telegram ID клиента
    
    Returns:
        True если отправлено успешно
    """
    
    try:
        logger.info(f"🔔 Отправка уведомления менеджеру...")
        logger.info(f"   Order ID: {order_id}")
        logger.info(f"   Manager Chat ID: {manager_chat_id}")
        logger.info(f"   Client User ID: {user_id}")
        
        bot = Bot(token=MANAGER_BOT_TOKEN)
        
        text = format_order_for_manager(order_data, order_id)
        keyboard = create_order_keyboard(order_id, user_id)
        
        logger.info(f"   Отправка сообщения через Telegram API...")
        
        await bot.send_message(
            chat_id=manager_chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
        logger.info(f"✅ Уведомление отправлено менеджеру! Order #={order_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки уведомления: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def notify_client_order_confirmed(
    client_bot_token: str,
    user_id: int,
    order_id: int,
    ration: str,
    days: int
) -> bool:
    """
    Уведомляет клиента в боте №1, что заказ подтвержден
    
    Args:
        client_bot_token: токен клиентского бота
        user_id: Telegram ID клиента
        order_id: ID заказа
        ration: тип рациона
        days: количество дней
    
    Returns:
        True если отправлено
    """
    
    try:
        bot = Bot(token=client_bot_token)
        
        text = (
            "✅ <b>ВАШ ЗАКАЗ ПОДТВЕРЖДЕН!</b>\n\n"
            f"📋 Заказ #{order_id}\n"
            f"🍱 Рацион: <b>{ration}</b>\n"
            f"📅 Дней: <b>{days}</b>\n\n"
            "Спасибо за заказ! Мы начнем подготовку к доставке."
        )
        
        await bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode="HTML"
        )
        
        logger.info(f"Order confirmed notification sent to client: user_id={user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to notify client: {e}")
        return False

async def notify_client_order_rejected(
    client_bot_token: str,
    user_id: int,
    order_id: int,
    reason: str = None
) -> bool:
    """
    Уведомляет клиента, что заказ отклонен
    
    Args:
        client_bot_token: токен клиентского бота
        user_id: Telegram ID клиента
        order_id: ID заказа
        reason: причина отклонения
    
    Returns:
        True если отправлено
    """
    
    try:
        bot = Bot(token=client_bot_token)
        
        text = (
            "❌ <b>ВАША ЗАКАЗ НЕ МОЖЕТ БЫТЬ ВЫПОЛНЕН</b>\n\n"
            f"📋 Заказ #{order_id}\n"
        )
        
        if reason:
            text += f"<b>Причина:</b> {reason}\n\n"
        
        text += "Пожалуйста, свяжитесь с нами для уточнения информации."
        
        business_phone = get_business_contact('main_phone')
        if business_phone:
            text += f"\n📱 {business_phone.get('value', '')}"
        
        await bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode="HTML"
        )
        
        logger.info(f"Order rejected notification sent: user_id={user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send rejection notification: {e}")
        return False

async def send_manager_notification_to_group(
    order_data: dict,
    order_id: int,
    manager_group_id: int,
    user_id: int = None
) -> bool:
    """
    Отправляет уведомление в группу менеджеров (если используется)
    """
    return await send_order_notification(
        order_data=order_data,
        order_id=order_id,
        manager_chat_id=manager_group_id,
        user_id=user_id
    )
