"""比較不同 f 值的回測結果"""
import pandas as pd
import sys
sys.path.insert(0, '.')
from backtest_engine import SpiderWebBacktest

data_path = '../加權歷史資料.xlsx'

print("=" * 70)
print("蜘蛛網策略比較 (微台, 50萬, 含4%逆價差)")
print("=" * 70)
print(f"{'f':^6} | {'策略報酬':^12} | {'買進持有':^12} | {'MDD':^8} | {'行為'}")
print("-" * 70)

for f in [0.5, 1.0, 2.0]:
    engine = SpiderWebBacktest(
        kelly_f=f,
        initial_capital=500000,
        rebalance_freq='daily',
        futures_mode=True,
        contract_multiplier=10,
        futures_fee_per_contract=22,
        backwardation_rate=0.04
    )
    data = engine.load_data(data_path)
    result = engine.run(data)
    
    behavior = "跌買漲賣" if f < 1 else ("不動" if f == 1 else "追高殺低")
    
    print(f"{f:^6.1f} | {result.total_return*100:>+10.2f}% | {result.buy_hold_return*100:>+10.2f}% | {result.max_drawdown*100:>6.2f}% | {behavior}")

print("=" * 70)
