"""
Flask API 後端 - 連接前端與回測引擎
"""

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import os
import sys

# 添加當前目錄到路徑
sys.path.insert(0, os.path.dirname(__file__))

from backtest_engine import SpiderWebBacktest

app = Flask(__name__)
CORS(app)  # 允許跨域請求

# 資料來源
DATA_PATH = os.path.join(os.path.dirname(__file__), '加權歷史資料.xlsx')
DASHBOARD_PATH = os.path.join(os.path.dirname(__file__), 'dashboard.html')


@app.route('/')
def index():
    """提供前端頁面"""
    return send_file(DASHBOARD_PATH)


@app.route('/api/backtest', methods=['POST'])
def run_backtest():
    """執行三策略回測"""
    try:
        # 獲取參數
        data = request.json
        initial_capital = float(data.get('capital', 1000000))
        backwardation_rate = float(data.get('backwardation', 4)) / 100
        spider_f = float(data.get('spider_f', 0.5))
        forever_f = float(data.get('forever_f', 3.0))
        buyhold_f = float(data.get('buyhold_f', 3.0))
        contract_multiplier = int(data.get('contract_multiplier', 10))
        
        results = {}
        
        # 策略1: 蜘蛛網
        engine1 = SpiderWebBacktest(
            kelly_f=spider_f,
            initial_capital=initial_capital,
            rebalance_freq='daily',
            futures_mode=True,
            contract_multiplier=contract_multiplier,
            futures_fee_per_contract=22,
            backwardation_rate=backwardation_rate
        )
        hist_data = engine1.load_data(DATA_PATH)
        r_spider = engine1.run(hist_data)
        
        # 策略2: 永遠做多
        engine2 = SpiderWebBacktest(
            kelly_f=forever_f,
            initial_capital=initial_capital,
            rebalance_freq='monthly',
            futures_mode=True,
            contract_multiplier=contract_multiplier,
            futures_fee_per_contract=22,
            backwardation_rate=backwardation_rate
        )
        r_forever = engine2.run(hist_data)
        
        # 策略3: 買進持有 (使用 buy_hold 數據)
        engine3 = SpiderWebBacktest(
            kelly_f=buyhold_f,
            initial_capital=initial_capital,
            rebalance_freq='daily',
            futures_mode=True,
            contract_multiplier=contract_multiplier,
            futures_fee_per_contract=22,
            backwardation_rate=backwardation_rate
        )
        r_buyhold = engine3.run(hist_data)
        
        # 建立交易明細 (只含有交易的日期)
        def get_trade_details(result, strategy_name):
            details = []
            for i in range(len(result.dates)):
                if abs(result.trades[i]) > 0:
                    details.append({
                        'date': result.dates[i],
                        'price': round(result.prices[i], 0),
                        'volume': round(result.volumes[i], 0),
                        'trade': int(result.trades[i]),
                        'capital': round(result.capitals[i], 0),
                        'reason': result.trade_reasons[i] if i < len(result.trade_reasons) else ''
                    })
            return details
        
        # 格式化回傳結果
        response = {
            'success': True,
            'spider': {
                'return': r_spider.total_return,
                'annual_return': r_spider.annual_return,
                'mdd': r_spider.max_drawdown,
                'final_capital': r_spider.capitals[-1],
                'dates': r_spider.dates[::5],  # 每5天取一點減少資料量
                'capitals': [round(c, 0) for c in r_spider.capitals[::5]],
                'params': f'f={spider_f}, 每日再平衡',
                'trades_detail': get_trade_details(r_spider, '蜘蛛網'),
                'total_trades': int(r_spider.total_trades),
                'total_buy': int(r_spider.total_buy_volume),
                'total_sell': int(r_spider.total_sell_volume)
            },
            'forever': {
                'return': r_forever.total_return,
                'annual_return': r_forever.annual_return,
                'mdd': r_forever.max_drawdown,
                'final_capital': r_forever.capitals[-1],
                'dates': r_forever.dates[::5],
                'capitals': [round(c, 0) for c in r_forever.capitals[::5]],
                'params': f'f={forever_f}, 每月再平衡',
                'trades_detail': get_trade_details(r_forever, '永遠做多'),
                'total_trades': int(r_forever.total_trades),
                'total_buy': int(r_forever.total_buy_volume),
                'total_sell': int(r_forever.total_sell_volume)
            },
            'buyhold': {
                'return': r_buyhold.buy_hold_return,
                'annual_return': r_buyhold.buy_hold_annual_return,
                'mdd': r_buyhold.buy_hold_mdd,
                'final_capital': r_buyhold.buy_hold_capitals[-1],
                'dates': r_buyhold.dates[::5],
                'capitals': [round(c, 0) for c in r_buyhold.buy_hold_capitals[::5]],
                'params': f'初始 {buyhold_f}x 槓桿',
                # 買進持有只有初始建倉一筆，之後不再交易
                'trades_detail': [{
                    'date': r_buyhold.dates[0],
                    'price': round(r_buyhold.prices[0], 0),
                    'volume': round(r_buyhold.volumes[0], 0),
                    'trade': int(r_buyhold.trades[0]),
                    'capital': round(initial_capital, 0),
                    'reason': '初始建倉後不再調整 (買進持有)'
                }],
                'total_trades': 1,  # 只有初始建倉
                'total_buy': int(r_buyhold.trades[0]),  # 初始買進量
                'total_sell': 0  # 不賣出
            },
            'data_range': f'{r_spider.dates[0]} ~ {r_spider.dates[-1]}'
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康檢查"""
    return jsonify({'status': 'ok', 'data_path': DATA_PATH})


if __name__ == '__main__':
    print("[API] Starting backtest API server...")
    print(f"[API] Data source: {DATA_PATH}")
    print(f"[API] API URL: http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=True)
