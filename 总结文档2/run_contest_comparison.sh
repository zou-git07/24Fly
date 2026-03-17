#!/bin/bash

# Run Contest Comparison Test
# 运行争球对照测试

echo "=== Ball Contest Support Comparison Test ==="
echo "=== 争球支援功能对照测试 ==="
echo ""
echo "This test compares two teams:"
echo "此测试对比两支队伍："
echo "- Black Team (B-Human): WITH Ball Contest Support"
echo "- 黑色队 (B-Human): 使用争球支援功能"
echo "- Red Team (B-Team): WITHOUT Ball Contest Support (Traditional)"
echo "- 红色队 (B-Team): 不使用争球支援功能 (传统策略)"
echo ""

# Set environment variables
export BALL_CONTEST_COMPARISON=1
export BALL_CONTEST_DEBUG=1

# Check if scene file exists
if [ ! -f "Config/Scenes/ContestComparison.ros3" ]; then
    echo "ERROR: Contest comparison scene not found!"
    echo "错误: 未找到争球对照场景文件!"
    echo "Please make sure ContestComparison.ros3 exists in Config/Scenes/"
    echo "请确保 ContestComparison.ros3 存在于 Config/Scenes/ 目录中"
    exit 1
fi

# Check if configuration files exist
if [ ! -f "Config/BallContestSupport_Enabled.cfg" ] || [ ! -f "Config/BallContestSupport_Disabled.cfg" ]; then
    echo "ERROR: Configuration files not found!"
    echo "错误: 未找到配置文件!"
    echo "Please make sure both BallContestSupport_Enabled.cfg and BallContestSupport_Disabled.cfg exist"
    echo "请确保 BallContestSupport_Enabled.cfg 和 BallContestSupport_Disabled.cfg 都存在"
    exit 1
fi

echo "Starting comparison test..."
echo "启动对照测试..."
echo ""
echo "Expected behaviors:"
echo "预期行为："
echo "1. Both teams will have forwards engaging in ball contest"
echo "1. 两队前锋都会参与争球"
echo "2. Black team should send support player (Robot3) to assist"
echo "2. 黑色队应该派遣支援球员 (Robot3) 协助"
echo "3. Red team should maintain traditional positions"
echo "3. 红色队应该保持传统位置"
echo "4. Observe the difference in ball possession success rate"
echo "4. 观察球权争夺成功率的差异"
echo ""

# Change to Make/Linux directory
cd Make/Linux

# Start SimRobot with comparison scene
echo "Loading ContestComparisonSimple.ros3 scene..."
echo "加载 ContestComparisonSimple.ros3 场景..."
echo ""
echo "In SimRobot:"
echo "在 SimRobot 中："
echo "1. Load debug configuration: Config/Debug/BallContestDebug.cfg"
echo "1. 加载调试配置: Config/Debug/BallContestDebug.cfg"
echo "2. Enable visualization: View -> Field -> Contest Areas"
echo "2. 启用可视化: View -> Field -> Contest Areas"
echo "3. Monitor console for contest detection logs"
echo "3. 监控控制台的争球检测日志"
echo "4. Watch Robot3 (black) movement vs Robot23 (red) behavior"
echo "4. 观察 Robot3 (黑色) 的移动与 Robot23 (红色) 行为的对比"
echo ""

./SimRobot ../../Config/Scenes/ContestComparisonSimple.ros3

echo ""
echo "Comparison test ended."
echo "对照测试结束。"