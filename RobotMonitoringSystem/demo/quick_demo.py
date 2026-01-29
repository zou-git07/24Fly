#!/usr/bin/env python3
"""
快速演示脚本 - 展示监控系统的核心功能
运行 5 秒，展示状态上报和事件检测
"""

import json
import time
import random
from datetime import datetime

def generate_robot_state(robot_id, timestamp, frame):
    """生成模拟的机器人状态"""
    return {
        "robot_id": robot_id,
        "timestamp": timestamp,
        "frame": frame,
        "battery": 100 - frame * 0.01,
        "temperature": 40 + random.uniform(-5, 15),
        "fallen": random.random() < 0.05,  # 5% 概率摔倒
        "behavior": random.choice(["stand", "walk", "searchForBall", "kick"]),
        "ball_visible": random.random() < 0.3,  # 30% 概率看到球
        "ball_x": random.uniform(-2000, 2000) if random.random() < 0.3 else 0,
        "ball_y": random.uniform(-1000, 1000) if random.random() < 0.3 else 0,
        "pos_x": random.uniform(-4500, 4500),
        "pos_y": random.uniform(-3000, 3000),
        "rotation": random.uniform(-3.14, 3.14)
    }

def main():
    print("=" * 60)
    print("机器人监控系统 - 快速演示")
    print("=" * 60)
    print()
    
    robots = ["1_1", "1_2", "1_3"]
    start_time = int(time.time() * 1000)
    
    print(f"✅ 模拟 {len(robots)} 个机器人")
    print(f"⏱️  运行 5 秒")
    print()
    
    for second in range(1, 6):
        print(f"--- 第 {second} 秒 ---")
        
        for robot_id in robots:
            frame = second
            timestamp = start_time + second * 1000
            state = generate_robot_state(robot_id, timestamp, frame)
            
            # 显示状态
            status_icon = "🔴" if state["fallen"] else "🟢"
            ball_icon = "⚽" if state["ball_visible"] else "❌"
            
            print(f"  {status_icon} Robot {robot_id}: "
                  f"电量 {state['battery']:.1f}%, "
                  f"温度 {state['temperature']:.1f}°C, "
                  f"行为 {state['behavior']}, "
                  f"球 {ball_icon}")
            
            # 检测事件
            if state["fallen"]:
                print(f"    ⚠️  事件: 机器人摔倒!")
            if state["ball_visible"] and second > 1:
                print(f"    🎯 事件: 发现球 at ({state['ball_x']:.0f}, {state['ball_y']:.0f})")
        
        print()
        time.sleep(1)
    
    print("=" * 60)
    print("✅ 演示完成!")
    print()
    print("📊 监控系统功能:")
    print("  ✓ 实时状态采集（电量、温度、姿态）")
    print("  ✓ 感知数据（球位置、定位）")
    print("  ✓ 行为状态（当前动作）")
    print("  ✓ 事件检测（摔倒、球发现）")
    print()
    print("📝 在真实系统中，这些数据会:")
    print("  1. 通过 UDP 发送到 Monitor Daemon")
    print("  2. 写入 JSON Lines 日志文件")
    print("  3. 通过 WebSocket 推送到 Web GUI")
    print("=" * 60)

if __name__ == "__main__":
    main()
