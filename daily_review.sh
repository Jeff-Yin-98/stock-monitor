#!/bin/bash
# 每日复盘学习 - 工作日晚上11点

SCRIPT_DIR="/home/admin/.openclaw/workspace/skills/stock"
LOG_FILE="$SCRIPT_DIR/review.log"
FLAG_FILE="/tmp/daily_review_pending.json"

cd "$SCRIPT_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 触发每日复盘学习任务" >> "$LOG_FILE"

# 写入标记文件，等待agent在心跳时处理
cat > "$FLAG_FILE" << EOF
{
  "type": "daily_review",
  "time": "$(date '+%Y-%m-%d %H:%M:%S')",
  "tasks": [
    "复盘今日选股结果，验证信号准确性",
    "学习新指标或策略",
    "如果发现更好策略，优化skill",
    "记录学习心得"
  ]
}
EOF

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 标记文件已创建，等待agent处理" >> "$LOG_FILE"