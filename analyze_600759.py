import requests
import json

# 腾讯接口获取实时数据
url = "https://web.sqt.gtimg.cn/q=sh600759"
resp = requests.get(url, timeout=10)
# 解析数据
data_str = resp.text.split('"')[1]
parts = data_str.split('~')

# 腾讯数据格式解析
name = parts[1]
code = parts[2]
current = float(parts[3])
prev_close = float(parts[4])
open_p = float(parts[5])
# 6: 成交量(手)
# 7: ?
# 8: ?
# 9: 买一价
# ...
high = float(parts[33]) if len(parts) > 33 else 0  # 最高价
low = float(parts[34]) if len(parts) > 34 else 0   # 最低价

# 计算涨跌
change = current - prev_close
change_pct = (change / prev_close) * 100

print(f'洲际油气 ({code})')
print(f'当前价: {current:.2f}')
print(f'昨收: {prev_close:.2f}')
print(f'今日: 开{open_p:.2f} 高{high:.2f} 低{low:.2f}')
print(f'涨跌: {change:+.2f} ({change_pct:+.2f}%)')
print()

# 获取K线数据计算技术指标 - 用东方财富接口
url_kline = f"http://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.{code}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62&klt=101&fqt=1&end=20500101&lmt=60"
try:
    resp_kline = requests.get(url_kline, timeout=10)
    kdata = json.loads(resp_kline.text)
    
    if kdata.get('data') and kdata['data'].get('klines'):
        klines = []
        for line in kdata['data']['klines']:
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
        
        # 简单计算技术指标
        closes = [k['close'] for k in klines]
        highs = [k['high'] for k in klines]
        lows = [k['low'] for k in klines]
        
        # MA
        ma5 = sum(closes[-5:]) / 5
        ma10 = sum(closes[-10:]) / 10
        ma20 = sum(closes[-20:]) / 20
        
        print(f'MA均线:')
        print(f'  MA5: {ma5:.2f} | MA10: {ma10:.2f} | MA20: {ma20:.2f}')
        
        if current > ma5 and current > ma10:
            print('  📈 站上短期均线')
        elif current < ma5 and current < ma10:
            print('  📉 跌破短期均线')
        
        # RSI (简化版)
        gains = []
        losses = []
        for i in range(1, min(15, len(closes))):
            diff = closes[-i] - closes[-i-1]
            if diff > 0:
                gains.append(diff)
            else:
                losses.append(abs(diff))
        
        avg_gain = sum(gains) / 14 if gains else 0
        avg_loss = sum(losses) / 14 if losses else 0.001
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        print()
        print(f'RSI(14): {rsi:.1f}')
        if rsi < 30:
            print('  ✅ RSI超卖区 (<30) - 短期可能反弹')
        elif rsi > 70:
            print('  ⚠️ RSI超买区 (>70)')
        else:
            print(f'  RSI正常区间')
        
        # KDJ (简化版)
        low_9 = min(lows[-9:])
        high_9 = max(highs[-9:])
        rsv = (current - low_9) / (high_9 - low_9) * 100 if high_9 != low_9 else 50
        
        print()
        print(f'RSV(9): {rsv:.1f}')
        if rsv < 20:
            print('  处于超卖区')
        elif rsv > 80:
            print('  处于超买区')
        
        print()
        
        # 趋势判断
        print('='*40)
        print('趋势判断:')
        
        high_20 = max(highs[-20:])
        low_20 = min(lows[-20:])
        high_60 = max(highs)
        low_60 = min(lows)
        
        print(f'近20日: 高点{high_20:.2f} 低点{low_20:.2f}')
        print(f'近60日: 高点{high_60:.2f} 低点{low_60:.2f}')
        
        # 距离前低
        dist_low = (current - low_60) / low_60 * 100
        dist_high = (high_60 - current) / current * 100
        print(f'距60日低点: +{dist_low:.1f}%')
        print(f'距60日高点: -{dist_high:.1f}%')
        
        # 趋势
        ma5_prev = sum(closes[-6:-1]) / 5
        ma10_prev = sum(closes[-11:-1]) / 10
        
        if ma5 > ma10 and ma5_prev <= ma10_prev:
            print('  ✅ MA金叉信号')
        elif ma5 < ma10 and ma5_prev >= ma10_prev:
            print('  ❌ MA死叉信号')
        
except Exception as e:
    print(f'获取K线数据失败: {e}')

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

print()
print('='*40)
print('🦞 分析建议:')
print()

# 分析
if rsi < 30 and rsv < 20:
    print('📊 技术面: RSI和KDJ都在超卖区，短期有反弹可能')
elif rsi > 70 or rsv > 80:
    print('📊 技术面: 短期超买，注意回调风险')
else:
    print('📊 技术面: 技术指标中性')

# 计算亏损程度
if loss_pct < -30:
    print(f'📉 浮亏{abs(loss_pct):.0f}%，深套中')
    print()
    print('💡 建议:')
    print('  1. 如果公司基本面没有重大恶化，不建议恐慌割肉')
    print('  2. 可以考虑分批加仓降低成本')
    print('  3. 加仓1倍后成本约7.45，需要涨22%回本')
    print('  4. 设好止损位（如60日低点附近），跌破再考虑止损')