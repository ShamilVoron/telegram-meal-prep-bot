"""
Handlers for Manager Bot
Обработка кнопок подтверждения/отклонения заказов
"""

import asyncio
import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
from bot.config import BOT_TOKEN, MANAGER_BOT_TOKEN
from bot.database import (
    update_order_status_db,
    get_order_by_id,
    get_user_contact,
    get_business_contact,
    register_manager
)
from bot.manager_notifications import (
    notify_client_order_confirmed,
    notify_client_order_rejected
)

router = Router()
logger = logging.getLogger(__name__)


# ==================== БАЗОВЫЕ КОМАНДЫ ====================

@router.message(Command("start"))
async def start_handler(message: Message):
    """Обработка /start - регистрирует менеджера автоматически"""
    chat_id = message.chat.id
    manager_name = message.from_user.full_name
    
    # Автоматически регистрируем менеджера при первом старте
    register_manager(chat_id, manager_name)
    logger.info(f"Manager registered: chat_id={chat_id}, name={manager_name}")
    
    await message.answer(
        "👋 <b>Добро пожаловать в Менеджер Бот!</b>\n\n"
        f"✅ Вы зарегистрированы как менеджер\n"
        f"📬 Будете получать уведомления о новых заказах\n\n"
        "💡 Используйте кнопки в уведомлениях для:\n"
        "✅ Подтверждения заказа\n"
        "❌ Отклонения заказа\n"
        "💬 Связи с клиентом\n"
        "☎️ Звонка клиенту",
        parse_mode="HTML"
    )
    logger.info(f"Manager started: user_id={message.from_user.id}")


@router.message(Command("help"))
async def help_handler(message: Message):
    """Обработка /help"""
    help_text = (
        "<b>📖 СПРАВКА</b>\n\n"
        "<b>Кнопки уведомлений:</b>\n"
        "✅ <b>ПОДТВЕРДИТЬ</b> - Подтвердить заказ\n"
        "❌ <b>ОТКЛОНИТЬ</b> - Отклонить заказ\n"
        "💬 <b>СВЯЗАТЬСЯ</b> - Открыть чат с клиентом\n"
        "☎️ <b>ПОЗВОНИТЬ</b> - Получить номер клиента\n\n"
        "<b>Команды:</b>\n"
        "/start - Начало\n"
        "/help - Эта справка\n"
        "/orders - Список новых заказов\n"
        "/stats - Статистика"
    )
    await message.answer(help_text, parse_mode="HTML")


@router.message(Command("orders"))
async def orders_handler(message: Message):
    """Обработка /orders"""
    from bot.database import get_new_orders
    
    orders = get_new_orders()
    
    if not orders:
        await message.answer("✅ Новых заказов нет!")
        return
    
    text = f"📋 <b>НОВЫЕ ЗАКАЗЫ ({len(orders)})</b>\n\n"
    
    for order in orders[:10]:  # Показать первые 10
        text += (
            f"#{order['id']} | {order['customer_name']}\n"
            f"   Рацион: {order['ration']}, Дней: {order['days_count']}\n"
            f"   Сумма: {order['total']} €\n\n"
        )
    
    await message.answer(text, parse_mode="HTML")


@router.message(Command("stats"))
async def stats_handler(message: Message):
    """Обработка /stats"""
    from bot.database import get_new_orders, get_all_orders
    
    all_orders = get_all_orders()
    new_orders = get_new_orders()
    
    # Подсчет статусов
    statuses = {}
    for order in all_orders:
        status = order['status']
        statuses[status] = statuses.get(status, 0) + 1
    
    text = (
        "<b>📊 СТАТИСТИКА</b>\n\n"
        f"Всего заказов: {len(all_orders)}\n"
        f"Новых заказов: {len(new_orders)}\n\n"
        "<b>По статусам:</b>\n"
    )
    
    for status, count in statuses.items():
        emoji = "🆕" if status == "New" else "✅" if status == "Confirmed" else "❌" if status == "Rejected" else "📦"
        text += f"{emoji} {status}: {count}\n"
    
    # Общая сумма
    total_sum = sum(order['total'] or 0 for order in all_orders)
    text += f"\n💰 Общая сумма: {total_sum:.2f} €"
    
    await message.answer(text, parse_mode="HTML")


@router.message(Command("check"))
async def check_new_orders_handler(message: Message):
    """Проверить незатронутые заказы и отправить уведомления"""
    from bot.database import get_unnotified_orders, mark_order_notified
    from bot.manager_notifications import send_order_notification
    
    unnotified = get_unnotified_orders()
    
    if not unnotified:
        await message.answer("✅ Нет новых незатронутых заказов!")
        return
    
    await message.answer(
        f"🔍 Найдено {len(unnotified)} незатронутых заказов.\n"
        f"⏳ Отправляю уведомления...",
        parse_mode="HTML"
    )
    
    sent_count = 0
    for order in unnotified:
        try:
            # Пересоздать order_data из БД
            order_data = {
                'customer': {
                    'firstName': order['customer_name'].split()[0] if order['customer_name'] else '',
                    'lastName': ' '.join(order['customer_name'].split()[1:]) if order['customer_name'] else '',
                    'phone': order['phone'],
                    'address': order['address'],
                    'postcode': order['postcode'],
                    'building': order['building'],
                    'floor': order['floor'],
                    'apartment': order['apartment']
                },
                'ration': order['ration'],
                'days': order['dates'].split(', ') if order['dates'] else [],
                'payment': {'method': order['payment_method']},
                'total': order['total']
            }
            
            success = await send_order_notification(
                order_data=order_data,
                order_id=order['id'],
                manager_chat_id=message.chat.id,
                user_id=None
            )
            
            if success:
                mark_order_notified(order['id'])
                sent_count += 1
                await asyncio.sleep(0.5)  # Небольшая задержка между сообщениями
                
        except Exception as e:
            logger.error(f"Error sending notification for order {order['id']}: {e}")
    
    await message.answer(
        f"✅ Отправлено уведомлений: {sent_count}/{len(unnotified)}",
        parse_mode="HTML"
    )


@router.message()
async def default_handler(message: Message):
    """Обработка всех остальных сообщений"""
    logger.info(f"Message from manager: {message.text}")
    await message.answer(
        "ℹ️ Я менеджер бот. Отправляю вам уведомления о заказах.\n\n"
        "Используйте /help для справки."
    )


@router.callback_query(F.data.startswith("confirm_order:"))
async def confirm_order_handler(query: CallbackQuery):
    """
    Обработка кнопки 'Подтвердить заказ'
    """
    try:
        order_id = int(query.data.split(":")[1])
        
        # Обновить статус заказа в БД
        success = update_order_status_db(order_id, "Confirmed")
        
        if not success:
            await query.answer("❌ Ошибка при обновлении заказа", show_alert=True)
            return
        
        # Получить информацию о заказе
        order = get_order_by_id(order_id)
        if not order:
            await query.answer("❌ Заказ не найден", show_alert=True)
            return
        
        # Уведомить клиента
        user_id = int(query.message.text.split("Telegram ID: ")[1].split("\n")[0])
        
        await notify_client_order_confirmed(
            client_bot_token=BOT_TOKEN,
            user_id=user_id,
            order_id=order_id,
            ration=order['ration'],
            days=order['days_count']
        )
        
        # Обновить сообщение менеджеру
        await query.answer("✅ Заказ подтвержден!", show_alert=True)
        
        # Отредактировать сообщение (добавить статус)
        new_text = query.message.text + "\n\n" + "✅ <b>СТАТУС: ПОДТВЕРЖДЕН</b>"
        
        # Удалить кнопки
        await query.message.edit_text(
            text=new_text,
            parse_mode="HTML",
            reply_markup=None
        )
        
        logger.info(f"Order {order_id} confirmed by manager")
        
    except Exception as e:
        logger.error(f"Error confirming order: {e}")
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("reject_order:"))
async def reject_order_handler(query: CallbackQuery):
    """
    Обработка кнопки 'Отклонить заказ'
    """
    try:
        order_id = int(query.data.split(":")[1])
        
        # Обновить статус заказа в БД
        success = update_order_status_db(order_id, "Rejected")
        
        if not success:
            await query.answer("❌ Ошибка при отклонении заказа", show_alert=True)
            return
        
        # Получить информацию о заказе
        order = get_order_by_id(order_id)
        if not order:
            await query.answer("❌ Заказ не найден", show_alert=True)
            return
        
        # Извлечь user_id из сообщения
        try:
            text_lines = query.message.text.split("\n")
            user_id = None
            for line in text_lines:
                if "Telegram ID:" in line:
                    user_id = int(line.split("<code>")[1].split("</code>")[0])
                    break
            
            if user_id:
                # Уведомить клиента об отклонении
                await notify_client_order_rejected(
                    client_bot_token=BOT_TOKEN,
                    user_id=user_id,
                    order_id=order_id,
                    reason="Заказ не может быть выполнен в указанные сроки"
                )
        except Exception as e:
            logger.warning(f"Could not notify client about rejection: {e}")
        
        # Ответить менеджеру
        await query.answer("❌ Заказ отклонен", show_alert=True)
        
        # Отредактировать сообщение
        new_text = query.message.text + "\n\n" + "❌ <b>СТАТУС: ОТКЛОНЕН</b>"
        
        await query.message.edit_text(
            text=new_text,
            parse_mode="HTML",
            reply_markup=None
        )
        
        logger.info(f"Order {order_id} rejected by manager")
        
    except Exception as e:
        logger.error(f"Error rejecting order: {e}")
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("contact_client:"))
async def contact_client_handler(query: CallbackQuery):
    """
    Обработка кнопки 'Связаться с клиентом'
    Открывает чат с клиентом в Telegram
    """
    try:
        user_id = int(query.data.split(":")[1])
        
        # Создаем URL для перехода на профиль/чат с пользователем
        # Способ 1: Если нужно перейти в личное сообщение с пользователем
        # (требует чтобы пользователь был известен боту)
        
        # Показываем информацию
        text = (
            f"👤 <b>КОНТАКТ С КЛИЕНТОМ</b>\n\n"
            f"Telegram ID: <code>{user_id}</code>\n\n"
            f"Вы можете открыть чат с клиентом, используя одну из ссылок ниже:"
        )
        
        # Создать кнопки для связи
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Написать в Telegram",
                    url=f"tg://user?id={user_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад к заказу",
                    callback_data=f"back_to_order:{user_id}"
                )
            ]
        ])
        
        await query.answer()
        await query.message.edit_text(
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
        logger.info(f"Manager viewing client contact: user_id={user_id}")
        
    except Exception as e:
        logger.error(f"Error contacting client: {e}")
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("call_client:"))
async def call_client_handler(query: CallbackQuery):
    """
    Обработка кнопки 'Позвонить клиенту'
    Показывает номер телефона клиента
    """
    try:
        order_id = int(query.data.split(":")[1])
        
        # Получить информацию о заказе
        order = get_order_by_id(order_id)
        if not order:
            await query.answer("❌ Заказ не найден", show_alert=True)
            return
        
        phone = order['phone']
        customer_name = order['customer_name']
        
        text = (
            f"☎️ <b>КОНТАКТНАЯ ИНФОРМАЦИЯ</b>\n\n"
            f"👤 Клиент: <b>{customer_name}</b>\n"
            f"📱 Телефон: <code>{phone}</code>\n\n"
            f"Нажмите на номер чтобы позвонить"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="☎️ Позвонить",
                    url=f"tel:{phone.replace('+', '').replace(' ', '').replace('-', '')}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💬 Написать SMS",
                    url=f"sms:{phone.replace('+', '').replace(' ', '').replace('-', '')}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=f"back_to_order:{order_id}"
                )
            ]
        ])
        
        await query.answer()
        await query.message.edit_text(
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error getting phone: {e}")
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("back_to_order:"))
async def back_to_order_handler(query: CallbackQuery):
    """
    Возврат к сообщению заказа
    """
    try:
        # Просто удаляем текущее сообщение и возвращаем к заказу
        await query.message.delete()
        
    except TelegramBadRequest:
        # Если сообщение не существует, просто ответим
        await query.answer("📋 Заказ", show_alert=True)
    except Exception as e:
        logger.error(f"Error going back: {e}")


@router.callback_query(F.data == "list_new_orders")
async def list_new_orders_handler(query: CallbackQuery):
    """
    Показывает список всех новых заказов (для справки)
    """
    try:
        from bot.database import get_new_orders
        
        orders = get_new_orders()
        
        if not orders:
            text = "✅ <b>НОВЫХ ЗАКАЗОВ НЕ НАЙДЕНО</b>\n\nВсе заказы обработаны!"
            await query.message.edit_text(text=text, parse_mode="HTML")
            return
        
        text = f"📋 <b>НОВЫЕ ЗАКАЗЫ ({len(orders)})</b>\n\n"
        
        for order in orders:
            text += (
                f"#{order['id']} | {order['customer_name']}\n"
                f"   Рацион: {order['ration']}, Дней: {order['days_count']}\n"
                f"   Сумма: {order['total']} €\n"
                f"   Время: {order['created_at']}\n\n"
            )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Обновить",
                    callback_data="list_new_orders"
                )
            ]
        ])
        
        await query.message.edit_text(
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error listing orders: {e}")
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
