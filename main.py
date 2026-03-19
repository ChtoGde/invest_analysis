from db_config import CONNECTION_DB
from tokens_and_passwords import get_t_bankAPI_token, get_db_connection
from data import MyClient
from analysis import Analysis
from db_update import db_update



# получаю токен из заранее созданного фаила, вы можее присвоить токен напрямую
T_BANK_TOKEN = get_t_bankAPI_token()
my_client = MyClient(T_BANK_TOKEN)


def main():
    db = CONNECTION_DB(get_db_connection()[0], get_db_connection()[1], get_db_connection()[2])
    # создаём файлы candles.csv и fundamentals.csv
    my_client.get_candles_and_fundamentals()
    # подключаем класс анализа
    analysis = Analysis()
    analysis.recommendations()
    # получаем рекомендации по акциям
    buy = analysis.get_buy_list()
    sell = analysis.get_sell_list()
    # сохраняем в эксель
    analysis.save_to_excel(buy, sell)

    # обновляем базу данных
    db_update(db, analysis)

    # выводим в консоль результат
    print(buy)
    print()
    print(sell)
    print()

    # убеждаемся, что программа завершилась без ошибок
    print('Программа завершилась')


if __name__ == "__main__":
    main()
