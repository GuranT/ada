import os
import logging
import telebot
import requests
import json

# ===== КОНФИГУРАЦИЯ =====
BOT_TOKEN = os.environ.get('BOT_TOKEN')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')

print("🔧 Проверка переменных...")
print(f"BOT_TOKEN: {'✅' if BOT_TOKEN else '❌'}")
print(f"DEEPSEEK_API_KEY: {'✅' if DEEPSEEK_API_KEY else '❌'}")

if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не установлен!")
    exit(1)

if not DEEPSEEK_API_KEY:
    print("❌ ОШИБКА: DEEPSEEK_API_KEY не установлен!")
    exit(1)

# Создаем бота
bot = telebot.TeleBot(BOT_TOKEN)

# Хранилище истории чата по пользователям
user_histories = {}

def ask_deepseek(user_id, question):
    """Функция для запроса к DeepSeek API"""
    url = "https://api.deepseek.com/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    
    # Получаем историю пользователя
    if user_id not in user_histories:
        user_histories[user_id] = []
    
    history = user_histories[user_id]
    
    # Формируем сообщения
    messages = [
        {"role": "system", "content": "Ты полезный AI-ассистент. Отвечай на русском языке."}
    ]
    
    # Добавляем историю (последние 5 пар сообщений)
    messages.extend(history[-10:])  # 5 пар = 10 сообщений
    
    # Добавляем текущий вопрос
    messages.append({"role": "user", "content": question})
    
    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "max_tokens": 2000,
        "temperature": 0.7,
        "stream": False
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        answer = result["choices"][0]["message"]["content"]
        
        # Обновляем историю
        user_histories[user_id].extend([
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer}
        ])
        
        # Ограничиваем размер истории
        if len(user_histories[user_id]) > 20:  # 10 пар сообщений
            user_histories[user_id] = user_histories[user_id][-20:]
        
        return answer
        
    except requests.exceptions.RequestException as e:
        logging.error(f"API Request error: {e}")
        return "❌ Ошибка соединения с API. Попробуйте позже."
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return "❌ Произошла непредвиденная ошибка."

def split_message(text, max_length=4000):
    """Разделение длинного сообщения на части"""
    if len(text) <= max_length:
        return [text]
    
    parts = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break
        
        # Ищем место для разделения
        split_pos = text.rfind('\n', 0, max_length)
        if split_pos == -1:
            split_pos = text.rfind(' ', 0, max_length)
        if split_pos == -1:
            split_pos = max_length
            
        parts.append(text[:split_pos])
        text = text[split_pos:].lstrip()
        
    return parts

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = """
🤖 *DeepSeek AI Assistant* 

Добро пожаловать! Я ваш персональный AI-помощник на основе DeepSeek.

*Что я умею:*
• 💬 Отвечать на любые вопросы
• 💻 Помогать с программированием  
• 📚 Объяснять сложные темы
• 🌐 Переводить тексты
• 💡 Генерировать идеи

*Доступные команды:*
/start - Запуск бота
/help - Помощь
/clear - Очистить историю диалога
/info - Информация

Просто напишите ваш вопрос!
    """
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """
🆘 *Помощь по использованию бота*

*Основные возможности:*
• Общение на любые темы
• Помощь с программированием
• Анализ и объяснения
• Переводы между языками
• Генерация идей и текстов

*Советы:*
• Будьте конкретны в вопросах
• Для кода указывайте язык программирования
• Используйте /clear чтобы очистить историю
• Бот запоминает контекст диалога
    """
    bot.reply_to(message, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['clear'])
def clear_history(message):
    user_id = message.from_user.id
    if user_id in user_histories:
        user_histories[user_id] = []
    
    bot.reply_to(message, "✅ История диалога очищена!")

@bot.message_handler(commands=['info'])
def send_info(message):
    info_text = """
📊 *Информация о боте*

*Технические данные:*
• 🤖 AI Модель: DeepSeek Chat
• 🚀 Версия: 2.0
• 💾 Память: Контекст диалога
• 🔧 Язык: Python

*Статус:* ✅ Активен
    """
    bot.reply_to(message, info_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        user_id = message.from_user.id
        user_text = message.text
        
        # Показываем индикатор набора
        bot.send_chat_action(message.chat.id, 'typing')
        
        # Получаем ответ от DeepSeek
        answer = ask_deepseek(user_id, user_text)
        
        # Разбиваем длинные сообщения
        message_parts = split_message(answer)
        
        for part in message_parts:
            bot.reply_to(message, part)
                
    except Exception as e:
        logging.error(f"Error: {e}")
        bot.reply_to(message, "❌ Произошла ошибка. Попробуйте еще раз.")

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 50)
    print("🤖 DeepSeek AI Telegram Bot")
    print("🚀 Бот успешно запущен!")
    print("📍 Ожидание сообщений...")
    print("=" * 50)
    
    bot.infinity_polling()
