#!/bin/bash
# 快速查看机器人监控数据

LOG_DIR="RobotMonitoringSystem/monitor_daemon/logs/match_*"

echo "=========================================="
echo "  机器人监控数据查看工具"
echo "=========================================="
echo ""

# 显示日志文件列表
echo "📁 日志文件列表："
ls -lh $LOG_DIR/*.jsonl 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
echo ""

# 统计数据包数量
echo "📊 数据包统计："
for file in $LOG_DIR/*.jsonl; do
    if [ -f "$file" ]; then
        count=$(wc -l < "$file")
        robot=$(basename "$file" .jsonl)
        echo "  $robot: $count 条数据"
    fi
done
echo ""

# 显示最新数据示例
echo "🤖 最新数据示例（机器人 5_5）："
tail -1 $LOG_DIR/robot_5_5.jsonl 2>/dev/null | python3 -m json.tool
echo ""

echo "=========================================="
echo "💡 查看方式："
echo "  1. 实时查看：tail -f $LOG_DIR/robot_5_5.jsonl"
echo "  2. 查看全部：cat $LOG_DIR/robot_5_5.jsonl | python3 -m json.tool"
echo "  3. 统计行数：wc -l $LOG_DIR/*.jsonl"
echo "=========================================="
