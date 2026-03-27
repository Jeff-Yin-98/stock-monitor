#!/bin/bash
# 每日复盘学习 - 工作日晚上11点（直接执行）

SCRIPT_DIR="/home/admin/.openclaw/workspace/skills/stock"
LOG_FILE="$SCRIPT_DIR/review.log"
PICK_FILE="/tmp/daily_stock_pick.json"

cd "$SCRIPT_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始每日复盘学习" >> "$LOG_FILE"

# 1. 验证今日选股结果（如果有）
if [ -f "$PICK_FILE" ]; then
    echo "验证今日选股结果..." >> "$LOG_FILE"
    # 统计评分分布
    /home/admin/.local/bin/uv run python3 << 'PYEOF'
import json
from datetime import datetime

try:
    with open('/tmp/daily_stock_pick.json') as f:
        data = json.load(f)
    
    print(f"数据日期: {data.get('data_date')}")
    print(f"分析股票: {data.get('total_stocks')}")
    print(f"符合条件: {data.get('found')}")
    
    strong = data.get('strong_picks', [])
    print(f"\n强烈推荐 ({len(strong)}只):")
    for s in strong[:5]:
        print(f"  - {s['name']} ({s['code']}): 评分{s['score']}, 信号: {', '.join(s['signals'][:3])}")
except Exception as e:
    print(f"Error: {e}")
PYEOF
    echo "" >> "$LOG_FILE"
fi

# 2. 学习任务提醒
echo "学习任务: CCI指标已添加 (评分+2/+3)" >> "$LOG_FILE"
echo "下次优化: 添加反弹幅度过滤，避免追高" >> "$LOG_FILE"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 复盘完成" >> "$LOG_FILE"