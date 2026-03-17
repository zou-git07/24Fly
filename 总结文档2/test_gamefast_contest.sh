#!/bin/bash

# Test Ball Contest Support in GameFast simulation
# 在GameFast仿真中测试争球支援功能

echo "=== Ball Contest Support Test in GameFast ==="
echo "=== GameFast中的争球支援功能测试 ==="

# Function to run test scenario
run_test_scenario() {
    local scenario_name=$1
    local scene_file=$2
    
    echo ""
    echo "Testing scenario: $scenario_name"
    echo "测试场景: $scenario_name"
    echo "Scene file: $scene_file"
    echo "场景文件: $scene_file"
    
    # Check if scene file exists
    if [ ! -f "Config/Scenes/$scene_file" ]; then
        echo "ERROR: Scene file not found: Config/Scenes/$scene_file"
        echo "错误: 场景文件未找到: Config/Scenes/$scene_file"
        return 1
    fi
    
    echo "Scene file found. Ready to start simulation."
    echo "场景文件已找到。准备启动仿真。"
    echo "Run the following command to start:"
    echo "运行以下命令启动:"
    echo "cd Make/Linux && ./SimRobot ../../Config/Scenes/$scene_file"
    echo ""
}

# Test scenarios
echo "Available test scenarios:"
echo "可用的测试场景:"
echo ""

# 1. Standard GameFast with Ball Contest Support
run_test_scenario "Standard GameFast with Contest Support" "GameFast.ros3"

# 2. Enhanced GameFast with Contest Scenarios
run_test_scenario "Enhanced GameFast with Contest Scenarios" "GameFastBallContest.ros3"

# 3. Dedicated Ball Contest Test
run_test_scenario "Dedicated Ball Contest Test" "BallContestTest.ros2"

# 4. Contest Comparison Test (NEW!)
run_test_scenario "Contest Comparison Test (Black vs Red)" "ContestComparison.ros3"

# 5. GameFast-based Contest Comparison (RECOMMENDED!)
run_test_scenario "GameFast Contest Comparison (Recommended)" "GameFastContest.ros3"

echo "=== Test Instructions ==="
echo "=== 测试说明 ==="
echo ""
echo "1. Choose a scenario and run the suggested command"
echo "1. 选择一个场景并运行建议的命令"
echo ""
echo "2. For Contest Comparison Test, use the dedicated scripts:"
echo "2. 对于争球对照测试，使用专用脚本："
echo "   ./run_contest_comparison.sh (custom positions)"
echo "   ./run_gamefast_contest_comparison.sh (GameFast-based, RECOMMENDED)"
echo ""
echo "3. In SimRobot, load the debug configuration:"
echo "3. 在SimRobot中，加载调试配置:"
echo "   File -> Load Configuration -> Config/Debug/BallContestDebug.cfg"
echo ""
echo "4. Monitor the following for Ball Contest Support activity:"
echo "4. 监控以下内容以观察争球支援活动:"
echo "   - Console output for contest detection logs"
echo "   - 控制台输出中的争球检测日志"
echo "   - Robot movements during ball contests"
echo "   - 争球期间的机器人移动"
echo "   - Support role assignments"
echo "   - 支援角色分配"
echo ""
echo "5. Expected behaviors:"
echo "5. 预期行为:"
echo "   - Automatic detection of ball contests between players"
echo "   - 自动检测球员之间的争球情况"
echo "   - Assignment of support roles to nearby teammates"
echo "   - 为附近队友分配支援角色"
echo "   - Movement to calculated support positions"
echo "   - 移动到计算出的支援位置"
echo "   - Return to original positions when contest ends"
echo "   - 争球结束时返回原位置"
echo ""
echo "6. Contest Comparison Test specific:"
echo "6. 争球对照测试特有:"
echo "   - Black team (B-Human) uses Ball Contest Support"
echo "   - 黑色队 (B-Human) 使用争球支援功能"
echo "   - Red team (B-Team) uses traditional strategy"
echo "   - 红色队 (B-Team) 使用传统策略"
echo "   - Compare ball possession success rates"
echo "   - 对比球权争夺成功率"
echo ""
echo "=== Debug Tips ==="
echo "=== 调试提示 ==="
echo ""
echo "- Enable visualization: View -> Field -> Contest Areas"
echo "- 启用可视化: View -> Field -> Contest Areas"
echo "- Monitor data streams: BallContestStatus, AgentStates"
echo "- 监控数据流: BallContestStatus, AgentStates"
echo "- Check logs in: Logs/BallContestProvider.log"
echo "- 检查日志: Logs/BallContestProvider.log"
echo ""

# Check if build is up to date
echo "=== Build Status Check ==="
echo "=== 构建状态检查 ==="
if [ -f "build_ball_contest_support.sh" ]; then
    echo "Build script found. Make sure to run it before testing:"
    echo "找到构建脚本。测试前请确保运行它:"
    echo "./build_ball_contest_support.sh"
else
    echo "Build script not found. Manual build may be required."
    echo "未找到构建脚本。可能需要手动构建。"
fi
echo ""

echo "Test preparation complete. Choose a scenario and start testing!"
echo "测试准备完成。选择一个场景并开始测试！"