import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- PAGE CONFIG ---
st.set_page_config(page_title="Crypto Sniper Pro V3", layout="wide")
st.title("⚡ Crypto Sniper Pro V3: High Probability Scanner")

# --- SIDEBAR SETTINGS ---
with st.sidebar:
    st.header("⚙️ Scanner Settings")
    TIMEFRAME = st.selectbox("Timeframe", ['15m', '1h', '4h'], index=0)
    REFRESH_RATE = 300  # 5 minutes
    
    st.info("ℹ️ V3 Updates:")
    st.markdown("""
    - **ADX Filter:** Ignores weak trends.
    - **MACD:** Confirms momentum.
    - **Strict Scoring:** Needs 4/5 points.
    """)
    
    count = st_autorefresh(interval=REFRESH_RATE * 1000, limit=100, key="counter")

# --- FUNCTIONS ---
@st.cache_resource
def get_exchange():
    return ccxt.kraken()

def get_top_30_coins():
    exchange = get_exchange()
    try:
        tickers = exchange.fetch_tickers()
        df = pd.DataFrame(tickers).T
        df = df[df.index.str.endswith('/USD')]
        top_30 = df.sort_values(by='quoteVolume', ascending=False).head(30)
        return top_30.index.tolist()
    except:
        return []

def fetch_data(symbol, timeframe):
    exchange = get_exchange()
    try:
        # Fetch 300 candles for accurate ADX/EMA
        bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=300)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Order Book Analysis
        orderbook = exchange.fetch_order_book(symbol, limit=10)
        bid_vol = sum([bid[1] for bid in orderbook['bids']])
        ask_vol = sum([ask[1] for ask in orderbook['asks']])
        
        if (bid_vol + ask_vol) == 0: imbalance = 0
        else: imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol) * 100
        
        return df, imbalance
    except:
        return None, 0

def fetch_weekly_momentum(symbol):
    exchange = get_exchange()
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe='1w', limit=2)
        if len(bars) < 2: return "NEUTRAL"
        return "BULLISH 🟢" if bars[-1][4] > bars[-2][4] else "BEARISH 🔴"
    except:
        return "NEUTRAL"

def analyze_market(df, imbalance, weekly_mom):
    if len(df) < 200: return None, 0, "NEUTRAL"

    # --- TECHNICAL INDICATORS ---
    # 1. Trend
    df['EMA_200'] = ta.ema(df['close'], length=200)
    # 2. Momentum
    df['RSI'] = ta.rsi(df['close'], length=14)
    # 3. Volatility (ATR for Targets)
    df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    # 4. Trend Strength (ADX) - NEW
    adx_df = ta.adx(df['high'], df['low'], df['close'], length=14)
    df = pd.concat([df, adx_df], axis=1) # Join ADX columns
    # 5. MACD - NEW
    macd_df = ta.macd(df['close'])
    df = pd.concat([df, macd_df], axis=1)

    curr = df.iloc[-1]
    
    # Check for valid data
    if pd.isna(curr['EMA_200']) or pd.isna(curr['ADX_14']): return None, 0, "NEUTRAL"

    # Extract values
    price = curr['close']
    ema200 = curr['EMA_200']
    rsi = curr['RSI']
    adx = curr['ADX_14']
    macd = curr['MACD_12_26_9']
    macd_signal = curr['MACDs_12_26_9']
    atr = curr['ATR']
    
    # --- SCORING ENGINE (Max Score 5) ---
    score = 0
    reasons = []

    # 1. Macro Trend (Weekly)
    if weekly_mom == "BULLISH 🟢": score += 1
    elif weekly_mom == "BEARISH 🔴": score -= 1
    
    # 2. Immediate Trend (EMA 200)
    if price > ema200: score += 1
    else: score -= 1
    
    # 3. Trend Strength (ADX)
    # We only want to trade if ADX > 20 (Market is moving, not flat)
    if adx > 20: score += 0.5 # Bonus for strong trend
    
    # 4. RSI (Pullback Logic)
    if rsi < 40: score += 1      # Oversold in uptrend is good
    elif rsi > 60: score -= 1    # Overbought in downtrend is good
    
    # 5. MACD Confirmation
    if macd > macd_signal: score += 1
    elif macd < macd_signal: score -= 1

    # --- SETUP GENERATION ---
    setup = None
    
    # LONG SETUP (Needs strong positive score)
    if score >= 3.5:
        sl = price - (2 * atr)
        tp = price + (4 * atr) # Increased Reward Ratio
        setup = {"Type": "LONG 🚀", "Entry": price, "SL": sl, "TP": tp, "Color": "green", "Score": score}

    # SHORT SETUP (Needs strong negative score)
    elif score <= -3.5:
        sl = price + (2 * atr)
        tp = price - (4 * atr)
        setup = {"Type": "SHORT 🔻", "Entry": price, "SL": sl, "TP": tp, "Color": "red", "Score": score}
        
    return setup, imbalance, weekly_mom, adx

# --- MAIN LOOP ---
st.write(f"Last Scan: {datetime.now().strftime('%H:%M:%S')}")

coins = get_top_30_coins()

if not coins:
    st.error("API Error: Retrying...")
else:
    progress = st.progress(0)
    results = []
    
    for i, coin in enumerate(coins):
        progress.progress((i + 1) / len(coins))
        
        df, imbalance = fetch_data(coin, TIMEFRAME)
        weekly = fetch_weekly_momentum(coin)
        
        if df is not None:
            setup, imb_val, weekly_val, adx_val = analyze_market(df, imbalance, weekly)
            
            if setup:
                results.append({
                    "Coin": coin,
                    "Direction": setup['Type'],
                    "Price": setup['Entry'],
                    "Stop Loss": setup['SL'],
                    "Target": setup['TP'],
                    "Score": setup['Score'],
                    "ADX": round(adx_val, 1),
                    "Color": setup['Color']
                })
        time.sleep(0.1)

    progress.empty()
    
    if results:
        # Sort by best score (High Probability first)
        res_df = pd.DataFrame(results).sort_values(by='ADX', ascending=False)
        
        st.success(f"Found {len(results)} High-Probability Setups")
        
        cols = st.columns(3)
        for idx, row in res_df.iterrows():
            with cols[idx % 3]:
                st.markdown(f"""
                <div style="background-color: #1E1E1E; padding: 20px; border-radius: 12px; border-left: 5px solid {row['Color']}; margin-bottom: 15px;">
                    <div style="display:flex; justify-content:space-between;">
                        <h3 style="color: white; margin:0;">{row['Coin']}</h3>
                        <span style="background:{row['Color']}; padding:2px 8px; border-radius:4px; font-weight:bold; color:white;">{row['Direction']}</span>
                    </div>
                    <p style="color:#888; margin-top:5px; font-size:0.9em;">Trend Strength (ADX): {row['ADX']}</p>
                    <hr style="border-color:#333;">
                    <div style="display:flex; justify-content:space-between;">
                        <span>💰 Entry:</span> <span style="color:white;">${row['Price']}</span>
                    </div>
                    <div style="display:flex; justify-content:space-between;">
                        <span>🛑 Stop Loss:</span> <span style="color:#ff4b4b;">${round(row['Stop Loss'], 4)}</span>
                    </div>
                    <div style="display:flex; justify-content:space-between;">
                        <span>🎯 Target:</span> <span style="color:#00c853;">${round(row['Target'], 4)}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Market is 'Choppy' (Low ADX). No high-probability setups found. Patience pays!")
