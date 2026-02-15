from t_tech.invest import Client, CandleInterval, GetAssetFundamentalsRequest
from datetime import datetime, timedelta
import pandas as pd


class MyClient(Client):
    def __init__(self, token):
        self.token = token
        with Client(token) as client:
            # получение списка акций
            self.shares = client.instruments.shares().instruments

            # фильтрация акций по классу и исключение акций для квалифицированных инвесторов
            # TQBR — аббревиатура, которая означает «Торги Квалифицированных Биржевых Рынков».
            # Это основной режим торгов на Московской бирже, предназначенный для торговли акциями.
            # for_qual_investor_flag = False - отбирает только акции, предназначенные для неквалифицированных инвесторов.
            # на выходe получаем словарь с {тикер: {figi, name, UID}}
            self.tickers_TQBR_nocval = {share.ticker: {'figi': share.figi, 'name': share.name,'UID': share.asset_uid} for share in self.shares if share.class_code == 'TQBR' and not share.for_qual_investor_flag}


    def get_candles_and_fundamentals(self):
        """Метод получения свечей за 5 лет с сохранением в .csv и последующим его обновлением"""
        with Client(self.token) as client:
            self.candles_data = {}

            # дата на сегодняшний день
            now = datetime.now()

            try:
                # пробуем выгрузить данные из файла
                old_candles_df = pd.read_csv('candles.csv', index_col='Date', parse_dates=['Date'])
                # количество дней без обновления данных
                days = (now - old_candles_df.index[-1]).days

            except FileNotFoundError:
                days = now - timedelta(days=365*5)

            # дата 5 лет назад
            start_date = now - timedelta(days=365*5)

            if days > 1:
                # получаем свечи для каждого тикера за указанный срок
                for ticker, values in self.tickers_TQBR_nocval.items():
                    candles = client.market_data.get_candles(figi=values['figi'], from_=start_date, to=now, interval=CandleInterval.CANDLE_INTERVAL_DAY).candles
                    df = pd.DataFrame([
                        {
                        'Date': candle.time.date(),
                        'Close': self._quotation_to_float(candle.close) # берем только свечи закрытия
                        }
                        for candle in candles])

                    df = df.set_index('Date') # установка индекса по 'Date'
                    self.candles_data[ticker] = df["Close"]

                 # объединение DataFrame
                candles_df = pd.DataFrame(self.candles_data) # создание DataFrame из словаря
                candles_df.to_csv('candles.csv', encoding='utf-8') # сохранение DataFrame в CSV файл

                print('Файл свечей создан')

                self._get_fundamentals()
            else:
                print('Данные не требуют обновления.')


    def _get_fundamentals(self):
        """Метод получения отчётностей по каждой акции"""
        with Client(self.token) as client:
            # получение фундаментальных данных
            self.fundamentals_data = {}
            for ticker, values in self.tickers_TQBR_nocval.items():
                #uid = self.tickers_assets[ticker]
                fundamentals = client.instruments.get_asset_fundamentals(request=GetAssetFundamentalsRequest(assets=[values['UID']],)).fundamentals

                self.fundamentals_data[ticker] = {
                # 1. Оценка стоимости
                'P/E_TTM': fundamentals[0].pe_ratio_ttm,
                'P/B_TTM': fundamentals[0].price_to_book_ttm,

                # 2. Прибыльность и эффективность
                'ROE': fundamentals[0].roe,

                # 3. Рост
                'Revenue_Growth_YOY': fundamentals[0].one_year_annual_revenue_growth_rate,

                # 4. Дивиденды
                'Div_Yield': fundamentals[0].dividend_yield_daily_ttm,

                # 5. Финансовая устойчивость
                'Debt_To_Equity': fundamentals[0].total_debt_to_equity_mrq,

                # 6. Рыночные характеристики
                'Beta': fundamentals[0].beta,

                # 7. Дополнительные метрики
                'FCF_Yield': fundamentals[0].price_to_free_cash_flow_ttm
            }

        fundamentals_df = pd.DataFrame(self.fundamentals_data) # создание DataFrame из словаря
        fundamentals_df.to_csv('fundamentals.csv', encoding='utf-8') # сохранение DataFrame в CSV файл

        print('Файл отчётностей создан')


    # API Т-банка возвращает стоимость активов в формате quotation - нужна фанкция для конвертации в привычные метрики
    def _quotation_to_float(self, quotation):
        """Преобразует объект Quotation в float"""
        return round(quotation.units + quotation.nano / 1000000000, 2)

    def get_ticker_and_names(self):
        return [(ticker, values['name']) for ticker, values in self.tickers_TQBR_nocval.items()]
