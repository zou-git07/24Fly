#!/usr/bin/env python3
"""
完整演示 - 包含日志写入和简单的 HTTP 服务器
"""

import json
import time
import random
from datetime import datetime
from pathlib import Path
import http.server
import socketserver
import threading

class RobotStateSimulator:
    """模拟机器人状态生成器"""
    
    def __init__(self, robot_id):
        self.robot_id = robot_id
        self.frame = 0
        self.battery = 100.0
        self.game_state = 1  # READY
        self.ball_visible = False
        self.role = "striker"
        self.last_ball_visible = False
        
    def generate_state(self):
        """生成一个状态快照"""
        self.frame += 1
        self.battery -= random.uniform(0.01, 0.05)
        
        # 模拟球的可见性变化
        if random.random() < 0.15:
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
                "motion_type": random.choice([0, 1])
            },
            "events": events
        }
        
        return state

class LogWriter:
    """日志写入器"""
    
    def __init__(self, log_dir):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.log_files = {}
        
    def write_state(self, robot_id, state):
        """写入状态到日志文件"""
        if robot_id not in self.log_files:
            log_file = self.log_dir / f"robot_{robot_id}.jsonl"
            self.log_files[robot_id] = open(log_file, 'w')
            
        json_line = json.dumps(state, ensure_ascii=False)
        self.log_files[robot_id].write(json_line + '\n')
        self.log_files[robot_id].flush()
        
    def close_all(self):
        """关闭所有日志文件"""
        for f in self.log_files.values():
            f.close()

def start_web_server(port=8080):
    """启动简单的 HTTP 服务器"""
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), Handler) as httpd:
        print(f"  🌐 Web 服务器启动: http://localhost:{port}")
        httpd.serve_forever()

def main():
    print("="*60)
    print("Nao 机器人监控系统 - 完整演示")
    print("="*60)
    print()
    
    # 创建日志目录
    match_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_dir = Path(f"RobotMonitoringSystem/demo/logs/match_{match_id}")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 日志目录: {log_dir}")
    print()
    
    # 创建日志写入器
    log_writer = LogWriter(log_dir)
    
    # 创建 3 个模拟机器人
    robots = [
        RobotStateSimulator("bhuman_1"),
        RobotStateSimulator("bhuman_2"),
        RobotStateSimulator("bhuman_3")
    ]
    
    print("✅ 已创建 3 个模拟机器人")
    print()
    
    # 模拟运行 15 秒
    print("🚀 开始模拟监控（15秒）...")
    print()
    
    event_count = 0
    
    for i in range(15):
        print(f"--- 第 {i+1} 秒 ---")
        
        for robot in robots:
            state = robot.generate_state()
            
            # 写入日志
            log_writer.write_state(state['robot_id'], state)
            
            # 显示关键信息
            quality_names = ['POOR', 'OKAY', 'SUPERB']
            quality = quality_names[state['perception']['localization']['quality']]
            
            print(f"  [{state['robot_id']}] "
                  f"电量: {state['system']['battery_charge']}%, "
                  f"温度: {state['system']['cpu_temperature']}°C, "
                  f"球: {'✅' if state['perception']['ball']['visible'] else '❌'}, "
                  f"定位: {quality}")
            
            # 显示事件
            for event in state['events']:
                print(f"    🔔 事件: {event['type']} - {event['description']}")
                event_count += 1
        
        print()
        time.sleep(1)
    
    # 关闭日志文件
    log_writer.close_all()
    
    print("="*60)
    print("✅ 演示完成！")
    print()
    print("📊 统计信息:")
    for robot in robots:
        print(f"  {robot.robot_id}: {robot.frame} 帧, "
              f"电量剩余 {robot.battery:.1f}%")
    print(f"  总事件数: {event_count}")
    print()
    print("📝 生成的日志文件:")
    for log_file in log_dir.glob("*.jsonl"):
        size = log_file.stat().st_size
        print(f"  {log_file.name} ({size} bytes)")
    print()
    print("💡 查看日志内容:")
    print(f"  cat {log_dir}/robot_bhuman_1.jsonl | head -3")
    print()
    print("="*60)

if __name__ == '__main__':
    main()
