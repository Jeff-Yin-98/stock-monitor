import requests
import pandas as pd
import numpy as np
import json

code = 'sh600759'

# 用东方财富接口获取实时数据
url_realtime = f'http://push2.eastmoney.com/api/qt/stock/get?secid=1.{code[2:]}&fields=f43,f44,f45,f46,f47,f48,f50,f51,f52,f58,f60,f170,f171'
resp_rt = requests.get(url_realtime, timeout=10)
rt_data = json.loads(resp_rt.text)

if rt_data.get('data'):
    d = rt_data['data']
    current = d.get('f43', 0) / 100 if d.get('f43') else 0
    high = d.get('f44', 0) / 100 if d.get('f44') else 0
    low = d.get('f45', 0) / 100 if d.get('f45') else 0
    open_p = d.get('f46', 0) / 100 if d.get('f46') else 0
    prev_close = d.get('f60', 0) / 100 if d.get('f60') else 0
    change_pct = ((current - prev_close) / prev_close * 100) if prev_close else 0
    
    print(f'洲际油气 ({code})')
    print(f'当前价: {current:.2f}')
    print(f'今日: 开{open_p:.2f} 高{high:.2f} 低{low:.2f}')
    print(f'涨跌幅: {change_pct:+.2f}%')
    print()
else:
    print('无法获取实时数据')
    current = 6.08

# 用东方财富接口获取日K数据
url3 = f'http://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.{code[2:]}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62&klt=101&fqt=1&end=20500101&lmt=60'
resp3 = requests.get(url3, timeout=10)
data3 = json.loads(resp3.text)

klines = []
if data3.get('data') and data3['data'].get('klines'):
    for line in data3['data']['klines']:
        parts = line.split(',')
        klines.append({
            'date': parts[0],
            'open': float(parts[1]),
            'close': float(parts[2]),
            'high': float(parts[3]),
            'low': float(parts[4]),
            'volume': float(parts[5]),
            'amount': float(parts[6]),
        })
    
    df = pd.DataFrame(klines)
    
    # MA均线
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    
    ma5 = df['ma5'].iloc[-1]
    ma10 = df['ma10'].iloc[-1]
    ma20 = df['ma20'].iloc[-1]
    ma60 = df['ma60'].iloc[-1] if len(df) >= 60 else None
    
    print(f'MA均线:')
    print(f'  MA5: {ma5:.2f} | MA10: {ma10:.2f} | MA20: {ma20:.2f}')
    if ma60:
        print(f'  MA60: {ma60:.2f}')
    
    # MA交叉信号
    if df['ma5'].iloc[-2] < df['ma10'].iloc[-2] and ma5 > ma10:
        print('  ✅ MA金叉信号 (5日上穿10日)')
    elif df['ma5'].iloc[-2] > df['ma10'].iloc[-2] and ma5 < ma10:
        print('  ❌ MA死叉信号 (5日下穿10日)')
    elif ma5 > ma10:
        print('  📈 多头排列 (MA5 > MA10)')
    else:
        print('  📉 空头排列 (MA5 < MA10)')
    
    print()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    rsi_val = rsi.iloc[-1]
    print(f'RSI(14): {rsi_val:.1f}')
    if rsi_val < 30:
        print('  ✅ RSI超卖区 (<30) - 短期可能反弹')
    elif rsi_val > 70:
        print('  ⚠️ RSI超买区 (>70) - 短期可能回调')
    else:
        print(f'  RSI正常区间')
    
    print()
    
    # KDJ
    low_min = df['low'].rolling(9).min()
    high_max = df['high'].rolling(9).max()
    rsv = (df['close'] - low_min) / (high_max - low_min) * 100
    df['k'] = rsv.ewm(com=2).mean()
    df['d'] = df['k'].ewm(com=2).mean()
    df['j'] = 3 * df['k'] - 2 * df['d']
    
    k = df['k'].iloc[-1]
    d = df['d'].iloc[-1]
    j = df['j'].iloc[-1]
    prev_k = df['k'].iloc[-2]
    prev_d = df['d'].iloc[-2]
    
    print(f'KDJ: K={k:.1f} D={d:.1f} J={j:.1f}')
    
    kdj_signals = []
    if prev_k < prev_d and k > d:
        kdj_signals.append('✅ KDJ金叉')
    elif prev_k > prev_d and k < d:
        kdj_signals.append('❌ KDJ死叉')
    
    if k < 20 and d < 20:
        kdj_signals.append('超卖区 (<20)')
    elif k > 80 and d > 80:
        kdj_signals.append('超买区 (>80)')
    
    if kdj_signals:
        print('  ' + ' | '.join(kdj_signals))
    
    print()
    
    # MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    dif = exp1 - exp2
    dea = dif.ewm(span=9, adjust=False).mean()
    macd = (dif - dea) * 2
    
    dif_val = dif.iloc[-1]
    dea_val = dea.iloc[-1]
    macd_val = macd.iloc[-1]
    prev_dif = dif.iloc[-2]
    prev_dea = dea.iloc[-2]
    
    print(f'MACD: DIF={dif_val:.3f} DEA={dea_val:.3f} MACD={macd_val:.3f}')
    
    if prev_dif < prev_dea and dif_val > dea_val:
        print('  ✅ MACD金叉')
    elif prev_dif > prev_dea and dif_val < dea_val:
        print('  ❌ MACD死叉')
    elif dif_val > 0 and dea_val > 0:
        print('  📈 MACD多头区域')
    elif dif_val < 0 and dea_val < 0:
        print('  📉 MACD空头区域')
    
    print()
    
    # 布林带
    mid = df['close'].rolling(20).mean()
    std = df['close'].rolling(20).std()
    upper = mid + 2 * std
    lower = mid - 2 * std
    
    bb_mid = mid.iloc[-1]
    bb_upper = upper.iloc[-1]
    bb_lower = lower.iloc[-1]
    
    print(f'布林带: 上轨={bb_upper:.2f} 中轨={bb_mid:.2f} 下轨={bb_lower:.2f}')
    
    if current <= bb_lower * 1.01:
        print('  ✅ 触及布林下轨 - 可能超跌反弹')
    elif current >= bb_upper * 0.99:
        print('  ⚠️ 触及布林上轨 - 可能回调')
    
    # 距离布林带位置
    bb_pos = (current - bb_lower) / (bb_upper - bb_lower) * 100
    print(f'  位置: {bb_pos:.1f}% (从下轨算起)')
    
    print()
    
    # 成交量分析
    vol_ma5 = df['volume'].rolling(5).mean().iloc[-1]
    vol_ratio = df['volume'].iloc[-1] / vol_ma5 if vol_ma5 > 0 else 1
    print(f'成交量: 量比={vol_ratio:.2f}')
    if vol_ratio > 1.5:
        print('  放量')
    elif vol_ratio < 0.5:
        print('  缩量')
    
    print()
    
    # 趋势判断
    print('='*40)
    print('趋势判断:')
    
    # 计算近20日高低点
    high_20 = df['high'].iloc[-20:].max()
    low_20 = df['low'].iloc[-20:].min()
    low_60 = df['low'].iloc[-60:].min() if len(df) >= 60 else df['low'].min()
    high_60 = df['high'].iloc[-60:].max() if len(df) >= 60 else df['high'].max()
    
    print(f'近20日: 高点{high_20:.2f} 低点{low_20:.2f}')
    print(f'近60日: 高点{high_60:.2f} 低点{low_60:.2f}')
    
    # 距离前低
    dist_low = (current - low_60) / low_60 * 100
    dist_high = (high_60 - current) / current * 100
    print(f'距60日低点: +{dist_low:.1f}%')
    print(f'距60日高点: -{dist_high:.1f}%')

print()
print('='*40)
print('持仓分析:')
cost = 8.81
loss_pct = (current - cost) / cost * 100
print(f'成本价: {cost:.2f}')
print(f'当前价: {current:.2f}')
print(f'浮亏: {loss_pct:.1f}%')
print()

# 加仓测算
print('加仓成本测算:')
for add_ratio in [0.5, 1.0, 1.5, 2.0]:
    new_cost = (cost + current * add_ratio) / (1 + add_ratio)
    need_rise = (new_cost / current - 1) * 100
    print(f'  加仓{add_ratio}倍 -> 新成本{new_cost:.2f} (需涨{need_rise:.1f}%回本)')