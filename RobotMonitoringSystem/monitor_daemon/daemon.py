#!/usr/bin/env python3
"""
监控守护进程主程序

功能：
1. 接收来自多个机器人的 UDP 状态数据
2. 解析 Protobuf 消息
3. 按 robot_id 分流并缓存
4. 异步写入日志文件
5. 提供 WebSocket 接口供 GUI 订阅
"""

import socket
import struct
import threading
import queue
import argparse
import sys
import time
from collections import defaultdict
from pathlib import Path

# 导入 Protobuf 生成的模块（需要先编译 .proto 文件）
try:
    from robot_state_pb2 import RobotState
except ImportError:
    print("Error: robot_state_pb2 module not found.")
    print("Please compile the .proto file first:")
    print("  protoc --python_out=. ../bhuman_integration/proto/robot_state.proto")
    sys.exit(1)

from log_writer import LogWriter
from websocket_server import WebSocketServer


class MonitorDaemon:
    """监控守护进程"""
    
    def __init__(self, port=10020, multicast_group='239.0.0.1', log_dir='logs', ws_port=8765):
        self.port = port
        self.multicast_group = multicast_group
        self.log_dir = Path(log_dir)
        self.ws_port = ws_port
        
        # 机器人状态缓存（robot_id -> queue）
        self.robot_states = defaultdict(lambda: queue.Queue(maxsize=1000))
        
        # 日志写入器
        self.log_writer = LogWriter(log_dir=self.log_dir)
        
        # WebSocket 服务器
        self.ws_server = WebSocketServer(port=ws_port, daemon=self)
        
        self.running = False
        self.stats = {
            'packets_received': 0,
            'packets_dropped': 0,
            'parse_errors': 0,
        }
        
    def start(self):
        """启动守护进程"""
        self.running = True
        
        # 创建 UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # 绑定到多播地址
        sock.bind(('', self.port))
        
        # 加入多播组
        mreq = struct.pack('4sl', socket.inet_aton(self.multicast_group), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        
        print(f"[MonitorDaemon] Listening on {self.multicast_group}:{self.port}")
        print(f"[MonitorDaemon] Log directory: {self.log_dir.absolute()}")
        print(f"[MonitorDaemon] WebSocket server on port {self.ws_port}")
        
        # 启动 WebSocket 服务器
        self.ws_server.start()
        
        # 启动接收线程
        receiver_thread = threading.Thread(target=self._receive_loop, args=(sock,), daemon=True)
        receiver_thread.start()
        
        # 启动统计输出线程
        stats_thread = threading.Thread(target=self._stats_loop, daemon=True)
        stats_thread.start()
        
        print("[MonitorDaemon] Started successfully")
        
    def _receive_loop(self, sock):
        """接收循环（独立线程）"""
        while self.running:
            try:
                data, addr = sock.recvfrom(65536)
                self.stats['packets_received'] += 1
                
                # 解析 Protobuf
                state = RobotState()
                try:
                    state.ParseFromString(data)
                except Exception as e:
                    self.stats['parse_errors'] += 1
                    print(f"[ERROR] Failed to parse protobuf: {e}")
                    continue
                
                robot_id = state.robot_id
                if not robot_id:
                    print("[WARNING] Received state without robot_id")
                    continue
                
                # 存入队列（限制队列长度，避免内存溢出）
                try:
                    if self.robot_states[robot_id].full():
                        self.robot_states[robot_id].get_nowait()  # 丢弃最旧的
                        self.stats['packets_dropped'] += 1
                    
                    self.robot_states[robot_id].put_nowait(state)
                except queue.Full:
                    self.stats['packets_dropped'] += 1
                
                # 写入日志
                self.log_writer.write_state(robot_id, state)
                
                # 广播到 WebSocket 客户端
                self.ws_server.broadcast_state(robot_id, state)
                
                # 打印事件
                for event in state.events:
                    event_type_name = RobotState.Event.EventType.Name(event.type)
                    print(f"[EVENT] [{robot_id}] {event_type_name}: {event.description}")
                    
            except Exception as e:
                print(f"[ERROR] Error in receive loop: {e}")
                
    def _stats_loop(self):
        """统计输出循环"""
        last_packets = 0
        while self.running:
            time.sleep(10)  # 每 10 秒输出一次
            
            packets = self.stats['packets_received']
            rate = (packets - last_packets) / 10.0
            last_packets = packets
            
            print(f"[STATS] Packets: {packets}, Rate: {rate:.1f}/s, "
                  f"Dropped: {self.stats['packets_dropped']}, "
                  f"Errors: {self.stats['parse_errors']}")
                
    def get_latest_state(self, robot_id):
        """获取指定机器人的最新状态"""
        if robot_id in self.robot_states and not self.robot_states[robot_id].empty():
            # 返回队列中最新的（不移除）
            return list(self.robot_states[robot_id].queue)[-1]
        return None
        
    def get_all_robot_ids(self):
        """获取所有活跃的机器人 ID"""
        return list(self.robot_states.keys())
        
    def stop(self):
        """停止守护进程"""
        print("[MonitorDaemon] Stopping...")
        self.running = False
        self.log_writer.close_all()
        self.ws_server.stop()
        print("[MonitorDaemon] Stopped")


def main():
    parser = argparse.ArgumentParser(description='Robot Monitoring Daemon')
    parser.add_argument('--port', type=int, default=10020, help='UDP port to listen on')
    parser.add_argument('--multicast', type=str, default='239.0.0.1', help='Multicast group address')
    parser.add_argument('--log-dir', type=str, default='logs', help='Log directory')
    parser.add_argument('--ws-port', type=int, default=8765, help='WebSocket server port')
    
    args = parser.parse_args()
    
    daemon = MonitorDaemon(
        port=args.port,
        multicast_group=args.multicast,
        log_dir=args.log_dir,
        ws_port=args.ws_port
    )
    
    daemon.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        daemon.stop()


if __name__ == '__main__':
    main()
