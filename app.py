import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
from datetime import datetime

# --- CONFIGURATION ---
# Coins to scan (You can add more)
PAIRS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'DOGE/USDT', 'XRP/USDT', 'ADA/USDT']
TIMEFRAME = '15m'  # 15 minute candles are good for day trading/scalping
EMA_LENGTH = 200   # To determine the main trend
RSI_LENGTH = 14    # To determine overbought/oversold

# --- PAGE SETUP ---
st.set_page_config(page_title="Crypto Sniper 20x", layout="wide")
st.title(f"⚡ Crypto Signal Scanner (Targeting 20x Leverage)")
st.write(f"Scanning Binance Data on **{TIMEFRAME}** timeframe...")

# --- FUNCTIONS ---
def get_data(symbol):
    exchange = ccxt.binance()
    try:
        # Fetch 300 candles to ensure EMA calculates correctly
        bars = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=300)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        st.error(f"Error fetching {symbol}: {e}")
        return None

def analyze_coin(df):
    # Calculate Indicators using pandas_ta
    df['EMA_200'] = ta.ema(df['close'], length=EMA_LENGTH)
    df['RSI'] = ta.rsi(df['close'], length=RSI_LENGTH)
    
    # Get current values (last completed candle is safer, but current is faster)
    current = df.iloc[-1]
    price = current['close']
    ema = current['EMA_200']
    rsi = current['RSI']
    
    signal = "NEUTRAL"
    color = "white"
    reason = "No clear setup"

    # --- STRATEGY LOGIC ---
    
    # LONG SCENARIO: Price is ABOVE 200 EMA (Uptrend) but RSI is LOW (Oversold Dip)
    if price > ema and rsi < 40:
        signal = "🚀 LONG CALL"
        color = "green"
        reason = "Uptrend Dip (Price > EMA200 + RSI Oversold)"
        
    # SHORT SCENARIO: Price is BELOW 200 EMA (Downtrend) but RSI is HIGH (Overbought Spike)
    elif price < ema and rsi > 60:
        signal = "🔻 SHORT CALL"
        color = "red"
        reason = "Downtrend Spike (Price < EMA200 + RSI Overbought)"

    return price, rsi, signal, color, reason

# --- MAIN APP LOOP ---
if st.button('🔄 Scan Market Now'):
    results = []
    
    progress_bar = st.progress(0)
    
    for i, symbol in enumerate(PAIRS):
        df = get_data(symbol)
        if df is not None:
            price, rsi, signal, color, reason = analyze_coin(df)
            
            # Add to results list
            results.append({
                "Symbol": symbol,
                "Price": price,
                "RSI": round(rsi, 2),
                "Signal": signal,
                "Reason": reason,
                "Color": color
            })
        progress_bar.progress((i + 1) / len(PAIRS))

    # Create a DataFrame for display
    res_df = pd.DataFrame(results)
    
    # Display logic
    st.markdown("### Signal Results")
    
    # Loop through results and display cards
    cols = st.columns(3) # Grid layout
    for index, row in res_df.iterrows():
        with cols[index % 3]:
            # CSS styling for the card
            st.markdown(f"""
            <div style="border:1px solid #333; padding: 20px; border-radius: 10px; margin-bottom: 10px; background-color: #1E1E1E;">
                <h3 style="color: white;">{row['Symbol']}</h3>
                <h4 style="color: {row['Color']};">{row['Signal']}</h4>
                <p>Price: <b>${row['Price']}</b></p>
                <p>RSI: {row['RSI']}</p>
                <small>Reason: {row['Reason']}</small>
            </div>
            """, unsafe_allow_html=True)

else:
    st.info("Click the button above to scan the market for 20x leverage opportunities.")

st.markdown("---")
st.warning("**Disclaimer:** 20x Leverage carries extreme risk. This tool provides technical indicators, not financial advice. Always use a Stop Loss.")
