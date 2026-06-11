import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def calculate_cmf(df, period=20):
    """Calculates the Chaikin Money Flow (CMF) with safety overrides"""
    if 'close' not in df.columns or 'high' not in df.columns or 'low' not in df.columns or 'volume' not in df.columns:
        return pd.Series(0, index=df.index)
    
    denom = (df['high'] - df['low']).replace(0, 1e-5) # Prevent division by zero
    mf_multiplier = ((df['close'] - df['low']) - (df['high'] - df['close'])) / denom
    mf_multiplier = mf_multiplier.bfill().ffill()
    
    mf_volume = mf_multiplier * df['volume']
    vol_sum = df['volume'].rolling(window=period).sum().replace(0, 1e-5)
    
    cmf = mf_volume.rolling(window=period).sum() / vol_sum
    return cmf.fillna(0)

def calculate_rsi(series, period=14):
    """Calculates the Relative Strength Index with safety boundaries"""
    if len(series) < period:
        return pd.Series(50, index=series.index)
    
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean().replace(0, 1e-5)
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.bfill().ffill().fillna(50)

def get_power_gauge_score(ticker):
    """
    Fetches data directly from Yahoo Finance with fast_info safety nets
    and direct dataframe math to bypass cloud scraping restrictions.
    """
    df = pd.DataFrame()
    
    # Secure baseline defaults to ensure app.py always receives valid fields
    fundamental_data = {
        "pe_ratio": 0.0,
        "pb_ratio": 0.0,
        "market_cap": 0.0,
        "dividend_yield": 0.0,
        "high_52w": 0.0,
        "low_52w": 0.0,
    }
    technical_score = 50
    financial_score = 50
    earnings_score = 55

    # PHASE 1: Historical Prices & Technicals (Ultra-Stable Endpoint)
    try:
        stock = yf.Ticker(ticker)
        raw_df = stock.history(period="5y", interval="1d")
        
        if not raw_df.empty:
            df = raw_df.reset_index()
            df.columns = df.columns.str.lower()
            df = df.rename(columns={'date': 'time_key'})
            df['time_key'] = pd.to_datetime(df['time_key']).dt.tz_localize(None)
            
            # Mathematical Technical indicators
            df['cmf'] = calculate_cmf(df)
            df['rsi'] = calculate_rsi(df['close'])
            df['lt_trend'] = df['close'].rolling(window=20).mean().bfill()
            
            latest_cmf = df['cmf'].iloc[-1]
            technical_score = 50 + (latest_cmf * 100)
            technical_score = max(10, min(90, technical_score))
            
            # CRITICAL FIX: Calculate 52-Week Peak & Floor directly from actual rows
            one_year_ago = datetime.now() - timedelta(days=365)
            df_1yr = df[df['time_key'] >= one_year_ago]
            
            if not df_1yr.empty:
                fundamental_data["high_52w"] = float(df_1yr['high'].max())
                fundamental_data["low_52w"] = float(df_1yr['low'].min())
            else:
                fundamental_data["high_52w"] = float(df['high'].iloc[-1])
                fundamental_data["low_52w"] = float(df['low'].iloc[-1])
                
    except Exception as e:
        print(f"Historical pricing layer failure: {e}")

    # PHASE 2: Isolated Fundamentals (Wrapped safely to prevent total failure)
    try:
        stock = yf.Ticker(ticker)
        
        # A. Try modern fast_info API property first (Bypasses traditional web-scraping blocks)
        if hasattr(stock, 'fast_info'):
            try:
                fundamental_data["market_cap"] = stock.fast_info.get("marketCap", 0.0)
                if fundamental_data["high_52w"] == 0.0:
                    fundamental_data["high_52w"] = stock.fast_info.get("yearHigh", 0.0)
                    fundamental_data["low_52w"] = stock.fast_info.get("yearLow", 0.0)
            except Exception:
                pass

        # B. Fallback to parsing standard .info dict with strict null/NaN filtering
        info = {}
        try:
            info = stock.info
        except Exception:
            info = {} # If entirely blocked by Yahoo, catch gracefully and proceed
            
        if info:
            pe = info.get("trailingPE", info.get("forwardPE", 0.0))
            fundamental_data["pe_ratio"] = float(pe) if (pe and not pd.isna(pe)) else 0.0
            
            pb = info.get("priceToBook", 0.0)
            fundamental_data["pb_ratio"] = float(pb) if (pb and not pd.isna(pb)) else 0.0
            
            div = info.get("dividendYield", 0.0)
            fundamental_data["dividend_yield"] = float(div) * 100 if (div and not pd.isna(div)) else 0.0
            
            if fundamental_data["market_cap"] == 0.0:
                fundamental_data["market_cap"] = info.get("marketCap", 0.0)

        # Fundamental Scoring Assignments based on parsed metrics
        pe_val = fundamental_data["pe_ratio"]
        if pe_val > 0:
            if pe_val < 18: financial_score = 85
            elif 18 <= pe_val <= 32: financial_score = 65
            else: financial_score = 45
        
        div_val = fundamental_data["dividend_yield"]
        earnings_score = 75 if div_val > 0.5 else 55

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