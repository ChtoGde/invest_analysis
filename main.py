import pandas as pd
from datetime import datetime
from data import MyClient
from analysis import Analysis
import os



# получаю токен из файла(если используете токен напрямую, то строку 10 - 11 нужно удалить)
with open("C:\\Programming\\Token_for_invest\\token.txt", 'r', encoding='utf-8') as f:
    TOKEN = f.read()
# у меня токен сохранён в отдельном файле, вы можете использовать свой напрямую в MyClient(TOKEN) где TOKEN - ваш токен
    my_client = MyClient(TOKEN)

# проверяем существование файлов и загружаем данные
if os.path.exists('candles.csv'):
    prices = pd.read_csv('candles.csv', index_col='Date')
else:
    my_client.get_candles()
    prices = pd.read_csv('candles.csv', index_col='Date')

if os.path.exists('fundamentals.csv'):
    fundamentals = pd.read_csv('fundamentals.csv', index_col=0).T
else:
    my_client.get_fundamentals()
    fundamentals = pd.read_csv('fundamentals.csv', index_col=0).T

# Эта функция нужна, чтобы не создавать файлы фундаментальных данных и свечей
# каждый раз при запуске программы
def subtract_dates(prices, now=datetime.now().date()):
    """Функция разницы даты последней свечи и настоящей даты"""
    date = pd.to_datetime(prices.index.max()).date()
    return (now - date).days


def main():
    # получаем разницу между последней датой в файле prices и сегодняшней датой
    days_between = subtract_dates(prices)
    # если разница больше 1 дня, то обновляем данные
    if days_between > 1:
        my_client.get_candles()
        my_client.get_fundamentals()

    # отправляем загруженные данные в класс Analysis
    analysis = Analysis(prices, fundamentals)

    # получаем рекомендации по акциям
    buy, sell = analysis.recomendations()

    # сохраняем в эксель
    analysis.save_to_excel(buy, sell)

    print(buy)
    print()
    print(sell)
    print()
    # убеждаемся, что программа завершилась без ошибок
    print('Программа завершилась')


if __name__ == "__main__":
    main()
