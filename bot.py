import os
import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler

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
    if user_id not in USER_MAX_WEIGHTS:
        USER_MAX_WEIGHTS[user_id] = {"жим": 117.5, "присед": 125}
    return USER_MAX_WEIGHTS[user_id].get(exercise, 100)

def set_user_max(user_id, exercise, value):
    if user_id not in USER_MAX_WEIGHTS:
        USER_MAX_WEIGHTS[user_id] = {}
    USER_MAX_WEIGHTS[user_id][exercise] = value

# ========== ПАРСЕР ==========
def parse_workout_data(text):
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
async def start_command(update: Update, context: CallbackContext):
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

# ========== ОСТАЛЬНОЙ КОД... ==========
# (тут остальной код из предыдущего сообщения - кнопки, расчеты и т.д.)
# ...

# ========== ЗАПУСК ==========
def main():
    logger.info("✅ Бот настроен и запускается...")
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    # добавьте остальные обработчики...
    
    # ЗАПУСК ДЛЯ RAILWAY
    webhook_url = f"https://{os.environ.get('RAILWAY_STATIC_URL', '')}/{TOKEN}"
    
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=webhook_url,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()
