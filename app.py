import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime
from data_engine import get_power_gauge_score

# --- 1. Global Page Configuration ---
st.set_page_config(page_title="Premium Hunter Power Gauge", layout="wide", initial_sidebar_state="expanded")

# --- 2. Advanced Premium Dark Mode CSS Engine ---
st.markdown("""
    <style>
    /* Main Canvas Deep Slate Theme */
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .block-container { padding-top: 0rem; padding-bottom: 0rem; max-width: 98%; }
    
    /* Top Brand Banner Ribbon - Styled exactly like your Chaikin Reference image */
    .brand-header {
        background: linear-gradient(90deg, #161b22 0%, #7a1c1c 25%, #1f2937 55%, #0d1117 100%);
        padding: 16px 24px;
        margin: 0rem -5rem 1.5rem -5rem;
        color: #ffffff;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 26px;
        font-weight: 700;
        letter-spacing: 0.5px;
        border-bottom: 2px solid #30363d;
        box-shadow: 0 4px 15px rgba(0,0,0,0.4);
    }
    
    /* Dark Theme Sidebar Workspace Configuration */
    section[data-testid="stSidebar"] { background-color: #161b22 !important; border-right: 1px solid #30363d !important; }
    section[data-testid="stSidebar"] * { color: #c9d1d9 !important; }
    
    /* CRITICAL FIX: Sidebar Button Styling Override (Eliminates dumb white blocks) */
    div[data-testid="stSidebar"] button {
        background-color: #21262d !important;
        color: #f0f6fc !important;
        border: 1px solid #30363d !important;
        border-radius: 6px !important;
        padding: 6px 12px !important;
        transition: all 0.2s ease-in-out !important;
        text-align: left !important;
        display: flex !important;
        align-items: center !important;
    }
    div[data-testid="stSidebar"] button:hover {
        background-color: #30363d !important;
        border-color: #8b949e !important;
        color: #ffffff !important;
        box-shadow: 0 0 8px rgba(255,255,255,0.1) !important;
    }
    
    /* Dashboard Cards Layout Grid Panel Theme */
    .dashboard-card {
        background-color: #161b22; border: 1px solid #30363d;
        padding: 20px; border-radius: 8px; margin-bottom: 15px; color: #c9d1d9;
    }
    .card-title { font-size: 15px; font-weight: bold; color: #f0f6fc; margin-bottom: 12px; border-bottom: 1px solid #30363d; padding-bottom: 6px; }
    .card-subtitle-bar { display: flex; justify-content: space-between; font-size: 12px; font-weight: bold; margin-bottom: 10px; padding: 3px 8px; border-radius: 4px; }
    .metric-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px; }
    .metric-label { color: #8b949e; }
    .metric-value { font-weight: bold; color: #f0f6fc; }
    
    /* Checklist Component Flex Row */
    .checklist-row { display: flex; justify-content: space-between; align-items: center; padding: 10px; border-radius: 6px; margin-bottom: 6px; font-size: 14px; color: white; font-weight: bold; }
    
    /* Maintain dark text boundaries across standard inputs */
    div[data-testid="stTextInput"] input { background-color: #21262d !important; color: #c9d1d9 !important; border: 1px solid #30363d !important; }
    hr { border-color: #30363d !important; }
    </style>
    
    <div class="brand-header">🎯 Premium Hunter Power Gauge ⚡</div>
""", unsafe_allow_html=True)

def evaluate_factor(score):
    if score >= 65: return "Bullish", "#2ca02c"
    if score <= 35: return "Bearish", "#d62728"
    return "Neutral", "#e6b800"

# --- Dynamic Session Memory Tracks ---
if "search_ticker" not in st.session_state: st.session_state.search_ticker = "ORCL"
if "history" not in st.session_state: st.session_state.history = ["ORCL", "AAPL", "MSFT"]

def load_ticker(t): st.session_state.search_ticker = t

# --- Left Sidebar Watchlist Execution ---
with st.sidebar:
    st.markdown("### **Watchlist Monitor**")
    st.selectbox("Group", ["Recently Viewed Tickers", "My Portfolio"], label_visibility="collapsed")
    st.markdown("<table style='width:100%; font-size:12px; color:#8b949e;'><tr><td>Rating Target</td><td>Symbol Info</td><td style='text-align:right;'>Price / Change</td></tr></table>", unsafe_allow_html=True)
    st.markdown("---")
    
    for symbol in st.session_state.history[:5]:
        try:
            sd = get_power_gauge_score(symbol)
            sdf = sd.get("history_df", pd.DataFrame())
            if not sdf.empty:
                last_p = sdf['close'].iloc[-1]
                prev_p = sdf['close'].iloc[-2] if len(sdf) > 1 else last_p
                chg_p = ((last_p - prev_p) / prev_p) * 100
                color = "#2ca02c" if chg_p >= 0 else "#d62728"
                sign = "+" if chg_p >= 0 else ""
                icon = "🟢" if sd['rating'] == "Bullish" else "🟡" if sd['rating'] == "Neutral" else "🔴"
                
                # Dynamic horizontal columns parsing custom dark buttons smoothly
                col_btn, col_stats = st.columns([1.1, 0.9])
                with col_btn:
                    st.button(f"{icon} {symbol.split('.')[-1]}", key=f"btn_{symbol}", on_click=load_ticker, args=(symbol,), use_container_width=True)
                with col_stats:
                    st.markdown(f"<div style='text-align:right; font-size:14px; margin-top:4px;'><b>${last_p:.2f}</b><br><span style='color:{color}; font-size:11px;'>{sign}{chg_p:.1f}%</span></div>", unsafe_allow_html=True)
                st.divider()
        except: pass

# --- Core Dashboard Search Interface ---
ticker_input = st.text_input("🔍 Quick search stocks & ETFs", key="search_ticker").upper().strip()

if ticker_input:
    if ticker_input not in st.session_state.history: st.session_state.history.insert(0, ticker_input)
        
    with st.spinner("Streaming Moomoo OpenD Terminal Layer..."):
        results = get_power_gauge_score(ticker_input)
        full_df = results.get("history_df", pd.DataFrame())
        funds = results.get("fundamentals", {})

    if full_df.empty:
            st.error("⚠️ Data connection failed. Yahoo Finance returned an empty dataset. Please clear the Streamlit cache and try again.")
        else:
        # Timeframe Controls
        col_meta, col_time = st.columns([2, 1])
        with col_time:
            timeframe = st.radio("TF", ["1M", "3M", "6M", "YTD", "1Y", "5Y"], horizontal=True, index=5, label_visibility="collapsed")
        
        today = full_df['time_key'].max()
        if timeframe == "1M": df = full_df[full_df['time_key'] >= (today - pd.Timedelta(days=30))]
        elif timeframe == "3M": df = full_df[full_df['time_key'] >= (today - pd.Timedelta(days=90))]
        elif timeframe == "6M": df = full_df[full_df['time_key'] >= (today - pd.Timedelta(days=180))]
        elif timeframe == "YTD": df = full_df[full_df['time_key'] >= datetime(today.year, 1, 1)]
        elif timeframe == "1Y": df = full_df[full_df['time_key'] >= (today - pd.Timedelta(days=365))]
        else: df = full_df 
            
        latest_price = df['close'].iloc[-1]
        prev_price = df['close'].iloc[-2] if len(df) > 1 else latest_price
        price_change = latest_price - prev_price
        pct_change = (price_change / prev_price) * 100
        trend_color = "#2ca02c" if price_change >= 0 else "#d62728"
        sign = "+" if price_change >= 0 else ""

        with col_meta:
            st.markdown(f"<h2 style='margin:0; color:#f0f6fc;'>📊 <b>{ticker_input}</b></h2>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='margin:0; color:#f0f6fc;'><b>${latest_price:.2f}</b> <span style='color:{trend_color}; font-size:18px;'>{sign}{price_change:.2f} ({sign}{pct_change:.2f}%)</span></h3>", unsafe_allow_html=True)

        col_left_chart, col_right_metrics = st.columns([2.8, 1.2], gap="large")

        # --- LEFT PANEL WORKSTATION: Interactive Candlesticks, CMF, and RSI ---
        with col_left_chart:
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.55, 0.22, 0.23])
            
            fig.add_trace(go.Scatter(x=df['time_key'], y=df['close'], mode='lines', name='Price', line=dict(color='#2ca02c', width=2)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df['time_key'], y=df['lt_trend'], mode='lines', name='LT Trend', line=dict(color='#58a6ff', width=1.5, dash='dash')), row=1, col=1)
            
            cmf_colors = ['#2ca02c' if val >= 0 else '#d62728' for val in df['cmf']]
            fig.add_trace(go.Bar(x=df['time_key'], y=df['cmf'], marker_color=cmf_colors, name="Chaikin Money Flow"), row=2, col=1)

            fig.add_trace(go.Scatter(x=df['time_key'], y=df['rsi'], mode='lines', name='RSI', line=dict(color='#ff7b72', width=1.5)), row=3, col=1)
            fig.add_hline(y=70, line_dash="dot", line_color="#f85149", row=3, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color="#56d364", row=3, col=1)

            fig.update_layout(
                height=560, margin=dict(l=10, r=10, t=10, b=10),
                plot_bgcolor='#161b22', paper_bgcolor='#0d1117',
                showlegend=False, hovermode="x unified", font=dict(color='#c9d1d9')
            )
            fig.update_xaxes(showgrid=True, gridcolor='#30363d', zeroline=False)
            fig.update_yaxes(showgrid=True, gridcolor='#30363d', zeroline=False)
            st.plotly_chart(fig, width="stretch")
            
            # --- Valuation, Fundamental, & Target Range Dynamic Matrix Cards ---
            st.write("")
            col_v1, col_v2, col_v3 = st.columns(3)
            
            pe_metric = funds.get('pe_ratio', 0.0)
            v_lbl, v_clr = ("Bullish", "#2ca02c") if pe_metric < 20 else ("Neutral", "#e6b800") if pe_metric <= 32 else ("Bearish", "#d62728")
            with col_v1:
                st.markdown(f"""
                    <div class='dashboard-card'>
                        <div class='card-title'>🔍 Valuation Matrix</div>
                        <div class='card-subtitle-bar' style='background-color:{v_clr}22; color:{v_clr};'><span>CLASSIFICATION:</span><span>{v_lbl.upper()}</span></div>
                        <div class='metric-row'><span class='metric-label'>P/E Ratio</span><span class='metric-value'>{pe_metric:.2f}x</span></div>
                        <div class='metric-row'><span class='metric-label'>P/B Ratio</span><span class='metric-value'>{funds.get('pb_ratio', 0.0):.2f}x</span></div>
                        <div class='metric-row'><span class='metric-label'>Pricing Context</span><span class='metric-value'>{"Value Multiples" if pe_metric < 25 else "Growth Premium"}</span></div>
                    </div>
                """, unsafe_allow_html=True)
                
            f_lbl, f_clr = evaluate_factor(results['pillars']['Financials'])
            with col_v2:
                st.markdown(f"""
                    <div class='dashboard-card'>
                        <div class='card-title'>📈 Fundamental Layer</div>
                        <div class='card-subtitle-bar' style='background-color:{f_clr}22; color:{f_clr};'><span>HEALTH INDEX:</span><span>{f_lbl.upper()}</span></div>
                        <div class='metric-row'><span class='metric-label'>Market Cap</span><span class='metric-value'>${(funds.get('market_cap', 0.0)/1e9):.2f}B</span></div>
                        <div class='metric-row'><span class='metric-label'>Dividend Yield</span><span class='metric-value'>{funds.get('dividend_yield', 0.0):.2f}%</span></div>
                        <div class='metric-row'><span class='metric-label'>Capitalization</span><span class='metric-value'>Institutional Asset</span></div>
                    </div>
                """, unsafe_allow_html=True)
                
            high_52 = funds.get('high_52w', latest_price)
            low_52 = funds.get('low_52w', latest_price)
            dist_peak = (((high_52 - latest_price) / high_52) * 100) if high_52 > 0 else 0
            t_lbl, t_clr = ("Bullish", "#2ca02c") if dist_peak > 12 else ("Neutral", "#e6b800")
            with col_v3:
                st.markdown(f"""
                    <div class='dashboard-card'>
                        <div class='card-title'>🎯 Target Ranges (52W)</div>
                        <div class='card-subtitle-bar' style='background-color:{t_clr}22; color:{t_clr};'><span>MOMENTUM STATE:</span><span>{t_lbl.upper()}</span></div>
                        <div class='metric-row'><span class='metric-label'>52W Peak Level</span><span class='metric-value'>${high_52:.2f}</span></div>
                        <div class='metric-row'><span class='metric-label'>52W Floor Level</span><span class='metric-value'>${low_52:.2f}</span></div>
                        <div class='metric-row'><span class='metric-label'>Distance From Peak</span><span class='metric-value'>-{dist_peak:.1f}%</span></div>
                    </div>
                """, unsafe_allow_html=True)

        # --- RIGHT PANEL WORKSTATION: Re-Engineered Premium Needle Speedometer & Checklists ---
        with col_right_metrics:
            rating = results['rating']
            score = results['final_score']
            rating_color = "#2ca02c" if rating == "Bullish" else "#d62728" if rating == "Bearish" else "#e6b800"
            
            # UPGRADED GAUGE CONTROLS: Clean matte textures with an overlapping dynamic threshold pointer block
            gauge_fig = go.Figure(go.Indicator(
                mode="gauge+number", value=score,
                gauge={
                    'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#8b949e", 'ticklen': 4},
                    'bar': {'color': '#f0f6fc', 'thickness': 0.14}, # Slim custom neon internal path tracking cursor
                    'bgcolor': "rgba(0,0,0,0)", 'borderwidth': 0,
                    'steps': [
                        {'range': [0, 35], 'color': '#f85149'},   # Matte Red
                        {'range': [35, 65], 'color': '#d4a373'},  # Matte Yellow/Orange
                        {'range': [65, 100], 'color': '#56d364'}  # Matte Green
                    ],
                    'threshold': {
                        'line': {'color': "#ffffff", 'width': 4}, # Prominent bright needle indicator line
                        'thickness': 0.85,
                        'value': score
                    }
                }
            ))
            gauge_fig.update_layout(height=165, paper_bgcolor='#161b22', plot_bgcolor='#161b22', margin=dict(l=20, r=20, t=10, b=10), font=dict(color='#c9d1d9'))
            
            st.markdown(f"""
                <div style='background-color:#161b22; border:1px solid #30363d; padding:15px; border-radius:8px; text-align:center;'>
                    <p style='color:#8b949e; margin:0; font-size:12px; text-align:left;'>System Target Engine Rating:</p>
                    <h2 style='color:{rating_color}; margin:10px 0 0 0; font-size:26px; font-weight:bold; letter-spacing:1px;'>{rating.upper()}</h2>
            """, unsafe_allow_html=True)
            st.plotly_chart(gauge_fig, width="stretch")
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.write("") 
            st.markdown("**Rating Summary:**")
            st.markdown(f"""
                <div style='background-color:#161b22; border:1px solid #30363d; padding:15px; border-radius:6px; font-size:13px; color:#c9d1d9; line-height:1.5;'>
                    <b>Premium Hunter Engine Status:</b> The systematic tracker evaluating <b>{ticker_input.split('.')[-1]}</b> confirms an active <b><span style='color:{rating_color}'>{rating.lower()}</span></b> trading condition. 
                    This layout index cross-calculates weighted balances across 20 directional variables across core timeframes to identify institutional momentum cycles.
                </div>
            """, unsafe_allow_html=True)
            
            st.write("")
            st.markdown(f"**Checklist Analysis Matrix:**")
            for pillar_name, pillar_score in results['pillars'].items():
                status_lbl, status_clr = evaluate_factor(pillar_score)
                st.markdown(f"""
                    <div class='checklist-row' style='background-color:#161b22; border:1px solid #30363d; border-left: 6px solid {status_clr};'>
                        <span style='color:#c9d1d9;'>{pillar_name}</span>
                        <span style='color:{status_clr};'>{status_lbl} ({pillar_score}/100)</span>
                    </div>
                """, unsafe_allow_html=True)