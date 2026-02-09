import os
import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
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
    """Получить максимум пользователя или значение по умолчанию"""
    if user_id not in USER_MAX_WEIGHTS:
        USER_MAX_WEIGHTS[user_id] = {
            "жим": 117.5,
            "присед": 125,
            "тяга": 150,
            "становая": 150
        }
    return USER_MAX_WEIGHTS[user_id].get(exercise, 100)

def set_user_max(user_id, exercise, value):
    """Установить максимум пользователя"""
    if user_id not in USER_MAX_WEIGHTS:
        USER_MAX_WEIGHTS[user_id] = {}
    USER_MAX_WEIGHTS[user_id][exercise] = value
    if exercise == "тяга":
        USER_MAX_WEIGHTS[user_id]["становая"] = value

# ========== ПОСТОЯННОЕ МЕНЮ ==========
def get_main_keyboard():
    """Создает постоянное меню внизу экрана"""
    keyboard = [
        [KeyboardButton("🏋️ НАЧАТЬ РАСЧЁТ"), KeyboardButton("📊 МАКСИМУМЫ")],
        [KeyboardButton("❓ ПОМОЩЬ"), KeyboardButton("ℹ️ О БОТЕ")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

def get_exercises_keyboard():
    """Клавиатура для выбора упражнений"""
    keyboard = [
        [InlineKeyboardButton("🏋️ ЖИМ", callback_data='exercise_жим')],
        [InlineKeyboardButton("🦵 ПРИСЕД", callback_data='exercise_присед')],
        [InlineKeyboardButton("🏗️ ТЯГА", callback_data='exercise_тяга')],
        [InlineKeyboardButton("🔙 НАЗАД", callback_data='back_to_main')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_max_menu_keyboard():
    """Меню для максимумов"""
    keyboard = [
        [InlineKeyboardButton("✏️ ИЗМЕНИТЬ ЖИМ", callback_data='change_жим')],
        [InlineKeyboardButton("✏️ ИЗМЕНИТЬ ПРИСЕД", callback_data='change_присед')],
        [InlineKeyboardButton("✏️ ИЗМЕНИТЬ ТЯГУ", callback_data='change_тяга')],
        [InlineKeyboardButton("📖 ИНСТРУКЦИИ", callback_data='instructions')],
        [InlineKeyboardButton("🔙 НАЗАД", callback_data='back_to_main')]
    ]
    return InlineKeyboardMarkup(keyboard)

# ========== ПАРСЕР ==========
def parse_workout_data(text):
    """Парсинг данных тренировки"""
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
    """Начало работы с ботом"""
    welcome_text = (
        "🏋️ БОТ ДЛЯ РАСЧЕТА ВЕСОВ\n\n"
        "Используйте меню внизу для навигации:\n"
        "• 🏋️ НАЧАТЬ РАСЧЁТ - выбрать упражнение\n"
        "• 📊 МАКСИМУМЫ - посмотреть/изменить максимумы\n"
        "• ❓ ПОМОЩЬ - инструкции по использованию\n"
        "• ℹ️ О БОТЕ - информация о боте"
    )
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard()
    )

# ========== КОМАНДА /MAX ==========
async def max_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать текущие максимумы"""
    user_id = update.effective_user.id
    
    жим_макс = get_user_max(user_id, "жим")
    присед_макс = get_user_max(user_id, "присед")
    тяга_макс = get_user_max(user_id, "тяга")
    
    await update.message.reply_text(
        f"🏋️ ВАШИ МАКСИМУМЫ:\n\n"
        f"• Жим: {жим_макс} кг\n"
        f"• Присед: {присед_макс} кг\n"
        f"• Тяга: {тяга_макс} кг\n\n"
        f"Изменить можно через меню 📊 МАКСИМУМЫ",
        reply_markup=get_main_keyboard()
    )

# ========== ОБРАБОТКА КНОПОК ПОСТОЯННОГО МЕНЮ ==========
async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий кнопок постоянного меню"""
    text = update.message.text
    
    if text == "🏋️ НАЧАТЬ РАСЧЁТ":
        await update.message.reply_text(
            "Выберите упражнение:",
            reply_markup=get_exercises_keyboard()
        )
    
    elif text == "📊 МАКСИМУМЫ":
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
        
        await update.message.reply_text(
            max_text,
            reply_markup=get_max_menu_keyboard()
        )
    
    elif text == "❓ ПОМОЩЬ":
        help_text = (
            "📖 ИНСТРУКЦИИ ПО ФОРМАТАМ ВВОДА:\n\n"
            "📌 Форматы данных:\n"
            "• 50-3;60-3-3;85-3-5\n"
            "• 50 3 60 3 3 85 3 5\n"
            "• 50-3 60-3-3 85-3-5\n\n"
            "📌 Обозначения:\n"
            "• 50-3 = 50% на 3 раза\n"
            "• 60-3-3 = 60% на 3 раза × 3 подхода\n"
            "• Разделитель: точка с запятой (;)\n\n"
            "📌 Примеры:\n"
            "• Один подход: 70-5\n"
            "• Несколько: 60-3-3;70-2-2;80-1\n"
            "• Смешанный: 50-5;60-3-3;70-2-2;85-1"
        )
        
        await update.message.reply_text(
            help_text,
            reply_markup=get_main_keyboard()
        )
    
    elif text == "ℹ️ О БОТЕ":
        about_text = (
            "🤖 БОТ ДЛЯ РАСЧЕТА ВЕСОВ В ПАУЭРЛИФТИНГЕ\n\n"
            "⚙️ Функционал:\n"
            "• Расчет рабочих весов по % от максимума\n"
            "• Округление до ближайших 2.5 кг\n"
            "• Поддержка 3х упражнений: жим, присед, тяга\n"
            "• Индивидуальные максимумы для каждого пользователя\n\n"
            "📱 Использование:\n"
            "1. Выберите упражнение\n"
            "2. Введите данные в формате: 50-3;60-3-3\n"
            "3. Получите результат\n\n"
            "💪 Удачных тренировок!"
        )
        
        await update.message.reply_text(
            about_text,
            reply_markup=get_main_keyboard()
        )

# ========== ОБРАБОТКА INLINE КНОПОК ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    # НАЗАД В ГЛАВНОЕ МЕНЮ
    if data == 'back_to_main':
        await query.edit_message_text(
            text="Используйте меню внизу для навигации:",
            reply_markup=None
        )
        await context.bot.send_message(
            chat_id=user_id,
            text="Главное меню:",
            reply_markup=get_main_keyboard()
        )
    
    # ИНСТРУКЦИИ
    elif data == 'instructions':
        instructions_text = (
            "📖 ИНСТРУКЦИИ ПО ФОРМАТАМ ВВОДА:\n\n"
            "📌 Форматы данных:\n"
            "• 50-3;60-3-3;85-3-5\n"
            "• 50 3 60 3 3 85 3 5\n"
            "• 50-3 60-3-3 85-3-5\n\n"
            "📌 Обозначения:\n"
            "• 50-3 = 50% на 3 раза\n"
            "• 60-3-3 = 60% на 3 раза × 3 подхода\n"
            "• Разделитель: точка с запятой (;)\n\n"
            "📌 Примеры:\n"
            "• Один подход: 70-5\n"
            "• Несколько: 60-3-3;70-2-2;80-1\n"
            "• Смешанный: 50-5;60-3-3;70-2-2;85-1"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔙 НАЗАД К МАКСИМУМАМ", callback_data='menu_max')]
        ]
        
        await query.edit_message_text(
            text=instructions_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # МЕНЮ МАКСИМУМОВ
    elif data == 'menu_max':
        жим_макс = get_user_max(user_id, "жим")
        присед_макс = get_user_max(user_id, "присед")
        тяга_макс = get_user_max(user_id, "тяга")
        
        max_text = (
            f"🏋️ ВАШИ МАКСИМУМЫ:\n\n"
            f"• Жим: {жим_макс} кг\n"
            f"• Присед: {присед_макс} кг\n"
            f"• Тяга: {тяга_макс} кг"
        )
        
        await query.edit_message_text(
            text=max_text,
            reply_markup=get_max_menu_keyboard()
        )
    
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
            f"📝 Выбран: {exercise_name}\n\n"
            f"Введите данные в формате:\n"
            f"50-3;60-3-3;85-3-5"
        )
    
    # ДЕТАЛИ РАСЧЕТА
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
                [InlineKeyboardButton("🔙 НАЗАД", callback_data='back_to_main')]
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
        [InlineKeyboardButton("🔄 НОВЫЙ РАСЧЁТ", callback_data='back_to_main')],
        [InlineKeyboardButton("📊 МАКСИМУМЫ", callback_data='menu_max')]
    ]
    
    await query.edit_message_text(
        text=details_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== ОБРАБОТКА СООБЩЕНИЙ ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода данных"""
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
            
            await update.message.reply_text(
                text=max_text,
                reply_markup=get_max_menu_keyboard()
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
                "❌ Не понял формат. Пример: 50-3;60-3-3;85-3-5",
                reply_markup=get_main_keyboard()
            )
            return
        
        try:
            # Сохраняем данные расчета
            if user_id not in CALCULATION_HISTORY:
                CALCULATION_HISTORY[user_id] = {}
            
            CALCULATION_HISTORY[user_id]['last_calculation'] = {
                'exercise': exercise,
                'max_weight': max_weight,
                'workouts': workouts
            }
            
            # 1. НАЗВАНИЕ УПРАЖНЕНИЯ
            exercise_name = ""
            if exercise == "жим":
                exercise_name = "🏋️ ЖИМ ЛЕЖА"
            elif exercise == "присед":
                exercise_name = "🦵 ПРИСЕДАНИЕ"
            elif exercise == "тяга":
                exercise_name = "🏗️ СТАНОВАЯ ТЯГА"
            
            # 2. БЛОК С ВЕСАМИ В ОДНОЙ СТРОКЕ
            result_parts = []
            for percent, reps, sets in workouts:
                exact = max_weight * (percent / 100)
                rounded = round(exact / 2.5) * 2.5
                
                if sets == 1:
                    result_parts.append(f"{rounded}×{reps}")
                else:
                    result_parts.append(f"{rounded} {reps}х{sets}")
            
            result_line = "; ".join(result_parts)
            
            # Отправляем результат
            await update.message.reply_text(exercise_name)
            await update.message.reply_text(result_line)
            
            # 3. КНОПКИ ДЛЯ ПРОДОЛЖЕНИЯ
            keyboard = [
                [InlineKeyboardButton("🔄 НОВЫЙ РАСЧЁТ", callback_data='back_to_main')],
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
                reply_markup=get_main_keyboard()
            )

# ========== ОБРАБОТКА ОШИБОК ==========
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ошибок"""
    logger.error(f"Ошибка: {context.error}")
    
    # Безопасная обработка
    try:
        if update and update.callback_query:
            await update.callback_query.answer("⚠️ Произошла ошибка. Попробуйте /start")
        elif update and update.message:
            await update.message.reply_text(
                "⚠️ Произошла ошибка. Попробуйте /start",
                reply_markup=get_main_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка в обработчике ошибок: {e}")

# ========== ЗАПУСК БОТА ==========
def main():
    """Запуск бота на Railway"""
    logger.info("🚀 Запуск бота для расчета весов...")
    
    try:
        # Создаем Application
        application = Application.builder().token(TOKEN).build()
        
        # Регистрируем обработчики в правильном порядке
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("max", max_command))
        application.add_handler(MessageHandler(filters.Regex("^(🏋️ НАЧАТЬ РАСЧЁТ|📊 МАКСИМУМЫ|❓ ПОМОЩЬ|ℹ️ О БОТЕ)$"), handle_main_menu))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_error_handler(error_handler)
        
        logger.info("✅ Бот запущен в режиме polling!")
        logger.info("🤖 Бот готов к работе!")
        
        # ЗАПУСК В РЕЖИМЕ POLLING (чистый запуск)
        application.run_polling(
            drop_pending_updates=True  # Удаляет ожидающие обновления при запуске
        )
        
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        raise

if __name__ == "__main__":
    main()
