import yfinance as yf
import pandas as pd
import requests
import streamlit as st
from datetime import datetime, timedelta

def calculate_cmf(df, period=20):
    """Calculates the Chaikin Money Flow (CMF)"""
    if 'close' not in df.columns or len(df) < period:
        return pd.Series(0, index=df.index)
    
    denom = (df['high'] - df['low']).replace(0, 1e-5)
    mf_multiplier = ((df['close'] - df['low']) - (df['high'] - df['close'])) / denom
    mf_multiplier = mf_multiplier.bfill().ffill()
    
    mf_volume = mf_multiplier * df['volume']
    vol_sum = df['volume'].rolling(window=period).sum().replace(0, 1e-5)
    
    cmf = mf_volume.rolling(window=period).sum() / vol_sum
    return cmf.fillna(0)

def calculate_rsi(series, period=14):
    """Calculates the Relative Strength Index"""
    if len(series) < period:
        return pd.Series(50, index=series.index)
    
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean().replace(0, 1e-5)
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.bfill().ffill().fillna(50)

# The cache prevents Streamlit from spamming Yahoo with duplicate requests
@st.cache_data(ttl=3600) 
def get_power_gauge_score(ticker):
    """Fetches data using a spoofed browser session to bypass Yahoo Cloud blocks"""
    df = pd.DataFrame()
    fundamental_data = {
        "pe_ratio": 0.0, "pb_ratio": 0.0, "market_cap": 0.0,
        "dividend_yield": 0.0, "high_52w": 0.0, "low_52w": 0.0,
    }
    technical_score = 50; financial_score = 50; earnings_score = 55

# Let yfinance handle the User-Agent and Crumb generation natively
    stock = yf.Ticker(ticker)

    # PHASE 1: Historical Prices (Ultra-Stable Endpoint)
    try:
        raw_df = stock.history(period="5y", interval="1d")
        if not raw_df.empty:
            df = raw_df.reset_index()
            df.columns = df.columns.str.lower()
            df = df.rename(columns={'date': 'time_key'})
            df['time_key'] = pd.to_datetime(df['time_key']).dt.tz_localize(None)
            
            df['cmf'] = calculate_cmf(df)
            df['rsi'] = calculate_rsi(df['close'])
            df['lt_trend'] = df['close'].rolling(window=20).mean().bfill()
            
            technical_score = max(10, min(90, 50 + (df['cmf'].iloc[-1] * 100)))
            
            # Calculate 52W High/Low directly from history
            one_year_ago = datetime.now() - timedelta(days=365)
            df_1yr = df[df['time_key'] >= one_year_ago]
            if not df_1yr.empty:
                fundamental_data["high_52w"] = float(df_1yr['high'].max())
                fundamental_data["low_52w"] = float(df_1yr['low'].min())
    except Exception as e:
        print(f"History failure: {e}")

    # PHASE 2: Fundamentals via Spoofed Session
    try:
        info = stock.info 
        
        if info:
            pe = info.get("trailingPE", info.get("forwardPE", 0.0))
            fundamental_data["pe_ratio"] = float(pe) if pd.notna(pe) else 0.0
            
            pb = info.get("priceToBook", 0.0)
            fundamental_data["pb_ratio"] = float(pb) if pd.notna(pb) else 0.0
            
            fundamental_data["market_cap"] = info.get("marketCap", 0.0)
            
            div = info.get("dividendYield", 0.0)
            fundamental_data["dividend_yield"] = float(div) * 100 if pd.notna(div) else 0.0

        # FAILSAFE: Manual dividend calculation if info is blocked
        if fundamental_data["dividend_yield"] == 0.0:
            div_history = stock.dividends
            if not div_history.empty and not df.empty:
                last_year_divs = div_history[div_history.index >= (pd.Timestamp.now(tz=div_history.index.tz) - pd.DateOffset(years=1))]
                total_annual_dividend = last_year_divs.sum()
                current_price = df['close'].iloc[-1]
                
                if current_price > 0 and total_annual_dividend > 0:
                    fundamental_data["dividend_yield"] = (total_annual_dividend / current_price) * 100

        # Fundamental Scoring Logic
        pe_val = fundamental_data["pe_ratio"]
        if pe_val > 0:
            if pe_val < 18: financial_score = 85
            elif 18 <= pe_val <= 32: financial_score = 65
            else: financial_score = 45
        
        earnings_score = 75 if fundamental_data["dividend_yield"] > 0.5 else 55

    except Exception as e:
        print(f"Fundamentals failure: {e}")

    final_score = (technical_score + financial_score + earnings_score + 58) / 4
    rating = "Bullish" if final_score >= 65 else "Bearish" if final_score <= 35 else "Neutral"

    return {
        "ticker": ticker,
        "final_score": round(final_score),
        "rating": rating,
        "pillars": {
            "Technicals": round(technical_score),
            "Financials": round(financial_score),
            "Earnings": round(earnings_score),
            "Expert Sentiment": 58
        },
        "fundamentals": fundamental_data,
        "history_df": df
    }