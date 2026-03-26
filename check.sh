#!/bin/bash
# 股票监控入口脚本
# 由 crontab 定时调用

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALERT_FILE="/tmp/stock_alert.json"
LOG_FILE="$SCRIPT_DIR/monitor.log"

cd "$SCRIPT_DIR"

# 运行监控
RESULT=$(uv run --with requests --with pandas --with numpy python core.py 2>&1)

# 检查是否有告警
ALERT=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('alert', False))" 2>/dev/null || echo "False")

# 记录日志
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 检查完成: alert=$ALERT" >> "$LOG_FILE"

# 有告警时写入文件
if [ "$ALERT" = "True" ]; then
    echo "$RESULT" > "$ALERT_FILE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 发现告警，已写入 $ALERT_FILE" >> "$LOG_FILE"
fi