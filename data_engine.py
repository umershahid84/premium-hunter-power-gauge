import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def calculate_cmf(df, period=20):
    """Calculates the Chaikin Money Flow (CMF)"""
    mf_multiplier = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low'])
    mf_multiplier = mf_multiplier.bfill() 
    mf_volume = mf_multiplier * df['volume']
    cmf = mf_volume.rolling(window=period).sum() / df['volume'].rolling(window=period).sum()
    return cmf

def calculate_rsi(series, period=14):
    """Calculates the Relative Strength Index for Overbought/Oversold"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.bfill()

def get_power_gauge_score(ticker):
    """Fetches data directly from Yahoo Finance Cloud API (No Local Gateway Needed)"""
    df = pd.DataFrame()
    fundamental_data = {}
    technical_score = 50
    financial_score = 50
    earnings_score = 55

    try:
        # 1. Fetch 5 years of daily K-line data from Yahoo Finance cloud
        stock = yf.Ticker(ticker)
        raw_df = stock.history(period="5y", interval="1d")
        
        if not raw_df.empty:
            # Clean and match your existing dataframe schema
            df = raw_df.reset_index()
            df.columns = df.columns.str.lower() # Convert 'Close', 'High' to lowercase
            df = df.rename(columns={'date': 'time_key'})
            df['time_key'] = pd.to_datetime(df['time_key']).dt.tz_localize(None) # Remove timezone data for plotly compatibility
            
            # Technical math operations
            df['cmf'] = calculate_cmf(df)
            df['rsi'] = calculate_rsi(df['close'])
            df['lt_trend'] = df['close'].rolling(window=20).mean().bfill()
            
            latest_cmf = df['cmf'].iloc[-1]
            technical_score = 50 + (latest_cmf * 100)
            technical_score = max(10, min(90, technical_score))

            # 2. Fetch Live Fundamentals safely via Cloud Info Dictionary
            info = stock.info
            
            # Safely grab metrics with logical fallback values
            pe_val = info.get("trailingPE", info.get("forwardPE", 25.0))
            pb_val = info.get("priceToBook", 4.0)
            mcap_val = info.get("marketCap", 150e9)
            div_val = info.get("dividendYield", 0.0) * 100 # yfinance uses decimals (0.01 = 1%)

            # Double check fallback filters for bad or empty values
            pe_val = 25.0 if pd.isna(pe_val) or pe_val is None else float(pe_val)
            pb_val = 4.0 if pd.isna(pb_val) or pb_val is None else float(pb_val)
            mcap_val = 150e9 if pd.isna(mcap_val) or mcap_val is None else float(mcap_val)
            div_val = 0.0 if pd.isna(div_val) or div_val is None else float(div_val)

            # Rolling 52-week calculation boundaries
            df_1yr = df[df['time_key'] >= (datetime.now() - timedelta(days=365))]
            h_52 = df_1yr['high'].max() if not df_1yr.empty else df['close'].iloc[-1]
            l_52 = df_1yr['low'].min() if not df_1yr.empty else df['close'].iloc[-1]

            fundamental_data = {
                "pe_ratio": pe_val,
                "pb_ratio": pb_val,
                "market_cap": mcap_val,
                "dividend_yield": div_val,
                "high_52w": h_52,
                "low_52w": l_52,
            }
            
            # Fundamental Scoring Assignments
            if 0 < pe_val < 18: financial_score = 85
            elif 18 <= pe_val <= 32: financial_score = 65
            else: financial_score = 45
            
            earnings_score = 75 if div_val > 0.5 else 55

    except Exception as e:
        print(f"Cloud fetching failure: {e}")

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