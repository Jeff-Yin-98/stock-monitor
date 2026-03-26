#!/usr/bin/env python3
"""
A股全市场选股 - 获取所有A股并筛选
"""
import sys
import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, '.')
import numpy as np
from Ashare import get_price

def get_all_stocks():
    """获取全部A股股票列表"""
    url = 'http://82.push2.eastmoney.com/api/qt/clist/get'
    
    all_stocks = []
    
    # 沪市
    params = {
        'pn': 1, 'pz': 5000, 'po': 1, 'np': 1, 'fltt': 2, 'invt': 2,
        'fs': 'm:1+t:2,m:1+t:23',  # 沪市
        'fields': 'f12,f14,f2,f3,f15,f16,f17,f18'
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        data = r.json()
        if data.get('data') and data['data'].get('diff'):
            for s in data['data']['diff']:
                if s['f12'].startswith('6'):
                    all_stocks.append(('sh' + s['f12'], s['f14'], s.get('f18', 0)))  # 代码, 名称, 总市值
    except Exception as e:
        print(f"获取沪市失败: {e}", file=sys.stderr)
    
    # 深市
    params['fs'] = 'm:0+t:6,m:0+t:80'  # 深市
    try:
        r = requests.get(url, params=params, timeout=15)
        data = r.json()
        if data.get('data') and data['data'].get('diff'):
            for s in data['data']['diff']:
                if s['f12'].startswith('0') or s['f12'].startswith('3'):
                    all_stocks.append(('sz' + s['f12'], s['f14'], s.get('f18', 0)))
    except Exception as e:
        print(f"获取深市失败: {e}", file=sys.stderr)
    
    return all_stocks

def calc_ma(prices, period):
    if len(prices) < period:
        return None
    return np.mean(prices[-period:])

def calc_rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    changes = np.diff(prices[-period-1:])
    gains = np.where(changes > 0, changes, 0)
    losses = np.where(changes < 0, -changes, 0)
    avg_gain, avg_loss = np.mean(gains), np.mean(losses)
    if avg_loss == 0:
        return 100
    return 100 - (100 / (1 + avg_gain / avg_loss))

def calc_kdj(highs, lows, closes, n=9):
    if len(closes) < n + 3:
        return None, None, None
    rsvs = []
    for i in range(n, len(closes) + 1):
        low_n, high_n = min(lows[i-n:i]), max(highs[i-n:i])
        rsv = 50 if high_n == low_n else (closes[i-1] - low_n) / (high_n - low_n) * 100
        rsvs.append(rsv)
    k_values = [50]
    for rsv in rsvs:
        k_values.append((2/3) * k_values[-1] + (1/3) * rsv)
    d_values = [50]
    for k in k_values[1:]:
        d_values.append((2/3) * d_values[-1] + (1/3) * k)
    return k_values[-1], d_values[-1], 3*k_values[-1] - 2*d_values[-1]

def analyze_stock(code, name, market_cap):
    """分析单只股票"""
    try:
        df = get_price(code, frequency='1d', count=60)
        if df is None or len(df) < 30:
            return None
        
        closes = df['close'].values.astype(float)
        highs = df['high'].values.astype(float)
        lows = df['low'].values.astype(float)
        volumes = df['volume'].values.astype(float)
        
        close = closes[-1]
        avg_vol = np.mean(volumes[-20:]) if len(volumes) >= 20 else 0
        
        # 过滤：成交量过小或ST股
        if avg_vol < 100000 or 'ST' in name or '*' in name:
            return None
        
        ma5, ma10, ma20 = calc_ma(closes, 5), calc_ma(closes, 10), calc_ma(closes, 20)
        rsi = calc_rsi(closes, 14)
        k, d, j = calc_kdj(highs, lows, closes)
        
        if not all([ma5, ma10, ma20, rsi, k]):
            return None
        
        signals, score = [], 0
        
        # 多头排列
        if ma5 > ma10 > ma20:
            signals.append("多头排列")
            score += 2
        
        # RSI超卖
        if rsi < 30:
            signals.append("RSI超卖")
            score += 2
        elif rsi < 40:
            score += 1
        
        # KDJ超卖
        if k < 20 and d < 20:
            signals.append("KDJ超卖")
            score += 2
        if j < 0:
            signals.append("J值负值")
            score += 1
        
        # 价格偏离MA20
        if ma20 and close < ma20 * 0.9:
            signals.append("偏离MA20超10%")
            score += 1
        
        # 金叉信号
        if len(closes) > 1:
            prev_k, prev_d, _ = calc_kdj(highs[:-1], lows[:-1], closes[:-1])
            if prev_k and prev_d and prev_k <= prev_d and k > d:
                signals.append("KDJ金叉")
                score += 3
        
        return {
            "code": code,
            "name": name,
            "close": round(close, 2),
            "market_cap": market_cap,
            "rsi": round(rsi, 1),
            "kdj_k": round(k, 1),
            "kdj_d": round(d, 1),
            "kdj_j": round(j, 1),
            "signals": signals,
            "score": score
        }
    except:
        return None

def main():
    print("正在获取A股全市场股票列表...", file=sys.stderr)
    stocks = get_all_stocks()
    print(f"获取到 {len(stocks)} 只股票", file=sys.stderr)
    
    print("开始分析...", file=sys.stderr)
    results = []
    
    # 多线程分析
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(analyze_stock, code, name, cap): (code, name) 
                   for code, name, cap in stocks}
        
        done = 0
        for future in as_completed(futures):
            done += 1
            if done % 100 == 0:
                print(f"已分析 {done}/{len(stocks)}", file=sys.stderr)
            result = future.result()
            if result and result['score'] >= 3:
                results.append(result)
    
    # 按评分排序
    results.sort(key=lambda x: x['score'], reverse=True)
    
    print(f"\n分析完成！共发现 {len(results)} 只符合条件的股票", file=sys.stderr)
    
    # 输出结果
    output = {
        "total_analyzed": len(stocks),
        "found": len(results),
        "top_picks": results[:20]
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()