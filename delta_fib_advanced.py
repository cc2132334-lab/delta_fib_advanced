import time
from datetime import datetime
import pytz
import requests

# --- TELEGRAM CONFIG ---
BOT_TOKEN = "8626042409:AAHElsiJD8_Jk9R7r5VHUj8fPjcl8Meacp4"
CHAT_ID = "706694019"

DELTA_SYMBOLS = ["BTCUSD", "ETHUSD"]

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, data=payload, timeout=15)
        if r.status_code == 200:
            print("Telegram Alert Sent Successfully!")
        else:
            print(f"Telegram API Error: {r.text}")
    except Exception as e:
        print(f"Connection Error: {e}")

def get_delta_candles(symbol, resolution="5m", count=288):
    end_time = int(time.time())
    start_time = end_time - (count * 5 * 60)
        
    url = "https://api.india.delta.exchange/v2/history/candles"
    params = {
        "symbol": symbol,
        "resolution": resolution,
        "start": start_time,
        "end": end_time
    }
    headers = {"Accept": "application/json"}
    
    try:
        res = requests.get(url, params=params, headers=headers, timeout=15).json()
        raw_candles = res.get("result", [])
        if not raw_candles:
            return []
            
        candles = []
        for c in raw_candles:
            if isinstance(c, dict):
                candles.append({
                    "time": int(c.get("time", c.get("t", 0))),
                    "open": float(c.get("open", c.get("o", 0))),
                    "high": float(c.get("high", c.get("h", 0))),
                    "low": float(c.get("low", c.get("l", 0))),
                    "close": float(c.get("close", c.get("c", 0))),
                    "volume": float(c.get("volume", c.get("v", 0)))
                })
            elif isinstance(c, list):
                candles.append({
                    "time": int(c[0]),
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "volume": float(c[5])
                })
        candles.reverse()  # Oldest -> Newest
        return candles
    except Exception as e:
        print(f"Fetch Error ({symbol}): {e}")
        return []

def run_fibonacci_scanner():
    ist = pytz.timezone('Asia/Kolkata')
    today_str = datetime.now(ist).strftime("%Y-%m-%d")
    print(f"[{datetime.now(ist).strftime('%H:%M:%S')}] Scanning Intraday Fibonacci Setups...")

    for sym in DELTA_SYMBOLS:
        try:
            candles = get_delta_candles(sym, resolution="5m", count=288)
            if len(candles) < 20:
                continue

            # આજના દિવસની કેન્ડલ્સ (00:00 IST પછી)
            today_candles = []
            for c in candles:
                c_date = datetime.fromtimestamp(c["time"], ist).strftime("%Y-%m-%d")
                if c_date == today_str:
                    today_candles.append(c)

            eval_candles = today_candles if len(today_candles) >= 15 else candles[-60:]

            # લેટેસ્ટ ક્લોઝ થયેલી કન્ફર્મેશન કેન્ડલ (-2) અને અગાઉની (-3)
            latest = eval_candles[-2]
            prev = eval_candles[-3]

            c_time = datetime.fromtimestamp(latest["time"], ist).strftime("%H:%M")
            c_open = latest["open"]
            c_high = latest["high"]
            c_low = latest["low"]
            c_close = latest["close"]

            search_window = eval_candles[:-2]
            if len(search_window) < 10:
                continue

            # ==========================================
            # 🟢 BUY SETUP (Day Low ➔ Swing High ➔ Pullback)
            # ==========================================
            all_lows = [x["low"] for x in search_window]
            day_low = min(all_lows)
            day_low_idx = all_lows.index(day_low)

            post_low_window = search_window[day_low_idx:]
            if len(post_low_window) >= 2:
                post_low_highs = [x["high"] for x in post_low_window]
                swing_high = max(post_low_highs)
                swing_high_rel_idx = post_low_highs.index(swing_high)
                swing_high_idx = day_low_idx + swing_high_rel_idx

                if swing_high_idx > day_low_idx:
                    time_day_low = datetime.fromtimestamp(search_window[day_low_idx]["time"], ist).strftime("%H:%M")
                    time_swing_high = datetime.fromtimestamp(search_window[swing_high_idx]["time"], ist).strftime("%H:%M")

                    swing_range = swing_high - day_low
                    if swing_range > 0:
                        fib_50 = swing_high - (0.50 * swing_range)
                        fib_618 = swing_high - (0.618 * swing_range)

                        touched_zone = (prev["low"] <= fib_50) or (c_low <= fib_50)
                        held_above_618 = (c_close >= fib_618 * 0.998)
                        is_green = (c_close > c_open)

                        if touched_zone and held_above_618 and is_green:
                            # Entry: Confirmation કેન્ડલના High પરથી
                            entry_price = c_high

                            # SL Logic
                            if c_low < fib_618:
                                stop_loss = c_low
                                sl_type = f"Candle Low (${stop_loss:,.2f})"
                            else:
                                stop_loss = fib_618
                                sl_type = f"Fib 0.618 Level (${stop_loss:,.2f})"

                            risk = entry_price - stop_loss
                            if risk > 0:
                                t1 = entry_price + (1.0 * risk)
                                t2 = entry_price + (2.0 * risk)
                                t3 = entry_price + (3.0 * risk)
                                t4 = entry_price + (4.0 * risk)
                                t5 = entry_price + (5.0 * risk)

                                alert_buy = (
                                    f"🎯 *FIBONACCI 0.5-0.618 BUY SIGNAL*\n"
                                    f"💎 *Pair:* `{sym}` (5-Min)\n"
                                    f"🟢 *Signal:* *STRONG BUY (Pullback Setup)*\n"
                                    f"━━━━━━━━━━━━━━━━━━━━\n"
                                    f"📉 *Day Low:* `${day_low:,.2f}` _({time_day_low} IST)_\n"
                                    f"📈 *Swing High:* `${swing_high:,.2f}` _({time_swing_high} IST)_\n"
                                    f"🟡 *Fib 50.0%:* `${fib_50:,.2f}`\n"
                                    f"🟠 *Fib 61.8%:* `${fib_618:,.2f}`\n"
                                    f"━━━━━━━━━━━━━━━━━━━━\n"
                                    f"🚀 *Entry (Candle High):* `${entry_price:,.2f}`\n"
                                    f"🛑 *Stop Loss:* `${stop_loss:,.2f}` _({sl_type})_\n"
                                    f"📏 *Risk (1R):* `${risk:,.2f}`\n"
                                    f"━━━━━━━━━━━━━━━━━━━━\n"
                                    f"🎯 *TARGET LEVELS (Risk-Reward):*\n"
                                    f"  • *1:1 Target:* `${t1:,.2f}`\n"
                                    f"  • *1:2 Target:* `${t2:,.2f}`\n"
                                    f"  • *1:3 Target:* `${t3:,.2f}`\n"
                                    f"  • *1:4 Target:* `${t4:,.2f}`\n"
                                    f"  • *1:5 Target:* `${t5:,.2f}`\n"
                                    f"━━━━━━━━━━━━━━━━━━━━\n"
                                    f"⏱ *Trigger Candle:* `{c_time} IST`"
                                )
                                send_telegram(alert_buy)
                                continue

            # ==========================================
            # 🔴 SELL SETUP (Day High ➔ Swing Low ➔ Pullback)
            # ==========================================
            all_highs = [x["high"] for x in search_window]
            day_high = max(all_highs)
            day_high_idx = all_highs.index(day_high)

            post_high_window = search_window[day_high_idx:]
            if len(post_high_window) >= 2:
                post_high_lows = [x["low"] for x in post_high_window]
                swing_low = min(post_high_lows)
                swing_low_rel_idx = post_high_lows.index(swing_low)
                swing_low_idx = day_high_idx + swing_low_rel_idx

                if swing_low_idx > day_high_idx:
                    time_day_high = datetime.fromtimestamp(search_window[day_high_idx]["time"], ist).strftime("%H:%M")
                    time_swing_low = datetime.fromtimestamp(search_window[swing_low_idx]["time"], ist).strftime("%H:%M")

                    swing_range = day_high - swing_low
                    if swing_range > 0:
                        fib_50 = swing_low + (0.50 * swing_range)
                        fib_618 = swing_low + (0.618 * swing_range)

                        touched_zone = (prev["high"] >= fib_50) or (c_high >= fib_50)
                        held_below_618 = (c_close <= fib_618 * 1.002)
                        is_red = (c_close < c_open)

                        if touched_zone and held_below_618 and is_red:
                            # Entry: Confirmation કેન્ડલના Low પરથી
                            entry_price = c_low

                            # SL Logic
                            if c_high > fib_618:
                                stop_loss = c_high
                                sl_type = f"Candle High (${stop_loss:,.2f})"
                            else:
                                stop_loss = fib_618
                                sl_type = f"Fib 0.618 Level (${stop_loss:,.2f})"

                            risk = stop_loss - entry_price
                            if risk > 0:
                                t1 = entry_price - (1.0 * risk)
                                t2 = entry_price - (2.0 * risk)
                                t3 = entry_price - (3.0 * risk)
                                t4 = entry_price - (4.0 * risk)
                                t5 = entry_price - (5.0 * risk)

                                alert_sell = (
                                    f"🎯 *FIBONACCI 0.5-0.618 SELL SIGNAL*\n"
                                    f"💎 *Pair:* `{sym}` (5-Min)\n"
                                    f"🔴 *Signal:* *STRONG SELL (Pullback Setup)*\n"
                                    f"━━━━━━━━━━━━━━━━━━━━\n"
                                    f"📈 *Day High:* `${day_high:,.2f}` _({time_day_high} IST)_\n"
                                    f"📉 *Swing Low:* `${swing_low:,.2f}` _({time_swing_low} IST)_\n"
                                    f"🟠 *Fib 61.8%:* `${fib_618:,.2f}`\n"
                                    f"🟡 *Fib 50.0%:* `${fib_50:,.2f}`\n"
                                    f"━━━━━━━━━━━━━━━━━━━━\n"
                                    f"🔻 *Entry (Candle Low):* `${entry_price:,.2f}`\n"
                                    f"🛑 *Stop Loss:* `${stop_loss:,.2f}` _({sl_type})_\n"
                                    f"📏 *Risk (1R):* `${risk:,.2f}`\n"
                                    f"━━━━━━━━━━━━━━━━━━━━\n"
                                    f"🎯 *TARGET LEVELS (Risk-Reward):*\n"
                                    f"  • *1:1 Target:* `${t1:,.2f}`\n"
                                    f"  • *1:2 Target:* `${t2:,.2f}`\n"
                                    f"  • *1:3 Target:* `${t3:,.2f}`\n"
                                    f"  • *1:4 Target:* `${t4:,.2f}`\n"
                                    f"  • *1:5 Target:* `${t5:,.2f}`\n"
                                    f"━━━━━━━━━━━━━━━━━━━━\n"
                                    f"⏱ *Trigger Candle:* `{c_time} IST`"
                                )
                                send_telegram(alert_sell)
                                continue

        except Exception as e:
            print(f"Error checking {sym}: {e}")
            continue

if __name__ == "__main__":
    run_fibonacci_scanner()

