from tokens import get_t_bankAPI_token
from data import MyClient
from analysis import Analysis



# получаю токен из заранее созданного фаила, вы можее присвоить токен напрямую
T_BANK_TOKEN = get_t_bankAPI_token()
my_client = MyClient(T_BANK_TOKEN)


def main():
    # создаём файлы candles.csv и fundamentals.csv
    my_client.get_candles_and_fundamentals()
    # подключаем класс анализа
    analysis = Analysis()
    # получаем рекомендации по акциям
    buy, sell = analysis.recomendations()
    # сохраняем в эксель
    analysis.save_to_excel(buy, sell)

    # выводим в консоль результат
    print(buy)
    print()
    print(sell)
    print()

    # убеждаемся, что программа завершилась без ошибок
    print('Программа завершилась')


if __name__ == "__main__":
    main()
