import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- PAGE CONFIG ---
st.set_page_config(page_title="Crypto Sniper Pro 30", layout="wide")
st.title("⚡ Crypto Sniper Pro: Top 30 Scanner (20x)")

# --- SIDEBAR SETTINGS ---
with st.sidebar:
    st.header("⚙️ Scanner Settings")
    TIMEFRAME = st.selectbox("Timeframe", ['15m', '1h', '4h'], index=0)
    LEVERAGE = 20
    REFRESH_RATE = 300  # 5 minutes in seconds
    
    st.info(f"Auto-refreshing every {REFRESH_RATE/60} minutes...")
    # Auto-refresh logic
    count = st_autorefresh(interval=REFRESH_RATE * 1000, limit=100, key="fizzbuzzcounter")

# --- FUNCTIONS ---
@st.cache_resource
def get_exchange():
    return ccxt.kraken()

def get_top_30_coins():
    exchange = get_exchange()
    try:
        tickers = exchange.fetch_tickers()
        df = pd.DataFrame(tickers).T
        # Filter for USD pairs
        df = df[df.index.str.endswith('/USD')]
        # Sort by volume
        top_30 = df.sort_values(by='quoteVolume', ascending=False).head(30)
        return top_30.index.tolist()
    except Exception as e:
        st.error(f"Error fetching top coins: {e}")
        return []

def fetch_data(symbol, timeframe):
    exchange = get_exchange()
    try:
        # FIX: Increased limit to 300 so EMA_200 can be calculated
        bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=300)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Order Book
        orderbook = exchange.fetch_order_book(symbol, limit=10)
        bid_vol = sum([bid[1] for bid in orderbook['bids']])
        ask_vol = sum([ask[1] for ask in orderbook['asks']])
        
        # Avoid division by zero
        if (bid_vol + ask_vol) == 0:
            imbalance = 0
        else:
            imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol) * 100
        
        return df, imbalance
    except:
        return None, 0

def fetch_weekly_momentum(symbol):
    exchange = get_exchange()
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe='1w', limit=2)
        if len(bars) < 2: return "NEUTRAL"
        current_close = bars[-1][4]
        prev_close = bars[-2][4]
        return "BULLISH 🟢" if current_close > prev_close else "BEARISH 🔴"
    except:
        return "NEUTRAL"

def analyze_market(df, imbalance, weekly_mom):
    # Safety Check: Do we have enough data?
    if len(df) < 200:
        return None, 0, "NEUTRAL"

    # Indicators
    df['EMA_50'] = ta.ema(df['close'], length=50)
    df['EMA_200'] = ta.ema(df['close'], length=200)
    df['RSI'] = ta.rsi(df['close'], length=14)
    df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    
    curr = df.iloc[-1]
    price = curr['close']
    
    # SAFETY FIX: Check for NaNs (Not a Number) before comparing
    if pd.isna(curr['EMA_200']) or pd.isna(curr['ATR']) or pd.isna(curr['RSI']):
        return None, 0, "NEUTRAL"

    atr = curr['ATR']
    rsi = curr['RSI']
    ema50 = curr['EMA_50']
    ema200 = curr['EMA_200']
    
    score = 0
    reason = []
    
    # 1. Trend Scoring
    if price > ema200: score += 1
    if weekly_mom == "BULLISH 🟢": score += 1
    
    # 2. RSI Scoring
    if rsi < 30: 
        score += 2
        reason.append("RSI Oversold")
    elif rsi > 70: 
        score -= 2
        reason.append("RSI Overbought")
        
    # 3. Order Book Scoring
    if imbalance > 20: 
        score += 1
    elif imbalance < -20: 
        score -= 1

    # --- TRADE SETUP ---
    setup = None
    
    # LONG
    if score >= 3:
        entry = price
        sl = price - (2 * atr)
        tp = price + (3 * atr)
        setup = {"Type": "LONG 🚀", "Entry": entry, "SL": sl, "TP": tp, "Color": "green"}
        
    # SHORT
    elif score <= -1:
        entry = price
        sl = price + (2 * atr)
        tp = price - (3 * atr)
        setup = {"Type": "SHORT 🔻", "Entry": entry, "SL": sl, "TP": tp, "Color": "red"}
        
    return setup, imbalance, weekly_mom

# --- MAIN APP ---
st.write(f"Last Updated: {datetime.now().strftime('%H:%M:%S')}")

coins = get_top_30_coins()

if not coins:
    st.error("Could not fetch top coins. API might be busy.")
else:
    progress = st.progress(0)
    results = []
    
    for i, coin in enumerate(coins):
        progress.progress((i + 1) / len(coins))
        
        df, imbalance = fetch_data(coin, TIMEFRAME)
        weekly = fetch_weekly_momentum(coin)
        
        if df is not None:
            setup, imb_val, weekly_val = analyze_market(df, imbalance, weekly)
            
            if setup:
                results.append({
                    "Coin": coin,
                    "Price": setup['Entry'],
                    "Direction": setup['Type'],
                    "Stop Loss": setup['SL'],
                    "Target": setup['TP'],
                    "Weekly": weekly_val,
                    "Order Book": f"{round(imb_val, 1)}%",
                    "Color": setup['Color']
                })
        
        time.sleep(0.1)

    progress.empty()
    
    if results:
        st.success(f"Found {len(results)} Opportunities!")
        res_df = pd.DataFrame(results)
        cols = st.columns(3)
        for idx, row in res_df.iterrows():
            with cols[idx % 3]:
                st.markdown(f"""
                <div style="background-color: #262730; padding: 15px; border-radius: 10px; border: 1px solid {row['Color']}; margin-bottom: 10px;">
                    <h3 style="color: white; margin:0;">{row['Coin']}</h3>
                    <h2 style="color: {row['Color']}; margin:0;">{row['Direction']}</h2>
                    <hr style="margin: 10px 0; border-color: #444;">
                    <p style="margin:0;">💰 <b>Entry:</b> ${row['Price']}</p>
                    <p style="margin:0;">🛑 <b>Stop Loss:</b> ${round(row['Stop Loss'], 4)}</p>
                    <p style="margin:0;">🎯 <b>Target:</b> ${round(row['Target'], 4)}</p>
                    <p style="font-size: 0.8em; color: #ccc;">Weekly: {row['Weekly']} | Book Imbalance: {row['Order Book']}</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.warning("No high-probability setups found right now. Market is chopping.")
