import pandas as pd
import requests
import streamlit as st
from datetime import datetime, timedelta

# Attempt to load the API key securely from Streamlit Secrets
try:
    API_KEY = st.secrets["DV9GYD1M7S3XE96O"]
except (KeyError, FileNotFoundError):
    # Fallback for local testing if secrets.toml isn't set up locally
    API_KEY = "demo" 

def calculate_cmf(df, period=20):
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
    if len(series) < period:
        return pd.Series(50, index=series.index)
    
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean().replace(0, 1e-5)
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.bfill().ffill().fillna(50)

def get_power_gauge_score(ticker):
    """Fetches Technical and Fundamental data via Alpha Vantage REST API"""
    df = pd.DataFrame()
    fundamental_data = {
        "pe_ratio": 0.0, "pb_ratio": 0.0, "market_cap": 0.0,
        "dividend_yield": 0.0, "high_52w": 0.0, "low_52w": 0.0,
    }
    technical_score = 50; financial_score = 50; earnings_score = 55

    # PHASE 1: Historical Prices (Daily OHLCV)
    try:
        url_daily = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ticker}&outputsize=full&apikey={API_KEY}"
        res_daily = requests.get(url_daily).json()
        
        if "Time Series (Daily)" in res_daily:
            ts = res_daily["Time Series (Daily)"]
            df = pd.DataFrame.from_dict(ts, orient='index')
            df.index.name = 'time_key'
            df = df.reset_index()
            
            # Rename columns to match the application's lowercase schema
            df = df.rename(columns={
                "1. open": "open", "2. high": "high", "3. low": "low", 
                "4. close": "close", "5. volume": "volume"
            })
            
            # Convert types and sort chronologically (oldest to newest)
            df['time_key'] = pd.to_datetime(df['time_key'])
            df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
            df = df.sort_values('time_key').reset_index(drop=True)
            
            # Filter to last 5 years for performance
            five_years_ago = datetime.now() - timedelta(days=1825)
            df = df[df['time_key'] >= five_years_ago].copy()
            
            # Mathematical Technical indicators
            df['cmf'] = calculate_cmf(df)
            df['rsi'] = calculate_rsi(df['close'])
            df['lt_trend'] = df['close'].rolling(window=20).mean().bfill()
            
            technical_score = max(10, min(90, 50 + (df['cmf'].iloc[-1] * 100)))
            
            # Calculate 52-Week Peak & Floor from historical data
            one_year_ago = datetime.now() - timedelta(days=365)
            df_1yr = df[df['time_key'] >= one_year_ago]
            if not df_1yr.empty:
                fundamental_data["high_52w"] = float(df_1yr['high'].max())
                fundamental_data["low_52w"] = float(df_1yr['low'].min())
        else:
            print(f"Alpha Vantage API limit reached or invalid ticker: {res_daily}")
            
    except Exception as e:
        print(f"Historical pricing layer failure: {e}")

    # PHASE 2: Fundamentals (Company Overview)
    try:
        url_overview = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={API_KEY}"
        info = requests.get(url_overview).json()
        
        # Check if the API returned valid fundamental data and not an error/limit message
        if "Symbol" in info:
            # Parse fields, replacing "None" strings with 0.0
            pe = info.get("PERatio", "0.0")
            fundamental_data["pe_ratio"] = float(pe) if pe and pe != "None" else 0.0
            
            pb = info.get("PriceToBookRatio", "0.0")
            fundamental_data["pb_ratio"] = float(pb) if pb and pb != "None" else 0.0
            
            mcap = info.get("MarketCapitalization", "0")
            fundamental_data["market_cap"] = float(mcap) if mcap and mcap != "None" else 0.0
            
            # Alpha Vantage returns yield as a decimal (e.g., 0.015 for 1.5%)
            div = info.get("DividendYield", "0.0")
            fundamental_data["dividend_yield"] = float(div) * 100 if div and div != "None" else 0.0

        # Fundamental Scoring Assignments based on parsed metrics
        pe_val = fundamental_data["pe_ratio"]
        if pe_val > 0:
            if pe_val < 18: financial_score = 85
            elif 18 <= pe_val <= 32: financial_score = 65
            else: financial_score = 45
        
        earnings_score = 75 if fundamental_data["dividend_yield"] > 0.5 else 55

    except Exception as e:
        print(f"Fundamentals metadata extraction failure: {e}")

    # Combine pillars safely
    pillars = {
        "Technicals": round(technical_score),
        "Financials": round(financial_score),
        "Earnings": round(earnings_score),
        "Expert Sentiment": 58
    }
    
    final_score = sum(pillars.values()) / 4
    rating = "Bullish" if final_score >= 65 else "Bearish" if final_score <= 35 else "Neutral"

    return {
        "ticker": ticker,
        "final_score": round(final_score),
        "rating": rating,
        "pillars": pillars,
        "fundamentals": fundamental_data,
        "history_df": df
    }