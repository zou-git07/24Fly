#!/usr/bin/env python3
"""
监控守护进程主程序 - JSON 版本（用于 SimRobot）

功能：
1. 接收来自多个机器人的 UDP 状态数据（JSON 格式）
2. 按 robot_id 分流并缓存
3. 异步写入日志文件
4. 实时显示统计信息
"""

import socket
import json
import threading
import queue
import argparse
import sys
import time
from collections import defaultdict
from pathlib import Path
from datetime import datetime


class LogWriter:
    """简化的日志写入器"""
    
    def __init__(self, log_dir='logs'):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_match_dir = None
        self.log_files = {}
        self.lock = threading.Lock()
        
    def start_match(self):
        """开始新的比赛日志"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_match_dir = self.log_dir / f"match_{timestamp}"
        self.current_match_dir.mkdir(parents=True, exist_ok=True)
        print(f"[LogWriter] Started new match: {self.current_match_dir}")
        
    def write_state(self, robot_id, state_json):
        """写入机器人状态"""
        if not self.current_match_dir:
            self.start_match()
            
        with self.lock:
            if robot_id not in self.log_files:
                log_file = self.current_match_dir / f"robot_{robot_id}.jsonl"
                self.log_files[robot_id] = open(log_file, 'a')
                print(f"[LogWriter] Created log file: {log_file}")
            
            self.log_files[robot_id].write(state_json + '\n')
            self.log_files[robot_id].flush()
    
    def close(self):
        """关闭所有日志文件"""
        with self.lock:
            for f in self.log_files.values():
                f.close()
            self.log_files.clear()


class MonitorDaemon:
    """监控守护进程 - JSON 版本"""
    
    def __init__(self, port=10020, log_dir='logs'):
        self.port = port
        self.log_dir = Path(log_dir)
        
        # 统计信息
        self.stats = {
            'packets_received': 0,
            'packets_dropped': 0,
            'parse_errors': 0,
            'last_report_time': time.time()
        }
        
        # 日志写入器
        self.log_writer = LogWriter(log_dir=self.log_dir)
        
        # UDP socket
        self.sock = None
        self.running = False
        
    def start(self):
        """启动守护进程"""
        # 创建 UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # 绑定到所有接口
        self.sock.bind(('0.0.0.0', self.port))
        
        print(f"[MonitorDaemon] Listening on 0.0.0.0:{self.port}")
        print(f"[MonitorDaemon] Log directory: {self.log_dir.absolute()}")
        print(f"[MonitorDaemon] Started successfully")
        print()
        
        self.running = True
        
        # 启动统计线程
        stats_thread = threading.Thread(target=self._stats_reporter, daemon=True)
        stats_thread.start()
        
        # 主接收循环
        try:
            while self.running:
                try:
                    data, addr = self.sock.recvfrom(65536)
                    self._handle_packet(data, addr)
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"[ERROR] Failed to receive packet: {e}")
                    
        except KeyboardInterrupt:
            print("\n[MonitorDaemon] Shutting down...")
        finally:
            self.stop()
    
    def _handle_packet(self, data, addr):
        """处理接收到的数据包"""
        try:
            # 解析 JSON
            state_json = data.decode('utf-8')
            state = json.loads(state_json)
            
            # 提取 robot_id
            robot_id = state.get('robot_id', 'unknown')
            
            # 写入日志
            self.log_writer.write_state(robot_id, state_json)
            
            # 更新统计
            self.stats['packets_received'] += 1
            
            # 显示状态（每秒最多一次）
            if time.time() - self.stats.get('last_display', 0) > 1.0:
                self._display_state(robot_id, state)
                self.stats['last_display'] = time.time()
                
        except json.JSONDecodeError as e:
            self.stats['parse_errors'] += 1
            print(f"[ERROR] JSON parse error: {e}")
        except Exception as e:
            self.stats['parse_errors'] += 1
            print(f"[ERROR] Failed to handle packet: {e}")
    
    def _display_state(self, robot_id, state):
        """显示机器人状态"""
        timestamp = state.get('timestamp', 0)
        battery = state.get('battery', 0)
        fallen = state.get('fallen', False)
        ball_visible = state.get('ball_visible', False)
        behavior = state.get('behavior', 'unknown')
        
        status_icon = "🔴" if fallen else "🟢"
        ball_icon = "⚽" if ball_visible else "❌"
        
        print(f"  {status_icon} Robot {robot_id}: "
              f"t={timestamp}, "
              f"battery={battery:.1f}%, "
              f"behavior={behavior}, "
              f"ball={ball_icon}")
    
    def _stats_reporter(self):
        """定期报告统计信息"""
        while self.running:
            time.sleep(10)
            
            elapsed = time.time() - self.stats['last_report_time']
            rate = self.stats['packets_received'] / elapsed if elapsed > 0 else 0
            
            print(f"\n[STATS] Packets: {self.stats['packets_received']}, "
                  f"Rate: {rate:.1f}/s, "
                  f"Dropped: {self.stats['packets_dropped']}, "
                  f"Errors: {self.stats['parse_errors']}\n")
            
            # 重置计数器
            self.stats['packets_received'] = 0
            self.stats['last_report_time'] = time.time()
    
    def stop(self):
        """停止守护进程"""
        self.running = False
        if self.sock:
            self.sock.close()
        self.log_writer.close()
        print("[MonitorDaemon] Stopped")


def main():
    parser = argparse.ArgumentParser(description='Robot Monitoring Daemon (JSON version)')
    parser.add_argument('--port', type=int, default=10020, help='UDP port to listen on')
    parser.add_argument('--log-dir', type=str, default='logs', help='Directory for log files')
    
    args = parser.parse_args()
    
    daemon = MonitorDaemon(port=args.port, log_dir=args.log_dir)
    daemon.start()


if __name__ == '__main__':
    main()
