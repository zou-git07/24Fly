#!/usr/bin/env python3
"""
简化演示版本 - 不依赖 protobuf 和 websockets
展示监控系统的核心工作流程
"""

import json
import time
import random
from datetime import datetime

class RobotStateSimulator:
    """模拟机器人状态生成器"""
    
    def __init__(self, robot_id):
        self.robot_id = robot_id
        self.frame = 0
        self.battery = 100.0
        self.game_state = 1  # READY
        self.ball_visible = False
        self.role = "striker"
        
    def generate_state(self):
        """生成一个状态快照"""
        self.frame += 1
        self.battery -= random.uniform(0.01, 0.05)
        
        # 模拟球的可见性变化
        if random.random() < 0.1:
            self.ball_visible = not self.ball_visible
            
        state = {
            "robot_id": self.robot_id,
            "system": {
                "timestamp_ms": int(time.time() * 1000),
                "frame_number": self.frame,
                "battery_charge": round(self.battery, 2),
                "cpu_temperature": round(random.uniform(45, 55), 1),
                "is_fallen": False
            },
            "perception": {
                "ball": {
                    "visible": self.ball_visible,
                    "pos_x": random.randint(-500, 500) if self.ball_visible else 0,
                    "pos_y": random.randint(-500, 500) if self.ball_visible else 0
                },
                "localization": {
                    "pos_x": random.randint(-1000, 1000),
                    "pos_y": random.randint(-1000, 1000),
                    "quality": random.choice([0, 1, 2])
                }
            },
            "decision": {
                "game_state": self.game_state,
                "role": self.role,
                "motion_type": random.choice([0, 1, 2])
            },
            "events": []
        }
        
        return state

def main():
    print("="*60)
    print("Nao 机器人监控系统 - 简化演示")
    print("="*60)
    print()
    
    # 创建 3 个模拟机器人
    robots = [
        RobotStateSimulator("bhuman_1"),
        RobotStateSimulator("bhuman_2"),
        RobotStateSimulator("bhuman_3")
    ]
    
    print("✅ 已创建 3 个模拟机器人")
    print()
    
    # 模拟运行 10 秒
    print("🚀 开始模拟监控...")
    print()
    
    for i in range(10):
        print(f"--- 第 {i+1} 秒 ---")
        
        for robot in robots:
            state = robot.generate_state()
            
            # 显示关键信息
            print(f"  [{state['robot_id']}] "
                  f"电量: {state['system']['battery_charge']}%, "
                  f"温度: {state['system']['cpu_temperature']}°C, "
                  f"球可见: {'✅' if state['perception']['ball']['visible'] else '❌'}")
            
            # 模拟日志写入
            if i == 0:
                print(f"    📝 创建日志文件: logs/robot_{state['robot_id']}.jsonl")
        
        print()
        time.sleep(1)
    
    print("="*60)
    print("✅ 演示完成！")
    print()
    print("📊 统计信息:")
    for robot in robots:
        print(f"  {robot.robot_id}: {robot.frame} 帧, "
              f"电量剩余 {robot.battery:.1f}%")
    print()
    print("💡 完整系统功能:")
    print("  - 实时 UDP 通信 (Protobuf)")
    print("  - WebSocket 实时推送")
    print("  - JSON Lines 日志记录")
    print("  - Web GUI 可视化")
    print("  - 赛后数据分析")
    print("="*60)

if __name__ == '__main__':
    main()
