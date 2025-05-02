import requests
import pandas as pd
import time
import datetime

# === Telegram Settings ===
BOT_TOKEN = '8195288813:AAFjnWDf1sP8WnzhEgar3zBh-wqVgp7Hctw'
CHAT_ID = '5421253351'

# === TwelveData API Key ===
API_KEY = '5c38db1488fc49bcb0258a48e6773dc6'

# === רשימת מטבעות (6 בלבד כדי לעמוד במגבלת API) ===
symbols = [
    "BTC/USDT",
    "ETH/USDT",
    "XRP/USDT",
    "BNB/USDT",
    "SOL/USDT",
    "DOGE/USDT"
]

last_heartbeat_hour = None

def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    data = {'chat_id': CHAT_ID, 'text': message}
    requests.post(url, data=data)

# === הודעת בדיקה כל שעה עגולה ===
def send_heartbeat():
    global last_heartbeat_hour
    now = datetime.datetime.now()
    current_hour = now.hour
    if current_hour != last_heartbeat_hour and now.minute == 0:
        last_heartbeat_hour = current_hour
        send_telegram_message("בדיקה 🟦")

# === נתוני גרף מ-TwelveData ===
def get_klines(symbol, interval, outputsize=500):
    url = 'https://api.twelvedata.com/time_series'
    params = {
        'symbol': symbol,
        'interval': interval,
        'apikey': API_KEY,
        'outputsize': outputsize
    }
    response = requests.get(url, params=params)
    data = response.json()
    if 'values' not in data:
        print(f"שגיאה בנתונים עבור {symbol}: {data}")
        return pd.DataFrame()
    df = pd.DataFrame(data['values'])
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)
    df = df.sort_index()
    df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].astype(float)
    return df

# === אסטרטגיית Sweep ===
def check_sweep(symbol):
    try:
        print(f"בודק {symbol}...")
        daily = get_klines(symbol, '1day', 3)
        if len(daily) < 2:
            return
        prev_day = daily.iloc[-2]
        prev_high = prev_day['high']
        prev_low = prev_day['low']

        df15 = get_klines(symbol, '15min', 200)
        if df15.empty:
            return

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

# === ריצה מתמשכת ===
while True:
    start_time = time.time()
    for symbol in symbols:
        check_sweep(symbol)
    elapsed = time.time() - start_time
    wait_time = max(0, 90 - elapsed)
    send_heartbeat()
    print(f"סבב הסתיים, ממתין {wait_time:.1f} שניות...")
    time.sleep(wait_time)
