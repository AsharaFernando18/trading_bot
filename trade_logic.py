import ccxt
import pandas as pd
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from telegram import Bot
from datetime import datetime
import csv
import os
from dotenv import load_dotenv

# === Load Env ===
load_dotenv()
api_key = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")
telegram_token = os.getenv("TELEGRAM_TOKEN")
chat_id = os.getenv("CHAT_ID")

# === Connect to Binance Futures Testnet ===
exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': api_secret,
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})
exchange.set_sandbox_mode(True)

# === Telegram Bot ===
bot = Bot(token=telegram_token)

# === Fetch Historical OHLCV Data ===
def fetch_data(symbol, timeframe='15m'):
    bars = exchange.fetch_ohlcv(symbol, timeframe, limit=200)
    df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
    df['time'] = pd.to_datetime(df['time'], unit='ms')
    return df

# === Generate Buy/Sell Signal ===
def generate_signal(df):
    df['ema50'] = EMAIndicator(close=df['close'], window=50).ema_indicator()
    df['ema200'] = EMAIndicator(close=df['close'], window=200).ema_indicator()
    df['rsi'] = RSIIndicator(close=df['close']).rsi()
    macd = MACD(close=df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()

    last = df.iloc[-1]

    if last['ema50'] > last['ema200'] and last['rsi'] < 30 and last['macd'] > last['macd_signal']:
        return 'buy'
    elif last['ema50'] < last['ema200'] and last['rsi'] > 70 and last['macd'] < last['macd_signal']:
        return 'sell'
    return None

# === Place Market Order with SL & TP ===
def place_order_with_sl_tp(symbol, side, qty, sl_pct=2, tp_pct=3):
    market_price = exchange.fetch_ticker(symbol)['last']
    entry = sl_price = tp_price = None

    if side == 'buy':
        entry = market_price
        sl_price = round(entry * (1 - sl_pct / 100), 2)
        tp_price = round(entry * (1 + tp_pct / 100), 2)

        exchange.create_market_buy_order(symbol, qty)

        # Take Profit
        exchange.create_order(symbol, 'market', 'sell', qty, None, {
            'stopPrice': tp_price,
            'reduceOnly': True,
            'type': 'TAKE_PROFIT_MARKET'
        })

        # Stop Loss
        exchange.create_order(symbol, 'market', 'sell', qty, None, {
            'stopPrice': sl_price,
            'reduceOnly': True,
            'type': 'STOP_MARKET'
        })

    elif side == 'sell':
        entry = market_price
        sl_price = round(entry * (1 + sl_pct / 100), 2)
        tp_price = round(entry * (1 - tp_pct / 100), 2)

        exchange.create_market_sell_order(symbol, qty)

        # Take Profit
        exchange.create_order(symbol, 'market', 'buy', qty, None, {
            'stopPrice': tp_price,
            'reduceOnly': True,
            'type': 'TAKE_PROFIT_MARKET'
        })

        # Stop Loss
        exchange.create_order(symbol, 'market', 'buy', qty, None, {
            'stopPrice': sl_price,
            'reduceOnly': True,
            'type': 'STOP_MARKET'
        })

    return entry, sl_price, tp_price

# === Send Telegram Message ===
def send_telegram(msg):
    try:
        bot.send_message(chat_id=chat_id, text=msg)
    except Exception as e:
        print("Telegram Error:", str(e))

# === Log Trade to CSV ===
def log_trade(entry_price, sl_price, tp_price, side):
    filename = 'trades.csv'
    fields = ['time', 'side', 'entry', 'stop_loss', 'take_profit']
    row = [datetime.now(), side, entry_price, sl_price, tp_price]
    try:
        with open(filename, 'a', newline='') as f:
            writer = csv.writer(f)
            if f.tell() == 0:
                writer.writerow(fields)
            writer.writerow(row)
    except Exception as e:
        print("Log Error:", str(e))
