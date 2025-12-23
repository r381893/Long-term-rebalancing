"""
蜘蛛網回測系統 - Streamlit UI
Spider Web Backtest System

基於凱利投資原理的固定槓桿再平衡策略回測
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
    page_title="🕸️ 蜘蛛網回測系統",
    page_icon="🕸️",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        border: 1px solid #0f3460;
    }
    .metric-value {
        font-size: 2.5em;
        font-weight: bold;
        color: #e94560;
    }
    .metric-label {
        font-size: 0.9em;
        color: #a0a0a0;
    }
    .positive { color: #00d26a !important; }
    .negative { color: #ff4757 !important; }
    .stMetric {
        background: linear-gradient(135deg, #1e1e2f 0%, #252540 100%);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #3a3a5c;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("🕸️ 蜘蛛網回測系統")
st.markdown("**基於凱利投資原理的固定槓桿再平衡策略**")

# Sidebar
st.sidebar.header("⚙️ 參數設定")

# 交易模式
st.sidebar.subheader("📊 交易模式")
futures_mode = st.sidebar.toggle("期貨模式 (微台指)", value=True)

if futures_mode:
    # 期貨合約類型
    contract_type = st.sidebar.selectbox(
        "合約類型",
        options=["微台", "小台", "大台"],
        index=0
    )
    contract_multipliers = {"微台": 10, "小台": 50, "大台": 200}
    contract_multiplier = contract_multipliers[contract_type]
    st.sidebar.caption(f"每點 {contract_multiplier} 元")
    
    # 期貨手續費
    futures_fee = st.sidebar.number_input("手續費/口", value=22, step=1)
else:
    contract_multiplier = 1
    futures_fee = 0

st.sidebar.markdown("---")

# 槓桿設定
st.sidebar.subheader("⚖️ 槓桿設定")
kelly_f = st.sidebar.slider(
    "投資槓桿 f",
    min_value=0.1,
    max_value=5.0,
    value=3.0 if futures_mode else 0.5,
    step=0.1,
    help="f < 1: 跌買漲賣 | f = 1: 不動 | f > 1: 追高殺低"
)

# 槓桿說明
if kelly_f < 1:
    st.sidebar.success(f"✅ f = {kelly_f} < 1 → 跌買漲賣（收割正期望報酬）")
elif kelly_f == 1:
    st.sidebar.info(f"ℹ️ f = {kelly_f} = 1 → 維持部位不動")
else:
    st.sidebar.warning(f"⚠️ f = {kelly_f} > 1 → 追高殺低（類似停損行為）")

st.sidebar.markdown("---")

# 初始資金
st.sidebar.subheader("💰 資金設定")
initial_capital = st.sidebar.number_input(
    "初始資金",
    min_value=100_000,
    max_value=100_000_000,
    value=500_000 if futures_mode else 1_000_000,
    step=50_000,
    format="%d"
)

# 再平衡頻率
rebalance_freq = st.sidebar.selectbox(
    "再平衡頻率",
    options=["daily", "weekly", "monthly"],
    format_func=lambda x: {"daily": "每日", "weekly": "每週", "monthly": "每月"}[x]
)

# 交易成本
include_cost = st.sidebar.checkbox("計入交易成本", value=True)
if not futures_mode:
    if include_cost:
        fee_rate = 0.001425
        tax_rate = 0.003
    else:
        fee_rate = 0
        tax_rate = 0
else:
    fee_rate = 0
    tax_rate = 0

# 逆價差補償 (台指期特有)
if futures_mode:
    include_backwardation = st.sidebar.checkbox(
        "計入逆價差補償 (4%/年)", 
        value=True,
        help="台指期通常有約 3~5% 的年化逆價差，持有期貨可獲得此收益"
    )
    backwardation_rate = 0.04 if include_backwardation else 0
else:
    backwardation_rate = 0

st.sidebar.markdown("---")

# 資料來源
data_path = os.path.join(os.path.dirname(__file__), '..', '加權歷史資料.xlsx')

# 執行按鈕
run_backtest = st.sidebar.button("🚀 執行回測", type="primary", use_container_width=True)

# Main content
if run_backtest or 'result' in st.session_state:
    
    if run_backtest:
        # 載入資料並執行回測
        with st.spinner("載入資料中..."):
            engine = SpiderWebBacktest(
                kelly_f=kelly_f,
                initial_capital=initial_capital,
                rebalance_freq=rebalance_freq,
                transaction_fee_rate=fee_rate,
                tax_rate=tax_rate,
                futures_mode=futures_mode,
                contract_multiplier=contract_multiplier if futures_mode else 1,
                futures_fee_per_contract=futures_fee if futures_mode else 0,
                backwardation_rate=backwardation_rate if futures_mode else 0
            )
            
            try:
                data = engine.load_data(data_path)
                result = engine.run(data)
                st.session_state.result = result
                st.session_state.kelly_f = kelly_f
            except Exception as e:
                st.error(f"回測失敗: {e}")
                st.stop()
    else:
        result = st.session_state.result
    
    # 績效概覽
    st.header("📊 績效概覽")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        return_pct = result.total_return * 100
        st.metric(
            "策略總報酬率",
            f"{return_pct:+.2f}%",
            delta=f"vs 買進持有 {(result.total_return - result.buy_hold_return)*100:+.2f}%"
        )
    
    with col2:
        st.metric(
            "年化報酬率",
            f"{result.annual_return*100:+.2f}%"
        )
    
    with col3:
        st.metric(
            "最大回撤 (MDD)",
            f"{result.max_drawdown*100:.2f}%"
        )
    
    with col4:
        st.metric(
            "夏普比率",
            f"{result.sharpe_ratio:.2f}"
        )
    
    # 對比表格
    st.markdown(f"### 策略比較 (同為 {kelly_f}x 槓桿)")
    compare_df = pd.DataFrame({
        "指標": ["總報酬率", "最終資金"],
        f"蜘蛛網 ({rebalance_freq})": [
            f"{result.total_return*100:+.2f}%",
            f"${result.capitals[-1]:,.0f}"
        ],
        f"永遠做多 (月再平衡)": [
            f"{result.buy_hold_rebal_return*100:+.2f}%",
            f"${result.buy_hold_rebal_capitals[-1]:,.0f}"
        ],
        f"買進持有 (不再平衡)": [
            f"{result.buy_hold_return*100:+.2f}%",
            f"${result.buy_hold_capitals[-1]:,.0f}"
        ]
    })
    st.dataframe(compare_df, use_container_width=True, hide_index=True)
    
    # 策略說明
    st.caption("💡 蜘蛛網: 依f值調整槓桿 | 永遠做多: 每月再平衡維持固定槓桿 | 買進持有: 初始槓桿後不調整")
    
    # 資產曲線圖
    st.header("📈 資產曲線")
    
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=("資產價值", "價格走勢 & 買賣信號", "部位變化"),
        row_heights=[0.4, 0.35, 0.25]
    )
    
    # 資產曲線
    fig.add_trace(
        go.Scatter(
            x=result.dates,
            y=result.capitals,
            name="蜘蛛網策略",
            line=dict(color="#e94560", width=2)
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=result.dates,
            y=result.buy_hold_rebal_capitals,
            name="永遠做多 (月再平衡)",
            line=dict(color="#00d26a", width=2)
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=result.dates,
            y=result.buy_hold_capitals,
            name="買進持有 (不再平衡)",
            line=dict(color="#4a9fff", width=2, dash="dot")
        ),
        row=1, col=1
    )
    
    # 價格 + 買賣信號
    fig.add_trace(
        go.Scatter(
            x=result.dates,
            y=result.prices,
            name="價格",
            line=dict(color="#ffd700", width=1.5)
        ),
        row=2, col=1
    )
    
    # 買進信號 (綠色)
    buy_dates = [result.dates[i] for i in range(len(result.trades)) if result.trades[i] > 100]
    buy_prices = [result.prices[i] for i in range(len(result.trades)) if result.trades[i] > 100]
    
    fig.add_trace(
        go.Scatter(
            x=buy_dates,
            y=buy_prices,
            mode="markers",
            name="買進",
            marker=dict(color="#00d26a", size=6, symbol="triangle-up")
        ),
        row=2, col=1
    )
    
    # 賣出信號 (紅色)
    sell_dates = [result.dates[i] for i in range(len(result.trades)) if result.trades[i] < -100]
    sell_prices = [result.prices[i] for i in range(len(result.trades)) if result.trades[i] < -100]
    
    fig.add_trace(
        go.Scatter(
            x=sell_dates,
            y=sell_prices,
            mode="markers",
            name="賣出",
            marker=dict(color="#ff4757", size=6, symbol="triangle-down")
        ),
        row=2, col=1
    )
    
    # 部位變化
    fig.add_trace(
        go.Scatter(
            x=result.dates,
            y=result.volumes,
            name="持有部位",
            fill="tozeroy",
            line=dict(color="#9b59b6", width=1)
        ),
        row=3, col=1
    )
    
    fig.update_layout(
        height=800,
        template="plotly_dark",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    fig.update_yaxes(title_text="資金", row=1, col=1)
    fig.update_yaxes(title_text="價格", row=2, col=1)
    fig.update_yaxes(title_text="部位", row=3, col=1)
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 價格 vs 口數 雙軸圖
    st.header("📊 價格與口數關係圖")
    st.caption("觀察價格漲跌時，口數如何反向變化（跌買漲賣 or 追高殺低）")
    
    fig_pv = make_subplots(specs=[[{"secondary_y": True}]])
    
    # 價格曲線 (左軸)
    fig_pv.add_trace(
        go.Scatter(
            x=result.dates,
            y=result.prices,
            name="價格",
            line=dict(color="#ffd700", width=2)
        ),
        secondary_y=False
    )
    
    # 口數曲線 (右軸)
    fig_pv.add_trace(
        go.Scatter(
            x=result.dates,
            y=result.volumes,
            name="持有口數",
            line=dict(color="#e94560", width=2)
        ),
        secondary_y=True
    )
    
    fig_pv.update_layout(
        height=400,
        template="plotly_dark",
        hovermode="x unified",
        title="價格↑口數↓ = 跌買漲賣 (f<1) | 價格↑口數↑ = 追高殺低 (f>1)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    
    fig_pv.update_yaxes(title_text="價格", secondary_y=False, color="#ffd700")
    fig_pv.update_yaxes(title_text="口數", secondary_y=True, color="#e94560")
    
    st.plotly_chart(fig_pv, use_container_width=True)
    
    # 交易統計
    st.header("📋 交易統計")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("總交易次數", f"{result.total_trades:,}")
    with col2:
        st.metric("累計買進單位", f"{result.total_buy_volume:,.0f}")
    with col3:
        st.metric("累計賣出單位", f"{result.total_sell_volume:,.0f}")
    
    # 詳細交易記錄 (可展開)
    with st.expander("📝 查看詳細交易記錄 (含進出邏輯)"):
        trade_df = pd.DataFrame({
            "日期": result.dates,
            "價格": result.prices,
            "部位": result.volumes,
            "買賣": result.trades,
            "進出邏輯": result.trade_reasons,
            "資金": result.capitals
        })
        
        # 只顯示有交易的日期
        trade_df = trade_df[trade_df["買賣"].abs() > 0]
        trade_df["買賣"] = trade_df["買賣"].apply(lambda x: f"+{int(x)}" if x > 0 else str(int(x)))
        trade_df["資金"] = trade_df["資金"].apply(lambda x: f"${x:,.0f}")
        
        st.dataframe(trade_df, use_container_width=True, hide_index=True)

else:
    # 首頁說明
    st.info("👈 請調整左側參數後，點擊「執行回測」按鈕開始")
    
    st.markdown("""
    ## 凱利投資原理
    
    | 槓桿 f | 價格變動時的行為 | 說明 |
    |--------|------------------|------|
    | **f < 1** | 跌買漲賣 | ✅ 收割正期望報酬率 |
    | **f = 1** | 不動 | 維持原有部位 |
    | **f > 1** | 追高殺低 | ⚠️ 類似停損行為 |
    
    ---
    
    ### 核心公式
    
    - **投資金額** = 總資金 × 槓桿 f
    - **期末資金** = 期初資金 + 部位 × 價差
    - **調整部位** bs = (f-1) × Δp × q / [p × (1 + f×Δp/p)]
    
    當 f < 1 且價格下跌時，bs > 0（買進）  
    當 f < 1 且價格上漲時，bs < 0（賣出）
    
    **這就是為什麼 f < 1 會跌買漲賣！**
    """)
