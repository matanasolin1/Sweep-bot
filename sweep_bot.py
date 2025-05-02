import requests
import pandas as pd
import time

BOT_TOKEN = '8195288813:AAFjnWDf1sP8WnzhEgar3zBh-wqVgp7Hctw'
CHAT_ID = '5421253351'

def get_all_usdt_symbols():
    url = 'https://api.binance.com/api/v3/exchangeInfo'
    data = requests.get(url).json()
    return [s['symbol'] for s in data['symbols'] if s['quoteAsset'] == 'USDT' and s['status'] == 'TRADING']

def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    data = {'chat_id': CHAT_ID, 'text': message}
    requests.post(url, data=data)

def get_klines(symbol, interval, limit=500):
    url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}'
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'
    ])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].astype(float)
    return df

def check_sweep(symbol):
    try:
        daily = get_klines(symbol, '1d', 3)
        if len(daily) < 2:
            return
        prev_day = daily.iloc[-2]
        prev_high = prev_day['high']
        prev_low = prev_day['low']

        df15 = get_klines(symbol, '15m', 200)
        breakout_index = None
        breakout_high = None
        breakout_low = None
        direction = None

        for i in range(len(df15)):
            row = df15.iloc[i]
            if row['high'] > prev_high:
                breakout_index = i
                breakout_high = row['high']
                breakout_low = row['low']
                direction = 'up'
                break
            elif row['low'] < prev_low:
                breakout_index = i
                breakout_high = row['high']
                breakout_low = row['low']
                direction = 'down'
                break

        if breakout_index is None:
            return

        for j in range(breakout_index + 1, len(df15)):
            row = df15.iloc[j]
            if direction == 'up' and row['close'] < breakout_low:
                msg = (
                    f'{symbol} - 🔴 Short Entry Signal!\n'
                    f'Crossed above previous day\'s high: {breakout_high:.2f}'
                )
                send_telegram_message(msg)
                return
            elif direction == 'down' and row['close'] > breakout_high:
                msg = (
                    f'{symbol} - 🟢 Long Entry Signal!\n'
                    f'Crossed below previous day\'s low: {breakout_low:.2f}'
                )
                send_telegram_message(msg)
                return

    except Exception as e:
        print(f"שגיאה ב-{symbol}: {e}")

symbols = get_all_usdt_symbols()
while True:
    for symbol in symbols:
        check_sweep(symbol)
        time.sleep(1)
