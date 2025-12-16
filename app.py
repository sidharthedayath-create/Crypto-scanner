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
    # This magic function refreshes the app automatically
    count = st_autorefresh(interval=REFRESH_RATE * 1000, limit=100, key="fizzbuzzcounter")

# --- FUNCTIONS ---
@st.cache_resource
def get_exchange():
    # We use Kraken for US-server compatibility, or Binance if you prefer
    return ccxt.kraken()

def get_top_30_coins():
    exchange = get_exchange()
    try:
        # Fetch tickers to find highest volume
        tickers = exchange.fetch_tickers()
        # Convert to DataFrame
        df = pd.DataFrame(tickers).T
        # Filter for USD pairs only (avoids duplicates)
        df = df[df.index.str.endswith('/USD')]
        # Sort by Volume and take top 30
        top_30 = df.sort_values(by='quoteVolume', ascending=False).head(30)
        return top_30.index.tolist()
    except Exception as e:
        st.error(f"Error fetching top coins: {e}")
        return []

def fetch_data(symbol, timeframe):
    exchange = get_exchange()
    try:
        # Fetch OHLCV data
        bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Fetch Order Book (for Buy/Sell Pressure)
        orderbook = exchange.fetch_order_book(symbol, limit=10)
        bid_vol = sum([bid[1] for bid in orderbook['bids']])
        ask_vol = sum([ask[1] for ask in orderbook['asks']])
        imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol) * 100 # % Imbalance
        
        return df, imbalance
    except:
        return None, 0

def fetch_weekly_momentum(symbol):
    exchange = get_exchange()
    try:
        # Fetch just the last 2 weekly candles
        bars = exchange.fetch_ohlcv(symbol, timeframe='1w', limit=2)
        if len(bars) < 2: return "NEUTRAL"
        
        # Compare current close to last week's close
        current_close = bars[-1][4]
        prev_close = bars[-2][4]
        
        if current_close > prev_close: return "BULLISH 🟢"
        else: return "BEARISH 🔴"
    except:
        return "NEUTRAL"

def analyze_market(df, imbalance, weekly_mom):
    # Indicators
    df['EMA_50'] = ta.ema(df['close'], length=50)
    df['EMA_200'] = ta.ema(df['close'], length=200)
    df['RSI'] = ta.rsi(df['close'], length=14)
    df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    
    curr = df.iloc[-1]
    price = curr['close']
    atr = curr['ATR']
    rsi = curr['RSI']
    ema50 = curr['EMA_50']
    ema200 = curr['EMA_200']
    
    score = 0
    reason = []
    setup = None
    
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
        reason.append("Strong Buying Pressure")
    elif imbalance < -20: 
        score -= 1
        reason.append("Strong Selling Pressure")

    # --- TRADE SETUP GENERATION ---
    # LONG SETUP (High Score + Uptrend)
    if score >= 3:
        entry = price
        sl = price - (2 * atr) # Wide stop for volatility
        tp = price + (3 * atr) # 1.5 Risk Reward
        setup = {
            "Type": "LONG 🚀",
            "Entry": entry,
            "SL": sl,
            "TP": tp,
            "Color": "green"
        }
        
    # SHORT SETUP (Low Score + Downtrend)
    elif score <= -1: # Modified threshold for shorts
        entry = price
        sl = price + (2 * atr)
        tp = price - (3 * atr)
        setup = {
            "Type": "SHORT 🔻",
            "Entry": entry,
            "SL": sl,
            "TP": tp,
            "Color": "red"
        }
        
    return setup, imbalance, weekly_mom

# --- MAIN APP ---

st.write(f"Last Updated: {datetime.now().strftime('%H:%M:%S')}")
st.write(f"Scanning Top 30 Coins by Volume on Kraken ({TIMEFRAME})...")

# 1. Get List
coins = get_top_30_coins()

if not coins:
    st.error("Could not fetch top coins. API might be busy.")
else:
    # 2. Create Progress Bar
    progress = st.progress(0)
    results = []
    
    for i, coin in enumerate(coins):
        # Update Progress
        progress.progress((i + 1) / len(coins))
        
        # Fetch Data
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
        
        time.sleep(0.1) # Tiny sleep prevents rate limits

    # 3. Display Results
    progress.empty()
    
    if results:
        st.success(f"Found {len(results)} Opportunities!")
        
        # Convert to DF for sorting
        res_df = pd.DataFrame(results)
        
        # Display Cards
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
