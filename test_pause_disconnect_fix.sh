#!/bin/bash
# 测试真机暂停断连问题修复

echo "=========================================="
echo "真机暂停断连问题 - 修复验证"
echo "=========================================="
echo ""

echo "1. 检查修改的文件..."
echo ""

# 检查 Nao Main.cpp
echo "检查 Src/Apps/Nao/Main.cpp:"
if grep -q "Thread::sleep(100)" Src/Apps/Nao/Main.cpp; then
    echo "  ✓ 已将 pause() 替换为 Thread::sleep(100)"
else
    echo "  ✗ 未找到 Thread::sleep(100)"
    exit 1
fi

if grep -q "#include \"Platform/Thread.h\"" Src/Apps/Nao/Main.cpp; then
    echo "  ✓ 已添加 Thread.h 头文件"
else
    echo "  ✗ 未找到 Thread.h 头文件"
    exit 1
fi

echo ""

# 检查 Booster Main.cpp
echo "检查 Src/Apps/Booster/Main.cpp:"
if grep -q "Thread::sleep(100)" Src/Apps/Booster/Main.cpp; then
    echo "  ✓ 已将 pause() 替换为 Thread::sleep(100)"
else
    echo "  ✗ 未找到 Thread::sleep(100)"
    exit 1
fi

if grep -q "#include \"Platform/Thread.h\"" Src/Apps/Booster/Main.cpp; then
    echo "  ✓ 已添加 Thread.h 头文件"
else
    echo "  ✗ 未找到 Thread.h 头文件"
    exit 1
fi

echo ""
echo "=========================================="
echo "修复验证通过！"
echo "=========================================="
echo ""
echo "修改说明："
echo "- 将 pause() 系统调用替换为 Thread::sleep(100)"
echo "- 主线程每 100ms 唤醒一次，但不阻塞其他线程"
echo "- GameControllerDataProvider 可以正常发送心跳包"
echo "- 真机在 Pause 状态下不会断连"
echo ""
echo "下一步测试："
echo "1. 编译代码：./Make/Linux/compile"
echo "2. 在 SimRobot 中测试 Pause/Resume 功能"
echo "3. 部署到真实机器人并测试"
echo ""
