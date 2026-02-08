import os
import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ========== НАСТРОЙКИ ==========
TOKEN = os.environ.get("BOT_TOKEN")  # Берем из Railway
PORT = int(os.environ.get("PORT", 8080))

# ========== ЛОГИРОВАНИЕ ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== ГЛОБАЛЬНЫЕ ДАННЫЕ ==========
USER_MAX_WEIGHTS = {}

def get_user_max(user_id, exercise):
    """Получить максимум пользователя"""
    if user_id not in USER_MAX_WEIGHTS:
        USER_MAX_WEIGHTS[user_id] = {"жим": 117.5, "присед": 125}
    return USER_MAX_WEIGHTS[user_id].get(exercise, 100)

def set_user_max(user_id, exercise, value):
    """Установить максимум пользователя"""
    if user_id not in USER_MAX_WEIGHTS:
        USER_MAX_WEIGHTS[user_id] = {}
    USER_MAX_WEIGHTS[user_id][exercise] = value

# ========== ПАРСЕР ==========
def parse_workout_data(text):
    """Парсинг данных тренировки"""
    text = text.strip()
    parts = [p.strip() for p in text.split(';') if p.strip()]
    results = []
    
    for part in parts:
        part = re.sub(r'\s*-\s*', '-', part)
        nums = part.split('-')
        
        if len(nums) == 2:
            try:
                percent, reps = int(nums[0]), int(nums[1])
                results.append((percent, reps, 1))
            except:
                continue
        elif len(nums) == 3:
            try:
                percent, reps, sets = int(nums[0]), int(nums[1]), int(nums[2])
                results.append((percent, reps, sets))
            except:
                continue
    
    return results

# ========== КОМАНДА /START ==========
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏋️ ЖИМ", callback_data='exercise_жим')],
        [InlineKeyboardButton("🦵 ПРИСЕД", callback_data='exercise_присед')],
        [InlineKeyboardButton("📊 МАКСИМУМЫ", callback_data='show_max')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🏋️ БОТ ДЛЯ РАСЧЕТА ВЕСОВ\n\nВыберите упражнение:",
        reply_markup=reply_markup
    )

# ========== КОМАНДА /MAX ==========
async def max_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    жим_макс = get_user_max(user_id, "жим")
    присед_макс = get_user_max(user_id, "присед")
    
    await update.message.reply_text(
        f"🏋️ ВАШИ МАКСИМУМЫ:\n\n"
        f"• Жим: {жим_макс} кг\n"
        f"• Присед: {присед_макс} кг\n\n"
        f"Изменить можно через /start → МАКСИМУМЫ"
    )

# ========== ОБРАБОТКА КНОПОК ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    # ПОКАЗ МАКСИМУМОВ
    if data == 'show_max':
        жим_макс = get_user_max(user_id, "жим")
        присед_макс = get_user_max(user_id, "присед")
        
        max_text = (
            f"🏋️ ВАШИ МАКСИМУМЫ:\n\n"
            f"• Жим: {жим_макс} кг\n"
            f"• Присед: {присед_макс} кг\n\n"
            f"⚙️ Нажмите для изменения"
        )
        
        keyboard = [
            [InlineKeyboardButton("✏️ ИЗМЕНИТЬ ЖИМ", callback_data='change_жим')],
            [InlineKeyboardButton("✏️ ИЗМЕНИТЬ ПРИСЕД", callback_data='change_присед')],
            [InlineKeyboardButton("🔙 НАЗАД", callback_data='back_start')]
        ]
        
        await query.edit_message_text(
            text=max_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ИЗМЕНЕНИЕ МАКСИМУМА
    elif data.startswith('change_'):
        exercise = data.split('_')[1]
        current_max = get_user_max(user_id, exercise)
        
        context.user_data['changing_exercise'] = exercise
        context.user_data['awaiting_max_input'] = True
        
        await query.edit_message_text(
            f"📝 Изменение максимума для {exercise.upper()}\n\n"
            f"Текущий: {current_max} кг\n"
            f"Введите новый вес (например: 120 или 122.5):",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 ОТМЕНА", callback_data='back_max')]
            ])
        )
    
    # НАЗАД К МАКСИМУМАМ
    elif data == 'back_max':
        жим_макс = get_user_max(user_id, "жим")
        присед_макс = get_user_max(user_id, "присед")
        
        max_text = (
            f"🏋️ ВАШИ МАКСИМУМЫ:\n\n"
            f"• Жим: {жим_макс} кг\n"
            f"• Присед: {присед_макс} кг\n\n"
            f"⚙️ Нажмите для изменения"
        )
        
        keyboard = [
            [InlineKeyboardButton("✏️ ИЗМЕНИТЬ ЖИМ", callback_data='change_жим')],
            [InlineKeyboardButton("✏️ ИЗМЕНИТЬ ПРИСЕД", callback_data='change_присед')],
            [InlineKeyboardButton("🔙 НАЗАД К ВЫБОРУ", callback_data='back_start')]
        ]
        
        await query.edit_message_text(
            text=max_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # НАЗАД К СТАРТУ
    elif data == 'back_start':
        keyboard = [
            [InlineKeyboardButton("🏋️ ЖИМ", callback_data='exercise_жим')],
            [InlineKeyboardButton("🦵 ПРИСЕД", callback_data='exercise_присед')],
            [InlineKeyboardButton("📊 МАКСИМУМЫ", callback_data='show_max')]
        ]
        
        await query.edit_message_text(
            text="🏋️ БОТ ДЛЯ РАСЧЕТА ВЕСОВ\n\nВыберите упражнение:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ВЫБОР УПРАЖНЕНИЯ
    elif data.startswith('exercise_'):
        exercise = data.split('_')[1]
        context.user_data['current_exercise'] = exercise
        context.user_data['awaiting_data'] = True
        context.user_data['awaiting_max_input'] = False
        
        await query.edit_message_text(
            f"📝 Выбран: {exercise.upper()}\n\n"
            f"Введите данные (примеры):\n"
            f"• 50-3;60-3-3;85-3-5\n"
            f"• 50 3 60 3 3 85 3 5\n"
            f"• 50-3 60-3-3 85-3-5",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 ВЫБРАТЬ ДРУГОЕ", callback_data='back_start')]
            ])
        )

# ========== ОБРАБОТКА СООБЩЕНИЙ ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # ВВОД НОВОГО МАКСИМУМА
    if context.user_data.get('awaiting_max_input'):
        exercise = context.user_data.get('changing_exercise')
        
        try:
            new_max = float(text.replace(',', '.'))
            
            if not (1 <= new_max <= 300):
                await update.message.reply_text("❌ Вес должен быть от 1 до 300 кг!")
                return
            
            set_user_max(user_id, exercise, new_max)
            
            жим_макс = get_user_max(user_id, "жим")
            присед_макс = get_user_max(user_id, "присед")
            
            await update.message.reply_text(f"✅ Максимум для {exercise.upper()} изменен на {new_max} кг!")
            
            max_text = (
                f"🏋️ ОБНОВЛЕННЫЕ МАКСИМУМЫ:\n\n"
                f"• Жим: {жим_макс} кг\n"
                f"• Присед: {присед_макс} кг"
            )
            
            keyboard = [
                [InlineKeyboardButton("✏️ ИЗМЕНИТЬ ЕЩЁ", callback_data='show_max')],
                [InlineKeyboardButton("🔙 К ВЫБОРУ УПРАЖНЕНИЙ", callback_data='back_start')]
            ]
            
            await update.message.reply_text(
                text=max_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            context.user_data['awaiting_max_input'] = False
            
        except ValueError:
            await update.message.reply_text("❌ Неверный формат! Введите число (например: 120 или 122.5):")
    
    # ВВОД ДАННЫХ ДЛЯ РАСЧЕТА
    elif context.user_data.get('awaiting_data'):
        exercise = context.user_data.get('current_exercise')
        max_weight = get_user_max(user_id, exercise)
        
        workouts = parse_workout_data(text)
        
        if not workouts:
            await update.message.reply_text(
                "❌ Не понял формат. Пример: 50-3;60-3-3;85-3-5",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 ВЫБРАТЬ ДРУГОЕ", callback_data='back_start')]
                ])
            )
            return
        
        # ФОРМИРУЕМ ОТВЕТ
        try:
            # 1. ЗАГОЛОВОК
            await update.message.reply_text(f"🏋️ РАСЧЕТ ВЕСОВ\n📊 {exercise.upper()}")
            
            # 2. ОСНОВНЫЕ ЦИФРЫ
            result_text = ""
            details_text = f"🔍 ДЕТАЛИ ({exercise}):\n📊 Максимум: {max_weight} кг\n\n"
            
            for i, (percent, reps, sets) in enumerate(workouts, 1):
                exact = max_weight * (percent / 100)
                rounded = round(exact / 2.5) * 2.5
                
                if sets == 1:
                    result_text += f"{i}. {rounded} × {reps}\n"
                    details_text += f"{i}. {percent}% = {exact:.1f} кг → {rounded} кг ({reps})\n"
                else:
                    result_text += f"{i}. {rounded} × {reps} × {sets}\n"
                    details_text += f"{i}. {percent}% = {exact:.1f} кг → {rounded} кг ({reps}×{sets})\n"
            
            await update.message.reply_text(result_text.strip())
            await update.message.reply_text(details_text + f"\n⚙️ Округление до 2.5 кг")
            
            # 3. КНОПКИ ДЛЯ ПРОДОЛЖЕНИЯ
            keyboard = [
                [InlineKeyboardButton("🔄 НОВЫЙ РАСЧЁТ", callback_data='back_start')],
                [InlineKeyboardButton("📊 ИЗМЕНИТЬ МАКСИМУМЫ", callback_data='show_max')]
            ]
            
            await update.message.reply_text(
                "✅ Расчет завершен!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            context.user_data['awaiting_data'] = False
            
        except Exception as e:
            logger.error(f"Ошибка расчета: {e}")
            await update.message.reply_text("❌ Ошибка расчета. Попробуйте другой формат.")

# ========== ЗАПУСК БОТА ==========
def main():
    """Запуск бота на Railway"""
    logger.info("✅ Бот настроен и запускается...")
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("max", max_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # ЗАПУСК ДЛЯ RAILWAY
    # Railway сам задаст WEBHOOK_URL через переменные окружения
    webhook_url = f"https://{os.environ.get('RAILWAY_STATIC_URL', '')}/{TOKEN}"
    
    logger.info(f"🌐 Webhook URL: {webhook_url}")
    logger.info(f"🚀 Бот запускается на порту {PORT}")
    
    # Установка webhook
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=webhook_url,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()
