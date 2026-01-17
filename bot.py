# ==================== ИМПОРТЫ ====================
import logging
import os
import asyncio
import json
from datetime import datetime, date
from typing import List, Dict, Set
from dataclasses import dataclass
import pickle

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
    JobQueue
)

# ==================== НАСТРОЙКИ БОТА ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8228635094:AAG00B2fq13G-kDGCkXO6O7wZydDQqyZpmk")

# Каналы для проверки - ТЕПЕРЬ 6 КАНАЛОВ
CHANNELS_TO_CHECK = [
    "@your_channel_1",    # 1
    "@your_channel_2",    # 2  
    "@pepeNFTchanne",     # 3
    "@your_channel_4",    # 4
    "@your_channel_5",    # 5
    "@your_channel_6",    # 6 - НОВЫЙ КАНАЛ! ⭐
]

# Файлы для хранения данных
DATA_FILE = "santa_bot_data.pkl"
STATS_FILE = "bot_stats.json"

# Интервал проверки подписок
CHECK_INTERVAL = 60

# ==================== ПРОСТАЯ АНАЛИТИКА ====================
def load_stats():
    """Загружает статистику из файла"""
    try:
        with open(STATS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {
            "total_users": 0,
            "total_starts": 0,
            "total_subscriptions": 0,
            "successful_subs": 0,
            "failed_subs": 0,
            "today_starts": 0,
            "today_subs": 0,
            "last_reset": str(date.today()),
            "user_ids": []
        }

def save_stats(stats):
    """Сохраняет статистику в файл"""
    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

def update_stats(event_type, user_id=None):
    """Обновляет статистику"""
    stats = load_stats()
    today = str(date.today())
    
    # Сбрасываем дневную статистику если новый день
    if stats["last_reset"] != today:
        stats["today_starts"] = 0
        stats["today_subs"] = 0
        stats["last_reset"] = today
    
    # Обрабатываем события
    if event_type == "start":
        stats["total_starts"] += 1
        stats["today_starts"] += 1
        
        # Уникальные пользователи
        if user_id and str(user_id) not in stats["user_ids"]:
            stats["user_ids"].append(str(user_id))
            stats["total_users"] = len(stats["user_ids"])
    
    elif event_type == "subscription_success":
        stats["total_subscriptions"] += 1
        stats["successful_subs"] += 1
        stats["today_subs"] += 1
    
    elif event_type == "subscription_failed":
        stats["total_subscriptions"] += 1
        stats["failed_subs"] += 1
    
    save_stats(stats)

# ==================== ТЕКСТОВЫЕ СООБЩЕНИЯ ====================
WELCOME_MESSAGE = """🎅 *Здравствуй, путник!*

Ты проделал долгий путь через заснеженные леса. Дедушка Мороз уже запряг оленей, но метель замела все тропинки к подаркам.

❄️ *Готов ли ты пройти проверку и забрать свой праздничный сюрприз?*"""

GIFT_PREPARING = """🎁 *Ваш подарок готовится...*

⏳ *Пожалуйста, подождите немного...*"""

GIFT_READY = """🎄 *Дед Мороз выбрал для вас самый лучший подарок!*

✨ *Но чтобы олени смогли доставить его, нужна помощь спонсоров...*

📜 *Подпишитесь на наших спонсоров:*

{channels_list}

🎅 *После подписки нажмите кнопку "✅ Проверить подписки" ниже, чтобы Дедушка Мороз отправил вам подарок!*"""

CHECKING_MESSAGE = """🔍 *Дедушка Мороз проверяет ваши подписки...*

🎄 *Эльфы уже упаковывают ваш подарок!*"""

SUCCESS_MESSAGE = """🎉 *ПОЗДРАВЛЯЕМ!*

✅ *Вы успешно подписаны на всех спонсоров!*

🎁 *Дед Мороз только что отправил ваш подарок!*

⏰ *Ваш подарок будет доставлен в течение 24 часов*
👨‍💼 *С вами свяжется наш менеджер для уточнения деталей*

✨ *Счастливого праздника и волшебного настроения!*

🎅 *С любовью, команда Деда Мороза*"""

FAIL_MESSAGE = """❌ *Ой-ой-ой!*

Вы не подписаны на следующих спонсоров:

{not_subscribed_list}

🎅 *Дедушка Мороз не может отправить подарок без поддержки спонсоров!*

👇 *Подпишитесь и проверьте снова:*

{channels_list}"""

UNSUBSCRIBE_NOTIFICATION = """⚠️ *ВНИМАНИЕ!*

Вы отписались от спонсора: *{channel}*

⛄ *Дед Мороз очень расстроен...*

🎁 *Ваш подарок приостановлен!*

Чтобы снова получить подарок:
1. Подпишитесь обратно на спонсора
2. Используйте команду /start"""

RESUBSCRIBE_NOTIFICATION = """✅ *Подписка восстановлена!*

Спасибо что вернулись к спонсору: @pepeNFTchanne

⏰ Время: {timestamp}

🎄 *Теперь Дед Мороз снова может отправлять вам подарки!*"""

HELP_MESSAGE = """🦌 *Помощь по боту Деда Мороза*

Это волшебный бот для получения праздничных подарков!

*Как получить подарок:*
1. Нажмите /start
2. Нажмите "🎁 Получить заветный подарок"
3. Подпишитесь на всех спонсоров (6 каналов)  ⭐ ТЕПЕРЬ 6!
4. Проверьте подписки
5. Получите подарок в течение 24 часов!

*Важно:*
• Не отписывайтесь от спонсоров
• Подписки проверяются автоматически
• При отписке подарок приостанавливается
• Подарок доставляется в течение 24 часов
• С вами свяжется менеджер для уточнения деталей

*Команды:*
/start - начать получение подарка
/status - статус ваших подписок
/stats - статистика бота (только для админа)
/help - эта справка"""

STATUS_MESSAGE = """📊 *Ваш статус у Деда Мороза*

{status_list}

⏰ Последняя проверка: {last_check}

{notification_status}"""

UNKNOWN_MESSAGE = """🎅 *Ой-ой-ой!*

Я, Дед Мороз, понимаю только специальные команды!

Попробуй:
• /start - получить подарок
• /status - статус ваших подписок
• /stats - статистика (админ)
• /help - помощь от эльфов"""

# ==================== КЛАССЫ ====================
@dataclass
class Channel:
    username: str
    invite_link: str = ""
    
    def __post_init__(self):
        if self.username.startswith('@') and not self.invite_link:
            self.invite_link = f"https://t.me/{self.username[1:]}"

class UserSubscription:
    """Хранит информацию о подписках пользователя"""
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.subscribed_channels: Set[str] = set()
        self.last_check: datetime = datetime.now()
        self.previously_unsubscribed: Set[str] = set()
        self.notified_unsubscribes: Set[str] = set()
        self.gift_received: bool = False
        
    def update_subscriptions(self, current_subs: List[str]):
        """Обновляет подписки и возвращает изменения"""
        previous_subs = self.subscribed_channels.copy()
        current_set = set(current_subs)
        
        unsubscribed = previous_subs - current_set
        resubscribed = current_set - previous_subs
        
        self.subscribed_channels = current_set
        self.last_check = datetime.now()
        
        for channel in unsubscribed:
            self.previously_unsubscribed.add(channel)
        
        return unsubscribed, resubscribed
    
    def is_resubscription(self, channel: str) -> bool:
        """Проверяет, является ли подписка повторной (после отписки)"""
        return channel in self.previously_unsubscribed
    
    def add_notified_unsubscribe(self, channel: str):
        """Добавляет канал в список уведомленных отписок"""
        self.notified_unsubscribes.add(channel)
    
    def remove_notified_unsubscribe(self, channel: str):
        """Удаляет канал из списка уведомленных отписок"""
        self.notified_unsubscribes.discard(channel)
        self.previously_unsubscribed.discard(channel)

# ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ====================
logger = logging.getLogger(__name__)
user_data: Dict[int, UserSubscription] = {}

# ==================== РАБОТА С ДАННЫМИ ====================
def load_data():
    """Загружает данные пользователей из файла"""
    global user_data
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'rb') as f:
                user_data = pickle.load(f)
            logger.info(f"Загружены данные {len(user_data)} пользователей")
    except Exception as e:
        logger.error(f"Ошибка загрузки данных: {e}")
        user_data = {}

def save_data():
    """Сохраняет данные пользователей в файл"""
    try:
        with open(DATA_FILE, 'wb') as f:
            pickle.dump(user_data, f)
        logger.info(f"Сохранены данные {len(user_data)} пользователей")
    except Exception as e:
        logger.error(f"Ошибка сохранения данных: {e}")

def get_or_create_user(user_id: int) -> UserSubscription:
    """Получает или создает объект пользователя"""
    if user_id not in user_data:
        user_data[user_id] = UserSubscription(user_id)
    return user_data[user_id]

def format_channels_list(channels: List[str]) -> str:
    """Форматирует список каналов в текст со ссылками и смайлами ✨"""
    channels_text = ""
    for i, channel in enumerate(channels, 1):
        if channel.startswith('@'):
            channels_text += f"{i}. ✨ [{channel}](https://t.me/{channel[1:]}) ✨\n"
        else:
            channels_text += f"{i}. ✨ {channel} ✨\n"
    return channels_text

# ==================== ФУНКЦИИ БОТА ====================
def setup_logging():
    """Настройка логирования"""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        handlers=[
            logging.FileHandler('santa_bot.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - приветственное сообщение с аналитикой"""
    user = update.effective_user
    
    # Собираем статистику
    update_stats("start", user.id)
    
    # Создаем кнопку для получения подарка
    keyboard = [[
        InlineKeyboardButton("🎁 Получить заветный подарок", callback_data="get_gift")
    ]]
    
    markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем приветственное сообщение С КНОПКОЙ
    await update.message.reply_text(
        WELCOME_MESSAGE,
        reply_markup=markup,
        parse_mode='Markdown'
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats для администратора"""
    
    # ⚠️ ЗАМЕНИТЕ НА ВАШ ID TELEGRAM!
    ADMIN_ID = 6566770852  # Получите через @userinfobot
    
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Только для админа!")
        return
    
    stats = load_stats()
    
    message = f"""📊 *СТАТИСТИКА БОТА*

👥 *Пользователи:*
• Всего уникальных: {stats['total_users']}
• Запусков бота: {stats['total_starts']}
• Сегодня: {stats['today_starts']}

🎁 *Подписки:*
• Всего проверок: {stats['total_subscriptions']}
• ✅ Успешных: {stats['successful_subs']}
• ❌ Неудачных: {stats['failed_subs']}
• Сегодня успешных: {stats['today_subs']}

📅 *Сегодня:* {stats['last_reset']}
⏰ *Отчет создан:* {datetime.now().strftime('%H:%M %d.%m.%Y')}"""
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий кнопок"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "get_gift":
        # Удаляем сообщение с кнопкой
        try:
            await query.message.delete()
        except Exception as e:
            logger.error(f"Не удалось удалить сообщение: {e}")
        
        # Показываем подготовку подарка
        await show_gift_preparing(query.message)
        
    elif query.data == "check_subs":
        await verify_subscriptions(query, context)

async def show_gift_preparing(message):
    """Показывает сообщение о подготовке подарка"""
    # Отправляем сообщение о подготовке
    msg = await message.reply_text(
        GIFT_PREPARING,
        parse_mode='Markdown'
    )
    
    # Ждем 3 секунды
    await asyncio.sleep(3)
    
    # Удаляем сообщение о подготовке
    try:
        await msg.delete()
    except Exception as e:
        logger.error(f"Не удалось удалить сообщение о подготовке: {e}")
    
    # Показываем сообщение о спонсорах
    await show_sponsors_message(message)

async def show_sponsors_message(message):
    """Показывает сообщение со спонсорами"""
    if not CHANNELS_TO_CHECK:
        await message.reply_text("❌ Список спонсоров не настроен")
        return
    
    # Форматируем список каналов
    channels_list = format_channels_list(CHANNELS_TO_CHECK)
    
    # Создаем ТОЛЬКО кнопку проверки подписок
    keyboard = [[
        InlineKeyboardButton("✅ Проверить подписки", callback_data="check_subs")
    ]]
    
    markup = InlineKeyboardMarkup(keyboard)
    
    await message.reply_text(
        GIFT_READY.format(channels_list=channels_list),
        reply_markup=markup,
        parse_mode='Markdown',
        disable_web_page_preview=True
    )

async def verify_subscriptions(query, context):
    """Проверка подписок пользователя с аналитикой"""
    user = query.from_user
    
    # Редактируем текущее сообщение на проверку
    await query.edit_message_text(
        CHECKING_MESSAGE,
        parse_mode='Markdown'
    )
    
    # Проверяем текущие подписки
    current_subs = []
    not_subscribed = []
    
    for channel in CHANNELS_TO_CHECK:
        try:
            member = await context.bot.get_chat_member(
                chat_id=channel,
                user_id=user.id
            )
            
            if member.status in ['member', 'administrator', 'creator']:
                current_subs.append(channel)
            else:
                not_subscribed.append(channel)
                
        except Exception as e:
            logger.error(f"Ошибка проверки {channel}: {e}")
            not_subscribed.append(channel)
    
    # Обновляем данные пользователя
    user_sub = get_or_create_user(user.id)
    unsubscribed, resubscribed = user_sub.update_subscriptions(current_subs)
    
    # Отправляем уведомления об изменениях
    await send_subscription_notifications(
        context, user.id, user.first_name, unsubscribed, resubscribed, user_sub
    )
    
    # Сохраняем данные
    save_data()
    
    # Собираем статистику
    if not not_subscribed:
        # УСПЕХ
        update_stats("subscription_success")
        user_sub.gift_received = True
        await query.edit_message_text(
            SUCCESS_MESSAGE,
            parse_mode='Markdown'
        )
    else:
        # НЕУДАЧА
        update_stats("subscription_failed")
        await show_failed_subscriptions(query, not_subscribed)

async def send_subscription_notifications(context, user_id, user_name, unsubscribed, resubscribed, user_sub):
    """Отправляет уведомления об изменениях подписок"""
    timestamp = datetime.now().strftime("%H:%M:%S %d.%m.%Y")
    
    # Уведомления об отписке
    for channel in unsubscribed:
        if channel not in user_sub.notified_unsubscribes:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=UNSUBSCRIBE_NOTIFICATION.format(
                        channel=channel,
                        timestamp=timestamp
                    ),
                    parse_mode='Markdown'
                )
                user_sub.add_notified_unsubscribe(channel)
                logger.info(f"Отправлено уведомление об отписке {user_id} от {channel}")
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления об отписке: {e}")
    
    # Уведомления о повторной подписке (ТОЛЬКО если была отписка!)
    for channel in resubscribed:
        if user_sub.is_resubscription(channel) or channel in user_sub.notified_unsubscribes:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=RESUBSCRIBE_NOTIFICATION.format(timestamp=timestamp),
                    parse_mode='Markdown'
                )
                user_sub.remove_notified_unsubscribe(channel)
                logger.info(f"Отправлено уведомление о восстановлении подписки {user_id} на {channel}")
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления о восстановлении: {e}")

async def show_failed_subscriptions(query, not_subscribed):
    """Показывает неподписанные каналы"""
    # Форматируем список всех каналов
    all_channels_list = format_channels_list(CHANNELS_TO_CHECK)
    
    # Форматируем список неподписанных каналов
    not_subscribed_list = "\n".join([f"• {ch}" for ch in not_subscribed])
    
    # Создаем ТОЛЬКО кнопку проверки подписок
    keyboard = [[
        InlineKeyboardButton("🔄 Проверить снова", callback_data="check_subs")
    ]]
    
    markup = InlineKeyboardMarkup(keyboard)
    
    fail_msg = FAIL_MESSAGE.format(
        not_subscribed_list=not_subscribed_list,
        channels_list=all_channels_list
    )
    
    await query.edit_message_text(
        fail_msg,
        reply_markup=markup,
        parse_mode='Markdown',
        disable_web_page_preview=True
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /status"""
    user = update.effective_user
    user_sub = get_or_create_user(user.id)
    
    status_lines = []
    for channel in CHANNELS_TO_CHECK:
        if channel in user_sub.subscribed_channels:
            status_lines.append(f"✅ {channel}")
        else:
            status_lines.append(f"❌ {channel}")
    
    status_list = "\n".join(status_lines)
    
    if user_sub.notified_unsubscribes:
        notification_status = "⚠️ *У вас есть непрочитанные уведомления от Деда Мороза!*"
    else:
        notification_status = "📭 Нет непрочитанных уведомлений"
    
    gift_status = "🎁 Подарок получен! (доставка в течение 24 часов)" if user_sub.gift_received else "🎁 Подарок ожидает"
    
    message = f"""📊 *Ваш статус у Деда Мороза*

{status_list}

{gift_status}
⏰ Последняя проверка: {user_sub.last_check.strftime("%H:%M:%S %d.%m.%Y")}

{notification_status}"""
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    await update.message.reply_text(HELP_MESSAGE, parse_mode='Markdown')

async def check_all_subscriptions(context: ContextTypes.DEFAULT_TYPE):
    """Периодическая проверка всех пользователей"""
    logger.info("🎅 Дед Мороз проверяет подписки...")
    
    for user_id, user_sub in list(user_data.items()):
        try:
            current_subs = []
            
            for channel in CHANNELS_TO_CHECK:
                try:
                    member = await context.bot.get_chat_member(
                        chat_id=channel,
                        user_id=user_id
                    )
                    
                    if member.status in ['member', 'administrator', 'creator']:
                        current_subs.append(channel)
                        
                except Exception as e:
                    logger.error(f"Ошибка проверки {channel} для {user_id}: {e}")
            
            unsubscribed, resubscribed = user_sub.update_subscriptions(current_subs)
            
            if unsubscribed or resubscribed:
                try:
                    user = await context.bot.get_chat(user_id)
                    user_name = user.first_name if user.first_name else "Путник"
                except:
                    user_name = "Путник"
                
                await send_subscription_notifications(
                    context, user_id, user_name, unsubscribed, resubscribed, user_sub
                )
                
        except Exception as e:
            logger.error(f"Ошибка проверки пользователя {user_id}: {e}")
    
    save_data()
    logger.info(f"🎄 Проверено {len(user_data)} путников")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка обычных сообщений"""
    await update.message.reply_text(UNKNOWN_MESSAGE, parse_mode='Markdown')

# ==================== ЗАПУСК БОТА ====================
def main():
    """Основная функция запуска"""
    setup_logging()
    
    print("=" * 50)
    print("🎅 ЗАПУСК БОТА ДЕДА МОРОЗА 🎄")
    print("⭐ ТЕПЕРЬ С 6 КАНАЛАМИ ДЛЯ ПОДПИСКИ!")
    print("=" * 50)
    
    load_data()
    
    # Загружаем и показываем статистику
    stats = load_stats()
    print(f"📊 Статистика: {stats['total_users']} пользователей, {stats['successful_subs']} успешных подписок")
    print(f"📺 Каналов для подписки: {len(CHANNELS_TO_CHECK)}")
    print("=" * 50)
    
    if "ВАШ_НОВЫЙ_ТОКЕН_ЗДЕСЬ" in BOT_TOKEN:
        print("❌ ОШИБКА: Токен бота не настроен!")
        print("\n📝 Как получить токен:")
        print("1. Откройте @BotFather в Telegram")
        print("2. Отправьте /newbot")
        print("3. Следуйте инструкциям")
        print("4. Скопируйте токен и вставьте в код")
        print("=" * 50)
        return
    
    print(f"🎄 Спонсоров: {len(CHANNELS_TO_CHECK)}")
    print("📋 Список каналов для проверки:")
    for i, channel in enumerate(CHANNELS_TO_CHECK, 1):
        print(f"  {i}. {channel}")
    print(f"👥 Путников в книге Деда Мороза: {len(user_data)}")
    print(f"📊 Уникальных пользователей: {stats['total_users']}")
    print(f"✅ Успешных подписок: {stats['successful_subs']}")
    print(f"⏰ Интервал проверки: {CHECK_INTERVAL} секунд")
    print("=" * 50)
    
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        job_queue = application.job_queue
        if job_queue:
            job_queue.run_repeating(
                check_all_subscriptions,
                interval=CHECK_INTERVAL,
                first=10
            )
            print("✅ Периодическая проверка настроена")
        
        # Регистрация команд
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("help", help_command))
        
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print("✅ Бот Деда Мороза готов к работе!")
        print("📊 Команда /stats доступна для админа")
        print("🚀 Запускаю волшебство...")
        print("=" * 50)
        print("📱 Идите в Telegram и найдите Деда Мороза")
        print("👉 Используйте команду /start для получения подарка")
        print("=" * 50)
        print("🎁 Нажмите кнопку 'Получить заветный подарок' для продолжения")
        print("⭐ Теперь нужно подписаться на 6 каналов")
        print("=" * 50)
        print("⏰ Подарок доставляется в течение 24 часов")
        print("👨‍💼 После успешной проверки с вами свяжется менеджер")
        print("=" * 50)
        print("🛑 Для остановки нажмите Ctrl+C")
        print("=" * 50)
        
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except Exception as e:
        print(f"💥 Ошибка запуска: {e}")
        print("=" * 50)
        logger.error(f"Ошибка запуска бота: {e}")
    finally:
        save_data()

if __name__ == '__main__':
    main()
