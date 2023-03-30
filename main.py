# Импорт необходимых библиотек
import requests  # Для выполнения HTTP-запросов к API
import pandas as pd  # Для работы с данными в виде таблиц (DataFrame)
import time  # Для работы с временем отправки уведомлений
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters
from telegram import ReplyKeyboardMarkup
from config import TELEGRAM_TOKEN  # Telegram-токен для работы с ботом

bot_token = TELEGRAM_TOKEN

# Базовый URL-адрес для доступа к Binance Futures API
base_url = "https://fapi.binance.com"

# Параметры запроса для получения цены фьючерса ETHUSDT
params_eth = {
    "symbol": "ETHUSDT"
}

# Параметры запроса для получения цены фьючерса BTCUSDT
params_btc = {
    "symbol": "BTCUSDT"
}


# Функция для получения цены указанного фьючерса (ETH или BTC)
def get_price(params):
    # URL для запроса последней цены фьючерса
    url = base_url + "/fapi/v1/ticker/price"
    # Выполняем запрос к API и сохраняем ответ
    response = requests.get(url, params=params)
    # Если запрос выполнен успешно (код состояния 200)
    if response.status_code == 200:
        # Преобразуем ответ в JSON-формат
        data = response.json()
        # Извлекаем цену из данных и преобразуем ее в число с плавающей точкой
        price = float(data["price"])
        # Возвращаем цену
        return price

# Функция для получения цены фьючерса ETHUSDT
def get_eth_price():
    # Возвращаем цену, вызывая функцию get_price() с параметрами для ETH
    return get_price(params_eth)

# Функция для получения цены фьючерса BTCUSDT
def get_btc_price():
    # Возвращаем цену, вызывая функцию get_price() с параметрами для BTC
    return get_price(params_btc)

# Функция для определения скорректированной цены ETH, исключая влияние BTC
def get_adjusted_eth_price(eth_price, btc_price):
    return eth_price / btc_price


# Функция для получения исторических данных цен указанного фьючерса (symbol)
def get_data(symbol):
    # URL для запроса свечных данных
    url = "https://fapi.binance.com/fapi/v1/klines"
    # Задаем параметры для запроса: символ фьючерса и интервал свечей (1 минута)
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


# Функция для отправки уведомления об изменении цены
def alert(chat_id, change):
    # Определяем направление изменения
    direction = "вверх" if change > 0 else "вниз"
    # Формируем сообщение
    message = f"Цена фьючерса ETHUSDT изменилась на {change:.2f}% {direction} за последний час."
    # Отправляем сообщение в чат
    return message


def settings(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    interval = context.user_data.get("interval", 3)
    alert_timeout = context.user_data.get("alert_timeout", 300)
    change_threshold = context.user_data.get("change_threshold", 1)

    # Создаем кнопки
    settings_keyboard = [
        ["Порог изменения цены", "Интервал обновления данных", "Таймаут уведомления"],
        ["Назад"]
    ]

    # Создаем клавиатуру с кнопками
    reply_markup = ReplyKeyboardMarkup(settings_keyboard, one_time_keyboard=True, resize_keyboard=True)

    current_settings_text = (
        "Текущие настройки:\n"
        f"Порог изменения цены: {change_threshold}%\n"
        f"Интервал обновления данных: {interval} секунд\n"
        f"Таймаут уведомления: {alert_timeout} секунд\n\n"
        "Нажмите на одну из кнопок ниже, чтобы изменить соответствующую настройку."
    )

    update.message.reply_text(current_settings_text, reply_markup=reply_markup)


def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    if query.data == "settings":
        settings(update, context)
    if query.data == "change_threshold":
        query.edit_message_text("Введите новый порог изменения цены после команды /set_change_threshold (например: /set_change_threshold 1)")
    elif query.data == "interval":
        query.edit_message_text("Введите новый интервал обновления данных после команды /set_interval (например: /set_interval 5)")
    elif query.data == "alert_timeout":
        query.edit_message_text("Введите новый таймаут уведомлений после команды /set_alert_timeout (например: /set_alert_timeout 300)")


def help_command(update: Update, _: CallbackContext):
    # Отправляем сообщение с инструкциями и кнопкой "Настройки"
    update.message.reply_text(
        "Доступные команды:\n"
        "/start - Запуск мониторинга цен\n"
        "/stop - Остановка мониторинга цен\n"
        "/set_change_threshold - Установка порога изменения цены для уведомлений\n"
        "/set_interval - Установка интервала обновления данных\n"
        "/set_alert_timeout - Установка времени ожидания между уведомлениями\n"
        "/help - Показать справочную информацию\n\n"
        "Используйте кнопку 'Настройки' ниже для быстрого доступа к настройкам:"
    )


def text_message_handler(update: Update, context: CallbackContext):
    text = update.message.text

    if text == "Настройки":
        return settings(update, context)
    elif text == "Порог изменения цены":
        update.message.reply_text("Введите новый порог изменения цены после команды /set\_change\_threshold \(например: `/set_change_threshold 1`\)", parse_mode='MarkdownV2')
    elif text == "Интервал обновления данных":
        update.message.reply_text("Введите новый интервал обновления данных после команды /set\_interval \(например: `/set_interval 5`\)", parse_mode='MarkdownV2')
    elif text == "Таймаут уведомления":
        update.message.reply_text("Введите новый таймаут уведомления после команды /set\_alert\_timeout \(например: `/set_alert_timeout 300`\)", parse_mode='MarkdownV2')
    elif text == "Назад":
        start(update, context)
    else:
        update.message.reply_text(
            "Я не понимаю эту команду. Пожалуйста, используйте /help для получения списка доступных команд.")


def set_alert_timeout(update: Update, context: CallbackContext):
    try:
        new_timeout = int(context.args[0])
        context.user_data["alert_timeout"] = new_timeout
        update.message.reply_text(f"Время ожидания уведомления успешно изменено на {new_timeout} секунд")
        start(update, context)
    except (ValueError, IndexError):
        update.message.reply_text("Пожалуйста, укажите число секунд после команды /set_alert_timeout")


def set_interval(update: Update, context: CallbackContext):
    try:
        new_interval = int(context.args[0])
        context.user_data["interval"] = new_interval
        update.message.reply_text(f"Интервал мониторинга успешно изменен на {new_interval} секунд")
        start(update, context)
    except (ValueError, IndexError):
        update.message.reply_text("Пожалуйста, укажите число секунд после команды /set_interval")


def set_threshold(update: Update, context: CallbackContext):
    try:
        new_threshold = float(context.args[0])
        context.user_data["change_threshold"] = new_threshold
        update.message.reply_text(f"Порог изменения цены успешно изменен на {new_threshold}%")
        start(update, context)
    except (ValueError, IndexError):
        update.message.reply_text("Пожалуйста, укажите число процентов после команды /set_change_threshold")


# Основная функция
def monitor_prices(context: CallbackContext):
    chat_id, alert_timeout, change_threshold, alert_timestamp = context.job.context

    # Получаем текущую цену ETH и BTC
    eth_price = get_eth_price()
    btc_price = get_btc_price()

    # Получаем исторические данные для ETH и BTC
    data_eth = get_data("ETHUSDT")
    data_btc = get_data("BTCUSDT")

    # Вычисляем скользящее среднее для полученных данных ETH с периодом 60 минут
    ma_eth = moving_average(data_eth, 60)
    # Вычисляем скользящее среднее для полученных данных BTC с периодом 60 минут
    ma_btc = moving_average(data_btc, 60)

    # Вычисляем изменение скорректированной цены ETH относительно предыдущего значения скользящего среднего в процентах
    change = ((eth_price - (eth_price / btc_price)) - ma_eth[-2]) / ma_eth[-2] * 100

    # Если изменение больше change_threshold
    if abs(change) >= change_threshold:
        # Получаем текущее время
        current_timestamp = int(time.time())

        # Проверяем, отправлялось ли уведомление ранее и прошло ли достаточно времени с момента последнего уведомления
        if alert_timestamp is None or (current_timestamp - alert_timestamp) >= alert_timeout:
            message = alert(chat_id, change)
            if message:
                send_message(chat_id, message)
                # Обновляем время отправки уведомления
                context.job.context = (chat_id, alert_timeout, change_threshold, current_timestamp) # Обновляем время отправки уведомления

    # Если изменение меньше change_threshold и уведомление было отправлено ранее
    elif abs(change) < change_threshold and alert_timestamp is not None:
        # Сбрасываем время отправки уведомления
        context.job.context = (chat_id, change_threshold, alert_timeout, None)


# Функция обработчика команды /start
def start(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    interval = context.user_data.get("interval", 3)
    alert_timeout = context.user_data.get("alert_timeout", 300)
    change_threshold = context.user_data.get("change_threshold", 1)
    alert_timestamp = 0

    # Создаем кнопку "Настройки"
    settings_button = [["Настройки"]]

    # Создаем клавиатуру с кнопками
    reply_markup = ReplyKeyboardMarkup(settings_button, one_time_keyboard=True, resize_keyboard=True)

    # Отправляем приветственное сообщение
    update.message.reply_text(
        "Привет! Я бот, который будет уведомлять тебя об изменении цены Ethereum (ETH) относительно Bitcoin (BTC). "
        "Я буду сообщать тебе, когда изменение цены превысит определенный порог (например, 1%).\n\n"
        "Чтобы начать работу, нажми на кнопку 'Настройки' или введи /help, чтобы узнать о доступных командах и настройках.",
        reply_markup=reply_markup,
    )

    # Добавление функции monitor_prices в JobQueue
    context.job_queue.run_repeating(monitor_prices, interval, context=(chat_id, alert_timeout, change_threshold, alert_timestamp))


# Функция обработчика команды /stop
def stop(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    # Проверяем, есть ли активный Job для данного chat_id
    current_job = context.job_queue.get_jobs_by_name(str(chat_id))

    if current_job:
        current_job[0].schedule_removal()  # Отменяем задачу
        update.message.reply_text("Мониторинг цен остановлен.")
    else:
        update.message.reply_text("Мониторинг цен не был запущен.")


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
    dp.add_handler(MessageHandler(Filters.text, text_message_handler))

    # Регистрация обработчиков кнопок
    dp.add_handler(CallbackQueryHandler(button_callback))

    # Запускаем бот
    updater.start_polling()
    updater.idle()


# Вызываем функцию run_bot(), при выполнении условия
if __name__ == "__main__":
    run_bot()
