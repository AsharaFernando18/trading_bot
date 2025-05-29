
import time
from trade_logic import fetch_data, generate_signal, place_order_with_sl_tp, send_telegram, log_trade

symbol = 'BTC/USDT'
qty = 0.001  # Position size per trade

while True:
    try:
        df = fetch_data(symbol)
        signal = generate_signal(df)

        if signal:
            entry, sl, tp = place_order_with_sl_tp(symbol, signal, qty)
            message = (
                f"🚨 {signal.upper()} Signal Executed\n"
                f"📈 Entry: {entry}\n"
                f"🛑 Stop Loss: {sl}\n"
                f"🎯 Take Profit: {tp}"
            )
            send_telegram(message)
            log_trade(entry, sl, tp, signal)
        else:
            print("🔍 No trading signal.")

    except Exception as e:
        print("❌ Error in main loop:", str(e))

    time.sleep(60 * 15)  # Sleep for 15 minutes
