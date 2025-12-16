import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time

# --- CONFIGURATION ---
# We use USD pairs because Kraken trades against USD
PAIRS = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'DOGE/USD', 'XRP/USD']
TIMEFRAME = '15m'
EMA_LENGTH = 200
RSI_LENGTH = 14

st.set_page_config(page_title="Crypto Sniper 20x", layout="wide")
st.title("⚡ Crypto Signal Scanner (US-Server Safe)")

# --- FUNCTIONS ---
def get_data(symbol):
    # Switch to KRAKEN (Works on US Servers)
    exchange = ccxt.kraken()
    try:
        # Fetch data
        bars = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=500)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        # If Kraken fails, try Coinbase
        try:
             exchange = ccxt.coinbase()
             bars = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=500)
             df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
             df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
             return df
        except:
             st.error(f"Error fetching {symbol}: {e}")
             return None

def analyze_coin(df):
    if len(df) < EMA_LENGTH:
        return None, None, "NOT ENOUGH DATA", "gray", "Need more candles"

    # Calculate Indicators
    try:
        # standard pandas_ta calculation
        df['EMA_200'] = ta.ema(df['close'], length=EMA_LENGTH)
        df['RSI'] = ta.rsi(df['close'], length=RSI_LENGTH)
    except Exception as e:
        return None, None, "ERROR", "red", str(e)

    current = df.iloc[-1]
    price = current['close']
    
    # Safety check for NaN values
    if pd.isna(current['EMA_200']) or pd.isna(current['RSI']):
         return price, 0, "CALC ERROR", "red", "Not enough history"

    ema = current['EMA_200']
    rsi = current['RSI']
    
    signal = "NEUTRAL"
    color = "white"
    reason = "Waiting for setup..."

    # --- STRATEGY ---
    if price > ema and rsi < 40:
        signal = "🚀 LONG CALL"
        color = "green"
        reason = f"Oversold in Uptrend (RSI: {round(rsi,1)})"
    elif price < ema and rsi > 60:
        signal = "🔻 SHORT CALL"
        color = "red"
        reason = f"Overbought in Downtrend (RSI: {round(rsi,1)})"

    return price, rsi, signal, color, reason

# --- MAIN APP ---
if st.button('🔄 Scan Market Now'):
    st.write("Scanning Kraken data... please wait...")
    results = []
    
    my_bar = st.progress(0)
    
    for i, symbol in enumerate(PAIRS):
        df = get_data(symbol)
        
        if df is not None:
            price, rsi, signal, color, reason = analyze_coin(df)
            
            if price is not None:
                results.append({
                    "Symbol": symbol,
                    "Price": price,
                    "RSI": round(rsi, 2) if rsi else 0,
                    "Signal": signal,
                    "Reason": reason,
                    "Color": color
