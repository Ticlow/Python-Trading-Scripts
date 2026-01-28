import time
import json
import smtplib
import csv
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from binance.client import Client
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# =======================
# CONFIG
# =======================
with open("config.json") as f:
    cfg = json.load(f)

ALERT_THRESHOLD = 0.2  # neuer Schwellenwert für Alerts

# =======================
# BINANCE CLIENT
# =======================
client = Client()

# =======================
# TIMEZONE (US MARKET)
# =======================
US_TZ = ZoneInfo("America/New_York")

# =======================
# CSV LOGGING
# =======================
CSV_FILE = "btc_signals_log.csv"
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp_et",
            "price_15m",
            "ema20_15m",
            "ema50_15m",
            "rsi_15m",
            "stoch_rsi_15m",
            "structure_15m",
            "bias_4h",
            "bias_1h",
            "signal",
            "confidence",
            "conf_4h",
            "conf_1h",
            "conf_structure",
            "conf_stoch",
            "conf_ema_dist"
        ])

# =======================
# EMAIL FUNCTION
# =======================
def send_email(subject, body):
    msg = MIMEMultipart()
    msg["From"] = cfg["email"]["sender"]
    msg["To"] = cfg["email"]["receiver"]
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(cfg["email"]["smtp_server"], cfg["email"]["smtp_port"])
        server.starttls()
        server.login(cfg["email"]["sender"], cfg["email"]["password"])
        server.send_message(msg)
        server.quit()
        print("📧 Email sent")
    except Exception as e:
        print("❌ Email error:", e)

# =======================
# WAIT UNTIL NEXT 5m (ET)
# =======================
def wait_until_next_5min_us():
    now = datetime.now(US_TZ)
    seconds = now.minute * 60 + now.second
    wait = 300 - (seconds % 300)
    if wait == 300:
        wait = 0
    next_run = now + timedelta(seconds=wait)
    print(f"⏳ Next scan at {next_run.strftime('%H:%M:%S')} ET")
    time.sleep(wait)

# =======================
# STATE (ANTI-SPAM)
# =======================
last_signal = None

print("🚀 BTC Algo started — synced to US (ET) 5m boundaries")

# =======================
# MAIN LOOP
# =======================
while True:
    wait_until_next_5min_us()
    timestamp_et = datetime.now(US_TZ).strftime("%Y-%m-%d %H:%M")
    print("\n-----------------------------")
    print(timestamp_et)

    # =======================
    # 4H BIAS
    # =======================
    klines_4h = client.get_klines(symbol=cfg["symbol"], interval=Client.KLINE_INTERVAL_4HOUR, limit=200)
    df_4h = pd.DataFrame(klines_4h, columns=[
        "time","open","high","low","close","volume",
        "close_time","qav","num_trades",
        "taker_base","taker_quote","ignore"
    ])
    df_4h["close"] = df_4h["close"].astype(float)
    df_4h["ema50"] = ta.ema(df_4h["close"], length=50)

    bias_4h_price = df_4h["close"].iloc[-2]
    bias_4h_ema50 = df_4h["ema50"].iloc[-2]
    bias_4h = "NEUTRAL"
    if bias_4h_price > bias_4h_ema50:
        bias_4h = "BULL"
    elif bias_4h_price < bias_4h_ema50:
        bias_4h = "BEAR"

    # =======================
    # 1H BIAS
    # =======================
    klines_1h = client.get_klines(symbol=cfg["symbol"], interval=Client.KLINE_INTERVAL_1HOUR, limit=200)
    df_1h = pd.DataFrame(klines_1h, columns=[
        "time","open","high","low","close","volume",
        "close_time","qav","num_trades",
        "taker_base","taker_quote","ignore"
    ])
    df_1h["close"] = df_1h["close"].astype(float)
    df_1h["ema50"] = ta.ema(df_1h["close"], length=50)

    bias_1h_price = df_1h["close"].iloc[-2]
    bias_1h_ema50 = df_1h["ema50"].iloc[-2]
    bias_1h = "NEUTRAL"
    if bias_1h_price > bias_1h_ema50:
        bias_1h = "BULL"
    elif bias_1h_price < bias_1h_ema50:
        bias_1h = "BEAR"

    # =======================
    # 15M DATA
    # =======================
    klines = client.get_klines(symbol=cfg["symbol"], interval=cfg["interval"], limit=cfg["candles"])
    df = pd.DataFrame(klines, columns=[
        "time","open","high","low","close","volume",
        "close_time","qav","num_trades",
        "taker_base","taker_quote","ignore"
    ])
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)

    df["ema20"] = ta.ema(df["close"], length=20)
    df["ema50"] = ta.ema(df["close"], length=50)
    df["rsi"] = ta.rsi(df["close"], length=14)
    stoch = ta.stochrsi(df["close"], length=14, smooth1=3, smooth2=3)
    df["stoch"] = stoch.iloc[:,0]

    price = df["close"].iloc[-2]
    ema20 = df["ema20"].iloc[-2]
    ema50 = df["ema50"].iloc[-2]
    rsi = df["rsi"].iloc[-2]
    stoch_val = df["stoch"].iloc[-2]

    recent_highs = df["high"].iloc[-10:-2]
    recent_lows = df["low"].iloc[-10:-2]
    structure = "range"
    if price > ema50 and df["low"].iloc[-2] > recent_lows.min():
        structure = "higher_low"
    elif price < ema50 and df["high"].iloc[-2] < recent_highs.max():
        structure = "lower_high"

    # =======================
    # PULLBACK SETUPS MIT 4H FILTER (RSI nur in Confidence)
    # =======================
    setup_long = (
        bias_4h == "BULL" and
        price > ema50 and
        ema20 <= price <= ema50*1.002 and
        structure == "higher_low"
    )

    setup_short = (
        bias_4h == "BEAR" and
        price < ema50 and
        ema50*0.998 <= price <= ema20 and
        structure == "lower_high"
    )

    signal = "NONE"
    confidence = 0.0
    if setup_long:
        signal = "LONG"
    elif setup_short:
        signal = "SHORT"

    # =======================
    # Confidence Komponenten
    # =======================
    conf_4h        = 0.4 if bias_4h != "NEUTRAL" else 0.15
    conf_1h        = 0.2 if ((signal=="LONG" and bias_1h=="BULL") or (signal=="SHORT" and bias_1h=="BEAR")) else 0.1
    conf_structure = 0.3 if structure in ["higher_low","lower_high"] else 0.0
    conf_stoch     = 0.2 if (stoch_val<20 or stoch_val>80) else 0.0
    conf_ema_dist  = 0.1 if abs(price-ema50)/price < 0.001 else 0.0

    confidence = min(conf_4h + conf_1h + conf_structure + conf_stoch + conf_ema_dist, 1.0)

    # =======================
    # Terminal Heatmap Farben nach Confidence
    # =======================
    color = "\033[0m"
    if signal=="LONG" and confidence>=0.6:
        color="\033[92m"   # grün
    elif signal=="SHORT" and confidence>=0.6:
        color="\033[91m" # rot
    elif signal!="NONE":
        color="\033[93m"                      # gelb

    print(color + f"Signal={signal} | Conf={confidence:.2f} | 4H={bias_4h} | 1H={bias_1h} | Struct={structure} | Stoch={stoch_val:.1f} | Price={price:.2f}" + "\033[0m")

    # =======================
    # CSV Log
    # =======================
    with open(CSV_FILE, mode="a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            timestamp_et, price, ema20, ema50, rsi, stoch_val, structure,
            bias_4h, bias_1h, signal, confidence,
            conf_4h, conf_1h, conf_structure, conf_stoch, conf_ema_dist
        ])

    # =======================
    # EMAIL ALERTS nach Confidence-Stufen
    # =======================
    if signal!="NONE" and confidence>=ALERT_THRESHOLD and (signal,confidence)!=last_signal:
        if confidence>=0.6:
            level="HIGH"
        elif confidence>=0.4:
            level="MEDIUM"
        else:
            level="LOW"
        send_email(
            f"BTCUSDT {signal} ({level} CONF {int(confidence*100)}%)",
            f"Signal: {signal}\nConfidence: {int(confidence*100)}%\nLevel: {level}\nStructure: {structure}\n4H Bias: {bias_4h}\n1H Bias: {bias_1h}\nPrice: {price:.2f}\nTime: {timestamp_et} ET"
        )
        last_signal=(signal,confidence)
        print(f"🚨 {signal} {level} ALERT SENT")
    elif signal=="NONE":
        last_signal=None

    # =======================
    # HEATMAP PNG speichern
    # =======================
    N = 50
    df_log = pd.read_csv(CSV_FILE).tail(N).reset_index(drop=True)
    heatmap_vals = []
    for idx, row in df_log.iterrows():
        val = 0
        if row["signal"]=="LONG":
            val = row["confidence"]
        elif row["signal"]=="SHORT":
            val = -row["confidence"]
        heatmap_vals.append(val)
    heatmap_array = [heatmap_vals]

    fig, ax = plt.subplots(figsize=(15,2))
    cmap = mcolors.LinearSegmentedColormap.from_list("conf_map", ["red","yellow","green"])
    im = ax.imshow(heatmap_array, aspect='auto', cmap=cmap, vmin=-1, vmax=1)
    ax.set_yticks([])
    ax.set_xticks(range(len(df_log)))
    ax.set_xticklabels(df_log['timestamp_et'], rotation=90, fontsize=8)
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Confidence (-Short ... +Long)")
    plt.title(f"BTC Signal Heatmap (last {N} bars)")
    plt.tight_layout()
    plt.savefig("btc_signal_heatmap.png", dpi=150)
    plt.close()
    print("🖼️ Heatmap saved as btc_signal_heatmap.png")

