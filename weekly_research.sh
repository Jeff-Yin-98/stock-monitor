#!/bin/bash
# 每周深度研究 - 周六上午11点

SCRIPT_DIR="/home/admin/.openclaw/workspace/skills/stock"
LOG_FILE="$SCRIPT_DIR/research.log"
FLAG_FILE="/tmp/weekly_research_pending.json"

cd "$SCRIPT_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 触发每周深度研究任务" >> "$LOG_FILE"

# 写入标记文件，等待agent在心跳时处理
cat > "$FLAG_FILE" << EOF
{
  "type": "weekly_research",
  "time": "$(date '+%Y-%m-%d %H:%M:%S')",
  "tasks": [
    "深度研究量化策略",
    "回测历史数据验证策略有效性",
    "优化选股算法",
    "添加新指标（威廉指标、CCI、布林带、MACD背离等）",
    "更新skill文档"
  ]
}
EOF

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 标记文件已创建，等待agent处理" >> "$LOG_FILE"