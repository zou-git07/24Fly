#!/bin/bash
# 测试 SimRobot 监控系统集成

echo "========================================="
echo "SimRobot 监控系统集成测试"
echo "========================================="
echo ""

# 检查 Monitor Daemon 是否运行
if pgrep -f "daemon_json.py" > /dev/null; then
    echo "✅ Monitor Daemon 正在运行"
else
    echo "❌ Monitor Daemon 未运行"
    echo "请先启动: python3 RobotMonitoringSystem/monitor_daemon/daemon_json.py --port 10020 --log-dir RobotMonitoringSystem/monitor_daemon/logs"
    exit 1
fi

echo ""
echo "准备启动 SimRobot..."
echo "请在 SimRobot 中："
echo "  1. 加载场景"
echo "  2. 启动机器人 (Ctrl+R)"
echo "  3. 观察 Monitor Daemon 的输出"
echo ""
echo "按 Enter 继续..."
read

# 启动 SimRobot (使用 GameFast 场景)
./Build/Linux/SimRobot/Develop/SimRobot Config/Scenes/GameFast.ros3
