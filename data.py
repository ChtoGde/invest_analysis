from t_tech.invest import Client, CandleInterval, GetAssetFundamentalsRequest
from datetime import datetime, timedelta
import pandas as pd


class MyClient(Client):
    def __init__(self, token):
        self.token = token
        with Client(token) as client:
            # получение списка акций
            self.shares = client.instruments.shares().instruments
            # получение UID акций
            self.assets = client.instruments.get_assets(request=GetAssetFundamentalsRequest()).assets

            # фильтрация акций по классу и исключение акций для квалифицированных инвесторов
            # TQBR — аббревиатура, которая означает «Торги Квалифицированных Биржевых Рынков».
            # Это основной режим торгов на Московской бирже, предназначенный для торговли акциями.
            # for_qual_investor_flag = False - отбирает только акции, предназначенные для неквалифицированных инвесторов
            self.tickers_figi = {share.ticker: share.figi for share in self.shares if share.class_code == 'TQBR' and not share.for_qual_investor_flag}
            # получаем uid акций после фильтрации
            self.tickers_assets = {}
            for ticker, figi in self.tickers_figi.items():
                for asset in self.assets:
                    for instrument in asset.instruments:
                        if instrument.figi == figi:
                            self.tickers_assets[ticker] = asset.uid


    def get_candles(self):
        """Метод получения свечей за 5 лет с сохранением в .csv"""
        with Client(self.token) as client:
            self.candles_data = {}

            # определяем срок от "5 лет назад" до "сегодня"
            now = datetime.now()
            five_years_old = now - timedelta(days=365*5)

            # получаем свечи для каждого тикера за указанный срок
            for ticker, figi in self.tickers_figi.items():
                candles = client.market_data.get_candles(figi=figi, from_=five_years_old, to=now, interval=CandleInterval.CANDLE_INTERVAL_DAY).candles
                df = pd.DataFrame([{
                    "Date": candle.time.date(),
                    "Close": self._quotation_to_float(candle.close) # берем только свечи закрытия
                    }
                    for candle in candles])
                df.set_index("Date", inplace=True) # установка индекса по 'Date'
                self.candles_data[ticker] = df["Close"]

        candles_df = pd.DataFrame(self.candles_data) # создание DataFrame из словаря
        candles_df.to_csv('candles.csv', encoding='utf-8') # сохранение DataFrame в CSV файл

        print('Файл свечей создан')


    def get_fundamentals(self):
        """Метод получения отчётностей по каждой акции"""
        with Client(self.token) as client:
            # получение фундаментальных данных
            self.fundamentals_data = {}
            for ticker in self.tickers_figi.keys() & self.tickers_assets.keys():
                uid = self.tickers_assets[ticker]
                fundamentals = client.instruments.get_asset_fundamentals(request=GetAssetFundamentalsRequest(assets=[uid],)).fundamentals

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
