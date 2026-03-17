#!/bin/bash

# Run Contest Comparison Test - Based on GameFast
# 运行争球对照测试 - 基于GameFast

echo "=== Ball Contest Support Comparison Test ==="
echo "=== 争球支援功能对照测试 ==="
echo ""
echo "This test uses the standard GameFast setup with ball positioned for contest:"
echo "此测试使用标准的GameFast设置，球位置设置为争球场景："
echo "- Both teams use standard 5vs5 formation"
echo "- 两队都使用标准5v5阵型"
echo "- Ball is positioned at center (0,0) to trigger contest"
echo "- 球位于中心(0,0)以触发争球"
echo "- Black team (B-Human): WITH Ball Contest Support"
echo "- 黑色队 (B-Human): 使用争球支援功能"
echo "- Red team (B-Team): WITHOUT Ball Contest Support (Traditional)"
echo "- 红色队 (B-Team): 不使用争球支援功能 (传统策略)"
echo ""

# Set environment variables
export BALL_CONTEST_COMPARISON=1
export BALL_CONTEST_DEBUG=1

# Check if scene file exists
if [ ! -f "Config/Scenes/GameFastContest.ros3" ]; then
    echo "ERROR: GameFastContest scene not found!"
    echo "错误: 未找到GameFastContest场景文件!"
    echo "Please make sure GameFastContest.ros3 exists in Config/Scenes/"
    echo "请确保 GameFastContest.ros3 存在于 Config/Scenes/ 目录中"
    exit 1
fi

echo "Starting comparison test..."
echo "启动对照测试..."
echo ""
echo "Expected behaviors:"
echo "预期行为："
echo "1. Both teams start in standard 5vs5 positions"
echo "1. 两队从标准5v5位置开始"
echo "2. Players will move toward the ball at center"
echo "2. 球员会向中心的球移动"
echo "3. Contest will be detected when players get close to ball"
echo "3. 当球员接近球时会检测到争球"
echo "4. Black team should send support (likely Robot3 or Robot4)"
echo "4. 黑色队应该派遣支援 (可能是Robot3或Robot4)"
echo "5. Red team should maintain traditional behavior"
echo "5. 红色队应该保持传统行为"
echo ""

# Change to Make/Linux directory
cd Make/Linux

# Start SimRobot with GameFast-based contest scene
echo "Loading GameFastContest.ros3 scene..."
echo "加载 GameFastContest.ros3 场景..."
echo ""
echo "In SimRobot:"
echo "在 SimRobot 中："
echo "1. Load debug configuration: Config/Debug/BallContestDebug.cfg"
echo "1. 加载调试配置: Config/Debug/BallContestDebug.cfg"
echo "2. Enable visualization: View -> Field -> Contest Areas"
echo "2. 启用可视化: View -> Field -> Contest Areas"
echo "3. Monitor console for contest detection logs"
echo "3. 监控控制台的争球检测日志"
echo "4. Watch for support player movement from black team"
echo "4. 观察黑色队的支援球员移动"
echo "5. Compare with red team's traditional behavior"
echo "5. 与红色队的传统行为对比"
echo ""

./SimRobot ../../Config/Scenes/GameFastContest.ros3

echo ""
echo "Comparison test ended."
echo "对照测试结束。"