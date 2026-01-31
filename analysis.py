import numpy as np
import pandas as pd
from sklearn.preprocessing import minmax_scale
from datetime import datetime

np.random.seed(42)  # Для воспроизводимости результатов



class Analysis():
    def __init__(self, prices, fundamentals):
        # Загрузка данных
        self.__prices = prices
        self.__fundamentals = fundamentals
        # Вычисление процентного изменения цены на каждый день(вчера - сегодня) с удалением NaN
        self.__returns = self.__prices.ffill().pct_change().dropna()
        # Вычисление волатильности
        self.__volatility = self.__returns.std()
        # Объединение данных
        self.__features = pd.DataFrame({
                'Return': self.__returns.mean(),
                'Volatility': self.__volatility
        })
        # Добавление финансовых показателей
        for col in self.__fundamentals.columns:
            self.__features[col] = self.__fundamentals[col].astype(float)
        # Удаляем строки с NaN
        self.__features.replace([np.inf, -np.inf], np.nan, inplace=True)
        self.__features.dropna(inplace=True)
        # Фильтрация по условиям (именно тут убираем рисковые активы можете выставить показатели на своё усмотрение)
        self.__cleaned = self.__features[
            (self.__features['ROE'] >= 3) &
            (self.__features['ROE'] < 50) &
            (self.__features['P/E_TTM'] > 0.5) &
            (self.__features['P/E_TTM'] < 30) &
            (self.__features['Div_Yield'] >= 0) &
            (self.__features['Div_Yield'] <= 15) &
            (self.__features['Volatility'] < 0.4)
        ]
        # Удаление выбросов по IQR
        self.__cleaned = self.__remove_outliers_iqr(self.__cleaned, 'ROE')
        self.__cleaned = self.__remove_outliers_iqr(self.__cleaned, 'P/E_TTM')
        # убираем очень дешевые акции (можете убрать код до следующего комментария, если это для вас не принципиально)
        self.__cleaned = self.__cleaned[self.__cleaned.index.isin(self.__prices.columns)]
        price_last = self.__prices.loc[:, self.__cleaned.index].iloc[-1]
        valid_tickers = price_last[price_last > 0.1].index
        self.__cleaned = self.__cleaned[self.__cleaned.index.isin(valid_tickers)]
        # Подготовка данных для нормализации (подводим к понятным значениям для компьютера)
        norm_metrics = pd.DataFrame(index=self.__cleaned.index)
        norm_metrics['ROE'] = self.__cleaned['ROE']
        norm_metrics['P/E_TTM'] = self.__cleaned['P/E_TTM']
        norm_metrics['Div_Yield'] = self.__cleaned['Div_Yield'].clip(0, 15)  # ограничение по дивидендам(в моём случае от 0% до 15%)
        # Нормализация: 0–100%, затем масштаб под max баллы
        norm_metrics['ROE_score'] = minmax_scale(norm_metrics['ROE'], feature_range=(0, 3))
        norm_metrics['Div_score'] = minmax_scale(norm_metrics['Div_Yield'], feature_range=(0, 0.5))
        # P/E: чем ниже, тем лучше → инвертируем
        pe_scaled = minmax_scale(norm_metrics['P/E_TTM'], feature_range=(0, 3))
        norm_metrics['P/E_score'] = 3 - pe_scaled  # инверсия
        # Сохраняем в self.__cleaned
        self.__cleaned = self.__cleaned.join(norm_metrics[['ROE_score', 'P/E_score', 'Div_score']])


    def recomendations(self):
        """Основная функция анализа акций и создания рекомендаций"""
        results = []

        for stock in self.__cleaned.index:
            data = self.__prices[stock].dropna()

            # Проверка на минимальное количество данных(от 200 дней, игнорируем молодые акции)
            if len(data) < 200:
                continue

            # Получение актуальной цены
            current_price = data.iloc[-1]
            # Вычисление RSI и Z-Score
            rsi_val = self.__rsi(data).dropna()
            z_val = self.__z_score(data).dropna()
            calc_rsi = rsi_val.iloc[-1] if len(rsi_val) > 0 else np.nan
            calc_z = z_val.iloc[-1] if len(z_val) > 0 else np.nan
            # Вычисление линии поддержки и сопротивления
            support, resistance = self.__support_resistance(data)
            # Получение финансовых показателей
            pe = self.__cleaned.loc[stock, 'P/E_TTM']
            roe = self.__cleaned.loc[stock, 'ROE']
            div_yield = self.__cleaned.loc[stock, 'Div_Yield']

            # Начисляем баллы каждой акции
            score = 0.0

            # 1. P/E (0–3), уже нормализован
            score += self.__cleaned.loc[stock, 'P/E_score']

            # 2. ROE (0–3)
            score += self.__cleaned.loc[stock, 'ROE_score']

            # 3. RSI (0–2)
            if not pd.isna(calc_rsi):
                if calc_rsi < 30:
                    score += 2.0
                elif calc_rsi < 40:
                    score += 1.5
                elif calc_rsi < 50:
                    score += 0.5

            # 4. Z-Score (0–1)
            if not pd.isna(calc_z):
                if calc_z < -1:
                    score += 1.0
                elif calc_z < 0:
                    score += 0.5

            # 5. Цена у поддержки (0–1)
            if current_price <= support * 1.05:
                score += 1.0

            # 6. Дивиденды (0–0.5)
            score += self.__cleaned.loc[stock, 'Div_score']

            # Сигналы
            buy_signal = (score >= 6) and (not pd.isna(calc_rsi)) and (calc_rsi < 50) and (pe < 15) and (roe > 10)
            sell_signal = (not pd.isna(calc_rsi)) and (calc_rsi > 70) and (not pd.isna(calc_z)) and (calc_z > 2)
            # Цены для лучшей покупки и продажи
            ideal_buy_price = max(support, current_price * 0.95, (support + current_price) / 2)
            ideal_sell_price = min(resistance, current_price * 1.15)

            # Формируем результат
            results.append({
                'Акция': stock,
                'Актуальная цена': round(current_price, 2),
                'Поддержка': round(support, 2),
                'Сопротивление': round(resistance, 2),
                'Покупать по': round(ideal_buy_price, 2),
                'Продавать по': round(ideal_sell_price, 2),
                'RSI': round(calc_rsi, 2) if not pd.isna(calc_rsi) else None,
                'Z-Score': round(calc_z, 2) if not pd.isna(calc_z) else None,
                'P/E': round(pe, 2),
                'ROE': round(roe, 2),
                'Div Yield': round(div_yield, 2),
                'Сигнал к покупке': '✅ Да' if buy_signal else '❌ Нет',
                'Сигнал к продаже': '✅ Да' if sell_signal else '❌ Нет',
                'Score': round(score, 2)
            })

        recomendations = pd.DataFrame(results)
        # генерируем список "к покупке"
        buy_list = recomendations[recomendations['Сигнал к покупке'] == '✅ Да'].copy()
        buy_list = buy_list.sort_values(by='Score', ascending=False)
        # генерируем список "к продаже"
        sell_list = recomendations[recomendations['Сигнал к продаже'] == '✅ Да'].copy()
        sell_list = sell_list.sort_values(by='RSI', ascending=False)

        return buy_list, sell_list


    def save_to_excel(self, buy_list, sell_list):
        """Сохранение результатов в Excel"""
        # Объединение двух сигналов в один датафрейм
        signals = pd.concat([
            buy_list[['Акция', 'Актуальная цена']].assign(Сигнал='Покупка'),
            sell_list[['Акция', 'Актуальная цена']].assign(Сигнал='Продажа')
        ])

        # чтение Exel файла
        stock_tracker_0 = pd.read_excel('stock_tracker.xlsx', index_col='Акция', sheet_name=0, parse_dates=['Дата рекомендации', 'Дата'])
        stock_tracker_1 = pd.read_excel('stock_tracker.xlsx', index_col='Акция', sheet_name=1)

        for ticker in stock_tracker_0.index:
            if ticker not in signals[['Акция']]:
                stock_tracker_0.loc[ticker, 'Актуальная цена'] = self.__prices[ticker].iloc[-1]
                stock_tracker_0.loc[ticker,'Изменение (%)'] = round((stock_tracker_0.loc[ticker, 'Актуальная цена'] - stock_tracker_0.loc[ticker, 'Начальная цена']) / stock_tracker_0.loc[ticker,'Начальная цена'] * 100, 1)

        for ticker, sign, price in signals[['Акция','Сигнал', 'Актуальная цена']].itertuples(index=False):
            # если тикер уже в файле
            if ticker in stock_tracker_0.index:
                # при этом сигналы тикера совпадают с сигналом в файле:
                if stock_tracker_0.loc[ticker, 'Сигнал'] == sign:
                    # то обновляем поля "Дата", "Актуальная цена" и "Изменение (%)"
                    stock_tracker_0.loc[ticker,'Дата'] = pd.Timestamp.now().normalize()
                    stock_tracker_0.loc[ticker,'Актуальная цена'] = price
                    stock_tracker_0.loc[ticker,'Изменение (%)'] = round((stock_tracker_0.loc[ticker, 'Актуальная цена'] - stock_tracker_0.loc[ticker, 'Начальная цена']) / stock_tracker_0.loc[ticker,'Начальная цена'] * 100, 1)
                # если сигнал не совпадает то переносим данные в лист "Trade_history"
                elif stock_tracker_0.loc[ticker, 'Сигнал'] != sign:
                    # Задаём новые поля "Акция", "Сигнал", "Цена", "Результат(%)", "Кол-во дней"(сколько сигнал просуществовал не меняясь)
                    stock_tracker_1 = pd.concat([stock_tracker_1, pd.DataFrame([{'Акция': ticker}]).set_index('Акция')])
                    stock_tracker_1.loc[ticker, 'Сигнал'] = stock_tracker_0.loc[ticker, 'Сигнал']
                    stock_tracker_1.loc[ticker, 'Цена'] = price
                    stock_tracker_1.loc[ticker, 'Результат(%)'] = round((price - stock_tracker_0.loc[ticker, 'Начальная цена']) / stock_tracker_0.loc[ticker,'Начальная цена'] * 100, 1)
                    stock_tracker_1.loc[ticker, 'Кол-во дней'] = (datetime.now().date() - stock_tracker_0.loc[ticker, 'Дата рекомендации'].to_pydatetime().date()).days
                    # удаляем тикер из листа "Recommendations"
                    stock_tracker_0.drop(ticker, inplace=True)
            # если тикера нет в файле:
            else:
                # добавляем поля "Акция", "Начальная цена", "Сигнал", "Дата рекомендации"
                stock_tracker_0 = pd.concat([stock_tracker_0, pd.DataFrame([{'Акция': ticker}]).set_index('Акция')])
                stock_tracker_0.loc[ticker, 'Начальная цена'] = price
                stock_tracker_0.loc[ticker, 'Сигнал'] = sign
                stock_tracker_0.loc[ticker, 'Дата рекомендации'] = pd.Timestamp.now().normalize()


        # запись в Exel файл
        with pd.ExcelWriter('stock_tracker.xlsx', engine='openpyxl', mode='w') as writer:
            stock_tracker_0.to_excel(writer, index=True, sheet_name='Recomendations')
            stock_tracker_1.to_excel(writer, index=True, sheet_name='Trade_History')

            print('Запись в Exel файл успешно завершена')




    def __remove_outliers_iqr(self, df, column):
        """Метод удаления выбросов по IQR"""
        Q1 = df[column].quantile(0.25)
        Q3 = df[column].quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - 1.5 * IQR
        upper = Q3 + 1.5 * IQR
        return df[(df[column] >= lower) & (df[column] <= upper)]


    def __rsi(self, series, window=14):
        """Метод расчета RSI"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss.replace(0, np.nan)  # Избежание деления на 0
        rsi = 100 - (100 / (1 + rs))
        return rsi


    def __z_score(self, series, window=60):
        """Метод расчета Z-Score"""
        mean = series.rolling(window=window).mean()
        std = series.rolling(window=window).std()
        z = (series - mean) / std
        return z


    def __support_resistance(self, series, window=200):
        """Метод расчета поддержки и сопротивления"""
        support = series.rolling(window=window).min()
        resistance = series.rolling(window=window).max()
        return support.iloc[-1], resistance.iloc[-1]
