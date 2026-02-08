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
CALCULATION_HISTORY = {}

def get_user_max(user_id, exercise):
    if user_id not in USER_MAX_WEIGHTS:
        USER_MAX_WEIGHTS[user_id] = {
            "жим": 117.5,
            "присед": 125,
            "тяга": 150,
            "становая": 150
        }
    return USER_MAX_WEIGHTS[user_id].get(exercise, 100)

def set_user_max(user_id, exercise, value):
    if user_id not in USER_MAX_WEIGHTS:
        USER_MAX_WEIGHTS[user_id] = {}
    USER_MAX_WEIGHTS[user_id][exercise] = value
    if exercise == "тяга":
        USER_MAX_WEIGHTS[user_id]["становая"] = value

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
    keyboard = [
        [InlineKeyboardButton("🏋️ ЖИМ", callback_data='exercise_жим')],
        [InlineKeyboardButton("🦵 ПРИСЕД", callback_data='exercise_присед')],
        [InlineKeyboardButton("🏗️ ТЯГА", callback_data='exercise_тяга')],
        [InlineKeyboardButton("📊 МАКСИМУМЫ", callback_data='menu_max')]
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
    тяга_макс = get_user_max(user_id, "тяга")
    
    await update.message.reply_text(
        f"🏋️ ВАШИ МАКСИМУМЫ:\n\n"
        f"• Жим: {жим_макс} кг\n"
        f"• Присед: {присед_макс} кг\n"
        f"• Тяга: {тяга_макс} кг\n\n"
        f"Изменить можно через /start → МАКСИМУМЫ"
    )

# ========== ГЛАВНОЕ МЕНЮ ==========
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏋️ ЖИМ", callback_data='exercise_жим')],
        [InlineKeyboardButton("🦵 ПРИСЕД", callback_data='exercise_присед')],
        [InlineKeyboardButton("🏗️ ТЯГА", callback_data='exercise_тяга')],
        [InlineKeyboardButton("📊 МАКСИМУМЫ", callback_data='menu_max')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text="🏋️ БОТ ДЛЯ РАСЧЕТА ВЕСОВ\n\nВыберите упражнение:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "🏋️ БОТ ДЛЯ РАСЧЕТА ВЕСОВ\n\nВыберите упражнение:",
            reply_markup=reply_markup
        )

# ========== МЕНЮ МАКСИМУМОВ ==========
async def show_max_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    жим_макс = get_user_max(user_id, "жим")
    присед_макс = get_user_max(user_id, "присед")
    тяга_макс = get_user_max(user_id, "тяга")
    
    max_text = (
        f"🏋️ ВАШИ МАКСИМУМЫ:\n\n"
        f"• Жим: {жим_макс} кг\n"
        f"• Присед: {присед_макс} кг\n"
        f"• Тяга: {тяга_макс} кг"
    )
    
    keyboard = [
        [InlineKeyboardButton("✏️ ИЗМЕНИТЬ ЖИМ", callback_data='change_жим')],
        [InlineKeyboardButton("✏️ ИЗМЕНИТЬ ПРИСЕД", callback_data='change_присед')],
        [InlineKeyboardButton("✏️ ИЗМЕНИТЬ ТЯГУ", callback_data='change_тяга')],
        [InlineKeyboardButton("📖 ИНСТРУКЦИИ", callback_data='instructions')],
        [InlineKeyboardButton("🔙 НАЗАД", callback_data='back_main')]
    ]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=max_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            text=max_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ========== ИНСТРУКЦИИ ==========
async def show_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    instructions_text = (
        "📖 ИНСТРУКЦИИ ПО ФОРМАТАМ ВВОДА:\n\n"
        "📌 Форматы данных:\n"
        "• 50-3;60-3-3;85-3-5\n"
        "• 50 3 60 3 3 85 3 5\n"
        "• 50-3 60-3-3 85-3-5\n\n"
        "📌 Обозначения:\n"
        "• 50-3 = 50% на 3 раза\n"
        "• 60-3-3 = 60% на 3 раза × 3 подхода\n"
        "• Разделитель между упражнениями: точка с запятой (;)\n\n"
        "📌 Примеры:\n"
        "• Для одного подхода: 70-5\n"
        "• Для нескольких: 60-3-3;70-2-2;80-1\n"
        "• Смешанный: 50-5;60-3-3;70-2-2;85-1"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 НАЗАД К МАКСИМУМАМ", callback_data='menu_max')]
    ]
    
    await update.callback_query.edit_message_text(
        text=instructions_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== ОБРАБОТКА КНОПОК ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    # ГЛАВНОЕ МЕНЮ
    if data == 'back_main':
        await show_main_menu(update, context)
    
    # МЕНЮ МАКСИМУМОВ
    elif data == 'menu_max':
        await show_max_menu(update, context)
    
    # ИНСТРУКЦИИ
    elif data == 'instructions':
        await show_instructions(update, context)
    
    # ИЗМЕНИТЬ МАКСИМУМ
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
                [InlineKeyboardButton("🔙 ОТМЕНА", callback_data='menu_max')]
            ])
        )
    
    # ВЫБОР УПРАЖНЕНИЯ ДЛЯ РАСЧЕТА
    elif data.startswith('exercise_'):
        exercise = data.split('_')[1]
        context.user_data['current_exercise'] = exercise
        context.user_data['awaiting_data'] = True
        context.user_data['awaiting_max_input'] = False
        
        exercise_name = ""
        if exercise == "жим":
            exercise_name = "ЖИМ ЛЕЖА"
        elif exercise == "присед":
            exercise_name = "ПРИСЕДАНИЕ"
        elif exercise == "тяга":
            exercise_name = "СТАНОВАЯ ТЯГА"
        
        await query.edit_message_text(
            f"📝 Выбран: {exercise_name}"
        )
    
    # ДЕТАЛИ РАСЧЕТА (ДОБАВЛЕН ОТДЕЛЬНЫЙ ОБРАБОТЧИК)
    elif data == 'show_details':
        await show_calculation_details(update, context)

# ========== ПОКАЗАТЬ ДЕТАЛИ РАСЧЕТА ==========
async def show_calculation_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать детали расчета"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id not in CALCULATION_HISTORY or 'last_calculation' not in CALCULATION_HISTORY[user_id]:
        await query.edit_message_text(
            text="❌ Нет данных о последнем расчете. Сначала сделайте расчет.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 НАЗАД", callback_data='back_main')]
            ])
        )
        return
    
    calc_data = CALCULATION_HISTORY[user_id]['last_calculation']
    exercise = calc_data['exercise']
    max_weight = calc_data['max_weight']
    workouts = calc_data['workouts']
    
    exercise_name = ""
    if exercise == "жим":
        exercise_name = "ЖИМ ЛЕЖА"
    elif exercise == "присед":
        exercise_name = "ПРИСЕДАНИЕ"
    elif exercise == "тяга":
        exercise_name = "СТАНОВАЯ ТЯГА"
    
    details_text = f"🔍 {exercise_name} - ДЕТАЛИ:\n📊 Максимум: {max_weight} кг\n\n"
    
    for i, (percent, reps, sets) in enumerate(workouts, 1):
        exact = max_weight * (percent / 100)
        rounded = round(exact / 2.5) * 2.5
        
        if sets == 1:
            details_text += f"{i}. {percent}% = {exact:.1f} кг → {rounded} кг ({reps} раз)\n"
        else:
            details_text += f"{i}. {percent}% = {exact:.1f} кг → {rounded} кг ({reps}×{sets})\n"
    
    details_text += f"\n⚙️ Округление до 2.5 кг"
    
    keyboard = [
        [InlineKeyboardButton("🔄 НОВЫЙ РАСЧЁТ", callback_data='back_main')],
        [InlineKeyboardButton("📊 МАКСИМУМЫ", callback_data='menu_max')]
    ]
    
    await query.edit_message_text(
        text=details_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== ОБРАБОТКА СООБЩЕНИЙ ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # ЕСЛИ ВВОДИМ НОВЫЙ МАКСИМУМ
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
            тяга_макс = get_user_max(user_id, "тяга")
            
            await update.message.reply_text(f"✅ Максимум для {exercise.upper()} изменен на {new_max} кг!")
            
            max_text = (
                f"🏋️ ОБНОВЛЕННЫЕ МАКСИМУМЫ:\n\n"
                f"• Жим: {жим_макс} кг\n"
                f"• Присед: {присед_макс} кг\n"
                f"• Тяга: {тяга_макс} кг"
            )
            
            keyboard = [
                [InlineKeyboardButton("✏️ ИЗМЕНИТЬ ЕЩЁ", callback_data='menu_max')],
                [InlineKeyboardButton("🔙 К ВЫБОРУ УПРАЖНЕНИЙ", callback_data='back_main')]
            ]
            
            await update.message.reply_text(
                text=max_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            context.user_data['awaiting_max_input'] = False
            
        except ValueError:
            await update.message.reply_text("❌ Неверный формат! Введите число (например: 120 или 122.5):")
        return
    
    # ЕСЛИ ВВОДИМ ДАННЫЕ ДЛЯ РАСЧЕТА
    if context.user_data.get('awaiting_data'):
        exercise = context.user_data.get('current_exercise')
        max_weight = get_user_max(user_id, exercise)
        
        workouts = parse_workout_data(text)
        
        if not workouts:
            await update.message.reply_text(
                "❌ Не понял формат. Используйте /start → МАКСИМУМЫ → ИНСТРУКЦИИ",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 ВЫБРАТЬ ДРУГОЕ", callback_data='back_main')]
                ])
            )
            return
        
        try:
            # Сохраняем данные расчета для кнопки "Детали"
            if user_id not in CALCULATION_HISTORY:
                CALCULATION_HISTORY[user_id] = {}
            
            CALCULATION_HISTORY[user_id]['last_calculation'] = {
                'exercise': exercise,
                'max_weight': max_weight,
                'workouts': workouts
            }
            
            # 1. НАЗВАНИЕ УПРАЖНЕНИЯ (первая строка)
            exercise_name = ""
            if exercise == "жим":
                exercise_name = "🏋️ ЖИМ ЛЕЖА"
            elif exercise == "присед":
                exercise_name = "🦵 ПРИСЕДАНИЕ"
            elif exercise == "тяга":
                exercise_name = "🏗️ СТАНОВАЯ ТЯГА"
            
            # 2. БЛОК С ВЕСАМИ В ОДНОЙ СТРОКЕ (вторая строка)
            result_parts = []
            for percent, reps, sets in workouts:
                exact = max_weight * (percent / 100)
                rounded = round(exact / 2.5) * 2.5
                
                if sets == 1:
                    result_parts.append(f"{rounded}×{reps}")
                else:
                    result_parts.append(f"{rounded} {reps}х{sets}")
            
            result_line = "; ".join(result_parts)
            
            # Отправляем две строки
            await update.message.reply_text(exercise_name)
            await update.message.reply_text(result_line)
            
            # 3. КНОПКИ ДЛЯ ПРОДОЛЖЕНИЯ
            keyboard = [
                [InlineKeyboardButton("🔄 НОВЫЙ РАСЧЁТ", callback_data='back_main')],
                [InlineKeyboardButton("🔍 ДЕТАЛИ/ОКРУГЛЕНИЯ", callback_data='show_details')],
                [InlineKeyboardButton("📊 ИЗМЕНИТЬ МАКСИМУМЫ", callback_data='menu_max')]
            ]
            
            await update.message.reply_text(
                "✅ Расчет завершен!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            context.user_data['awaiting_data'] = False
            
        except Exception as e:
            logger.error(f"Ошибка расчета: {e}")
            await update.message.reply_text(
                "❌ Ошибка расчета. Проверьте формат данных.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 ВЫБРАТЬ ДРУГОЕ", callback_data='back_main')]
                ])
            )

# ========== ОБРАБОТКА ОШИБОК ==========
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}")
    if update.callback_query:
        await update.callback_query.answer("⚠️ Произошла ошибка. Попробуйте /start")

# ========== ЗАПУСК БОТА ==========
def main():
    logger.info("🚀 Запуск бота для расчета весов...")
    
    try:
        application = Application.builder().token(TOKEN).build()
        
        # Регистрируем обработчики В ПРАВИЛЬНОМ ПОРЯДКЕ
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("max", max_command))
        
        # Обработка кнопок
        application.add_handler(CallbackQueryHandler(button_handler))
        
        # Обработка ввода данных
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Обработчик ошибок
        application.add_error_handler(error_handler)
        
        logger.info("✅ Бот запущен в режиме polling!")
        logger.info("🤖 Бот готов к работе!")
        
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            poll_interval=1.0
        )
        
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        raise

if __name__ == "__main__":
    main()
