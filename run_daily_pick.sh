#!/bin/bash
# 每日选股任务 - 下午6点运行

SCRIPT_DIR="/home/admin/.openclaw/workspace/skills/stock"
LOG_FILE="$SCRIPT_DIR/daily_pick.log"
OUTPUT_FILE="/tmp/daily_stock_pick.json"
UV="/home/admin/.local/bin/uv"

cd "$SCRIPT_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始每日选股..." >> "$LOG_FILE"

# 运行选股脚本（使用完整路径）
$UV run --with requests --with pandas --with numpy python daily_pick.py 2>> "$LOG_FILE"

if [ -f "$OUTPUT_FILE" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 选股完成，结果已生成" >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 选股失败" >> "$LOG_FILE"
fi