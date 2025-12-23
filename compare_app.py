"""
三策略比較回測系統
1. 蜘蛛網 (f<1, 跌買漲賣)
2. 永遠做多 (維持固定槓桿)
3. 買進持有 (不再平衡)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

from backtest_engine import SpiderWebBacktest

# Page Config
st.set_page_config(
    page_title="📊 三策略比較系統",
    page_icon="📊",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .stMetric {
        background: linear-gradient(135deg, #1e1e2f 0%, #252540 100%);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #3a3a5c;
    }
    .strategy-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #0f3460;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("📊 三策略比較系統")
st.markdown("**蜘蛛網 vs 永遠做多 vs 買進持有**")

# Sidebar - 共用設定
st.sidebar.header("⚙️ 共用設定")

# 初始資金
initial_capital = st.sidebar.number_input(
    "初始資金",
    min_value=100_000,
    max_value=100_000_000,
    value=1_000_000,
    step=100_000,
    format="%d"
)

# 合約類型
contract_type = st.sidebar.selectbox(
    "合約類型",
    options=["微台", "小台", "大台"],
    index=0
)
contract_multipliers = {"微台": 10, "小台": 50, "大台": 200}
contract_multiplier = contract_multipliers[contract_type]
st.sidebar.caption(f"每點 {contract_multiplier} 元")

# 逆價差
backwardation_rate = st.sidebar.slider(
    "逆價差補償 (%/年)",
    min_value=0.0,
    max_value=8.0,
    value=4.0,
    step=0.5
) / 100

st.sidebar.markdown("---")

# 策略一: 蜘蛛網
st.sidebar.header("🕸️ 策略1: 蜘蛛網")
spider_f = st.sidebar.slider(
    "蜘蛛網槓桿 f",
    min_value=0.1,
    max_value=1.0,
    value=0.5,
    step=0.1,
    help="f < 1: 跌買漲賣，收割期望報酬率"
)
spider_freq = st.sidebar.selectbox(
    "蜘蛛網再平衡頻率",
    options=["daily", "weekly", "monthly"],
    format_func=lambda x: {"daily": "每日", "weekly": "每週", "monthly": "每月"}[x],
    key="spider_freq"
)
st.sidebar.success(f"✅ f={spider_f} → 跌買漲賣")

st.sidebar.markdown("---")

# 策略二: 永遠做多
st.sidebar.header("📈 策略2: 永遠做多")
forever_f = st.sidebar.slider(
    "永遠做多槓桿",
    min_value=1.0,
    max_value=5.0,
    value=3.0,
    step=0.5,
    help="維持固定槓桿，定期再平衡"
)
forever_freq = st.sidebar.selectbox(
    "永遠做多再平衡頻率",
    options=["daily", "weekly", "monthly"],
    format_func=lambda x: {"daily": "每日", "weekly": "每週", "monthly": "每月"}[x],
    index=2,  # 預設每月
    key="forever_freq"
)
st.sidebar.warning(f"⚠️ f={forever_f} → 追高殺低")

st.sidebar.markdown("---")

# 策略三: 買進持有
st.sidebar.header("🏦 策略3: 買進持有")
buyhold_f = st.sidebar.slider(
    "買進持有初始槓桿",
    min_value=1.0,
    max_value=5.0,
    value=3.0,
    step=0.5,
    help="初始槓桿，之後不調整"
)
st.sidebar.info(f"ℹ️ 初始 {buyhold_f}x，不再平衡")

st.sidebar.markdown("---")

# 執行按鈕
run_backtest = st.sidebar.button("🚀 執行比較回測", type="primary", use_container_width=True)

# 資料來源
data_path = os.path.join(os.path.dirname(__file__), '..', '加權歷史資料.xlsx')

# Main content
if run_backtest or 'results' in st.session_state:
    
    if run_backtest:
        results = {}
        
        with st.spinner("執行回測中..."):
            # 策略1: 蜘蛛網
            engine1 = SpiderWebBacktest(
                kelly_f=spider_f,
                initial_capital=initial_capital,
                rebalance_freq=spider_freq,
                futures_mode=True,
                contract_multiplier=contract_multiplier,
                futures_fee_per_contract=22,
                backwardation_rate=backwardation_rate
            )
            data = engine1.load_data(data_path)
            results['spider'] = engine1.run(data)
            
            # 策略2: 永遠做多
            engine2 = SpiderWebBacktest(
                kelly_f=forever_f,
                initial_capital=initial_capital,
                rebalance_freq=forever_freq,
                futures_mode=True,
                contract_multiplier=contract_multiplier,
                futures_fee_per_contract=22,
                backwardation_rate=backwardation_rate
            )
            results['forever'] = engine2.run(data)
            
            # 策略3: 買進持有 (用 daily 但實際上我們看 buy_hold_capitals)
            engine3 = SpiderWebBacktest(
                kelly_f=buyhold_f,
                initial_capital=initial_capital,
                rebalance_freq='daily',
                futures_mode=True,
                contract_multiplier=contract_multiplier,
                futures_fee_per_contract=22,
                backwardation_rate=backwardation_rate
            )
            results['buyhold'] = engine3.run(data)
            
            st.session_state.results = results
            st.session_state.params = {
                'spider_f': spider_f,
                'forever_f': forever_f,
                'buyhold_f': buyhold_f,
                'spider_freq': spider_freq,
                'forever_freq': forever_freq,
            }
    else:
        results = st.session_state.results
    
    # 績效概覽
    st.header("📊 三策略績效比較")
    
    col1, col2, col3 = st.columns(3)
    
    r_spider = results['spider']
    r_forever = results['forever']
    r_buyhold = results['buyhold']
    
    with col1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #e94560 0%, #c73e54 100%); 
                    padding: 20px; border-radius: 15px; color: white; margin-bottom: 10px;">
            <h3 style="color: white; margin: 0;">🕸️ 蜘蛛網</h3>
            <p style="color: #ffcdd2; margin: 5px 0;">跌買漲賣</p>
        </div>
        """, unsafe_allow_html=True)
        st.metric("總報酬率", f"{r_spider.total_return*100:+.2f}%")
        st.metric("最終資金", f"${r_spider.capitals[-1]:,.0f}")
        st.metric("MDD", f"{r_spider.max_drawdown*100:.2f}%")
        st.caption(f"f={spider_f}, {spider_freq}")
    
    with col2:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #00d26a 0%, #00b359 100%); 
                    padding: 20px; border-radius: 15px; color: white; margin-bottom: 10px;">
            <h3 style="color: white; margin: 0;">📈 永遠做多</h3>
            <p style="color: #c8f7dc; margin: 5px 0;">再平衡維持槓桿</p>
        </div>
        """, unsafe_allow_html=True)
        st.metric("總報酬率", f"{r_forever.total_return*100:+.2f}%")
        st.metric("最終資金", f"${r_forever.capitals[-1]:,.0f}")
        st.metric("MDD", f"{r_forever.max_drawdown*100:.2f}%")
        st.caption(f"f={forever_f}, {forever_freq}")
    
    with col3:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #4a9fff 0%, #3a8ed8 100%); 
                    padding: 20px; border-radius: 15px; color: white; margin-bottom: 10px;">
            <h3 style="color: white; margin: 0;">🏦 買進持有</h3>
            <p style="color: #bbdefb; margin: 5px 0;">不再平衡</p>
        </div>
        """, unsafe_allow_html=True)
        st.metric("總報酬率", f"{r_buyhold.buy_hold_return*100:+.2f}%")
        st.metric("最終資金", f"${r_buyhold.buy_hold_capitals[-1]:,.0f}")
        st.metric("MDD", f"{r_buyhold.buy_hold_mdd*100:.2f}%")
        st.caption(f"初始 {buyhold_f}x")
    
    # 對比表格
    st.markdown("### 詳細比較表")
    compare_df = pd.DataFrame({
        "策略": ["🕸️ 蜘蛛網", "📈 永遠做多", "🏦 買進持有"],
        "槓桿": [f"{spider_f}x", f"{forever_f}x", f"{buyhold_f}x (初始)"],
        "再平衡": [spider_freq, forever_freq, "不再平衡"],
        "總報酬率": [
            f"{r_spider.total_return*100:+.2f}%",
            f"{r_forever.total_return*100:+.2f}%",
            f"{r_buyhold.buy_hold_return*100:+.2f}%"
        ],
        "最終資金": [
            f"${r_spider.capitals[-1]:,.0f}",
            f"${r_forever.capitals[-1]:,.0f}",
            f"${r_buyhold.buy_hold_capitals[-1]:,.0f}"
        ],
        "年化報酬": [
            f"{r_spider.annual_return*100:.2f}%",
            f"{r_forever.annual_return*100:.2f}%",
            f"{r_buyhold.buy_hold_annual_return*100:.2f}%"
        ],
        "MDD": [
            f"{r_spider.max_drawdown*100:.2f}%",
            f"{r_forever.max_drawdown*100:.2f}%",
            f"{r_buyhold.buy_hold_mdd*100:.2f}%"
        ]
    })
    st.dataframe(compare_df, use_container_width=True, hide_index=True)
    
    # 資產曲線圖
    st.header("📈 資產曲線比較")
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=r_spider.dates,
        y=r_spider.capitals,
        name=f"🕸️ 蜘蛛網 (f={spider_f})",
        line=dict(color="#e94560", width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=r_forever.dates,
        y=r_forever.capitals,
        name=f"📈 永遠做多 (f={forever_f})",
        line=dict(color="#00d26a", width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=r_buyhold.dates,
        y=r_buyhold.buy_hold_capitals,
        name=f"🏦 買進持有 ({buyhold_f}x)",
        line=dict(color="#4a9fff", width=2, dash="dot")
    ))
    
    fig.update_layout(
        height=500,
        template="plotly_dark",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        yaxis_title="資產價值"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 策略說明
    st.header("📖 策略說明")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        #### 🕸️ 蜘蛛網策略
        - **f < 1**: 跌買漲賣
        - 下跌時買進，上漲時賣出
        - 收割價格波動的正期望報酬
        - 適合震盪市場
        """)
    
    with col2:
        st.markdown("""
        #### 📈 永遠做多
        - **維持固定槓桿**
        - 定期再平衡維持目標槓桿
        - 上漲時加碼，下跌時減碼
        - 適合趨勢市場
        """)
    
    with col3:
        st.markdown("""
        #### 🏦 買進持有
        - **初始槓桿後不調整**
        - 槓桿會隨價格漂移
        - 上漲後槓桿降低
        - 最低交易成本
        """)

else:
    # 首頁說明
    st.info("👈 請調整左側三種策略的參數，點擊「執行比較回測」開始")
    
    st.markdown("""
    ## 三種策略比較
    
    | 策略 | f 值 | 行為 | 特點 |
    |------|------|------|------|
    | **🕸️ 蜘蛛網** | f < 1 | 跌買漲賣 | 收割期望報酬率 |
    | **📈 永遠做多** | f ≥ 1 | 維持槓桿 | 追高殺低 |
    | **🏦 買進持有** | 初始設定 | 不調整 | 槓桿漂移 |
    
    ---
    
    ### 使用說明
    1. 設定共用參數（初始資金、合約類型、逆價差）
    2. 分別設定三種策略的槓桿和再平衡頻率
    3. 點擊「執行比較回測」查看結果
    """)
