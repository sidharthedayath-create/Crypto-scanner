import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time

# --- CONFIGURATION ---
PAIRS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'DOGE/USDT', 'XRP/USDT']
TIMEFRAME = '15m'
EMA_LENGTH = 200
RSI_LENGTH = 14

st.set_page_config(page_title="Crypto Sniper 20x", layout="wide")
st.title("⚡ Crypto Signal Scanner (v2)")

# --- FUNCTIONS ---
def get_data(symbol):
    # Enable Rate Limit to avoid bans
    exchange = ccxt.binance({'enableRateLimit': True})
    try:
        # Fetch 500 candles to be safe
        bars = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=500)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        st.error(f"Error fetching {symbol}: {e}")
        return None

def analyze_coin(df):
    # Check if we have enough data
    if len(df) < EMA_LENGTH:
        return None, None, "NOT ENOUGH DATA", "gray", "Need more candles"

    # Calculate Indicators
    try:
        df.ta.ema(length=EMA_LENGTH, append=True)
        df.ta.rsi(length=RSI_LENGTH, append=True)
    except Exception as e:
        st.error(f"Calculation Error: {e}")
        return None, None, "ERROR", "red", str(e)

    # Get values
    current = df.iloc[-1]
    price = current['close']
    
    # Check if columns exist (sometimes calculation fails silently)
    if f'EMA_{EMA_LENGTH}' not in df.columns or f'RSI_{RSI_LENGTH}' not in df.columns:
         return price, 0, "CALC ERROR", "red", "Indicators missing"
         
    ema = current[f'EMA_{EMA_LENGTH}']
    rsi = current[f'RSI_{RSI_LENGTH}']
    
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
    st.write("Scanning... please wait...")
    results = []
    
    # Progress bar
    my_bar = st.progress(0)
    
    for i, symbol in enumerate(PAIRS):
        df = get_data(symbol)
        
        if df is not None:
            price, rsi, signal, color, reason = analyze_coin(df)
            
            # Only add if we got valid data
            if price is not None:
                results.append({
                    "Symbol": symbol,
                    "Price": price,
                    "RSI": round(rsi, 2) if rsi else 0,
                    "Signal": signal,
                    "Reason": reason,
                    "Color": color
                })
        
        # Update progress
        my_bar.progress((i + 1) / len(PAIRS))
        
        # Tiny sleep to be nice to the API
        time.sleep(0.5)

    # Display Results
    if results:
        res_df = pd.DataFrame(results)
        cols = st.columns(len(results) if len(results) < 3 else 3)
        
        for index, row in res_df.iterrows():
            with cols[index % 3]:
                st.markdown(f"""
                <div style="border:1px solid #444; padding: 15px; border-radius: 10px; margin-bottom: 10px; background-color: #222;">
                    <h3 style="color: white; margin:0;">{row['Symbol']}</h3>
                    <h4 style="color: {row['Color']}; margin: 5px 0;">{row['Signal']}</h4>
                    <p style="margin:0;">Price: <b>${row['Price']}</b></p>
                    <p style="margin:0;">RSI: {row['RSI']}</p>
                    <small style="color: #aaa;">{row['Reason']}</small>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.warning("No results found. Check connection.")
else:
    st.info("Ready to scan.")
