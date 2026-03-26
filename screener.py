#!/usr/bin/env python3
"""
A股选股脚本 - 筛选技术指标符合条件的股票
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    import numpy as np
    from Ashare import get_price
except ImportError:
    print(json.dumps({"error": "缺少依赖"}))
    sys.exit(1)

# A股热门股票列表（示例，实际应该获取完整列表）
STOCK_POOL = [
    # 上证
    ("sh600519", "贵州茅台"), ("sh600036", "招商银行"), ("sh601318", "中国平安"),
    ("sh600000", "浦发银行"), ("sh601166", "兴业银行"), ("sh600030", "中信证券"),
    ("sh601398", "工商银行"), ("sh601288", "农业银行"), ("sh600276", "恒瑞医药"),
    ("sh600887", "伊利股份"), ("sh601888", "中国中免"), ("sh600900", "长江电力"),
    ("sh600021", "上海电力"), ("sh601012", "隆基绿能"), ("sh600438", "通威股份"),
    ("sh603259", "药明康德"), ("sh600309", "万华化学"), ("sh601899", "紫金矿业"),
    ("sh600585", "海螺水泥"), ("sh601328", "交通银行"),
    # 深证
    ("sz000001", "平安银行"), ("sz000002", "万科A"), ("sz000333", "美的集团"),
    ("sz000651", "格力电器"), ("sz000858", "五粮液"), ("sz002594", "比亚迪"),
    ("sz000063", "中兴通讯"), ("sz002415", "海康威视"), ("sz300750", "宁德时代"),
    ("sz002304", "洋河股份"), ("sz000568", "泸州老窖"), ("sz002352", "顺丰控股"),
    ("sz300059", "东方财富"), ("sz002714", "牧原股份"), ("sz000725", "京东方A"),
    ("sz002475", "立讯精密"), ("sz300015", "爱尔眼科"), ("sz002230", "科大讯飞"),
    ("sz000333", "美的集团"), ("sz002129", "中环股份"),
]

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
    avg_gain = np.mean(gains)
    avg_loss = np.mean(losses)
    if avg_loss == 0:
        return 100
    return 100 - (100 / (1 + avg_gain / avg_loss))

def calc_kdj(highs, lows, closes, n=9):
    if len(closes) < n + 3:
        return None, None, None
    rsvs = []
    for i in range(n, len(closes) + 1):
        low_n = min(lows[i-n:i])
        high_n = max(highs[i-n:i])
        if high_n == low_n:
            rsv = 50
        else:
            rsv = (closes[i-1] - low_n) / (high_n - low_n) * 100
        rsvs.append(rsv)
    if len(rsvs) < 3:
        return None, None, None
    k_values = [50]
    for rsv in rsvs:
        k = (2/3) * k_values[-1] + (1/3) * rsv
        k_values.append(k)
    d_values = [50]
    for k in k_values[1:]:
        d = (2/3) * d_values[-1] + (1/3) * k
        d_values.append(d)
    k = k_values[-1]
    d = d_values[-1]
    j = 3 * k - 2 * d
    return k, d, j

def analyze_stock(code, name):
    """分析单只股票"""
    try:
        df = get_price(code, frequency='1d', count=60)
        if df is None or len(df) < 30:
            return None
        
        closes = df['close'].values.astype(float)
        highs = df['high'].values.astype(float)
        lows = df['low'].values.astype(float)
        
        close = closes[-1]
        ma5 = calc_ma(closes, 5)
        ma10 = calc_ma(closes, 10)
        ma20 = calc_ma(closes, 20)
        rsi = calc_rsi(closes, 14)
        k, d, j = calc_kdj(highs, lows, closes)
        
        signals = []
        score = 0
        
        # 均线排列
        if ma5 and ma10 and ma20:
            if ma5 > ma10 > ma20:
                signals.append("多头排列")
                score += 1
            elif ma5 < ma10 < ma20:
                signals.append("空头排列")
                score -= 1
        
        # RSI
        if rsi:
            if rsi < 30:
                signals.append("RSI超卖")
                score += 2
            elif rsi > 70:
                signals.append("RSI超买")
                score -= 1
        
        # KDJ
        if k is not None:
            if k < 20 and d < 20:
                signals.append("KDJ超卖")
                score += 2
            elif k > 80 and d > 80:
                signals.append("KDJ超买")
                score -= 1
            if j < 0:
                signals.append("J值负值")
                score += 1
        
        # 价格位置
        if ma20:
            price_position = (close - ma20) / ma20 * 100
            if price_position < -10:
                signals.append("低于MA20超10%")
                score += 1
        
        return {
            "code": code,
            "name": name,
            "close": round(close, 2),
            "ma5": round(ma5, 2) if ma5 else None,
            "ma10": round(ma10, 2) if ma10 else None,
            "ma20": round(ma20, 2) if ma20 else None,
            "rsi": round(rsi, 1) if rsi else None,
            "kdj_k": round(k, 1) if k else None,
            "kdj_d": round(d, 1) if d else None,
            "kdj_j": round(j, 1) if j else None,
            "signals": signals,
            "score": score
        }
    except Exception as e:
        return None

def main():
    results = []
    
    print(f"开始分析 {len(STOCK_POOL)} 只股票...", file=sys.stderr)
    
    for code, name in STOCK_POOL:
        result = analyze_stock(code, name)
        if result:
            results.append(result)
    
    # 按评分排序
    results.sort(key=lambda x: x['score'], reverse=True)
    
    # 筛选推荐（score >= 2）
    recommended = [r for r in results if r['score'] >= 2]
    
    output = {
        "total": len(results),
        "recommended": recommended[:10],  # 最多推荐10只
        "all_results": results
    }
    
    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()