import re
import os
import time
import logging
from typing import Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler

# ========== НАСТРОЙКИ ==========
TOKEN = os.environ.get("BOT_TOKEN", "8514815854:AAH2CVbpxaPTTNtcdHj8j9lcbYa2zgBoVn8")
PORT = int(os.environ.get("PORT", 8080))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://ваш-домен.railway.app")

# ========== ЛОГИРОВАНИЕ ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ========== ГЛОБАЛЬНЫЕ ДАННЫЕ (в памяти) ==========
MAX_WEIGHTS: Dict[str, float] = {
    "жим": 117.5,
    "присед": 125,
    "присяд": 125
}

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def parse_digital_with_semicolon(text: str):
    """Парсинг данных с точкой с запятой"""
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
    
    return results

def parse_workout_data(text: str):
    """Парсинг данных тренировки"""
    results = parse_digital_with_semicolon(text)
    
    if not results:
        numbers = re.findall(r'\d+', text)
        numbers = [int(n) for n in numbers]
        
        i = 0
        while i < len(numbers):
            if i + 2 < len(numbers):
                percent = numbers[i]
                reps = numbers[i+1]
                sets = numbers[i+2]
                
                if 10 <= percent <= 120 and 1 <= reps <= 10:
                    results.append((percent, reps, sets))
                    i += 3
                else:
                    i += 1
            elif i + 1 < len(numbers):
                percent = numbers[i]
                reps = numbers[i+1]
                
                if 10 <= percent <= 120 and 1 <= reps <= 10:
                    results.append((percent, reps, 1))
                    i += 2
                else:
                    i += 1
            else:
                i += 1
    
    return results

def calculate_weight(weight: float, percentage: float):
    """Расчет веса с округлением"""
    exact = weight * (percentage / 100)
    return round(exact / 2.5) * 2.5

async def show_exercise_buttons_after_calc(update: Update, context: CallbackContext):
    """Показать кнопки упражнений после расчета"""
    keyboard = [
        [InlineKeyboardButton("🏋️ ЖИМ", callback_data='exercise_жим')],
        [InlineKeyboardButton("🦵 ПРИСЕД", callback_data='exercise_присед')],
        [InlineKeyboardButton("📊 МАКСИМУМЫ", callback_data='show_max')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.effective_message:
        await update.effective_message.reply_text(
            "✅ Расчет завершен!\n\nВыберите упражнение для нового расчета:",
            reply_markup=reply_markup
        )

# ========== ОСНОВНЫЕ ОБРАБОТЧИКИ ==========

async def start_command(update: Update, context: CallbackContext):
    """Команда /start"""
    # Сохраняем состояние - ждем выбора упражнения
    if 'user_data' not in context.__dict__:
        context.user_data = {}
    
    context.user_data.clear()
    context.user_data['awaiting_exercise'] = True
    
    keyboard = [
        [InlineKeyboardButton("🏋️ ЖИМ", callback_data='exercise_жим')],
        [InlineKeyboardButton("🦵 ПРИСЕД", callback_data='exercise_присед')],
        [InlineKeyboardButton("📊 МАКСИМУМЫ", callback_data='show_max')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        text="🏋️ БОТ ДЛЯ РАСЧЕТА ВЕСОВ\n\nВыберите упражнение:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: CallbackContext):
    """Обработка нажатия кнопок"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # 🔧 РЕЖИМ ИЗМЕНЕНИЯ МАКСИМУМА
    if data.startswith('change_max_'):
        exercise = data.split('_')[2]  # change_max_жим или change_max_присед
        
        # Сохраняем какое упражнение меняем
        context.user_data['changing_max_for'] = exercise
        context.user_data['awaiting_new_max'] = True
        
        await query.edit_message_text(
            text=f"📝 Изменение максимума для {exercise.upper()}\n\n"
                 f"Текущий максимум: {MAX_WEIGHTS[exercise]} кг\n\n"
                 f"Введите новый максимум в кг (например: 120 или 122.5):",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 ОТМЕНА", callback_data='back_to_max')]
            ])
        )
    
    # 📊 ПОКАЗ МАКСИМУМОВ
    elif data == 'show_max':
        max_text = (
            f"🏋️ ТЕКУЩИЕ МАКСИМУМЫ:\n\n"
            f"• Жим: {MAX_WEIGHTS['жим']} кг\n"
            f"• Присед: {MAX_WEIGHTS['присед']} кг\n\n"
            f"⚙️ Нажмите кнопку ниже для изменения"
        )
        
        keyboard = [
            [InlineKeyboardButton("✏️ ИЗМЕНИТЬ ЖИМ", callback_data='change_max_жим')],
            [InlineKeyboardButton("✏️ ИЗМЕНИТЬ ПРИСЕД", callback_data='change_max_присед')],
            [InlineKeyboardButton("🔙 НАЗАД К ВЫБОРУ", callback_data='back_to_exercises')]
        ]
        
        await query.edit_message_text(
            text=max_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ↩️ ВОЗВРАТ К МАКСИМУМАМ
    elif data == 'back_to_max':
        max_text = (
            f"🏋️ ТЕКУЩИЕ МАКСИМУМЫ:\n\n"
            f"• Жим: {MAX_WEIGHTS['жим']} кг\n"
            f"• Присед: {MAX_WEIGHTS['присед']} кг\n\n"
            f"⚙️ Нажмите кнопку ниже для изменения"
        )
        
        keyboard = [
            [InlineKeyboardButton("✏️ ИЗМЕНИТЬ ЖИМ", callback_data='change_max_жим')],
            [InlineKeyboardButton("✏️ ИЗМЕНИТЬ ПРИСЕД", callback_data='change_max_присед')],
            [InlineKeyboardButton("🔙 НАЗАД К ВЫБОРУ", callback_data='back_to_exercises')]
        ]
        
        await query.edit_message_text(
            text=max_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ↩️ ВОЗВРАТ К ВЫБОРУ УПРАЖНЕНИЙ
    elif data == 'back_to_exercises':
        keyboard = [
            [InlineKeyboardButton("🏋️ ЖИМ", callback_data='exercise_жим')],
            [InlineKeyboardButton("🦵 ПРИСЕД", callback_data='exercise_присед')],
            [InlineKeyboardButton("📊 МАКСИМУМЫ", callback_data='show_max')]
        ]
        await query.edit_message_text(
            text="Выберите упражнение:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # 🏋️ ВЫБОР УПРАЖНЕНИЯ ДЛЯ РАСЧЕТА
    elif data.startswith('exercise_'):
        exercise = data.split('_')[1]
        
        # Сохраняем выбранное упражнение
        context.user_data['current_exercise'] = exercise
        context.user_data['awaiting_data'] = True
        context.user_data['awaiting_new_max'] = False
        
        # Просим ввести данные
        await query.edit_message_text(
            text=f"📝 Выбран: {exercise.upper()}\n\n"
                 f"Введите данные (пример: 50-3;60-3-3;85-3-5):",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 ВЫБРАТЬ ДРУГОЕ", callback_data='back_to_exercises')]
            ])
        )

async def handle_message(update: Update, context: CallbackContext):
    """Обработка ввода данных"""
    text = update.message.text.strip()
    
    # 🔧 ПРОВЕРЯЕМ, ЕСЛИ ЭТО ИЗМЕНЕНИЕ МАКСИМУМА
    if context.user_data.get('awaiting_new_max'):
        exercise = context.user_data.get('changing_max_for')
        
        if not exercise:
            await update.message.reply_text("❌ Ошибка. Начните с /start")
            return
        
        try:
            # Пробуем преобразовать в число
            new_max = float(text.replace(',', '.'))
            
            # Проверяем корректность
            if new_max <= 0 or new_max > 300:
                await update.message.reply_text("❌ Некорректное значение! Введите число от 1 до 300 кг.")
                return
            
            # Обновляем максимум
            MAX_WEIGHTS[exercise] = new_max
            if exercise == 'присед':
                MAX_WEIGHTS['присяд'] = new_max  # Обновляем синоним
            
            # Подтверждаем изменение
            await update.message.reply_text(f"✅ Максимум для {exercise.upper()} изменен на {new_max} кг!")
            
            # Показываем обновленные максимумы
            max_text = (
                f"🏋️ ОБНОВЛЕННЫЕ МАКСИМУМЫ:\n\n"
                f"• Жим: {MAX_WEIGHTS['жим']} кг\n"
                f"• Присед: {MAX_WEIGHTS['присед']} кг\n\n"
                f"⚙️ Изменения сохранены"
            )
            
            keyboard = [
                [InlineKeyboardButton("✏️ ИЗМЕНИТЬ ЖИМ", callback_data='change_max_жим')],
                [InlineKeyboardButton("✏️ ИЗМЕНИТЬ ПРИСЕД", callback_data='change_max_присед')],
                [InlineKeyboardButton("🔙 НАЗАД К ВЫБОРУ", callback_data='back_to_exercises')]
            ]
            
            await update.message.reply_text(
                text=max_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            # Сбрасываем состояние
            context.user_data['awaiting_new_max'] = False
            if 'changing_max_for' in context.user_data:
                del context.user_data['changing_max_for']
            
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат! Введите число (например: 120 или 122.5):",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 ОТМЕНА", callback_data='back_to_max')]
                ])
            )
        return
    
    # 📊 ПРОВЕРЯЕМ, ЕСЛИ ЭТО РАСЧЕТ УПРАЖНЕНИЯ
    if not context.user_data.get('awaiting_data'):
        return
    
    if text.startswith('/'):
        return
    
    # Получаем выбранное упражнение
    exercise = context.user_data.get('current_exercise')
    if not exercise:
        return
    
    # Парсим данные
    workouts = parse_workout_data(text)
    
    if not workouts:
        await update.message.reply_text(
            "❌ Не понял формат. Пример: 50-3;60-3-3;85-3-5\n\nПопробуйте еще раз:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 ВЫБРАТЬ ДРУГОЕ", callback_data='back_to_exercises')]
            ])
        )
        return
    
    max_weight = MAX_WEIGHTS[exercise]
    
    try:
        # 🎯 БЛОК 1: ЗАГОЛОВОК С НАЗВАНИЕМ УПРАЖНЕНИЯ
        header = f"🏋️ РАСЧЕТ ВЕСОВ\n📊 {exercise.upper()}"
        await update.message.reply_text(header)
        
        # 📊 БЛОК 2: ТОЛЬКО ЦИФРЫ (для копирования)
        main_result = ""
        
        for i, (percent, reps, sets) in enumerate(workouts, 1):
            rounded = calculate_weight(max_weight, percent)
            
            if sets == 1:
                main_result += f"{i}. {rounded} × {reps}\n"
            else:
                main_result += f"{i}. {rounded} × {reps} × {sets}\n"
        
        main_result = main_result.strip()
        await update.message.reply_text(main_result)
        
        # 🔍 БЛОК 3: ДЕТАЛИ
        details = f"🔍 ДЕТАЛИ ({exercise}):\n\n"
        details += f"📊 Максимум: {max_weight} кг\n\n"
        details += "📝 Точные значения %:\n"
        
        for i, (percent, reps, sets) in enumerate(workouts, 1):
            exact = max_weight * (percent / 100)
            rounded = calculate_weight(max_weight, percent)
            
            if sets == 1:
                details += f"{i}. {percent}% = {exact:.1f} кг → {rounded} кг ({reps})\n"
            else:
                details += f"{i}. {percent}% = {exact:.1f} кг → {rounded} кг ({reps}×{sets})\n"
        
        details += f"\n⚙️ Округление до 2.5 кг"
        
        await update.message.reply_text(details)
        
        # Сбрасываем состояние
        context.user_data['awaiting_data'] = False
        
        # Показываем кнопки для нового расчета
        await show_exercise_buttons_after_calc(update, context)
        
    except Exception as e:
        logger.error(f"Ошибка расчета: {e}")
        await update.message.reply_text(
            "❌ Ошибка расчета. Попробуйте еще раз:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 ВЫБРАТЬ ДРУГОЕ", callback_data='back_to_exercises')]
            ])
        )

async def max_command(update: Update, context: CallbackContext):
    """Команда /max"""
    await update.message.reply_text(
        f"🏋️ ТЕКУЩИЕ МАКСИМУМЫ:\n\n"
        f"• Жим: {MAX_WEIGHTS['жим']} кг\n"
        f"• Присед: {MAX_WEIGHTS['присед']} кг\n\n"
        f"Используйте /start для расчета или изменения"
    )

async def error_handler(update: Update, context: CallbackContext):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")
    
    try:
        if update.callback_query:
            await update.callback_query.answer("⚠️ Произошла ошибка. Попробуй /start")
    except:
        pass

# ========== ОСНОВНАЯ ФУНКЦИЯ ==========
def main():
    """Основная функция запуска"""
    logger.info("🚀 Запуск бота для расчета весов...")
    logger.info(f"Начальные максимумы: Жим={MAX_WEIGHTS['жим']}кг, Присед={MAX_WEIGHTS['присед']}кг")
    
    try:
        # Создаем приложение
        application = Application.builder().token(TOKEN).build()
        
        # Регистрируем обработчики
        application.add_handler(CommandHandler('start', start_command))
        application.add_handler(CommandHandler('max', max_command))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Обработчик ошибок
        application.add_error_handler(error_handler)
        
        logger.info("✅ Приложение создано и настроено")
        
        # Запускаем в режиме webhook для Railway
        webhook_url = f"{WEBHOOK_URL.rstrip('/')}/{TOKEN}"
        logger.info(f"🌐 Настройка webhook на: {webhook_url}")
        
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=webhook_url,
            drop_pending_updates=True
        )
        
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        raise

if __name__ == '__main__':
    main()
