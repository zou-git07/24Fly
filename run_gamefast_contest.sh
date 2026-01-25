#!/bin/bash

# Run GameFast simulation with Ball Contest Support
# 运行带有争球支援功能的GameFast仿真

echo "Starting GameFast simulation with Ball Contest Support..."
echo "启动带有争球支援功能的GameFast仿真..."

# Set environment variables for Ball Contest Support
export BALL_CONTEST_SUPPORT=1
export BALL_CONTEST_DEBUG=1

# Change to Make/Linux directory
cd Make/Linux

# Start SimRobot with GameFast scene
echo "Loading GameFast.ros3 scene..."
echo "加载GameFast.ros3场景..."
./SimRobot ../../Config/Scenes/GameFast.ros3

echo "Simulation ended."
echo "仿真结束。"