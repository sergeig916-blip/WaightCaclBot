import os
import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# ========== НАСТРОЙКИ ==========
TOKEN = os.environ.get("BOT_TOKEN", "8514815854:AAH2CVbpxaPTTNtcdHj8j9lcbYa2zgBoVn8")

# ========== ЛОГИРОВАНИЕ ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== ГЛОБАЛЬНЫЕ ДАННЫЕ ==========
USER_MAX_WEIGHTS = {}

def get_user_max(user_id, exercise):
    if user_id not in USER_MAX_WEIGHTS:
        USER_MAX_WEIGHTS[user_id] = {
            "жим": 117.5,
            "присед": 125,
            "присяд": 125
        }
    return USER_MAX_WEIGHTS[user_id].get(exercise, 100)

def set_user_max(user_id, exercise, value):
    if user_id not in USER_MAX_WEIGHTS:
        USER_MAX_WEIGHTS[user_id] = {}
    USER_MAX_WEIGHTS[user_id][exercise] = value
    if exercise == "присед":
        USER_MAX_WEIGHTS[user_id]["присяд"] = value

# ========== ПАРСЕР ==========
def parse_workout_data(text):
    text = text.strip()
    parts = [p.strip() for p in text.split(';') if p.strip()]
    results = []
    
    for part in parts:
        part = re.sub(r'\s*-\s*', '-', part)
        numbers = part.split('-')
        
        if len(numbers) == 2:
            try:
                percent = int(numbers[0])
                reps = int(numbers[1])
                results.append((percent, reps, 1))
            except:
                continue
        elif len(numbers) == 3:
            try:
                percent = int(numbers[0])
                reps = int(numbers[1])
                sets = int(numbers[2])
                results.append((percent, reps, sets))
            except:
                continue
    
    if not results:
        numbers = re.findall(r'\d+', text)
        numbers = [int(n) for n in numbers]
        
        i = 0
        while i < len(numbers):
            if i + 2 < len(numbers):
                percent, reps, sets = numbers[i], numbers[i+1], numbers[i+2]
                if 10 <= percent <= 120 and 1 <= reps <= 10:
                    results.append((percent, reps, sets))
                    i += 3
                else:
                    i += 1
            elif i + 1 < len(numbers):
                percent, reps = numbers[i], numbers[i+1]
                if 10 <= percent <= 120 and 1 <= reps <= 10:
                    results.append((percent, reps, 1))
                    i += 2
                else:
                    i += 1
            else:
                i += 1
    
    return results

# ========== КОМАНДА /START ==========
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
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
    
    if data == 'show_max':
        жим_макс = get_user_max(user_id, "жим")
        присед_макс = get_user_max(user_id, "присед")
        
        max_text = f"🏋️ ВАШИ МАКСИМУМЫ:\n\n• Жим: {жим_макс} кг\n• Присед: {присед_макс} кг\n\n⚙️ Нажмите для изменения"
        
        keyboard = [
            [InlineKeyboardButton("✏️ ИЗМЕНИТЬ ЖИМ", callback_data='change_жим')],
            [InlineKeyboardButton("✏️ ИЗМЕНИТЬ ПРИСЕД", callback_data='change_присед')],
            [InlineKeyboardButton("🔙 НАЗАД", callback_data='back_start')]
        ]
        
        await query.edit_message_text(text=max_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith('change_'):
        exercise = data.split('_')[1]
        current_max = get_user_max(user_id, exercise)
        
        context.user_data['changing_exercise'] = exercise
        context.user_data['awaiting_max_input'] = True
        
        await query.edit_message_text(
            f"📝 Изменение максимума для {exercise.upper()}\n\nТекущий: {current_max} кг\nВведите новый вес (например: 120 или 122.5):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ОТМЕНА", callback_data='back_max')]])
        )
    
    elif data == 'back_max':
        жим_макс = get_user_max(user_id, "жим")
        присед_макс = get_user_max(user_id, "присед")
        
        max_text = f"🏋️ ВАШИ МАКСИМУМЫ:\n\n• Жим: {жим_макс} кг\n• Присед: {присед_макс} кг\n\n⚙️ Нажмите для изменения"
        
        keyboard = [
            [InlineKeyboardButton("✏️ ИЗМЕНИТЬ ЖИМ", callback_data='change_жим')],
            [InlineKeyboardButton("✏️ ИЗМЕНИТЬ ПРИСЕД", callback_data='change_присед')],
            [InlineKeyboardButton("🔙 НАЗАД К ВЫБОРУ", callback_data='back_start')]
        ]
        
        await query.edit_message_text(text=max_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
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
    
    elif data.startswith('exercise_'):
        exercise = data.split('_')[1]
        context.user_data['current_exercise'] = exercise
        context.user_data['awaiting_data'] = True
        context.user_data['awaiting_max_input'] = False
        
        await query.edit_message_text(
            f"📝 Выбран: {exercise.upper()}\n\nВведите данные (примеры):\n• 50-3;60-3-3;85-3-5\n• 50 3 60 3 3 85 3 5\n• 50-3 60-3-3 85-3-5",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ВЫБРАТЬ ДРУГОЕ", callback_data='back_start')]])
        )

# ========== ОБРАБОТКА СООБЩЕНИЙ ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
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
            
            max_text = f"🏋️ ОБНОВЛЕННЫЕ МАКСИМУМЫ:\n\n• Жим: {жим_макс} кг\n• Присед: {присед_макс} кг"
            
            keyboard = [
                [InlineKeyboardButton("✏️ ИЗМЕНИТЬ ЕЩЁ", callback_data='show_max')],
                [InlineKeyboardButton("🔙 К ВЫБОРУ УПРАЖНЕНИЙ", callback_data='back_start')]
            ]
            
            await update.message.reply_text(text=max_text, reply_markup=InlineKeyboardMarkup(keyboard))
            
            context.user_data['awaiting_max_input'] = False
            
        except ValueError:
            await update.message.reply_text("❌ Неверный формат! Введите число (например: 120 или 122.5):")
        return
    
    if context.user_data.get('awaiting_data'):
        exercise = context.user_data.get('current_exercise')
        max_weight = get_user_max(user_id, exercise)
        
        workouts = parse_workout_data(text)
        
        if not workouts:
            await update.message.reply_text(
                "❌ Не понял формат. Пример: 50-3;60-3-3;85-3-5",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ВЫБРАТЬ ДРУГОЕ", callback_data='back_start')]])
            )
            return
        
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
            
            await update.message.reply_text("✅ Расчет завершен!", reply_markup=InlineKeyboardMarkup(keyboard))
            
            context.user_data['awaiting_data'] = False
            
        except Exception as e:
            logger.error(f"Ошибка расчета: {e}")
            await update.message.reply_text(
                "❌ Ошибка расчета. Попробуйте другой формат:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ВЫБРАТЬ ДРУГОЕ", callback_data='back_start')]])
            )

# ========== ОБРАБОТКА ОШИБОК ==========
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ошибок"""
    logger.error(f"Ошибка: {context.error}")
    if update.callback_query:
        await update.callback_query.answer("⚠️ Произошла ошибка. Попробуйте /start")

# ========== ЗАПУСК БОТА ==========
def main():
    """Запуск бота на Railway"""
    logger.info("🚀 Запуск бота для расчета весов...")
    
    try:
        # Создаем Application для версии 21.0
        application = Application.builder().token(TOKEN).build()
        
        # Регистрируем обработчики
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("max", max_command))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_error_handler(error_handler)
        
        logger.info("✅ Бот запущен в режиме polling!")
        logger.info("🤖 Бот готов к работе!")
        
        # ЗАПУСК В РЕЖИМЕ POLLING
        application.run_polling()
        
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        raise

if __name__ == "__main__":
    main()
