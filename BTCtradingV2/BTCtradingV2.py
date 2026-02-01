import time
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import pandas_ta as ta
from binance.client import Client

# =======================
# LOAD CONFIG
# =======================
with open("config.json") as f:
    cfg = json.load(f)

SYMBOL = cfg["symbol"]
SCAN_INTERVAL = cfg["scan_interval_seconds"]

EMA_FAST = cfg["ema_fast"]
EMA_SLOW = cfg["ema_slow"]

# =======================
# BINANCE CLIENT
# =======================
client = Client()

# =======================
# TIMEZONE
# =======================
US_TZ = ZoneInfo("America/New_York")

# =======================
# HELPERS
# =======================
def get_structure_lookback(interval):
    return cfg.get("structure_lookbacks", {}).get(interval, 30)

# =======================
# DATA FETCH
# =======================
def fetch_klines(symbol, interval, limit=300):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(klines, columns=[
        "time","open","high","low","close","volume",
        "_","_","_","_","_","_"
    ])
    df["close"] = df["close"].astype(float)
    return df

# =======================
# MARKET BIAS
# =======================
def market_bias(df):
    ema_fast = ta.ema(df["close"], EMA_FAST)
    ema_slow = ta.ema(df["close"], EMA_SLOW)
    if ema_fast.iloc[-1] > ema_slow.iloc[-1]:
        return "BULL"
    elif ema_fast.iloc[-1] < ema_slow.iloc[-1]:
        return "BEAR"
    return "NEUTRAL"

# =======================
# MARKET STRUCTURE (CLOSES ONLY)
# =======================
def market_structure(df, interval):
    lookback = get_structure_lookback(interval)
    closes = df["close"].tail(lookback)

    half = lookback // 2
    older = closes.iloc[:half]
    recent = closes.iloc[half:]

    old_low = older.min()
    old_high = older.max()
    recent_low = recent.min()
    recent_high = recent.max()

    if recent_low > old_low and recent_high > old_high:
        return "BULLISH", 1
    elif recent_low < old_low and recent_high < old_high:
        return "BEARISH", -1
    else:
        return "RANGE", 0

# =======================
# TREND REGIME
# =======================
def is_trending(df):
    ema_fast = ta.ema(df["close"], EMA_FAST)
    ema_slow = ta.ema(df["close"], EMA_SLOW)
    price = df["close"].iloc[-1]
    spread = abs(ema_fast.iloc[-1] - ema_slow.iloc[-1]) / price
    return spread > 0.001

# =======================
# SIGNAL EVALUATION
# =======================
def evaluate():
    df_1h = fetch_klines(SYMBOL, Client.KLINE_INTERVAL_1HOUR)
    df_4h = fetch_klines(SYMBOL, Client.KLINE_INTERVAL_4HOUR)

    price = df_1h["close"].iloc[-1]
    timestamp = datetime.now(US_TZ)

    htf_bias = market_bias(df_4h)
    ltf_bias = market_bias(df_1h)
    structure_label, raw_structure_score = market_structure(
        df_1h, Client.KLINE_INTERVAL_1HOUR
    )
    trending = is_trending(df_1h)

    # =======================
    # DIRECTION-AWARE STRUCTURE SCORE (FIX)
    # =======================
    structure_score = 0
    if raw_structure_score != 0 and htf_bias != "NEUTRAL":
        if (raw_structure_score == 1 and htf_bias == "BULL") or \
           (raw_structure_score == -1 and htf_bias == "BEAR"):
            structure_score = 1
        else:
            structure_score = -1

    # =======================
    # CONFIDENCE (AGREEMENT SCORE)
    # =======================
    htf_score = 1 if htf_bias != "NEUTRAL" else 0
    ltf_score = 1 if ltf_bias != "NEUTRAL" else 0
    trend_score = 1 if trending else 0

    confidence = htf_score + ltf_score + structure_score + trend_score

    # =======================
    # DIRECTION & REASONING
    # =======================
    direction = "NONE"
    reason = []

    if confidence >= 3:
        if raw_structure_score > 0:
            if htf_bias == "BULL":
                direction = "LONG"
                reason.append("Structure and HTF bias aligned (trend continuation).")
            elif htf_bias == "BEAR":
                direction = "PULLBACK LONG (against HTF)."
                reason.append("Structure bullish but HTF bias bearish (pullback).")
        elif raw_structure_score < 0:
            if htf_bias == "BEAR":
                direction = "SHORT"
                reason.append("Structure and HTF bias aligned (trend continuation).")
            elif htf_bias == "BULL":
                direction = "PULLBACK SHORT (against HTF)."
                reason.append("Structure bearish but HTF bias bullish (pullback).")
        else:
            direction = "NONE"
            reason.append("Market in RANGE, no clear direction.")
    else:
        direction = "NONE"
        reason.append("Confidence too low for signal.")

    reason.append(f"Trending regime: {'Yes' if trending else 'No'}")

    # =======================
    # NEXT SCAN TIME
    # =======================
    next_scan = (timestamp + timedelta(seconds=SCAN_INTERVAL)).replace(
        second=0, microsecond=0
    )

    # =======================
    # PRINT OUTPUT
    # =======================
    print(
        f"\n[{timestamp.strftime('%Y-%m-%d %H:%M:%S')} {US_TZ.key}]"
        f"\nPrice: {price:.2f}"
        f"\nHTF Bias (4H): {htf_bias} ({htf_score})"
        f"\nLTF Bias (1H): {ltf_bias} ({ltf_score})"
        f"\nStructure: {structure_label} ({structure_score})"
        f"\nTrending Regime: {trending} ({trend_score})"
        f"\n-------------------------"
        f"\nConfidence Score: {confidence}"
        f"\nInferred Direction: {direction}"
        f"\nReasoning: {' | '.join(reason)}"
        f"\nNext scan at: {next_scan.strftime('%Y-%m-%d %H:%M:%S')} {US_TZ.key}\n"
    )

# =======================
# MAIN LOOP
# =======================
while True:
    evaluate()
    time.sleep(SCAN_INTERVAL)




