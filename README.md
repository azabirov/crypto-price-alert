Я выбрал методики для определения тренда по значениям скользящей средней, получения данных по ценам фьючерсов ETHUSDT из API Binance, получения предыдущей цены по данным из API Binance и сохранения данных в файл в формате CSV. Я подобрал параметры для запроса к API Binance (символ фьючерса и интервал свечей) и для записи данных в формате CSV (названия столбцов). Я выбрал эти методики и параметры по следующим причинам:

- Определение тренда по значениям скользящей средней - это простой и популярный способ анализа ценовых движений на рынке. Скользящая средняя показывает среднее значение цены за определенный период времени и сглаживает случайные колебания. Сравнение текущего значения скользящей средней с предыдущим позволяет определить направление тренда (восходящий, нисходящий или боковой).
- Получение данных по ценам фьючерсов ETHUSDT из API Binance - это удобный и быстрый способ получить актуальные данные по одному из самых ликвидных инструментов на рынке криптовалют. API Binance предоставляет доступ к различным данным по торговле на бирже Binance, включая свечные данные по фьючерсам. Задание символа фьючерса и интервала свечей позволяет получить данные по нужному инструменту и временному периоду.
- Получение предыдущей цены по данным из API Binance - это необходимый шаг для определения тренда по значениям скользящей средней. Предыдущая цена может быть определена как цена закрытия предыдущей свечи или как среднее значение цены за определенный период времени. Я выбрал первый вариант, так как он проще в реализации и не требует дополнительных вычислений.
- Сохранение данных в файл в формате CSV - это универсальный и простой способ хранения и обмена данными. Файл в формате CSV состоит из строк и столбцов, разделенных запятой или другим символом. Этот формат поддерживается большинством программ для работы с данными, таких как Excel или Pandas. Задание названий столбцов позволяет легко идентифицировать данные по цене и времени свечи.#   c r y p t o - p r i c e - a l e r t  
 