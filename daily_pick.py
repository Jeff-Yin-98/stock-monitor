#!/usr/bin/env python3
"""
全A股选股 - 每日定时运行（使用内置股票池）
"""
import sys
import json
import time
import numpy as np
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, '/home/admin/.openclaw/workspace/skills/stock')
from Ashare import get_price

OUTPUT_FILE = "/tmp/daily_stock_pick.json"

# 内置股票池（沪深300 + 创业板龙头 + 科创板龙头）
STOCK_POOL = [
    # 上证50
    ('sh600519', '贵州茅台'), ('sh600036', '招商银行'), ('sh601318', '中国平安'),
    ('sh600000', '浦发银行'), ('sh601166', '兴业银行'), ('sh600030', '中信证券'),
    ('sh601398', '工商银行'), ('sh601288', '农业银行'), ('sh600276', '恒瑞医药'),
    ('sh600887', '伊利股份'), ('sh601888', '中国中免'), ('sh600900', '长江电力'),
    ('sh600021', '上海电力'), ('sh601012', '隆基绿能'), ('sh600438', '通威股份'),
    ('sh603259', '药明康德'), ('sh600309', '万华化学'), ('sh601899', '紫金矿业'),
    ('sh600585', '海螺水泥'), ('sh601328', '交通银行'), ('sh601939', '建设银行'),
    ('sh600016', '民生银行'), ('sh601229', '上海银行'), ('sh601658', '邮储银行'),
    ('sh600048', '保利发展'), ('sh601816', '京沪高铁'), ('sh600346', '恒力石化'),
    ('sh601668', '中国建筑'), ('sh600028', '中国石化'), ('sh601857', '中国石油'),
    ('sh600104', '上汽集团'), ('sh601211', '国泰君安'), ('sh600690', '海尔智家'),
    ('sh603288', '海天味业'), ('sh600893', '航发动力'), ('sh601688', '华泰证券'),
    ('sh600009', '上海机场'), ('sh601766', '中国中车'), ('sh601818', '光大银行'),
    ('sh601066', '中信建投'), ('sh600019', '宝钢股份'), ('sh601669', '中国电建'),
    ('sh601138', '工业富联'), ('sh600006', '东风汽车'), ('sh600008', '首创环保'),
    ('sh600011', '华能国际'), ('sh600015', '华夏银行'), ('sh600017', '日照港'),
    ('sh600018', '上港集团'), ('sh600020', '中原高速'), ('sh600026', '中远海能'),
    ('sh600029', '南方航空'), ('sh600035', '楚天高速'), ('sh600050', '中国联通'),
    ('sh600056', '中国医药'), ('sh600058', '五矿发展'), ('sh600059', '古越龙山'),
    ('sh600060', '海信视像'), ('sh600062', '华润双鹤'), ('sh600064', '南京高科'),
    ('sh600066', '宇通客车'), ('sh600067', '冠城大通'), ('sh600068', '葛洲坝'),
    ('sh600070', '浙江富润'), ('sh600071', '凤凰光学'), ('sh600073', '上海梅林'),
    ('sh600074', '中航产融'), ('sh600075', '新疆天业'), ('sh600076', '康欣新材'),
    ('sh600077', '宋都股份'), ('sh600078', '澄星股份'), ('sh600079', '人福医药'),
    ('sh600080', '金花股份'), ('sh600081', '东风科技'), ('sh600082', '海泰发展'),
    ('sh600083', '博信股份'), ('sh600084', '中葡股份'), ('sh600085', '同仁堂'),
    ('sh600086', '东方金钰'), ('sh600088', '中视传媒'), ('sh600089', '特变电工'),
    ('sh600090', '啤酒花'), ('sh600091', '明星电力'), ('sh600092', 'ST宏盛'),
    ('sh600093', '禾嘉股份'), ('sh600094', '*ST华源'), ('sh600095', '哈高科'),
    ('sh600096', '云天化'), ('sh600097', '开创国际'), ('sh600098', '广州发展'),
    ('sh600099', '林海股份'), ('sh600100', '同方股份'), ('sh600101', '明星电缆'),
    # 深证龙头
    ('sz000001', '平安银行'), ('sz000002', '万科A'), ('sz000333', '美的集团'),
    ('sz000651', '格力电器'), ('sz000858', '五粮液'), ('sz002594', '比亚迪'),
    ('sz000063', '中兴通讯'), ('sz002415', '海康威视'), ('sz300750', '宁德时代'),
    ('sz002304', '洋河股份'), ('sz000568', '泸州老窖'), ('sz002352', '顺丰控股'),
    ('sz300059', '东方财富'), ('sz002714', '牧原股份'), ('sz000725', '京东方A'),
    ('sz002475', '立讯精密'), ('sz300015', '爱尔眼科'), ('sz002230', '科大讯飞'),
    ('sz002129', 'TCL中环'), ('sz000069', '华侨城A'), ('sz000768', '中航西飞'),
    ('sz000625', '长安汽车'), ('sz002142', '宁波银行'), ('sz300014', '亿纬锂能'),
    ('sz002648', '卫星化学'), ('sz000100', 'TCL科技'), ('sz300124', '汇川技术'),
    ('sz002032', '苏泊尔'), ('sz002353', '杰瑞股份'), ('sz300274', '阳光电源'),
    ('sz300450', '先导智能'), ('sz300012', '华测检测'), ('sz000538', '云南白药'),
    ('sz002007', '华兰生物'), ('sz300003', '乐普医疗'), ('sz002311', '海大集团'),
    ('sz002920', '德赛西威'), ('sz300033', '同花顺'), ('sz300347', '泰格医药'),
    ('sz300146', '汤臣倍健'), ('sz300122', '智飞生物'), ('sz300999', '金龙鱼'),
    ('sz300628', '亿联网络'), ('sz300413', '芒果超媒'), ('sz300408', '三环集团'),
    ('sz300595', '欧普康视'), ('sz300676', '华大基因'), ('sz300037', '新宙邦'),
    ('sz300496', '中科创达'), ('sz002601', '龙佰集团'), ('sz000703', '盛世天颐'),
    ('sz002607', '中公教育'), ('sz300763', '锦浪科技'), ('sz300759', '康希诺'),
    ('sz300896', '爱美客'), ('sz301029', '怡合达'), ('sz301122', '采纳股份'),
    # 科创板龙头
    ('sh688981', '中芯国际'), ('sh688012', '中微公司'), ('sh688008', '澜起科技'),
    ('sh688005', '容百科技'), ('sh688015', '交控科技'), ('sh688036', '传音控股'),
    ('sh688041', '海光信息'), ('sh688048', '长光华芯'), ('sh688063', '澜起科技'),
    ('sh688111', '金山办公'), ('sh688126', '沪硅产业'), ('sh688169', '石头科技'),
    ('sh688180', '君实生物'), ('sh688185', '康希诺'), ('sh688187', '时代电气'),
    ('sh688223', '晶科能源'), ('sh688256', '寒武纪'), ('sh688303', '大全能源'),
    ('sh688369', '致远互联'), ('sh688396', '华润微'), ('sh688567', '孚能科技'),
]

def calc_ma(p, n): return np.mean(p[-n:]) if len(p) >= n else None

def calc_rsi(p, n=14):
    if len(p) < n+1: return None
    ch = np.diff(p[-n-1:])
    g = np.where(ch>0,ch,0)
    lo = np.where(ch<0,-ch,0)
    return 100 - (100/(1+np.mean(g)/np.mean(lo))) if np.mean(lo) > 0 else 100

def calc_kdj(hi, lo, cl, n=9):
    if len(cl) < n+3: return None, None, None, None, None
    rsv = []
    for i in range(n, len(cl)+1):
        ln, hn = min(lo[i-n:i]), max(hi[i-n:i])
        rsv.append(50 if hn==ln else (cl[i-1]-ln)/(hn-ln)*100)
    k = [50]
    for r in rsv: k.append((2/3)*k[-1]+(1/3)*r)
    d = [50]
    for kv in k[1:]: d.append((2/3)*d[-1]+(1/3)*kv)
    return k[-1], d[-1], 3*k[-1]-2*d[-1], k[-2], d[-2]

def calc_willr(hi, lo, cl, n=14):
    """威廉指标 %R"""
    if len(cl) < n: return None
    hn = max(hi[-n:])
    ln = min(lo[-n:])
    if hn == ln: return -50
    return (hn - cl[-1]) / (hn - ln) * (-100)

def calc_boll(c, n=20):
    """布林带: 返回(中轨, 上轨, 下轨)"""
    if len(c) < n: return None, None, None
    ma = np.mean(c[-n:])
    std = np.std(c[-n:])
    return ma, ma + 2*std, ma - 2*std

def calc_cci(hi, lo, cl, n=20):
    """CCI商品通道指数"""
    if len(cl) < n: return None
    tp = (hi[-n:] + lo[-n:] + cl[-n:]) / 3
    ma_tp = np.mean(tp)
    md = np.mean(np.abs(tp - ma_tp))
    if md == 0: return 0
    return (tp[-1] - ma_tp) / (0.015 * md)

def analyze(code, name):
    try:
        df = get_price(code, frequency='1d', count=60)
        if df is None or len(df) < 30: return None
        # 验证数据是否为当天
        today = datetime.now().date()
        last_date = df.index[-1].date() if hasattr(df.index[-1], 'date') else pd.to_datetime(df.index[-1]).date()
        if last_date != today:
            # 数据不是今天的，跳过（可能是停牌或数据延迟）
            return None
        c = df['close'].values.astype(float)
        h = df['high'].values.astype(float)
        l = df['low'].values.astype(float)
        v = df['volume'].values.astype(float)
        close = c[-1]
        ma5, ma10, ma20 = calc_ma(c,5), calc_ma(c,10), calc_ma(c,20)
        rsi = calc_rsi(c)
        k, d, j, pk, pd = calc_kdj(h, l, c)
        willr = calc_willr(h, l, c)
        boll_mid, boll_up, boll_low = calc_boll(c)
        cci = calc_cci(h, l, c)
        if not all([ma5, ma10, ma20, rsi, k]): return None
        
        signals, score = [], 0
        if pk and pd and pk <= pd and k > d: signals.append('KDJ金叉'); score += 3
        if ma5 > ma10 > ma20: signals.append('多头排列'); score += 2
        if rsi < 30: signals.append('RSI超卖'); score += 2
        elif rsi < 40: score += 1
        # 威廉指标
        if willr and willr < -80: signals.append('威廉超卖'); score += 2
        elif willr and willr < -70: score += 1
        # 布林带
        if boll_low and close < boll_low: signals.append('布林下轨'); score += 2
        # CCI指标
        if cci:
            if cci < -200: signals.append('CCI极度超卖'); score += 3
            elif cci < -100: signals.append('CCI超卖'); score += 2
        if len(c) > 1 and c[-2] < ma5 and close > ma5: signals.append('突破MA5'); score += 1
        vol5, vol20 = np.mean(v[-5:]), np.mean(v[-20:])
        if vol5 > vol20 * 1.3: signals.append('放量'); score += 1
        if k < 20 and d < 20: signals.append('KDJ超卖'); score += 1
        if j < 0: signals.append('J<0'); score += 1
        
        if score < 3: return None
        
        # === 计算挂单价、止盈、止损 ===
        # 次日挂单价：收盘价附近，留出一点空间
        buy_price = round(close * 0.99, 2)  # 比收盘价低1%挂单
        
        # 止损位：根据信号强度和技术位设定
        # - 找最近5日最低价作为止损参考
        # - 或用布林下轨
        recent_low = min(l[-5:])
        stop_loss = round(min(recent_low, boll_low if boll_low else recent_low) * 0.98, 2)
        
        # 止盈位：根据评分设定
        # 评分>=7: 两档止盈 (5%/10%)
        # 评分5-6: 单档止盈 (5%)
        if score >= 7:
            take_profit_1 = round(close * 1.05, 2)  # 第一档：5%
            take_profit_2 = round(close * 1.10, 2)  # 第二档：10%
        else:
            take_profit_1 = round(close * 1.05, 2)
            take_profit_2 = None
        
        result = {
            'code': code, 
            'name': name, 
            'close': round(close, 2), 
            'rsi': round(rsi, 1), 
            'k': round(k, 1), 
            'd': round(d, 1), 
            'signals': signals, 
            'score': score,
            'buy_price': buy_price,
            'stop_loss': stop_loss,
            'take_profit_1': take_profit_1,
            'take_profit_2': take_profit_2,
            'risk_reward': round((take_profit_1 - buy_price) / (buy_price - stop_loss), 2) if buy_price != stop_loss else 0
        }
        if willr: result['willr'] = round(willr, 1)
        if boll_low: result['boll_low'] = round(boll_low, 2)
        if cci: result['cci'] = round(cci, 1)
        return result
    except: return None

def main():
    start = time.time()
    today = datetime.now().date()
    print(f"[{datetime.now()}] 开始分析 {len(STOCK_POOL)} 只股票... (期望数据日期: {today})", file=sys.stderr)
    
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(analyze, code, name): (code, name) for code, name in STOCK_POOL}
        done = 0
        for future in as_completed(futures):
            done += 1
            if done % 50 == 0:
                print(f"已分析 {done}/{len(STOCK_POOL)}", file=sys.stderr)
            r = future.result()
            if r: results.append(r)
    
    results.sort(key=lambda x: x['score'], reverse=True)
    elapsed = time.time() - start
    
    output = {
        'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'data_date': str(today),  # 记录数据应该是什么日期
        'total_stocks': len(STOCK_POOL),
        'found': len(results),
        'elapsed_seconds': round(elapsed, 1),
        'strong_picks': [r for r in results if r['score'] >= 5][:10],
        'top_picks': results[:20]
    }
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"完成! 发现 {len(results)} 只, 耗时 {elapsed:.1f}秒", file=sys.stderr)
    return output

if __name__ == "__main__":
    main()