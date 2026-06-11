import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import streamlit as st
from datetime import datetime, timedelta

def calculate_cmf(df, period=20):
    if 'close' not in df.columns or len(df) < period: return pd.Series(0, index=df.index)
    denom = (df['high'] - df['low']).replace(0, 1e-5)
    mf_multiplier = ((df['close'] - df['low']) - (df['high'] - df['close'])) / denom
    mf_multiplier = mf_multiplier.bfill().ffill()
    mf_volume = mf_multiplier * df['volume']
    vol_sum = df['volume'].rolling(window=period).sum().replace(0, 1e-5)
    return (mf_volume.rolling(window=period).sum() / vol_sum).fillna(0)

def calculate_rsi(series, period=14):
    if len(series) < period: return pd.Series(50, index=series.index)
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean().replace(0, 1e-5)
    rs = gain / loss
    return (100 - (100 / (1 + rs))).bfill().ffill().fillna(50)

def scrape_finviz_fundamentals(ticker):
    """Bypasses Yahoo API blocks by scraping fundamentals directly from Finviz HTML"""
    fund_data = {"pe_ratio": 0.0, "pb_ratio": 0.0, "market_cap": 0.0, "dividend_yield": 0.0}
    try:
        # Finviz uses dashes for tickers like BRK.B -> BRK-B
        ticker_formatted = ticker.replace('.', '-')
        url = f"https://finviz.com/quote.ashx?t={ticker_formatted}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Hunt through table cells to rip the numbers directly off the page
        cells = soup.find_all('td')
        for i, cell in enumerate(cells):
            text = cell.get_text(strip=True)
            if text == "P/E" and i + 1 < len(cells):
                val = cells[i+1].get_text(strip=True)
                if val and val != '-': fund_data['pe_ratio'] = float(val)
            elif text == "P/B" and i + 1 < len(cells):
                val = cells[i+1].get_text(strip=True)
                if val and val != '-': fund_data['pb_ratio'] = float(val)
            elif text == "Dividend %" and i + 1 < len(cells):
                val = cells[i+1].get_text(strip=True)
                if val and val != '-': fund_data['dividend_yield'] = float(val.strip('%'))
            elif text == "Market Cap" and i + 1 < len(cells):
                val = cells[i+1].get_text(strip=True)
                if val and val != '-':
                    if 'B' in val: fund_data['market_cap'] = float(val.replace('B', '')) * 1e9
                    elif 'M' in val: fund_data['market_cap'] = float(val.replace('M', '')) * 1e6
                    elif 'T' in val: fund_data['market_cap'] = float(val.replace('T', '')) * 1e12
    except Exception as e:
        print(f"Finviz HTML scraping failed: {e}")
        
    return fund_data

@st.cache_data(ttl=3600)
def get_power_gauge_score(ticker):
    df = pd.DataFrame()
    fundamental_data = {"pe_ratio": 0.0, "pb_ratio": 0.0, "market_cap": 0.0, "dividend_yield": 0.0, "high_52w": 0.0, "low_52w": 0.0}
    technical_score = 50; financial_score = 50; earnings_score = 55

    # PHASE 1: Historical Prices via yfinance (Yahoo does not block this)
    try:
        stock = yf.Ticker(ticker)
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
            
            # Calculate 52W levels cleanly
            one_year_ago = datetime.now() - timedelta(days=365)
            df_1yr = df[df['time_key'] >= one_year_ago]
            if not df_1yr.empty:
                fundamental_data["high_52w"] = float(df_1yr['high'].max())
                fundamental_data["low_52w"] = float(df_1yr['low'].min())
    except Exception as e:
        print(f"Historical pricing failure: {e}")

    # PHASE 2: Fetch Fundamentals via Finviz Scraper
    finviz_data = scrape_finviz_fundamentals(ticker)
    fundamental_data.update(finviz_data) # Inject the scraped data

    # Phase 3: Score Processing
    pe_val = fundamental_data["pe_ratio"]
    if pe_val > 0:
        if pe_val < 18: financial_score = 85
        elif 18 <= pe_val <= 32: financial_score = 65
        else: financial_score = 45

    earnings_score = 75 if fundamental_data["dividend_yield"] > 0.5 else 55

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