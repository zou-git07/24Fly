#!/usr/bin/env python3
"""
持续运行演示 - 模拟真实的监控系统
按 Ctrl+C 停止
"""

import json
import time
import random
from datetime import datetime
from pathlib import Path
import signal
import sys

class RobotStateSimulator:
    """模拟机器人状态生成器"""
    
    def __init__(self, robot_id):
        self.robot_id = robot_id
        self.frame = 0
        self.battery = 100.0
        self.game_state = 1  # READY
        self.ball_visible = False
        self.role = random.choice(["striker", "supporter", "defender"])
        self.last_ball_visible = False
        self.position_x = random.randint(-1000, 1000)
        self.position_y = random.randint(-1000, 1000)
        
    def generate_state(self):
        """生成一个状态快照"""
        self.frame += 1
        self.battery -= random.uniform(0.005, 0.02)
        
        # 模拟位置移动
        self.position_x += random.randint(-50, 50)
        self.position_y += random.randint(-50, 50)
        self.position_x = max(-4500, min(4500, self.position_x))
        self.position_y = max(-3000, min(3000, self.position_y))
        
        # 模拟球的可见性变化
        if random.random() < 0.08:
            self.ball_visible = not self.ball_visible
            
        # 检测事件
        events = []
        if self.ball_visible != self.last_ball_visible:
            event_type = "BALL_FOUND" if self.ball_visible else "BALL_LOST"
            events.append({
                "type": event_type,
                "description": f"Ball {'found' if self.ball_visible else 'lost'}",
                "timestamp_ms": int(time.time() * 1000)
            })
        self.last_ball_visible = self.ball_visible
            
        state = {
            "robot_id": self.robot_id,
            "system": {
                "timestamp_ms": int(time.time() * 1000),
                "frame_number": self.frame,
                "battery_charge": round(self.battery, 2),
                "cpu_temperature": round(random.uniform(45, 60), 1),
                "is_fallen": False
            },
            "perception": {
                "ball": {
                    "visible": self.ball_visible,
                    "pos_x": random.randint(-500, 500) if self.ball_visible else 0,
                    "pos_y": random.randint(-500, 500) if self.ball_visible else 0
                },
                "localization": {
                    "pos_x": self.position_x,
                    "pos_y": self.position_y,
                    "quality": random.choice([0, 1, 2])
                }
            },
            "decision": {
                "game_state": self.game_state,
                "role": self.role,
                "motion_type": random.choice([0, 1, 1, 1, 2])  # 更多 WALK
            },
            "events": events
        }
        
        return state

class LogWriter:
    """日志写入器"""
    
    def __init__(self, log_dir):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_files = {}
        
    def write_state(self, robot_id, state):
        """写入状态到日志文件"""
        if robot_id not in self.log_files:
            log_file = self.log_dir / f"robot_{robot_id}.jsonl"
            self.log_files[robot_id] = open(log_file, 'w')
            
        json_line = json.dumps(state, ensure_ascii=False)
        self.log_files[robot_id].write(json_line + '\n')
        
        # 每 10 条记录 flush 一次
        if state['system']['frame_number'] % 10 == 0:
            self.log_files[robot_id].flush()
        
    def close_all(self):
        """关闭所有日志文件"""
        for f in self.log_files.values():
            f.close()

class MonitoringSystem:
    """监控系统"""
    
    def __init__(self):
        self.running = True
        self.robots = []
        self.log_writer = None
        self.start_time = None
        self.total_events = 0
        
        # 注册信号处理
        signal.signal(signal.SIGINT, self.signal_handler)
        
    def signal_handler(self, sig, frame):
        """处理 Ctrl+C"""
        print("\n\n⚠️  收到停止信号，正在关闭系统...")
        self.running = False
        
    def start(self, num_robots=3):
        """启动监控系统"""
        print("="*70)
        print("🤖 Nao 机器人监控系统 - 持续运行演示")
        print("="*70)
        print()
        print("💡 提示：按 Ctrl+C 停止系统")
        print()
        
        # 创建日志目录
        match_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_dir = Path(f"RobotMonitoringSystem/demo/logs/match_{match_id}")
        
        print(f"📁 日志目录: {log_dir}")
        print()
        
        # 创建日志写入器
        self.log_writer = LogWriter(log_dir)
        
        # 创建机器人
        self.robots = [
            RobotStateSimulator(f"bhuman_{i+1}")
            for i in range(num_robots)
        ]
        
        print(f"✅ 已创建 {num_robots} 个模拟机器人")
        for robot in self.robots:
            print(f"   • {robot.robot_id} - 角色: {robot.role}")
        print()
        
        print("🚀 系统启动中...")
        print()
        
        self.start_time = time.time()
        self.run()
        
    def run(self):
        """主循环"""
        frame_count = 0
        last_summary_time = time.time()
        
        while self.running:
            frame_count += 1
            current_time = time.time()
            
            # 每秒显示一次状态
            if frame_count % 3 == 0:  # 3Hz 显示
                elapsed = int(current_time - self.start_time)
                print(f"⏱️  运行时间: {elapsed}秒 | 帧: {frame_count}")
                
                for robot in self.robots:
                    state = robot.generate_state()
                    
                    # 写入日志
                    self.log_writer.write_state(state['robot_id'], state)
                    
                    # 显示关键信息
                    quality_names = ['POOR', 'OKAY', 'SUPERB']
                    quality = quality_names[state['perception']['localization']['quality']]
                    motion_names = ['STAND', 'WALK', 'KICK']
                    motion = motion_names[state['decision']['motion_type']]
                    
                    ball_icon = '⚽✅' if state['perception']['ball']['visible'] else '⚽❌'
                    
                    print(f"  [{state['robot_id']}] "
                          f"🔋{state['system']['battery_charge']:.1f}% "
                          f"🌡️{state['system']['cpu_temperature']:.0f}°C "
                          f"{ball_icon} "
                          f"📍{quality} "
                          f"🏃{motion}")
                    
                    # 显示事件
                    for event in state['events']:
                        print(f"    🔔 {event['type']}: {event['description']}")
                        self.total_events += 1
                
                print()
            
            # 每 30 秒显示一次统计
            if current_time - last_summary_time >= 30:
                self.show_summary()
                last_summary_time = current_time
            
            # 控制频率 (3Hz)
            time.sleep(0.33)
        
        # 停止时显示最终统计
        self.shutdown()
        
    def show_summary(self):
        """显示统计摘要"""
        elapsed = int(time.time() - self.start_time)
        print("─" * 70)
        print(f"📊 统计摘要 (运行 {elapsed} 秒)")
        print("─" * 70)
        for robot in self.robots:
            print(f"  {robot.robot_id}: "
                  f"{robot.frame} 帧, "
                  f"电量 {robot.battery:.1f}%, "
                  f"位置 ({robot.position_x}, {robot.position_y})")
        print(f"  总事件数: {self.total_events}")
        print("─" * 70)
        print()
        
    def shutdown(self):
        """关闭系统"""
        print()
        print("="*70)
        print("🛑 系统正在关闭...")
        print("="*70)
        print()
        
        # 关闭日志文件
        self.log_writer.close_all()
        
        # 显示最终统计
        elapsed = int(time.time() - self.start_time)
        print(f"⏱️  总运行时间: {elapsed} 秒")
        print()
        print("📊 最终统计:")
        for robot in self.robots:
            print(f"  {robot.robot_id}: "
                  f"{robot.frame} 帧, "
                  f"电量剩余 {robot.battery:.1f}%")
        print(f"  总事件数: {self.total_events}")
        print()
        
        # 显示日志文件
        print("📝 生成的日志文件:")
        for log_file in self.log_writer.log_dir.glob("*.jsonl"):
            size = log_file.stat().st_size
            print(f"  {log_file.name} ({size:,} bytes)")
        print()
        
        print("✅ 系统已安全关闭")
        print("="*70)

def main():
    system = MonitoringSystem()
    system.start(num_robots=3)

if __name__ == '__main__':
    main()
