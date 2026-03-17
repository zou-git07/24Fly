#!/bin/bash

# Ball Contest Support Build Script
# 争球支援策略编译脚本

echo "Building Ball Contest Support for BeHuman..."

# 检查是否在BeHuman项目根目录
if [ ! -d "Src" ] || [ ! -d "Config" ]; then
    echo "Error: Please run this script from BeHuman project root directory"
    exit 1
fi

# 创建必要的目录
echo "Creating directories..."
mkdir -p Src/Modules/BehaviorControl/BallContestProvider
mkdir -p Src/Representations/BehaviorControl

# 检查文件是否存在
echo "Checking implementation files..."
files=(
    "Src/Representations/BehaviorControl/BallContestStatus.h"
    "Src/Representations/BehaviorControl/BallContestStatus.cpp"
    "Src/Modules/BehaviorControl/BallContestProvider/BallContestProvider.h"
    "Src/Modules/BehaviorControl/BallContestProvider/BallContestProvider.cpp"
    "Src/Modules/BehaviorControl/StrategyBehaviorControl/ActiveRoles/BallContestSupport.h"
    "Src/Modules/BehaviorControl/StrategyBehaviorControl/ActiveRoles/BallContestSupport.cpp"
)

missing_files=()
for file in "${files[@]}"; do
    if [ ! -f "$file" ]; then
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -ne 0 ]; then
    echo "Error: Missing implementation files:"
    for file in "${missing_files[@]}"; do
        echo "  - $file"
    done
    exit 1
fi

echo "All implementation files found!"

# 检查修改的文件
echo "Checking modified files..."
modified_files=(
    "Src/Tools/BehaviorControl/Strategy/ActiveRole.h"
    "Src/Modules/BehaviorControl/StrategyBehaviorControl/Behavior.h"
    "Src/Modules/BehaviorControl/StrategyBehaviorControl/Behavior.cpp"
)

for file in "${modified_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "Warning: Modified file not found: $file"
    else
        echo "  ✓ $file"
    fi
done

# 编译项目 (假设使用标准BeHuman编译流程)
echo "Starting compilation..."
if [ -f "Make/Linux/generate" ]; then
    echo "Generating build files..."
    cd Make/Linux
    ./generate
    
    echo "Building project..."
    make -j$(nproc) Nao Release
    
    if [ $? -eq 0 ]; then
        echo "✓ Ball Contest Support compiled successfully!"
    else
        echo "✗ Compilation failed. Please check the error messages above."
        exit 1
    fi
else
    echo "Warning: BeHuman build system not found. Please compile manually."
fi

# 复制配置文件
echo "Installing configuration..."
if [ -f "Config/BallContestSupport.cfg" ]; then
    echo "  ✓ Configuration file ready"
else
    echo "  Warning: Configuration file not found"
fi

echo ""
echo "Ball Contest Support installation completed!"
echo ""
echo "Next steps:"
echo "1. Review and adjust parameters in Config/BallContestSupport.cfg"
echo "2. Test the implementation in simulation"
echo "3. Deploy to robots for field testing"
echo ""
echo "For more information, see BallContestSupport_README.md"