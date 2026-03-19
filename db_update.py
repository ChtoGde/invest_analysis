import pandas as pd
from datetime import datetime



def db_update(db, analysis):

    tickers_in_db = pd.read_sql_query("""SELECT * FROM tickers""",con=db.conn).values
    new_tickers = pd.read_csv('candles.csv').columns[1:]
    tickers_records = ', '.join([f"('{ticker}')" for ticker in new_tickers if ticker not in tickers_in_db])
    columns = '(name)'

    if tickers_records:
        db.insert_into(table='tickers',columns=columns, values=tickers_records)

    recommendations = analysis.get_recommendations()
    recommendations_records = ', '.join([f"{tuple(recommendation)}" for recommendation in recommendations.values])
    columns = '(name, start_price, support_line, resistance_line, buy_by, sell_by, RSI, Z_score, P_E, ROE, div_yield, signal, score)'

    db.clear_table('recommendations')
    db.insert_into(table='recommendations', columns=columns, values=recommendations_records)


    table_of_signals = pd.read_sql_query("""SELECT * FROM signals""", db.conn).set_index('ticker_name')
    signals = pd.concat([analysis.get_buy_list(), analysis.get_sell_list()])
    prices = pd.read_csv('candles.csv').set_index('Date')
    columns_signals = '(ticker_name, start_date, signal, start_price, price_now, score)'
    columns_history = '(ticker_name, signal, start_date, end_date, start_price, end_price, delta)'

    for ticker in table_of_signals.index:
        price_now = prices[ticker].sort_index().iloc[-1]
        db.update_table('signals', 'price_now', price_now, {'ticker_name': ticker})

    for ticker, signal, price_now, score in signals[['Акция', 'Сигнал', 'Актуальная цена', 'Score']].itertuples(index=False):
        if ticker in table_of_signals.index:
            db.update_table('signals', 'price_now', price_now, {'ticker_name': ticker})
            db.update_table('signals', 'score', score, {'ticker_name': ticker})
            if table_of_signals.loc[ticker, 'signal'] != signal:
                db.insert_into('history', columns_history, f"""({ticker},
                            {table_of_signals.loc[ticker, 'signal']},
                            {table_of_signals.loc[ticker, 'start_date']},
                            '{datetime.date().isoformat()}',
                            {table_of_signals.loc[ticker, 'start_price']}
                            {price_now},
                            {round((price_now - table_of_signals.loc[ticker, 'start_price']) / table_of_signals.loc[ticker, 'start_price'], 2)})""")

                db.delete_from('signals', {'ticker_name': ticker})
                db.insert_into('signals', columns_signals, f"('{ticker}', '{datetime.now().date().isoformat()}', '{signal}', {price_now}, {price_now}, {score})")
        else:
            db.insert_into('signals', columns_signals, f"('{ticker}', '{datetime.now().date().isoformat()}', '{signal}', {price_now}, {price_now}, {score})")

    db.close()
    print('База данных обновлена')
