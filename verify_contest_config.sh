#!/bin/bash

# Verify Ball Contest Support Configuration
# 验证争球支援配置

echo "=== Ball Contest Support Configuration Verification ==="
echo "=== 争球支援配置验证 ==="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check file existence
check_file() {
    local file=$1
    local description=$2
    
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $description: $file"
        return 0
    else
        echo -e "${RED}✗${NC} $description: $file (NOT FOUND)"
        return 1
    fi
}

# Function to check directory existence
check_directory() {
    local dir=$1
    local description=$2
    
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✓${NC} $description: $dir"
        return 0
    else
        echo -e "${RED}✗${NC} $description: $dir (NOT FOUND)"
        return 1
    fi
}

# Function to check for content in file
check_content() {
    local file=$1
    local pattern=$2
    local description=$3
    
    if [ -f "$file" ] && grep -q "$pattern" "$file"; then
        echo -e "${GREEN}✓${NC} $description found in $file"
        return 0
    else
        echo -e "${YELLOW}!${NC} $description not found in $file"
        return 1
    fi
}

echo "1. Checking core source files..."
echo "1. 检查核心源文件..."
check_file "Src/Modules/BehaviorControl/BallContestProvider/BallContestProvider.h" "BallContestProvider Header"
check_file "Src/Modules/BehaviorControl/BallContestProvider/BallContestProvider.cpp" "BallContestProvider Implementation"
check_file "Src/Modules/BehaviorControl/StrategyBehaviorControl/ActiveRoles/BallContestSupport.h" "BallContestSupport Header"
check_file "Src/Modules/BehaviorControl/StrategyBehaviorControl/ActiveRoles/BallContestSupport.cpp" "BallContestSupport Implementation"
check_file "Src/Representations/BehaviorControl/BallContestStatus.h" "BallContestStatus Header"
check_file "Src/Representations/BehaviorControl/BallContestStatus.cpp" "BallContestStatus Implementation"
echo ""

echo "2. Checking configuration files..."
echo "2. 检查配置文件..."
check_file "Config/BallContestSupport.cfg" "Main Configuration"
check_file "Config/BallContestSupport_Enabled.cfg" "Enabled Configuration"
check_file "Config/BallContestSupport_Disabled.cfg" "Disabled Configuration"
check_file "Config/Debug/BallContestDebug.cfg" "Debug Configuration"
check_file "Config/settings_contest.cfg" "Contest Settings"
echo ""

echo "3. Checking scene files..."
echo "3. 检查场景文件..."
check_file "Config/Scenes/GameFast.ros3" "GameFast Scene"
check_file "Config/Scenes/GameFastContest.ros3" "GameFast Contest Scene"
check_file "Config/Scenes/GameFastBallContest.ros3" "Enhanced GameFast Scene"
check_file "Config/Scenes/BallContestTest.ros2" "Dedicated Test Scene"
check_file "Config/Scenes/ContestComparison.ros3" "Contest Comparison Scene"
echo ""

echo "4. Checking strategy and tactics..."
echo "4. 检查策略和战术..."
check_file "Config/Behavior/Strategies/s5v5_contest.cfg" "Contest Strategy"
check_file "Config/Behavior/Tactics/t211_contest.cfg" "Contest Tactics"
check_directory "Config/Behavior/Strategies" "Strategies Directory"
check_directory "Config/Behavior/Tactics" "Tactics Directory"
echo ""

echo "5. Checking build and test scripts..."
echo "5. 检查构建和测试脚本..."
check_file "build_ball_contest_support.sh" "Build Script"
check_file "run_gamefast_contest.sh" "GameFast Run Script"
check_file "run_contest_comparison.sh" "Contest Comparison Script"
check_file "run_gamefast_contest_comparison.sh" "GameFast Contest Comparison Script"
check_file "test_gamefast_contest.sh" "Test Script"
check_file "verify_contest_config.sh" "This Verification Script"
echo ""

echo "6. Checking documentation..."
echo "6. 检查文档..."
check_file "SimRobot_Testing_Guide.md" "Testing Guide"
check_file "GameFast_BallContest_Guide.md" "GameFast Integration Guide"
check_file "Contest_Comparison_Guide.md" "Contest Comparison Guide"
check_file "BallContestSupport_README.md" "README"
echo ""

echo "7. Checking for key content in configuration files..."
echo "7. 检查配置文件中的关键内容..."
check_content "Config/BallContestSupport.cfg" "BallContestProvider" "BallContestProvider section"
check_content "Config/BallContestSupport.cfg" "contestDetectionRadius" "Contest detection parameters"
check_content "Config/Debug/BallContestDebug.cfg" "enableDebugOutput" "Debug output settings"
check_content "Config/Behavior/Tactics/t211_contest.cfg" "ballContestSupport" "BallContestSupport role"
echo ""

echo "8. Checking build system integration..."
echo "8. 检查构建系统集成..."
if [ -d "Make" ]; then
    echo -e "${GREEN}✓${NC} Make directory exists"
    if [ -d "Make/Linux" ]; then
        echo -e "${GREEN}✓${NC} Linux build directory exists"
    else
        echo -e "${YELLOW}!${NC} Linux build directory not found"
    fi
else
    echo -e "${RED}✗${NC} Make directory not found"
fi
echo ""

echo "9. Permissions check..."
echo "9. 权限检查..."
for script in "build_ball_contest_support.sh" "run_gamefast_contest.sh" "run_contest_comparison.sh" "run_gamefast_contest_comparison.sh" "test_gamefast_contest.sh" "verify_contest_config.sh"; do
    if [ -f "$script" ]; then
        if [ -x "$script" ]; then
            echo -e "${GREEN}✓${NC} $script is executable"
        else
            echo -e "${YELLOW}!${NC} $script is not executable (run: chmod +x $script)"
        fi
    fi
done
echo ""

echo "=== Configuration Verification Complete ==="
echo "=== 配置验证完成 ==="
echo ""
echo "Next steps / 下一步:"
echo "1. If any files are missing, check the implementation"
echo "1. 如果有文件缺失，请检查实现"
echo "2. Run build script: ./build_ball_contest_support.sh"
echo "2. 运行构建脚本: ./build_ball_contest_support.sh"
echo "3. Test with: ./test_gamefast_contest.sh"
echo "3. 测试: ./test_gamefast_contest.sh"
echo "4. Start GameFast simulation: ./run_gamefast_contest.sh"
echo "4. 启动GameFast仿真: ./run_gamefast_contest.sh"
echo "5. Run comparison test: ./run_gamefast_contest_comparison.sh (RECOMMENDED)"
echo "5. 运行对照测试: ./run_gamefast_contest_comparison.sh (推荐)"