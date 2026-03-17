#!/bin/bash

# SimRobot Integration Test Script
# 在SimRobot中测试争球支援功能

echo "=== BeHuman Ball Contest Support - SimRobot Test ==="

# 检查基本文件结构
echo "1. Checking project structure..."
if [ ! -d "Src" ] || [ ! -d "Config" ] || [ ! -d "Make" ]; then
    echo "❌ Error: Not in BeHuman project root directory"
    exit 1
fi
echo "✅ Project structure OK"

# 检查SimRobot相关文件
echo "2. Checking SimRobot availability..."
if [ -d "Util/SimRobot" ]; then
    echo "✅ SimRobot found"
else
    echo "⚠️  SimRobot not found in Util/ directory"
fi

# 检查我们的实现文件
echo "3. Checking Ball Contest Support files..."
contest_files=(
    "Src/Representations/BehaviorControl/BallContestStatus.h"
    "Src/Modules/BehaviorControl/StrategyBehaviorControl/ActiveRoles/BallContestSupport.h"
)

for file in "${contest_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ Missing: $file"
    fi
done

# 检查5V5场景文件
echo "4. Checking 5V5 scenario..."
if [ -f "Config/Scenes/Includes/5vs5.rsi3" ]; then
    echo "✅ 5V5 scenario file found"
    echo "   Current configuration:"
    head -20 "Config/Scenes/Includes/5vs5.rsi3"
else
    echo "❌ 5V5 scenario file not found"
fi

echo ""
echo "=== SimRobot Testing Instructions ==="
echo ""
echo "To test Ball Contest Support in SimRobot:"
echo ""
echo "1. 编译项目:"
echo "   cd Make/Linux"
echo "   ./generate"
echo "   make -j$(nproc) SimRobot"
echo ""
echo "2. 启动SimRobot:"
echo "   cd ../../"
echo "   ./Build/Linux/SimRobot/Release/SimRobot"
echo ""
echo "3. 加载5V5场景:"
echo "   File -> Open -> Config/Scenes/Includes/5vs5.rsi3"
echo ""
echo "4. 测试争球支援:"
echo "   a) 启动仿真 (按空格键)"
echo "   b) 将球放置在两个机器人之间"
echo "   c) 观察是否有第三个机器人前来支援"
echo "   d) 检查支援机器人的定位是否合理"
echo ""
echo "5. 调试和监控:"
echo "   - 打开 View -> Plot 查看机器人状态"
echo "   - 使用 View -> Console 查看调试信息"
echo "   - 在 View -> Field 中观察机器人行为"
echo ""
echo "6. 验证要点:"
echo "   ✓ 争球检测是否准确"
echo "   ✓ 支援球员选择是否合理"
echo "   ✓ 支援位置是否战术正确"
echo "   ✓ 防守是否保持稳定"
echo "   ✓ 支援结束后是否正确回位"
echo ""
echo "=== 预期行为 ==="
echo "当两个机器人争抢球时:"
echo "- 系统应该检测到争球情况"
echo "- 选择最近的非争球球员作为支援"
echo "- 支援球员移动到争球后方约1米处"
echo "- 支援球员面向争球位置准备接球"
echo "- 保持至少40%的球员在防守位置"
echo ""