"""
📊 三策略比較系統 - Streamlit UI
重建 dashboard.html 的精美介面
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

from backtest_engine import SpiderWebBacktest, BacktestResult

# Page Config
st.set_page_config(
    page_title="📊 三策略比較系統",
    page_icon="📊",
    layout="wide"
)

# Premium Dark Theme CSS (from dashboard.html)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&family=Inter:wght@400;600;700&display=swap');
    
    /* 全域深色背景 */
    .stApp {
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%) !important;
    }
    
    /* 隱藏 Streamlit 預設元素 */
    #MainMenu, footer, header {visibility: hidden;}
    
    /* 漸層標題 */
    .gradient-title {
        font-size: 2.8rem !important;
        font-weight: 700 !important;
        background: linear-gradient(90deg, #e94560, #00d26a, #4a9fff) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        background-clip: text !important;
        text-align: center !important;
        margin-bottom: 5px !important;
    }
    
    .subtitle {
        color: #888 !important;
        font-size: 1.2rem !important;
        text-align: center !important;
        margin-bottom: 30px !important;
    }
    
    /* 參數區毛玻璃效果 */
    .params-section {
        background: rgba(255, 255, 255, 0.05) !important;
        border-radius: 20px !important;
        padding: 25px !important;
        margin-bottom: 30px !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    
    /* 策略卡片 - 蜘蛛網 (紅) */
    .card-spider {
        background: linear-gradient(135deg, rgba(233, 69, 96, 0.15) 0%, rgba(233, 69, 96, 0.05) 100%) !important;
        border: 1px solid rgba(233, 69, 96, 0.3) !important;
        border-top: 5px solid #e94560 !important;
        border-radius: 20px !important;
        padding: 25px !important;
    }
    
    /* 策略卡片 - 永遠做多 (綠) */
    .card-forever {
        background: linear-gradient(135deg, rgba(0, 210, 106, 0.15) 0%, rgba(0, 210, 106, 0.05) 100%) !important;
        border: 1px solid rgba(0, 210, 106, 0.3) !important;
        border-top: 5px solid #00d26a !important;
        border-radius: 20px !important;
        padding: 25px !important;
    }
    
    /* 策略卡片 - 買進持有 (藍) */
    .card-buyhold {
        background: linear-gradient(135deg, rgba(74, 159, 255, 0.15) 0%, rgba(74, 159, 255, 0.05) 100%) !important;
        border: 1px solid rgba(74, 159, 255, 0.3) !important;
        border-top: 5px solid #4a9fff !important;
        border-radius: 20px !important;
        padding: 25px !important;
    }
    
    .card-icon { font-size: 2.5rem; }
    .card-title { font-size: 1.5rem; font-weight: 700; color: #fff; }
    .card-subtitle { font-size: 0.95rem; color: #888; }
    
    .metric-label { font-size: 0.9rem; color: #888; margin-bottom: 5px; }
    .metric-value { font-size: 2rem; font-weight: 700; font-family: 'Inter', sans-serif; }
    .metric-value.positive { color: #00d26a; }
    .metric-value.negative { color: #e94560; }
    .metric-value.neutral { color: #4a9fff; }
    
    .card-footer { 
        margin-top: 15px; 
        padding-top: 15px; 
        border-top: 1px solid rgba(255,255,255,0.1); 
        font-size: 0.9rem; 
        color: #666; 
    }
    
    /* 圖表區 */
    .chart-section {
        background: rgba(255, 255, 255, 0.03) !important;
        border-radius: 20px !important;
        padding: 25px !important;
        margin-top: 30px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    
    /* 按鈕樣式 */
    .stButton > button {
        background: linear-gradient(135deg, #e94560 0%, #ff6b6b 100%) !important;
        color: white !important;
        border: none !important;
        padding: 15px 40px !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        border-radius: 12px !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 10px 30px rgba(233, 69, 96, 0.4) !important;
    }
    
    /* 輸入框 */
    .stNumberInput > div > div > input {
        background: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 10px !important;
        color: #fff !important;
    }
    
    /* 說明卡片 */
    .info-card {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 15px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .info-card h4 { font-size: 1.1rem; margin-bottom: 10px; color: #fff; }
    .info-card p { color: #888; font-size: 0.9rem; line-height: 1.6; }
    
    /* 隱藏側邊欄 */
    [data-testid="stSidebar"] { display: none; }
</style>
""", unsafe_allow_html=True)

# 標題
st.markdown('<h1 class="gradient-title">📊 三策略比較系統</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">蜘蛛網 vs 永遠做多 vs 買進持有</p>', unsafe_allow_html=True)

# 參數區
st.markdown('<div class="params-section">', unsafe_allow_html=True)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    initial_capital = st.number_input("初始資金", value=1000000, step=100000, format="%d")

with col2:
    backwardation = st.number_input("逆價差補償 (%/年)", value=4.0, step=0.5, min_value=0.0, max_value=8.0)

with col3:
    spider_f = st.number_input("🕸️ 蜘蛛網 f 值", value=0.5, step=0.1, min_value=0.1, max_value=1.0)

with col4:
    forever_f = st.number_input("📈 永遠做多槓桿", value=3.0, step=0.5, min_value=1.0, max_value=5.0)

with col5:
    buyhold_f = st.number_input("🏦 買進持有初始槓桿", value=3.0, step=0.5, min_value=1.0, max_value=5.0)

st.markdown('</div>', unsafe_allow_html=True)

# 執行按鈕
run_backtest = st.button("🚀 執行比較回測", use_container_width=True)

# 資料來源
data_path = os.path.join(os.path.dirname(__file__), '加權歷史資料.xlsx')

if run_backtest or 'results' in st.session_state:
    
    if run_backtest:
        with st.spinner("計算中，請稍候..."):
            # 策略1: 蜘蛛網
            engine1 = SpiderWebBacktest(
                kelly_f=spider_f,
                initial_capital=initial_capital,
                rebalance_freq='daily',
                futures_mode=True,
                contract_multiplier=10,
                futures_fee_per_contract=22,
                backwardation_rate=backwardation/100
            )
            data = engine1.load_data(data_path)
            r_spider = engine1.run(data)
            
            # 策略2: 永遠做多
            engine2 = SpiderWebBacktest(
                kelly_f=forever_f,
                initial_capital=initial_capital,
                rebalance_freq='monthly',
                futures_mode=True,
                contract_multiplier=10,
                futures_fee_per_contract=22,
                backwardation_rate=backwardation/100
            )
            r_forever = engine2.run(data)
            
            # 策略3: 買進持有
            engine3 = SpiderWebBacktest(
                kelly_f=buyhold_f,
                initial_capital=initial_capital,
                rebalance_freq='daily',
                futures_mode=True,
                contract_multiplier=10,
                futures_fee_per_contract=22,
                backwardation_rate=backwardation/100
            )
            r_buyhold = engine3.run(data)
            
            st.session_state.results = {
                'spider': r_spider,
                'forever': r_forever,
                'buyhold': r_buyhold,
                'spider_f': spider_f,
                'forever_f': forever_f,
                'buyhold_f': buyhold_f
            }
    
    results = st.session_state.results
    r_spider = results['spider']
    r_forever = results['forever']
    r_buyhold = results['buyhold']
    
    # 三策略卡片
    col1, col2, col3 = st.columns(3)
    
    # 蜘蛛網卡片
    with col1:
        st.markdown(f'''
        <div class="card-spider">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
                <span class="card-icon">🕸️</span>
                <div>
                    <div class="card-title">蜘蛛網</div>
                    <div class="card-subtitle">跌買漲賣</div>
                </div>
            </div>
            <div style="margin-bottom: 15px;">
                <div class="metric-label">總報酬率</div>
                <div class="metric-value positive">+{r_spider.total_return*100:.2f}%</div>
            </div>
            <div style="margin-bottom: 15px;">
                <div class="metric-label">最終資金</div>
                <div class="metric-value neutral">${r_spider.capitals[-1]:,.0f}</div>
            </div>
            <div style="margin-bottom: 15px;">
                <div class="metric-label">最大回撤 (MDD)</div>
                <div class="metric-value negative">{r_spider.max_drawdown*100:.2f}%</div>
            </div>
            <div class="card-footer">f={results['spider_f']}, 每日再平衡</div>
        </div>
        ''', unsafe_allow_html=True)
    
    # 永遠做多卡片
    with col2:
        st.markdown(f'''
        <div class="card-forever">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
                <span class="card-icon">📈</span>
                <div>
                    <div class="card-title">永遠做多</div>
                    <div class="card-subtitle">再平衡維持槓桿</div>
                </div>
            </div>
            <div style="margin-bottom: 15px;">
                <div class="metric-label">總報酬率</div>
                <div class="metric-value positive">+{r_forever.total_return*100:.2f}%</div>
            </div>
            <div style="margin-bottom: 15px;">
                <div class="metric-label">最終資金</div>
                <div class="metric-value neutral">${r_forever.capitals[-1]:,.0f}</div>
            </div>
            <div style="margin-bottom: 15px;">
                <div class="metric-label">最大回撤 (MDD)</div>
                <div class="metric-value negative">{r_forever.max_drawdown*100:.2f}%</div>
            </div>
            <div class="card-footer">f={results['forever_f']}, 每月再平衡</div>
        </div>
        ''', unsafe_allow_html=True)
    
    # 買進持有卡片
    with col3:
        st.markdown(f'''
        <div class="card-buyhold">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
                <span class="card-icon">🏦</span>
                <div>
                    <div class="card-title">買進持有</div>
                    <div class="card-subtitle">不再平衡</div>
                </div>
            </div>
            <div style="margin-bottom: 15px;">
                <div class="metric-label">總報酬率</div>
                <div class="metric-value positive">+{r_buyhold.buy_hold_return*100:.2f}%</div>
            </div>
            <div style="margin-bottom: 15px;">
                <div class="metric-label">最終資金</div>
                <div class="metric-value neutral">${r_buyhold.buy_hold_capitals[-1]:,.0f}</div>
            </div>
            <div style="margin-bottom: 15px;">
                <div class="metric-label">最大回撤 (MDD)</div>
                <div class="metric-value negative">{r_buyhold.buy_hold_mdd*100:.2f}%</div>
            </div>
            <div class="card-footer">初始 {results['buyhold_f']}x 槓桿</div>
        </div>
        ''', unsafe_allow_html=True)
    
    # 圖表區
    st.markdown('<div class="chart-section">', unsafe_allow_html=True)
    st.markdown("### 📈 資產曲線比較")
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=r_spider.dates,
        y=r_spider.capitals,
        name='🕸️ 蜘蛛網',
        line=dict(color='#e94560', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=r_forever.dates,
        y=r_forever.capitals,
        name='📈 永遠做多',
        line=dict(color='#00d26a', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=r_buyhold.dates,
        y=r_buyhold.buy_hold_capitals,
        name='🏦 買進持有',
        line=dict(color='#4a9fff', width=2)
    ))
    
    fig.update_layout(
        height=450,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#888', family='Inter, sans-serif', size=14),
        xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(gridcolor='rgba(255,255,255,0.1)', title='資產價值', tickformat=',.0f'),
        legend=dict(orientation='h', y=1.1, font=dict(size=14)),
        margin=dict(t=50, b=50, l=80, r=30)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 詳細比較表
    st.markdown('<div class="chart-section">', unsafe_allow_html=True)
    st.markdown("### 📋 詳細比較表")
    
    compare_df = pd.DataFrame({
        "策略": ["🕸️ 蜘蛛網", "📈 永遠做多", "🏦 買進持有"],
        "槓桿": [f"{results['spider_f']}x", f"{results['forever_f']}x", f"{results['buyhold_f']}x (初始)"],
        "再平衡": ["每日", "每月", "不再平衡"],
        "總報酬率": [f"+{r_spider.total_return*100:.2f}%", f"+{r_forever.total_return*100:.2f}%", f"+{r_buyhold.buy_hold_return*100:.2f}%"],
        "年化報酬": [f"{r_spider.annual_return*100:.2f}%", f"{r_forever.annual_return*100:.2f}%", f"{r_buyhold.buy_hold_annual_return*100:.2f}%"],
        "MDD": [f"{r_spider.max_drawdown*100:.2f}%", f"{r_forever.max_drawdown*100:.2f}%", f"{r_buyhold.buy_hold_mdd*100:.2f}%"]
    })
    
    st.dataframe(compare_df, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

else:
    # 首頁說明區
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('''
        <div class="info-card">
            <h4>🕸️ 蜘蛛網策略</h4>
            <p>• f < 1: 跌買漲賣<br>
            • 下跌時買進，上漲時賣出<br>
            • 收割價格波動的正期望報酬<br>
            • 適合震盪市場</p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col2:
        st.markdown('''
        <div class="info-card">
            <h4>📈 永遠做多</h4>
            <p>• 維持固定槓桿<br>
            • 定期再平衡維持目標槓桿<br>
            • 上漲時加碼，下跌時減碼<br>
            • 適合趨勢市場</p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col3:
        st.markdown('''
        <div class="info-card">
            <h4>🏦 買進持有</h4>
            <p>• 初始槓桿後不調整<br>
            • 槓桿會隨價格漂移<br>
            • 上漲後槓桿降低<br>
            • 最低交易成本</p>
        </div>
        ''', unsafe_allow_html=True)
