"""
蜘蛛網回測引擎 (Spider Web Backtest Engine)
基於凱利投資原理：固定槓桿再平衡策略

核心公式：
- 投資金額 = 總資金 × 槓桿 f
- 期末資金 = 期初資金 + 部位 × 價差
- 調整部位 bs = (f-1) × Δp × q / [p × (1 + f×Δp/p)]

當 f < 1：跌買漲賣（收割正期望報酬率）
當 f = 1：不動
當 f > 1：追高殺低
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class BacktestResult:
    """回測結果資料結構"""
    dates: List[str]
    prices: List[float]
    capitals: List[float]
    volumes: List[float]
    trades: List[float]  # bs: 正=買, 負=賣
    trade_reasons: List[str]  # 進出邏輯說明
    buy_hold_capitals: List[float]  # 買進持有對照組 (不再平衡)
    buy_hold_rebal_capitals: List[float]  # 買進持有+月再平衡 (永遠做多)
    
    # 績效指標
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    buy_hold_return: float
    buy_hold_annual_return: float  # 買進持有年化報酬
    buy_hold_mdd: float  # 買進持有最大回撇
    buy_hold_rebal_return: float  # 月再平衡買進持有報酬率
    
    # 交易統計
    total_trades: int
    total_buy_volume: float
    total_sell_volume: float


class SpiderWebBacktest:
    """
    蜘蛛網回測引擎
    
    使用固定槓桿再平衡策略，模擬歷史資料上的投資績效。
    """
    
    def __init__(
        self,
        kelly_f: float = 0.5,
        initial_capital: float = 1_000_000,
        rebalance_freq: str = "daily",  # daily, weekly, monthly
        transaction_fee_rate: float = 0.001425,  # 台股手續費率
        tax_rate: float = 0.003,  # 證交稅率
        # 期貨模式參數
        futures_mode: bool = False,
        contract_multiplier: float = 10,  # 微台每點10元
        futures_fee_per_contract: float = 22,  # 期貨手續費/口
        backwardation_rate: float = 0,  # 逆價差補償率 (年化)
    ):
        """
        初始化回測引擎
        
        Args:
            kelly_f: 凱利槓桿 (0~2)，建議 < 1
            initial_capital: 初始資金
            rebalance_freq: 再平衡頻率 (daily/weekly/monthly)
            transaction_fee_rate: 手續費率 (股票模式)
            tax_rate: 賣出時的稅率 (股票模式)
            futures_mode: 是否為期貨模式
            contract_multiplier: 期貨合約乘數 (微台=10, 小台=50, 大台=200)
            futures_fee_per_contract: 期貨手續費/口
            backwardation_rate: 逆價差補償率 (年化，如 0.04 = 4%)
        """
        self.f = kelly_f
        self.initial_capital = initial_capital
        self.rebalance_freq = rebalance_freq
        self.fee_rate = transaction_fee_rate
        self.tax_rate = tax_rate
        self.futures_mode = futures_mode
        self.contract_multiplier = contract_multiplier
        self.futures_fee = futures_fee_per_contract
        self.backwardation_rate = backwardation_rate
        # 每日逆價差收益 (252個交易日)
        self.daily_backwardation = backwardation_rate / 252
        
    def load_data(self, filepath: str) -> pd.DataFrame:
        """載入歷史資料"""
        if filepath.endswith('.xlsx'):
            df = pd.read_excel(filepath)
        else:
            df = pd.read_csv(filepath)
        
        # 標準化欄位名稱
        df.columns = [c.strip().upper() for c in df.columns]
        if 'CLOSE' not in df.columns:
            # 嘗試找收盤價欄位
            for col in df.columns:
                if '收盤' in col or 'PRICE' in col:
                    df['CLOSE'] = df[col]
                    break
        
        df['DATE'] = pd.to_datetime(df['DATE'])
        df = df.sort_values('DATE').reset_index(drop=True)
        
        return df
    
    def _should_rebalance(self, date: pd.Timestamp, prev_date: Optional[pd.Timestamp]) -> bool:
        """判斷是否需要再平衡"""
        if prev_date is None:
            return True
            
        if self.rebalance_freq == "daily":
            return True
        elif self.rebalance_freq == "weekly":
            return date.isocalendar()[1] != prev_date.isocalendar()[1]
        elif self.rebalance_freq == "monthly":
            return date.month != prev_date.month
        return True
    
    def _calculate_trade_cost(self, trade_value: float, is_sell: bool, contracts: int = 0) -> float:
        """計算交易成本"""
        if self.futures_mode:
            # 期貨: 固定手續費/口
            return abs(contracts) * self.futures_fee
        else:
            # 股票: 成交金額比例
            cost = abs(trade_value) * self.fee_rate
            if is_sell:
                cost += abs(trade_value) * self.tax_rate
            return cost
    
    def run(self, data: pd.DataFrame) -> BacktestResult:
        """
        執行回測
        
        Args:
            data: 包含 DATE 和 CLOSE 欄位的 DataFrame
            
        Returns:
            BacktestResult: 回測結果
        """
        dates = []
        prices = []
        capitals = []
        volumes = []
        trades = []
        trade_reasons = []  # 進出邏輯說明
        buy_hold_capitals = []
        buy_hold_rebal_capitals = []  # 月再平衡買進持有
        
        # 初始化
        cap = self.initial_capital
        price = data.loc[0, 'CLOSE']
        
        if self.futures_mode:
            # 期貨模式: 投資金額 = 口數 × 價格 × 乘數
            # 口數 = 資金 × 槓桿 / (價格 × 乘數)
            vol = int(cap * self.f / (price * self.contract_multiplier))
            # 買進持有也用相同槓桿，才能公平比較
            bh_vol = int(self.initial_capital * self.f / (price * self.contract_multiplier))
            bh_rebal_vol = bh_vol  # 月再平衡買進持有
        else:
            # 股票模式: 直接用價格計算單位數
            vol = int(cap * self.f / price)
            bh_vol = int(self.initial_capital * self.f / price)
            bh_rebal_vol = bh_vol
        
        # 買進持有對照組 (相同槓桿，不再平衡)
        bh_cap = self.initial_capital
        # 月再平衡買進持有 (永遠做多)
        bh_rebal_cap = self.initial_capital
        bh_rebal_prev_month = None
        
        prev_date = None
        total_trade_cost = 0
        
        for i in range(len(data)):
            row = data.iloc[i]
            date = row['DATE']
            new_price = row['CLOSE']
            
            if i == 0:
                # 第一期：買進初始部位
                dates.append(str(date.date()))
                prices.append(new_price)
                capitals.append(cap)
                volumes.append(vol)
                trades.append(vol)  # 初始買進
                trade_reasons.append(f"初始建倉: 資金{cap:,.0f} × 槓桿{self.f} = 投資{cap*self.f:,.0f}")
                buy_hold_capitals.append(bh_cap)
                prev_date = date
                price = new_price
                continue
            
            # 計算損益
            delta_p = new_price - price
            if self.futures_mode:
                # 期貨: 損益 = 口數 × 點差 × 乘數
                pnl = vol * delta_p * self.contract_multiplier
                bh_pnl = bh_vol * delta_p * self.contract_multiplier
                bh_rebal_pnl = bh_rebal_vol * delta_p * self.contract_multiplier
                
                # 逆價差補償: 每日收益 = 合約價值 × 每日補償率
                if self.daily_backwardation > 0:
                    contract_value = vol * price * self.contract_multiplier
                    bh_contract_value = bh_vol * price * self.contract_multiplier
                    bh_rebal_contract_value = bh_rebal_vol * price * self.contract_multiplier
                    backwardation_income = contract_value * self.daily_backwardation
                    bh_backwardation_income = bh_contract_value * self.daily_backwardation
                    bh_rebal_backwardation = bh_rebal_contract_value * self.daily_backwardation
                    pnl += backwardation_income
                    bh_pnl += bh_backwardation_income
                    bh_rebal_pnl += bh_rebal_backwardation
                
                cap = cap + pnl
                bh_cap = bh_cap + bh_pnl
                bh_rebal_cap = bh_rebal_cap + bh_rebal_pnl
                
                # 月再平衡買進持有 (每月調整口數維持槓桿)
                if bh_rebal_prev_month is None or date.month != bh_rebal_prev_month:
                    bh_rebal_vol = int(bh_rebal_cap * self.f / (new_price * self.contract_multiplier))
                    bh_rebal_prev_month = date.month
            else:
                # 股票: 損益 = 單位數 × 價差
                cap = cap + vol * delta_p
                bh_cap = bh_cap + bh_vol * delta_p
                bh_rebal_cap = bh_rebal_cap + bh_rebal_vol * delta_p
                if bh_rebal_prev_month is None or date.month != bh_rebal_prev_month:
                    bh_rebal_vol = int(bh_rebal_cap * self.f / new_price)
                    bh_rebal_prev_month = date.month
            
            # 決定是否再平衡
            if self._should_rebalance(date, prev_date):
                # 計算目標部位
                if self.futures_mode:
                    target_vol = int(cap * self.f / (new_price * self.contract_multiplier))
                else:
                    target_vol = int(cap * self.f / new_price)
                bs = target_vol - vol
                
                # 計算交易成本
                if self.futures_mode:
                    trade_value = abs(bs * new_price * self.contract_multiplier)
                else:
                    trade_value = abs(bs * new_price)
                is_sell = bs < 0
                trade_cost = self._calculate_trade_cost(trade_value, is_sell, contracts=bs)
                cap -= trade_cost
                total_trade_cost += trade_cost
                
                vol = target_vol
            else:
                bs = 0
            
            # 生成進出邏輯說明
            if bs > 0:
                reason = f"下跌加碼: 價格{delta_p:+.0f}點 → 槓桿不足 → 買進{bs}口維持{self.f}x"
            elif bs < 0:
                reason = f"上漲減碼: 價格{delta_p:+.0f}點 → 槓桿過高 → 賣出{abs(bs)}口維持{self.f}x"
            else:
                reason = "維持不動"
            trade_reasons.append(reason)
            
            # 記錄
            dates.append(str(date.date()))
            prices.append(new_price)
            capitals.append(cap)
            volumes.append(vol)
            trades.append(bs)
            buy_hold_capitals.append(bh_cap)
            buy_hold_rebal_capitals.append(bh_rebal_cap)
            
            prev_date = date
            price = new_price
        
        # 計算績效指標
        capitals_arr = np.array(capitals)
        
        # 總報酬率
        total_return = (capitals_arr[-1] - self.initial_capital) / self.initial_capital
        
        # 年化報酬率 (假設252個交易日)
        years = len(data) / 252
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        
        # 最大回撤
        peak = np.maximum.accumulate(capitals_arr)
        drawdown = (peak - capitals_arr) / peak
        max_drawdown = np.max(drawdown)
        
        # 夏普比率 (假設無風險利率 2%)
        daily_returns = np.diff(capitals_arr) / capitals_arr[:-1]
        if len(daily_returns) > 0 and np.std(daily_returns) > 0:
            sharpe_ratio = (np.mean(daily_returns) * 252 - 0.02) / (np.std(daily_returns) * np.sqrt(252))
        else:
            sharpe_ratio = 0
        
        # 買進持有報酬率
        buy_hold_return = (buy_hold_capitals[-1] - self.initial_capital) / self.initial_capital
        
        # 買進持有年化報酬率
        buy_hold_annual = (1 + buy_hold_return) ** (1 / years) - 1 if years > 0 else 0
        
        # 買進持有最大回撤
        bh_arr = np.array(buy_hold_capitals)
        bh_peak = np.maximum.accumulate(bh_arr)
        bh_drawdown = (bh_peak - bh_arr) / bh_peak
        buy_hold_mdd = np.max(bh_drawdown)
        
        # 月再平衡買進持有報酬率 (永遠做多)
        buy_hold_rebal_return = (buy_hold_rebal_capitals[-1] - self.initial_capital) / self.initial_capital
        
        # 交易統計
        trades_arr = np.array(trades)
        total_trades = np.sum(trades_arr != 0)
        total_buy_volume = np.sum(trades_arr[trades_arr > 0])
        total_sell_volume = np.abs(np.sum(trades_arr[trades_arr < 0]))
        
        return BacktestResult(
            dates=dates,
            prices=prices,
            capitals=capitals,
            volumes=volumes,
            trades=trades,
            trade_reasons=trade_reasons,
            buy_hold_capitals=buy_hold_capitals,
            buy_hold_rebal_capitals=buy_hold_rebal_capitals,
            total_return=total_return,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            buy_hold_return=buy_hold_return,
            buy_hold_annual_return=buy_hold_annual,
            buy_hold_mdd=buy_hold_mdd,
            buy_hold_rebal_return=buy_hold_rebal_return,
            total_trades=total_trades,
            total_buy_volume=total_buy_volume,
            total_sell_volume=total_sell_volume,
        )


def run_simple_test():
    """使用文章中的範例資料進行簡單測試"""
    # 你文章中的範例價格
    prices = [100, 80, 64, 51, 40, 32, 40, 51, 64, 80, 100]
    
    # 建立測試資料
    dates = pd.date_range(start='2024-01-01', periods=len(prices), freq='D')
    df = pd.DataFrame({
        'DATE': dates,
        'CLOSE': prices
    })
    
    # 執行回測
    engine = SpiderWebBacktest(kelly_f=0.5, initial_capital=1_000_000)
    result = engine.run(df)
    
    print("=" * 60)
    print("蜘蛛網回測引擎 - 簡單測試 (f=0.5)")
    print("=" * 60)
    print(f"{'日期':<12} {'價格':>8} {'部位':>10} {'買賣':>10} {'資金':>15}")
    print("-" * 60)
    
    for i in range(len(result.dates)):
        print(f"{result.dates[i]:<12} {result.prices[i]:>8.0f} {result.volumes[i]:>10.0f} "
              f"{result.trades[i]:>+10.0f} {result.capitals[i]:>15,.0f}")
    
    print("-" * 60)
    print(f"總報酬率: {result.total_return:.2%}")
    print(f"買進持有報酬率: {result.buy_hold_return:.2%}")
    print(f"最大回撤: {result.max_drawdown:.2%}")
    print(f"總交易次數: {result.total_trades}")
    print("=" * 60)
    
    return result


if __name__ == "__main__":
    run_simple_test()
