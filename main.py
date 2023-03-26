# Импорт необходимых библиотек
import requests  # Для выполнения HTTP-запросов к API
import pandas as pd  # Для работы с данными в виде таблиц (DataFrame)
import time  # Для работы со временем, задержками и таймерами

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

bot_token = "TELEGRAM_API_TOKEN"

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


def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    requests.post(url, data=data)


# Функция для отправки уведомления об изменении цены
def alert(chat_id, change):
    # Если абсолютное значение изменения больше или равно 1%
    if abs(change) >= 1:
        # Определяем направление изменения
        direction = "вверх" if change > 0 else "вниз"
        # Формируем сообщение
        message = f"Цена фьючерса ETHUSDT изменилась на {change:.2f}% {direction} за последний час."
        # Отправляем сообщение в чат
        send_message(chat_id, message)

# Функция обработчика команды /start
def start(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    # Отправка приветственного сообщения
    send_message(chat_id, "Привет! Я запущен и начинаю отслеживание цен фьючерсов. Буду уведомлять об изменениях!")
    # Запуск функции main с chat_id
    main(chat_id)


# Основная функция
def main(chat_id):
    # Задаем интервал времени между проверками цены (в секундах)
    interval = 3

    # Бесконечный цикл для отслеживания цены в реальном времени
    while True:
        try:
            # Получаем текущую цену ETH и BTC
            eth_price = get_eth_price()
            btc_price = get_btc_price()

            eth_btc_ratio = eth_price / btc_price

            # Получаем исторические данные для ETH и BTC
            data_eth = get_data("ETHUSDT")
            data_btc = get_data("BTCUSDT")

            # Вычисляем скользящее среднее для полученных данных ETH с периодом 60 минут
            ma_eth = moving_average(data_eth, 60)
            # Вычисляем скользящее среднее для полученных данных BTC с периодом 60 минут
            ma_btc = moving_average(data_btc, 60)

            # Вычисляем изменение скорректированной цены ETH относительно предыдущего значения скользящего среднего в процентах
            change = ((eth_price - (eth_price / btc_price)) - ma_eth[-2]) / ma_eth[-2] * 100

            # Отправляем функцию alert с вычисленным изменением цены в Telegram-бот
            alert(chat_id, change)

            # Ждем заданный интервал времени перед следующей проверкой
            time.sleep(interval)

        except Exception as e:
            # Выводим сообщение об ошибке, если она произошла
            send_message(chat_id, f"Произошла ошибка: {e}")

            # Добавляем время задержки перед повторной попыткой выполнения кода
            time.sleep(interval)

# Функция для запуска бота
def run_bot():
    updater = Updater(bot_token)

    # Добавляем обработчик команды /start
    updater.dispatcher.add_handler(CommandHandler("start", start))

    # Запускаем бот
    updater.start_polling()
    updater.idle()

# Вызываем функцию run_bot(), при выполнении условия
if __name__ == "__main__":
    run_bot()
