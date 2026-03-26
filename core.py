#!/usr/bin/env python3
"""
股价监控核心模块 - 读取配置，计算指标，生成信号
"""
import sys
import os
import json
import configparser
from pathlib import Path
from datetime import datetime

# 配置路径
SKILL_DIR = Path(__file__).parent
CONFIG_FILE = SKILL_DIR / "config.ini"
STATE_FILE = SKILL_DIR / "state.json"

# 添加当前目录到路径
sys.path.insert(0, str(SKILL_DIR))

try:
    import numpy as np
    from Ashare import get_price
except ImportError:
    print(json.dumps({"error": "缺少依赖: pip install numpy pandas requests"}))
    sys.exit(1)


def load_config():
    """加载配置文件"""
    config = configparser.ConfigParser()
    if CONFIG_FILE.exists():
        config.read(CONFIG_FILE, encoding='utf-8')
    
    # 安全读取浮点数
    def safe_float(section, key, default=None):
        try:
            val = config.get(section, key, fallback="")
            if val and val.lower() != "null" and val.strip():
                return float(val)
        except:
            pass
        return default
    
    return {
        "stock_code": config.get("stock", "code", fallback="sh600021"),
        "stock_name": config.get("stock", "name", fallback="上海电力"),
        "change_threshold": safe_float("alert", "change_threshold", 1.0),
        "target_low": safe_float("alert", "target_low", None),
        "target_high": safe_float("alert", "target_high", None),
        "ma_fast": config.getint("indicators", "ma_fast", fallback=5),
        "ma_slow": config.getint("indicators", "ma_slow", fallback=10),
        "ma_trend": config.getint("indicators", "ma_trend", fallback=20),
        "rsi_period": config.getint("indicators", "rsi_period", fallback=14),
        "rsi_oversold": config.getint("indicators", "rsi_oversold", fallback=30),
        "rsi_overbought": config.getint("indicators", "rsi_overbought", fallback=70),
        "boll_period": config.getint("indicators", "boll_period", fallback=20),
        "boll_std": safe_float("indicators", "boll_std", 2.0),
    }


def load_state():
    """加载状态"""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {
        "last_price": None,
        "last_time": None,
        "low_alert_sent": False,
        "high_alert_sent": False,
        "last_signals": []
    }


def save_state(state):
    """保存状态"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ============ 指标计算 ============

def calc_ma(prices, period):
    if len(prices) < period:
        return None
    return np.mean(prices[-period:])


def calc_ema(prices, period):
    if len(prices) < period:
        return None
    multiplier = 2 / (period + 1)
    ema = np.mean(prices[:period])
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    return ema


def calc_macd(prices, fast=12, slow=26, signal=9):
    if len(prices) < slow + signal:
        return None, None, None
    
    difs = []
    for i in range(slow, len(prices) + 1):
        ef = calc_ema(prices[:i], fast)
        es = calc_ema(prices[:i], slow)
        if ef and es:
            difs.append(ef - es)
    
    if len(difs) < signal:
        return None, None, None
    
    dif = difs[-1]
    dea = calc_ema(difs, signal)
    macd = (dif - dea) * 2 if dea else None
    
    return dif, dea, macd


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


def calc_boll(prices, period=20, std_dev=2):
    if len(prices) < period:
        return None, None, None
    
    ma = np.mean(prices[-period:])
    std = np.std(prices[-period:])
    
    return ma + std_dev * std, ma, ma - std_dev * std


def calc_kdj(highs, lows, closes, n=9):
    """计算KDJ指标
    
    RSV = (收盘价-N日最低)/(N日最高-N日最低) * 100
    K = SMA(RSV, 3)
    D = SMA(K, 3)  
    J = 3K - 2D
    
    信号：
    - K上穿D且J>K → 买入
    - K下穿D且J<K → 卖出
    - K,D > 80 超买
    - K,D < 20 超卖
    """
    if len(closes) < n + 3:
        return None, None, None
    
    # 计算RSV序列
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
    
    # 计算K（SMA(RSV, 3)）
    k_values = [50]  # K初始值
    for rsv in rsvs:
        k = (2/3) * k_values[-1] + (1/3) * rsv
        k_values.append(k)
    
    # 计算D（SMA(K, 3)）
    d_values = [50]  # D初始值
    for k in k_values[1:]:
        d = (2/3) * d_values[-1] + (1/3) * k
        d_values.append(d)
    
    k = k_values[-1]
    d = d_values[-1]
    j = 3 * k - 2 * d
    
    return k, d, j


# ============ 信号检测 ============

def detect_signals(prices, config, prev_prices=None):
    """检测买卖信号"""
    signals = []
    
    if len(prices) < 60:
        return signals
    
    close = prices[-1]
    
    # MA参数
    ma_fast = config["ma_fast"]
    ma_slow = config["ma_slow"]
    ma_trend = config["ma_trend"]
    
    # 计算均线
    ma_f = calc_ma(prices, ma_fast)
    ma_s = calc_ma(prices, ma_slow)
    ma_t = calc_ma(prices, ma_trend)
    
    # 1. MA信号
    if ma_f and ma_s:
        if prev_prices is not None and len(prev_prices) >= ma_slow:
            prev_ma_f = calc_ma(prev_prices, ma_fast)
            prev_ma_s = calc_ma(prev_prices, ma_slow)
            
            if prev_ma_f and prev_ma_s:
                if prev_ma_f <= prev_ma_s and ma_f > ma_s:
                    signals.append({"type": "buy", "indicator": "MA", "desc": f"MA{ma_fast}上穿MA{ma_slow}金叉"})
                elif prev_ma_f >= prev_ma_s and ma_f < ma_s:
                    signals.append({"type": "sell", "indicator": "MA", "desc": f"MA{ma_fast}下穿MA{ma_slow}死叉"})
    
    # 2. MACD信号
    dif, dea, macd = calc_macd(prices)
    if dif is not None and dea is not None:
        if macd and macd > 0 and dif > dea:
            signals.append({"type": "buy", "indicator": "MACD", "desc": f"MACD金叉 DIF={dif:.3f}"})
        elif macd and macd < 0 and dif < dea:
            signals.append({"type": "sell", "indicator": "MACD", "desc": f"MACD死叉 DIF={dif:.3f}"})
    
    # 3. RSI信号
    rsi = calc_rsi(prices, config["rsi_period"])
    if rsi is not None:
        if rsi < config["rsi_oversold"]:
            signals.append({"type": "buy", "indicator": "RSI", "desc": f"RSI={rsi:.1f}超卖"})
        elif rsi > config["rsi_overbought"]:
            signals.append({"type": "sell", "indicator": "RSI", "desc": f"RSI={rsi:.1f}超买"})
    
    # 4. 布林带信号
    upper, mid, lower = calc_boll(prices, config["boll_period"], config["boll_std"])
    if upper and lower:
        if close <= lower:
            signals.append({"type": "buy", "indicator": "BOLL", "desc": f"触及布林下轨{lower:.2f}"})
        elif close >= upper:
            signals.append({"type": "sell", "indicator": "BOLL", "desc": f"触及布林上轨{upper:.2f}"})
    
    return signals


def detect_signals_with_kdj(prices, highs, lows, closes, config, prev_prices=None, prev_highs=None, prev_lows=None, prev_closes=None):
    """检测买卖信号（含KDJ）"""
    signals = detect_signals(prices, config, prev_prices)
    
    if len(closes) < 12:
        return signals
    
    # 5. KDJ信号
    k, d, j = calc_kdj(highs, lows, closes)
    if k is not None and d is not None:
        # KDJ超买超卖
        if k < 20 and d < 20:
            signals.append({"type": "buy", "indicator": "KDJ", "desc": f"KDJ超卖 K={k:.1f} D={d:.1f}"})
        elif k > 80 and d > 80:
            signals.append({"type": "sell", "indicator": "KDJ", "desc": f"KDJ超买 K={k:.1f} D={d:.1f}"})
        
        # KDJ交叉
        if prev_closes is not None and len(prev_closes) >= 12:
            prev_k, prev_d, _ = calc_kdj(prev_highs, prev_lows, prev_closes)
            if prev_k is not None and prev_d is not None:
                if prev_k <= prev_d and k > d and j > k:
                    signals.append({"type": "buy", "indicator": "KDJ", "desc": f"KDJ金叉 K={k:.1f} D={d:.1f} J={j:.1f}"})
                elif prev_k >= prev_d and k < d and j < k:
                    signals.append({"type": "sell", "indicator": "KDJ", "desc": f"KDJ死叉 K={k:.1f} D={d:.1f} J={j:.1f}"})
    
    return signals


def calc_trade_advice(signals, close, indicators, config):
    """计算交易建议"""
    buy_signals = [s for s in signals if s["type"] == "buy"]
    sell_signals = [s for s in signals if s["type"] == "sell"]
    
    advice = {
        "action": "hold",
        "price": round(close, 2),
        "stop_loss": None,
        "take_profit": None,
        "position": "观望",
        "reason": []
    }
    
    buy_score = len(buy_signals)
    sell_score = len(sell_signals)
    
    boll_lower = indicators.get("boll_lower")
    boll_upper = indicators.get("boll_upper")
    boll_mid = indicators.get("boll_mid")
    rsi = indicators.get("rsi")
    
    if buy_score > sell_score:
        advice["action"] = "buy"
        advice["reason"].append(f"{buy_score}个买入信号")
        
        if boll_lower:
            advice["stop_loss"] = round(boll_lower * 0.97, 2)
        if boll_mid:
            advice["take_profit"] = round(boll_mid, 2)
        
        if buy_score >= 3:
            advice["position"] = "50-70%"
        elif buy_score >= 2:
            advice["position"] = "30-50%"
        else:
            advice["position"] = "10-20%"
    
    elif sell_score > buy_score:
        advice["action"] = "sell"
        advice["reason"].append(f"{sell_score}个卖出信号")
        
        if boll_upper:
            advice["stop_loss"] = round(boll_upper * 1.03, 2)
        if boll_mid:
            advice["take_profit"] = round(boll_mid, 2)
        
        if sell_score >= 3:
            advice["position"] = "减仓50-70%"
        elif sell_score >= 2:
            advice["position"] = "减仓30-50%"
        else:
            advice["position"] = "减仓10-20%"
    else:
        advice["reason"].append("暂无明确信号")
    
    return advice


# ============ 主函数 ============

def run():
    """运行监控"""
    config = load_config()
    state = load_state()
    
    # 获取日线数据
    df = get_price(config["stock_code"], frequency='1d', count=100)
    if df is None or len(df) < 60:
        return {"error": "数据不足"}
    
    prices = df['close'].values.astype(float)
    highs = df['high'].values.astype(float)
    lows = df['low'].values.astype(float)
    closes = prices  # alias
    
    # 获取分钟线实时价格
    df_min = get_price(config["stock_code"], frequency='15m', count=1)
    if df_min is not None and len(df_min) > 0:
        realtime_close = float(df_min['close'].iloc[-1])
        realtime_time = df_min.index[-1].strftime('%Y-%m-%d %H:%M')
    else:
        realtime_close = float(prices[-1])
        realtime_time = df.index[-1].strftime('%Y-%m-%d')
    
    # 计算指标
    indicators = {
        "ma_fast": calc_ma(prices, config["ma_fast"]),
        "ma_slow": calc_ma(prices, config["ma_slow"]),
        "ma_trend": calc_ma(prices, config["ma_trend"]),
        "rsi": calc_rsi(prices, config["rsi_period"]),
        "boll_upper": None,
        "boll_mid": None,
        "boll_lower": None,
        "kdj_k": None,
        "kdj_d": None,
        "kdj_j": None,
    }
    
    upper, mid, lower = calc_boll(prices, config["boll_period"], config["boll_std"])
    if upper:
        indicators["boll_upper"] = round(upper, 2)
        indicators["boll_mid"] = round(mid, 2)
        indicators["boll_lower"] = round(lower, 2)
    
    # 计算KDJ
    k, d, j = calc_kdj(highs, lows, closes)
    if k is not None:
        indicators["kdj_k"] = round(k, 1)
        indicators["kdj_d"] = round(d, 1)
        indicators["kdj_j"] = round(j, 1)
    
    # 检测信号
    prev_prices = prices[:-1] if len(prices) > 1 else None
    prev_highs = highs[:-1] if len(highs) > 1 else None
    prev_lows = lows[:-1] if len(lows) > 1 else None
    prev_closes = closes[:-1] if len(closes) > 1 else None
    signals = detect_signals_with_kdj(prices, highs, lows, closes, config, prev_prices, prev_highs, prev_lows, prev_closes)
    
    # 计算交易建议
    advice = calc_trade_advice(signals, realtime_close, indicators, config)
    
    # 检查价格变动
    price_alerts = []
    last_price = state.get("last_price")
    
    if last_price:
        change = realtime_close - last_price
        change_pct = (change / last_price) * 100
        if abs(change_pct) >= config["change_threshold"]:
            price_alerts.append("change")
    
    # 检查目标价
    if config["target_low"] and realtime_close < config["target_low"]:
        if not state.get("low_alert_sent"):
            price_alerts.append("low_price")
            state["low_alert_sent"] = True
    else:
        state["low_alert_sent"] = False
    
    if config["target_high"] and realtime_close > config["target_high"]:
        if not state.get("high_alert_sent"):
            price_alerts.append("high_price")
            state["high_alert_sent"] = True
    else:
        state["high_alert_sent"] = False
    
    # 检查新信号
    prev_signal_keys = set(state.get("last_signals", []))
    new_signals = []
    for sig in signals:
        if sig["type"] in ["buy", "sell"]:
            key = f"{sig['indicator']}_{sig['type']}"
            if key not in prev_signal_keys:
                new_signals.append(sig)
    
    # 更新状态
    state["last_price"] = realtime_close
    state["last_time"] = realtime_time
    state["last_signals"] = [f"{s['indicator']}_{s['type']}" for s in signals if s["type"] in ["buy", "sell"]]
    save_state(state)
    
    # 返回结果
    result = {
        "stock_code": config["stock_code"],
        "stock_name": config["stock_name"],
        "time": realtime_time,
        "close": realtime_close,
        "indicators": {k: round(v, 2) if v else None for k, v in indicators.items()},
        "signals": signals,
        "new_signals": new_signals,
        "advice": advice,
        "price_alerts": price_alerts,
        "alert": len(new_signals) > 0 or len(price_alerts) > 0
    }
    
    return result


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, ensure_ascii=False, indent=2))