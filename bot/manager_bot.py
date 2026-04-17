# Manager Bot - для уведомлений о заказах
# Manager Bot - для уведомлений о заказах
import asyncio
import logging
from aiogram import Bot

async def send_order_to_manager(order_data: dict, manager_token: str, manager_chat_id: str):
    """
    Send order notification to manager bot/group
    
    Args:
        order_data: Order data from WebApp
        manager_token: Manager bot token
        manager_chat_id: Chat ID where to send (group or user)
    """
    try:
        manager_bot = Bot(token=manager_token)
        
        customer = order_data.get('customer', {})
        payment = order_data.get('payment', {})
        days = order_data.get('days', [])
        total = order_data.get('total', 0)
        
        # Build message
        message = f"""
🔔 **НОВЫЙ ЗАКАЗ!**

👤 **Клиент:**
{customer.get('firstName', '')} {customer.get('lastName', '')}
📱 {customer.get('phone', '')}

📍 **Адрес доставки:**
{customer.get('address', '')}
Индекс: {customer.get('postcode', '')}
Подъезд: {customer.get('building', '')} | Этаж: {customer.get('floor', '')} | Кв: {customer.get('apartment', '')}

🍽️ **Заказ:**
Рацион: **{order_data.get('ration', '')}**
Количество дней: **{len(days)}**
Даты: {', '.join(days)}

💳 **Оплата:**
Способ: **{get_payment_method_name(payment.get('method', ''))}**
"""
        
        # Add cash payment details
        if payment.get('method') == 'cash':
            if payment.get('needChange'):
                change_needed = payment.get('cashBill', 0) - total
                message += f"💶 Купюра: {payment.get('cashBill')} €\n"
                message += f"💰 Сдача: {change_needed:.2f} €\n"
            else:
                message += "✅ Точная сумма (без сдачи)\n"
        
        message += f"\n💰 **ИТОГО: {total:.2f} €**"
        message += f"\n\n🕐 Время заказа: {order_data.get('timestamp', '')}"
        
        # Send message
        await manager_bot.send_message(manager_chat_id, message, parse_mode="Markdown")
        
        # Close bot session
        await manager_bot.session.close()
        
        logging.info(f"Order notification sent to manager: {customer.get('firstName')} {customer.get('lastName')}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to send to manager bot: {e}")
        return False

def get_payment_method_name(method: str) -> str:
    """Get readable payment method name"""
    methods = {
        'cash': 'Наличные 💵',
        'terminal': 'Терминал 💳',
        'transfer': 'Банковский перевод 🏦'
    }
    return methods.get(method, method)
