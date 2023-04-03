# Импорт необходимых библиотек
import requests  # Для выполнения HTTP-запросов к API
import pandas as pd  # Для работы с данными в виде таблиц (DataFrame)
import time  # Для работы с временем отправки уведомлений
from telegram import Update, Bot, ReplyKeyboardMarkup  # Компоненты из библиотеки python-telegram-bot
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters
from config import TELEGRAM_TOKEN  # Telegram-токен для работы с ботом

bot_token = TELEGRAM_TOKEN


# Функция для получения исторических данных цен указанного актива (symbol)
def get_data(symbol):
    # URL для запроса свечных данных на спотовом рынке
    url = "https://api.binance.com/api/v3/klines"
    # Задаем параметры для запроса: символ актива и интервал свечей (1 минута)
    params = {"symbol": symbol, "interval": "1m", "limit": 61}
    # Выполняем запрос и преобразуем ответ в JSON
    response = requests.get(url, params=params).json()
    # Создаем пустой список для хранения данных
    data = []
    # Обходим все свечи в ответе
    for candle in response:
        # Извлекаем цену закрытия и время закрытия свечи, преобразуем в нужные типы данных
        item = {"price": float(candle[4]), "time": int(candle[6])}
        # Добавляем элемент в список данных
        data.append(item)
    # Возвращаем список данных
    return data


def get_data(symbol):
    # URL для запроса свечных данных
    url = "https://fapi.binance.com/fapi/v1/klines"
    # Задаем параметры для запроса: символ фьючерса и интервал свечей (1 минута)
    params = {"symbol": symbol, "interval": "1m", "limit": 61}
    # Выполняем запрос и преобразуем ответ в JSON
    response = requests.get(url, params=params)

    # Проверяем, успешен ли запрос
    if response.status_code != 200:
        print(f"{symbol} Ошибка: получен код {response.status_code} от Binance API. Сообщение: {response.text}")
        return []

    response_data = response.json()

    # Создаем пустой список для хранения данных
    data = []
    # Обходим все свечи в ответе
    for candle in response_data:
        # Извлекаем цену закрытия и время закрытия свечи, преобразуем в нужные типы данных
        item = {"price": float(candle[4]), "time": int(candle[6])}
        # Добавляем элемент в список данных
        data.append(item)
    # Возвращаем список данных
    return data


# Функция для расчета скользящего среднего на основе данных цен
def moving_average(data, period):
    # Создаем DataFrame на основе списка данных
    df = pd.DataFrame(data)
    # Вычисляем скользящее среднее для цен с заданным периодом
    df["ma"] = df["price"].rolling(period).mean()
    # Возвращаем скользящее среднее в виде списка значений
    return df["ma"].tolist()


# Функция отправки сообщений
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    requests.post(url, data=data)


# Функция для формирования уведомления об изменении цены
def alert(change, base_asset, quote_asset, base_price):
    # Определяем направление изменения
    direction = "вверх" if change > 0 else "вниз"
    direction_emoji = "📈" if change > 0 else "📉"
    # Формируем сообщение
    message = f"{direction_emoji} Цена {base_asset}/{quote_asset} изменилась на {change:.2f}% {direction}" \
              f" относительно последнего часа. Текущая цена: {base_price:.2f} {quote_asset}"
    # Возвращаем сообщение
    return message


# Функция обработчика команды /settings
def settings(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    interval = context.user_data.get("interval", 3)
    alert_timeout = context.user_data.get("alert_timeout", 300)
    change_threshold = context.user_data.get("change_threshold", 1)
    base_asset = context.user_data.get("base_asset", "ETH")
    quote_asset = context.user_data.get("quote_asset", "USDT")
    message_id = update.effective_message.message_id
    # Создаем кнопки для настроек
    settings_keyboard = [
        ["📊 Порог изменения цены", "⏱️ Интервал обновления данных", "🔕 Таймаут уведомления"],
        ["💹 Настройки активов"],
        ["↩️ Назад"]
    ]

    # Создаем клавиатуру с кнопками
    reply_markup = ReplyKeyboardMarkup(settings_keyboard, one_time_keyboard=True, resize_keyboard=True)

    current_settings_text = (
        "🔧 *Здесь вы можете изменить настройки уведомлений о ценах активов. Текущие настройки:*\n\n"
        f"*Отслеживаемая пара активов: {base_asset}/{quote_asset}*\n"
        f"Порог изменения цены: {change_threshold}%\n"
        f"Интервал обновления данных: {interval} секунд\n"
        f"Таймаут уведомления: {alert_timeout} секунд\n\n"
        "Нажмите на одну из кнопок ниже, чтобы изменить соответствующую настройку."
    )
    # Экранируем точки
    current_settings_text = current_settings_text.replace('.', r'\.')

    update.message.reply_text(current_settings_text, reply_markup=reply_markup, parse_mode='MarkdownV2')
    delete_message(context.bot, chat_id, message_id)


# Функция обработчика кнопок
def button_callback(update: Update, context: CallbackContext):
    # Обработка нажатия кнопок в зависимости от данных CallbackQuery
    query = update.callback_query
    query.answer()
    message_id = update.effective_message.message_id
    chat_id = update.effective_chat.id
    if query.data == "settings":
        settings(update, context)
    elif query.data == "change_threshold":
        query.edit_message_text("Введите новый порог изменения цены после команды /set_change_threshold (например: /set_change_threshold 1)")
    elif query.data == "interval":
        query.edit_message_text("Введите новый интервал обновления данных после команды /set_interval (например: /set_interval 5)")
    elif query.data == "alert_timeout":
        query.edit_message_text("Введите новый таймаут уведомлений после команды /set_alert_timeout (например: /set_alert_timeout 300)")
    delete_message(context.bot, chat_id, message_id)


# Функция обработчика команды /help
def help_command(update: Update, context: CallbackContext):
    message_id = update.effective_message.message_id
    chat_id = update.effective_chat.id
    # Отправляет сообщение с описанием доступных команд и настроек
    update.message.reply_text(
        "Доступные команды:\n\n"
        "/start - Запуск мониторинга цен\n"
        "/stop - Остановка мониторинга цен\n"
        "/set_change_threshold - Установка порога изменения цены для уведомлений\n"
        "/set_interval - Установка интервала обновления данных\n"
        "/set_alert_timeout - Установка времени ожидания между уведомлениями\n"
        "/help - Показать справочную информацию\n\n"
        "Используйте кнопку 'Настройки' ниже для быстрого доступа к настройкам:"
    )
    delete_message(context.bot, chat_id, message_id)


def set_assets(update: Update, context: CallbackContext):
    message_id = update.effective_message.message_id
    chat_id = update.effective_chat.id

    try:
        base_asset = context.args[0]
        quote_asset = context.args[1]
        context.user_data["base_asset"] = base_asset
        context.user_data["quote_asset"] = quote_asset
        update.message.reply_text(f"Отслеживаемая пара активов успешно изменена на {base_asset}/{quote_asset}")
        delete_message(context.bot, chat_id, message_id)
        start(update, context)
    except (ValueError, IndexError):
        update.message.reply_text("Пожалуйста, укажите пару активов после команды /set_assets (например: `/set_assets DOGE USDT`)")
        delete_message(context.bot, chat_id, message_id)


# Обрабатывает текстовые сообщения
def text_message_handler(update: Update, context: CallbackContext):
    text = update.message.text
    message_id = update.effective_message.message_id
    chat_id = update.effective_chat.id

    if text == "⚙️ Настройки":
        return settings(update, context)
    elif text == "📊 Порог изменения цены":
        update.message.reply_text("Введите новый порог изменения цены _\(в процентах\)_ после команды /set\_change\_threshold \(например: `/set_change_threshold 1`\)", parse_mode='MarkdownV2')
    elif text == "⏱️ Интервал обновления данных":
        update.message.reply_text("Введите новый интервал обновления данных _\(в секундах\)_ после команды /set\_interval \(например: `/set_interval 5`\)", parse_mode='MarkdownV2')
    elif text == "⌛ Таймаут уведомления":
        update.message.reply_text("Введите новый таймаут уведомления _\(в секундах\)_ после команды /set\_alert\_timeout \(например: `/set_alert_timeout 300`\)", parse_mode='MarkdownV2')
    elif text == "💹 Настройки активов":
        update.message.reply_text(
            "Введите новую пару активов для отслеживания в формате BASE/QUOTE \(например, DOGE/USDT\) после команды /set\_assets \(например: `/set_assets DOGE USDT`\)", parse_mode='MarkdownV2')
    elif text == "↩️ Назад":
        start(update, context)
    else:
        update.message.reply_text(
            "Я не понимаю эту команду. Пожалуйста, используйте /help для получения списка доступных команд.")
    delete_message(context.bot, chat_id, message_id)


# Функция обработчика команды /set_alert_timeout
def set_alert_timeout(update: Update, context: CallbackContext):
    message_id = update.effective_message.message_id
    chat_id = update.effective_chat.id
    # Изменяет время ожидания между отправкой уведомлений
    try:
        new_timeout = int(context.args[0])
        context.user_data["alert_timeout"] = new_timeout
        update.message.reply_text(f"Время ожидания уведомления успешно изменено на {new_timeout} секунд")
        delete_message(context.bot, chat_id, message_id)
        start(update, context)
    except (ValueError, IndexError):
        update.message.reply_text("Пожалуйста, укажите число секунд после команды /set_alert_timeout")


# Функция обработчика команды /set_interval
def set_interval(update: Update, context: CallbackContext):
    message_id = update.effective_message.message_id
    chat_id = update.effective_chat.id
    # Изменяет интервал мониторинга цен
    try:
        new_interval = int(context.args[0])
        context.user_data["interval"] = new_interval
        update.message.reply_text(f"Интервал мониторинга успешно изменен на {new_interval} секунд")
        delete_message(context.bot, chat_id, message_id)
        start(update, context)
    except (ValueError, IndexError):
        update.message.reply_text("Пожалуйста, укажите число секунд после команды /set_interval")
        delete_message(context.bot, chat_id, message_id)


# Функция обработчика команды /set_change_threshold
def set_threshold(update: Update, context: CallbackContext):
    message_id = update.effective_message.message_id
    chat_id = update.effective_chat.id
    # Изменяет порог изменения цены, после которого будет отправлено уведомление
    try:
        new_threshold = float(context.args[0])
        context.user_data["change_threshold"] = new_threshold
        update.message.reply_text(f"Порог изменения цены успешно изменен на {new_threshold}%")
        delete_message(context.bot, chat_id, message_id)
        start(update, context)
    except (ValueError, IndexError):
        update.message.reply_text("Пожалуйста, укажите число процентов после команды /set_change_threshold")
        delete_message(context.bot, chat_id, message_id)


# Получает текущую цену актива на Binance
def get_asset_price(asset: str, quote_asset: str = "USDT") -> float:
    if asset == quote_asset:
        return 1.0

    url = "https://api.binance.com/api/v3/ticker/price"
    params = {"symbol": f"{asset}{quote_asset}"}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return float(data["price"])
    except requests.exceptions.HTTPError as e:
        print(f"Ошибка в получении цены: {e}")
        return None
    except ValueError as e:
        print(f"Ошибка преобразования цены: {e}")
    except Exception as e:
        print(f"Неизвестная ошибка: {e}")


# Основная функция
def monitor_prices(context: CallbackContext):
    chat_id, alert_timeout, change_threshold, alert_timestamp, base_asset, quote_asset = context.job.context

    # Получаем текущую цену базового актива и актива-котировки
    base_price = get_asset_price(base_asset, quote_asset)

    # Получаем исторические данные для базового актива и актива-котировки
    data_base = get_data(f"{base_asset}{quote_asset}")

    # Вычисляем скользящее среднее для полученных данных базового актива с периодом 60 минут
    ma_base = moving_average(data_base, 60)

    # Вычисляем изменение скорректированной цены базового актива относительно предыдущего значения скользящего среднего в процентах
    change = (base_price - ma_base[-2]) / ma_base[-2] * 100

    # Если изменение больше change_threshold
    if abs(change) >= change_threshold:
        # Получаем текущее время
        current_timestamp = int(time.time())

        # Проверяем, отправлялось ли уведомление ранее и прошло ли достаточно времени с момента последнего уведомления
        if alert_timestamp is None or (current_timestamp - alert_timestamp) >= alert_timeout:
            message = alert(change, base_asset, quote_asset, base_price)
            if message:
                send_message(chat_id, message)
                # Обновляем время отправки уведомления
                context.job.context = (chat_id, alert_timeout, change_threshold, current_timestamp, base_asset, quote_asset)

    # Если изменение меньше change_threshold и уведомление было отправлено ранее
    elif abs(change) < change_threshold and alert_timestamp is not None:
        # Сбрасываем время отправки уведомления
        context.job.context = (chat_id, alert_timeout, change_threshold, None, base_asset, quote_asset)


# Функция для удаления сообщений
def delete_message(bot: Bot, chat_id, message_id):
    # Удаляет сообщение с заданным chat_id и message_id
    try:
        bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"Не удалось удалить сообщение: {e}")


# Функция обработчика команды /start
def start(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    interval = context.user_data.get("interval", 3)
    alert_timeout = context.user_data.get("alert_timeout", 300)
    change_threshold = context.user_data.get("change_threshold", 1)
    base_asset = context.user_data.get("base_asset", "ETH")
    quote_asset = context.user_data.get("quote_asset", "USDT")
    alert_timestamp = 0

    # Создаем кнопку "Настройки"
    settings_button = [["⚙️ Настройки"]]

    # Создаем клавиатуру с кнопками
    reply_markup = ReplyKeyboardMarkup(settings_button, one_time_keyboard=True, resize_keyboard=True)

    message_id = update.effective_message.message_id

    # Отправляем приветственное сообщение
    update.message.reply_text(
        f"👋 Привет\! Я отслеживаю цену {base_asset}/{quote_asset} и оповещаю об изменениях\.\n\n"
        "Я буду сообщать тебе, когда изменение цены превысит определенный порог _\(например, 1%\)_\.\n\n"
        "_Чтобы начать работу, нажми на кнопку 'Настройки' или введи /help, чтобы узнать о доступных командах и настройках\._",
        reply_markup=reply_markup, parse_mode='MarkdownV2',
    )

    delete_message(context.bot, chat_id, message_id)

    # Добавление функции monitor_prices в JobQueue
    #context.job_queue.run_repeating(monitor_prices, interval, context=(chat_id, alert_timeout, change_threshold, alert_timestamp))
    context.job_queue.run_repeating(monitor_prices, interval, context=(chat_id, alert_timeout, change_threshold, alert_timestamp, base_asset, quote_asset), name=str(chat_id))


# Функция обработчика команды /stop
def stop(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    # Проверяем, есть ли активный Job для данного chat_id
    current_job = context.job_queue.get_jobs_by_name(str(chat_id))

    message_id = update.effective_message.message_id

    if current_job:
        current_job[0].schedule_removal()  # Отменяем задачу
        update.message.reply_text("Мониторинг цен остановлен.")
    else:
        update.message.reply_text("Мониторинг цен не был запущен.")

    delete_message(context.bot, chat_id, message_id)


# Функция для запуска бота
def run_bot():
    updater = Updater(bot_token)

    # Получаем диспетчер для регистрации обработчиков
    dp = updater.dispatcher

    # Регистрация обработчиков команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("set_change_threshold", set_threshold))
    dp.add_handler(CommandHandler("set_interval", set_interval))
    dp.add_handler(CommandHandler("set_alert_timeout", set_alert_timeout))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_handler(CommandHandler("set_assets", set_assets))
    dp.add_handler(MessageHandler(Filters.text, text_message_handler))

    # Регистрация обработчиков кнопок
    dp.add_handler(CallbackQueryHandler(button_callback))

    # Запускаем бот
    updater.start_polling()
    updater.idle()


# Вызываем функцию run_bot(), при выполнении условия
if __name__ == "__main__":
    run_bot()
